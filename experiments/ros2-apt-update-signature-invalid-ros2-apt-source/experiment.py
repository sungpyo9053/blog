#!/usr/bin/env python3
"""ROS 2 저장소 키 만료와 ros2-apt-source 전달 경로를 오프라인 컨테이너에서 실제로 잰다.

1부(image): ros:jazzy-ros-base 이미지에 실제로 깔린 ROS 키·소스 파일을 읽어 지문·만료일을 잰다.
2부(conflict): 예전 ros2.list와 새 ros2.sources가 함께 있을 때 apt 2.8.x가 실제로 내는 결과를 잰다.
3부(lab): 실험용 키로 file: 저장소에 서명하고, 같은 키의 만료일만 늘리는 사건을 k번 일으킨다.
   방식 A(기계마다 키 파일 수동 관리)와 방식 B(키·소스를 담은 설정 패키지)를 기계 n대로 비교해
   사람이 손을 대야 했던 횟수를 apt-get update의 실제 서명 검사 결과로 센다.
모든 수치는 실행 중에 측정하며 각 결과를 JSON 한 줄로 출력한다.
"""
from __future__ import annotations

import base64
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

T0 = time.monotonic()
N_MACHINES = 3        # 방식마다 기계 수 n
K_EVENTS = 2          # 같은 키의 만료일 연장 사건 수 k
FIRST_WINDOW = 9.0   # 키 생성 후 첫 만료까지(초): 준비 작업과 1회차 사전 갱신을 덮는 시간
GAP = 9.0            # 다음 만료까지 간격(초)
LAB = Path("/tmp/lab")
REPO = LAB / "repo"
GNUPG = LAB / "gnupg"
UID = "HuntLab Lab Repo <lab@example.invalid>"


def emit(record: dict) -> None:
    record["t"] = round(time.monotonic() - T0, 3)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- OpenPGP 정적 파싱(표준 라이브러리)
def _packets(data: bytes):
    i = 0
    while i < len(data):
        hdr = data[i]
        i += 1
        if hdr & 0x40:
            tag = hdr & 0x3F
            first = data[i]
            i += 1
            if first < 192:
                length = first
            elif first < 224:
                length = ((first - 192) << 8) + data[i] + 192
                i += 1
            elif first == 255:
                length = struct.unpack(">I", data[i:i + 4])[0]
                i += 4
            else:
                raise ValueError("partial body length not supported")
        else:
            tag = (hdr >> 2) & 0x0F
            size = {0: 1, 1: 2, 2: 4}.get(hdr & 3)
            if size is None:
                length = len(data) - i
            else:
                length = int.from_bytes(data[i:i + size], "big")
                i += size
        yield tag, data[i:i + length]
        i += length


def _subpackets(blob: bytes) -> dict:
    out, i = {}, 0
    while i < len(blob):
        first = blob[i]
        if first < 192:
            length, i = first, i + 1
        elif first < 255:
            length, i = ((first - 192) << 8) + blob[i + 1] + 192, i + 2
        else:
            length, i = struct.unpack(">I", blob[i + 1:i + 5])[0], i + 5
        kind, body = blob[i] & 0x7F, blob[i + 1:i + length]
        out.setdefault(kind, body)
        i += length
    return out


def parse_key(data: bytes) -> dict:
    """주 키 지문, 긴 키 ID, 생성 시각, 가장 최근 자기서명이 정한 만료 시각."""
    if data.lstrip().startswith(b"-----BEGIN"):
        data = dearmor(data.decode())
    primary, created, sigs, in_primary = None, None, [], True
    for tag, body in _packets(data):
        if tag == 6 and primary is None and body[0] == 4:
            created = struct.unpack(">I", body[1:5])[0]
            primary = hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body).hexdigest().upper()
        elif tag == 14:
            in_primary = False
        elif tag == 2 and in_primary and body[0] == 4 and (0x10 <= body[1] <= 0x13 or body[1] == 0x1F):
            hashed_len = struct.unpack(">H", body[4:6])[0]
            sub = _subpackets(body[6:6 + hashed_len])
            if 2 in sub:
                sigs.append((struct.unpack(">I", sub[2])[0],
                             struct.unpack(">I", sub[9])[0] if 9 in sub else 0))
    sig_time, offset = max(sigs) if sigs else (None, 0)
    return {"fingerprint": primary, "long_key_id": primary[-16:] if primary else None,
            "key_created": iso(created), "selfsig_created": iso(sig_time),
            "expires_epoch": created + offset if offset else None,
            "expires": iso(created + offset) if offset else None}


def dearmor(text: str) -> bytes:
    lines, body, started, headers_done = text.splitlines(), [], False, False
    for line in lines:
        line = line.strip()
        if line.startswith("-----BEGIN PGP PUBLIC KEY BLOCK"):
            started = True
            continue
        if not started:
            continue
        if line.startswith("-----END"):
            break
        if not headers_done:
            if line == "" or ":" not in line:
                headers_done = True
                if line == "":
                    continue
            else:
                continue
        if line.startswith("=") and len(line) == 5:
            continue
        body.append(line)
    return base64.b64decode("".join(body))


def deb822_field(text: str, name: str) -> str | None:
    lines, value, grab = text.splitlines(), [], False
    for line in lines:
        if grab:
            if line[:1] in (" ", "\t"):
                value.append("" if line.strip() == "." else line[1:])
                continue
            break
        if line.lower().startswith(name.lower() + ":"):
            grab = True
            value.append(line.split(":", 1)[1].strip())
    return "\n".join(value).strip() if grab else None


def gpg_show(path: str) -> dict:
    home = LAB / "show-home"
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    res = run(["gpg", "--homedir", str(home), "--batch", "--with-colons", "--show-keys", path])
    fpr, expires = None, None
    for line in res.stdout.splitlines():
        f = line.split(":")
        if f[0] == "pub":
            expires = iso(int(f[6])) if f[6] else None
        if f[0] == "fpr" and fpr is None:
            fpr = f[9]
    return {"gpg_fingerprint": fpr, "gpg_expires": expires, "gpg_exit": res.returncode}


# ---------------------------------------------------------------- 1부: 이미지 안의 실제 ROS 키
def part_image() -> dict:
    ver = run(["dpkg-query", "-W", "-f", "${Version}", "ros2-apt-source"])
    entries = []
    for p in sorted(glob.glob("/etc/apt/sources.list.d/*ros*")):
        entries.append({"path": p, "is_symlink": os.path.islink(p),
                        "target": os.readlink(p) if os.path.islink(p) else None,
                        "owner": (run(["dpkg", "-S", p]).stdout.split(":")[0] or None)})
    keyring = "/usr/share/keyrings/ros2-archive-keyring.gpg"
    key = parse_key(Path(keyring).read_bytes())
    key.update(gpg_show(keyring))
    sources = Path("/etc/apt/sources.list.d/ros2.sources").read_text()
    embedded = parse_key(deb822_field(sources, "Signed-By").encode())
    embedded = {"fingerprint": embedded["fingerprint"], "expires": embedded["expires"]}
    now = time.time()
    old_style = [p for p in ("/usr/share/keyrings/ros-archive-keyring.gpg", "/etc/apt/sources.list.d/ros2.list",
                             "/etc/apt/sources.list.d/ros2-latest.list") if os.path.exists(p)]
    grep_r = run(["grep", "-rl", "packages.ros.org", "/etc/apt/sources.list.d/"])
    grep_R = run(["grep", "-Rl", "packages.ros.org", "/etc/apt/sources.list.d/"])
    out = {"part": "image", "ros2_apt_source_version": ver.stdout or None,
           "sources_list_d": entries, "keyring": keyring, "keyring_bytes": os.path.getsize(keyring),
           "keyring_key": key, "embedded_signed_by_key": embedded,
           "embedded_equals_keyring_fingerprint": embedded["fingerprint"] == key["fingerprint"],
           "measured_at": iso(now),
           "days_until_expiry": round((key["expires_epoch"] - now) / 86400, 1) if key["expires_epoch"] else None,
           "old_style_files_present": old_style,
           "uris": deb822_field(sources, "URIs"), "suites": deb822_field(sources, "Suites"),
           "types": deb822_field(sources, "Types"),
           "grep_r": {"exit": grep_r.returncode, "matches": grep_r.stdout.split()},
           "grep_R": {"exit": grep_R.returncode, "matches": grep_R.stdout.split()}}
    out["keyring_key"].pop("expires_epoch", None)
    out["keyring_key"].pop("gpg_exit", None)
    return out


# ---------------------------------------------------------------- 공통 apt 호출(격리된 디렉터리)
def apt_opts(root: Path) -> list[str]:
    return ["-o", f"Dir::Etc::SourceList={root}/etc/apt/sources.list",
            "-o", f"Dir::Etc::SourceParts={root}/etc/apt/sources.list.d",
            "-o", f"Dir::State={root}/var/lib/apt", "-o", f"Dir::Cache={root}/var/cache/apt",
            "-o", f"Dir::State::status={root}/var/lib/dpkg/status",
            "-o", f"Dir::Etc::Trusted={root}/etc/apt/trusted.gpg",
            "-o", f"Dir::Etc::TrustedParts={root}/etc/apt/trusted.gpg.d",
            "-o", "APT::Sandbox::User=root", "-o", "Acquire::Languages=none"]


def make_root(root: Path) -> Path:
    for d in ("etc/apt/sources.list.d", "etc/apt/trusted.gpg.d", "var/lib/apt/lists/partial",
              "var/cache/apt/archives/partial", "var/lib/dpkg/info", "var/lib/dpkg/updates",
              "var/lib/dpkg/triggers", "usr/share/keyrings"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "var/lib/dpkg/status").touch()
    (root / "var/lib/dpkg/available").touch()
    return root


def classify(text: str) -> dict:
    exp = re.findall(r"EXPKEYSIG ([0-9A-F]{16})", text)
    return {"expkeysig_ids": sorted(set(exp)),
            "no_pubkey": bool(re.search(r"NO_PUBKEY", text)),
            "signature_invalid_line": "signatures were invalid" in text,
            "previous_index_used": "previous index files will be used" in text,
            "not_signed": "is not signed" in text,
            "conflicting_signed_by": "Conflicting values set for option Signed-By" in text,
            "w_lines": sum(1 for l in text.splitlines() if l.startswith("W:")),
            "e_lines": sum(1 for l in text.splitlines() if l.startswith("E:"))}


def apt_update(root: Path) -> dict:
    start = time.monotonic()
    res = run(["apt-get", "-q", *apt_opts(root), "update"])
    text = res.stdout + res.stderr
    info = classify(text)
    info.update({"exit": res.returncode, "seconds": round(time.monotonic() - start, 3)})
    info["signature_ok"] = (res.returncode == 0 and not info["expkeysig_ids"] and not info["no_pubkey"]
                            and not info["not_signed"] and "GPG error" not in text)
    lines = [l for l in text.splitlines() if l.startswith(("W:", "E:"))]
    key = [l for l in lines if "EXPKEYSIG" in l or "not signed" in l or "NO_PUBKEY" in l]
    info["first_message"] = (key or lines or [""])[0][:170] or None
    for drop in ("no_pubkey", "signature_invalid_line", "conflicting_signed_by"):
        info.pop(drop)
    return info


# ---------------------------------------------------------------- 2부: 예전 파일과 새 패키지 공존
def part_conflict() -> list[dict]:
    real_sources = Path("/etc/apt/sources.list.d/ros2.sources").read_text()
    pkg_keyring = "/usr/share/keyrings/ros2-archive-keyring.gpg"
    base = LAB / "conflict"
    copied = base / "ros-archive-keyring.gpg"
    base.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pkg_keyring, copied)
    old_line = ("deb [arch=amd64 signed-by={key}] http://packages.ros.org/ros2/ubuntu noble main\n")
    cases = {
        "new_only": {"ros2.sources": real_sources},
        "old_only": {"ros2.list": old_line.format(key=copied)},
        "old_plus_new": {"ros2.sources": real_sources, "ros2.list": old_line.format(key=copied)},
        "old_pointing_package_keyring_plus_new": {"ros2.sources": real_sources,
                                                  "ros2.list": old_line.format(key=pkg_keyring)},
        "old_duplicated_same_key": {"ros2.list": old_line.format(key=copied),
                                    "ros2-latest.list": old_line.format(key=copied)},
    }
    out = []
    for name, files in cases.items():
        root = make_root(base / name)
        for fname, content in files.items():
            (root / "etc/apt/sources.list.d" / fname).write_text(content)
        res = run(["apt-cache", *apt_opts(root), "policy"])
        text = res.stdout + res.stderr
        info = classify(text)
        rec = {"part": "conflict", "case": name, "files": sorted(files), "apt_cache_policy_exit": res.returncode,
               "conflicting_signed_by": info["conflicting_signed_by"],
               "configured_multiple_times": "configured multiple times" in text,
               "first_message": next((l[:200] for l in text.splitlines() if l.startswith(("W:", "E:"))), None)}
        out.append(rec)
        emit(rec)
    return out


# ---------------------------------------------------------------- 3부: 실험용 저장소와 기계 n대
def gpg(*args: str) -> subprocess.CompletedProcess:
    res = run(["gpg", "--homedir", str(GNUPG), "--batch", "--yes", "--pinentry-mode", "loopback",
               "--passphrase", "", *args])
    if res.returncode != 0:
        raise RuntimeError(f"gpg {args[:2]} failed: {res.stderr[-400:]}")
    return res


def export_key(fpr: str, armor: bool = False) -> bytes:
    res = subprocess.run(["gpg", "--homedir", str(GNUPG), "--batch", "--export", *(["--armor"] if armor else []), fpr],
                         capture_output=True)
    return res.stdout


def build_config_package(version: str, fpr: str) -> Path:
    stage = LAB / "build" / version
    shutil.rmtree(stage, ignore_errors=True)
    (stage / "DEBIAN").mkdir(parents=True)
    (stage / "usr/share/keyrings").mkdir(parents=True)
    (stage / "usr/share/lab-apt-source").mkdir(parents=True)
    (stage / "etc/apt/sources.list.d").mkdir(parents=True)
    (stage / "DEBIAN/control").write_text(
        f"Package: lab-apt-source\nVersion: {version}\nArchitecture: all\n"
        "Maintainer: HuntLab Experiment <lab@example.invalid>\n"
        "Description: lab repository key and apt source (ros2-apt-source style)\n")
    (stage / "usr/share/keyrings/lab2-archive-keyring.gpg").write_bytes(export_key(fpr))
    armored = export_key(fpr, armor=True).decode().strip().splitlines()
    block = "\n".join(" " + (l if l.strip() else ".") for l in armored)
    (stage / "usr/share/lab-apt-source/lab.sources").write_text(
        f"Types: deb\nURIs: file:{REPO}\nSuites: stable\nComponents: main\nArchitectures: amd64\n"
        f"Signed-By:\n{block}\n")
    # ros2-apt-source처럼 /etc 쪽은 심볼릭 링크. 기계 루트 안에서 풀리도록 상대 경로를 쓴다.
    os.symlink("../../../usr/share/lab-apt-source/lab.sources", stage / "etc/apt/sources.list.d/lab.sources")
    pool = REPO / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    deb = pool / f"lab-apt-source_{version}_all.deb"
    res = run(["dpkg-deb", "--root-owner-group", "-Zgzip", "--build", str(stage), str(deb)])
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    return deb


def publish_repo(fpr: str) -> None:
    """Packages·Release를 만들고 현재 서명 키로 InRelease를 다시 서명한다(실제 저장소의 주기적 재서명)."""
    stanzas = []
    for deb in sorted((REPO / "pool").glob("*.deb")):
        control = run(["dpkg-deb", "-f", str(deb)]).stdout.strip()
        data = deb.read_bytes()
        stanzas.append(f"{control}\nFilename: pool/{deb.name}\nSize: {len(data)}\n"
                       f"SHA256: {hashlib.sha256(data).hexdigest()}\n")
    pkgdir = REPO / "dists/stable/main/binary-amd64"
    pkgdir.mkdir(parents=True, exist_ok=True)
    packages = ("\n".join(stanzas)).encode()
    (pkgdir / "Packages").write_bytes(packages)
    date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")
    release = (f"Origin: HuntLab Lab\nLabel: HuntLab Lab\nSuite: stable\nCodename: stable\nDate: {date}\n"
               f"Architectures: amd64\nComponents: main\nSHA256:\n"
               f" {hashlib.sha256(packages).hexdigest()} {len(packages)} main/binary-amd64/Packages\n")
    (REPO / "dists/stable/Release").write_text(release)
    gpg("--local-user", fpr, "--digest-algo", "SHA256", "--clearsign",
        "-o", str(REPO / "dists/stable/InRelease"), str(REPO / "dists/stable/Release"))
    (REPO / "lab.key").write_bytes(export_key(fpr))  # 예전 방식이 손으로 다시 받는 'ros.key' 역할


def set_expiry(fpr: str, absolute: float) -> dict:
    gpg("--quick-set-expire", fpr, f"seconds={max(1, int(round(absolute - time.time())))}")
    return parse_key(export_key(fpr))


def dpkg_install(root: Path, deb: Path) -> int:
    return run(["dpkg", f"--root={root}", "--force-script-chrootless", "-i", str(deb)]).returncode


def installed_version(root: Path) -> str | None:
    res = run(["dpkg-query", f"--admindir={root}/var/lib/dpkg", "-W", "-f", "${Version}", "lab-apt-source"])
    return (res.stdout or None) if res.returncode == 0 else None


def auto_upgrade(root: Path) -> dict:
    """사람 없이 도는 'apt update && apt upgrade' 대역: 서명 검사된 색인에서 새 버전을 받아 설치한다."""
    upd = apt_update(root)
    pol = run(["apt-cache", *apt_opts(root), "policy", "lab-apt-source"]).stdout
    cand = re.search(r"Candidate:\s*(\S+)", pol)
    candidate = cand.group(1) if cand else None
    before = installed_version(root)
    upgraded = False
    if candidate and candidate != "(none)" and candidate != before:
        dl_dir = root / "dl"
        dl_dir.mkdir(exist_ok=True)
        dl = run(["apt-get", "-q", *apt_opts(root), "download", "lab-apt-source"], cwd=dl_dir)
        debs = sorted(dl_dir.glob(f"lab-apt-source_{candidate}_all.deb"))
        if dl.returncode == 0 and debs and dpkg_install(root, debs[-1]) == 0:
            upgraded = True
    return {"update_signature_ok": upd["signature_ok"], "candidate": candidate, "before": before,
            "after": installed_version(root), "upgraded": upgraded}


def machine_key(root: Path, method: str) -> dict:
    if method == "A":
        return parse_key((root / "usr/share/keyrings/lab-archive-keyring.gpg").read_bytes())
    text = (root / "etc/apt/sources.list.d/lab.sources").read_text()  # 심볼릭 링크를 따라 읽는다
    return parse_key(deb822_field(text, "Signed-By").encode())


def part_lab() -> dict:
    GNUPG.mkdir(parents=True, mode=0o700)
    start = time.monotonic()
    gpg("--quick-gen-key", UID, "ed25519", "sign", f"seconds={int(FIRST_WINDOW)}")
    fpr = run(["gpg", "--homedir", str(GNUPG), "--batch", "--with-colons", "--list-keys"]).stdout
    fpr = [l.split(":")[9] for l in fpr.splitlines() if l.startswith("fpr")][0]
    versions = [parse_key(export_key(fpr))]
    expiry = [versions[0]["expires_epoch"]]
    deb_v = [build_config_package("1.0", fpr)]
    publish_repo(fpr)
    emit({"part": "lab_key", "event": 0, "key": {k: v for k, v in versions[0].items() if k != "expires_epoch"},
          "keygen_and_publish_seconds": round(time.monotonic() - start, 3)})

    machines, manual = [], {"A": 0, "B": 0, "B_offline": 0}
    old_list = f"deb [arch=amd64 signed-by={{root}}/usr/share/keyrings/lab-archive-keyring.gpg] file:{REPO} stable main\n"
    specs = [("A", f"A{i}", None) for i in range(1, N_MACHINES + 1)] + \
            [("B", f"B{i}", None) for i in range(1, N_MACHINES + 1)] + [("B_offline", "B_off", 1)]
    setup = {}
    for group, name, offline_event in specs:
        root = make_root(LAB / "m" / name)
        # 모든 기계는 예전 수동 방식(키 파일 + 한 줄 .list)으로 이미 설정돼 있다고 놓는다.
        (root / "usr/share/keyrings/lab-archive-keyring.gpg").write_bytes(export_key(fpr))
        (root / "etc/apt/sources.list.d/lab.list").write_text(old_list.format(root=root))
        first = apt_update(root)
        g = setup.setdefault(group, {"machines": 0, "initial_update_ok": 0})
        g["machines"] += 1
        g["initial_update_ok"] += first["signature_ok"]
        if group != "A":
            # 이전 작업 1회(사람): 예전 파일 정리 → 설정 패키지 설치 → apt update 확인
            (root / "etc/apt/sources.list.d/lab.list").unlink()
            (root / "usr/share/keyrings/lab-archive-keyring.gpg").unlink()
            rc = dpkg_install(root, deb_v[0])
            check = apt_update(root)
            manual[group] += 1
            g["migration_dpkg_ok"] = g.get("migration_dpkg_ok", 0) + (rc == 0)
            g["after_migration_update_ok"] = g.get("after_migration_update_ok", 0) + check["signature_ok"]
            g["installed"] = installed_version(root)
            g["sources_symlink"] = os.readlink(root / "etc/apt/sources.list.d/lab.sources")
            g["old_list_files_left"] = g.get("old_list_files_left", 0) + len(
                list((root / "etc/apt/sources.list.d").glob("*.list")))
        machines.append({"group": group, "name": name, "root": root, "offline_event": offline_event,
                         "method": "A" if group == "A" else "B"})
    emit({"part": "lab_setup", "groups": setup,
          "seconds_left_before_first_expiry": round(expiry[0] - time.time(), 2)})

    for event in range(1, K_EVENTS + 1):
        current_exp = expiry[-1]
        # --- 만료 전: 저장소 운영자가 같은 키의 만료일을 늘리고 새 설정 패키지를 올린다.
        new_key = set_expiry(fpr, current_exp + GAP)
        versions.append(new_key)
        expiry.append(new_key["expires_epoch"])
        deb_v.append(build_config_package(f"1.{event}", fpr))
        publish_repo(fpr)
        pre = {"tried": 0, "upgraded": 0, "update_signature_ok": 0, "skipped_offline": [], "versions_after": []}
        for m in machines:
            if m["method"] != "B":
                continue
            if m["offline_event"] == event:
                pre["skipped_offline"].append(m["name"])
                continue
            r = auto_upgrade(m["root"])
            pre["tried"] += 1
            pre["upgraded"] += r["upgraded"]
            pre["update_signature_ok"] += r["update_signature_ok"]
            pre["versions_after"].append(r["after"])
        pre["versions_after"] = sorted(set(pre["versions_after"]))
        margin = round(current_exp - time.time(), 2)
        emit({"part": "lab_pre_expiry", "event": event,
              "same_fingerprint": new_key["fingerprint"] == versions[0]["fingerprint"],
              "old_expires": versions[-2]["expires"], "new_expires": new_key["expires"],
              "package_version_published": f"1.{event}", "auto_upgrade": pre,
              "seconds_left_before_old_expiry": margin, "timing_ok": margin > 0})
        # --- 예전 만료 시각이 실제로 지나갈 때까지 기다린 뒤 저장소를 다시 서명한다.
        wait = current_exp + 1.5 - time.time()
        if wait > 0:
            time.sleep(wait)
        publish_repo(fpr)
        if event == 1:
            # 예전 키를 품은 채 처음 apt update를 하는 기계(예: 오래된 캐시로 만든 이미지)
            fresh = make_root(LAB / "m" / "A_fresh")
            (fresh / "usr/share/keyrings/lab-archive-keyring.gpg").write_bytes(
                (LAB / "m" / "A1" / "usr/share/keyrings/lab-archive-keyring.gpg").read_bytes())
            (fresh / "etc/apt/sources.list.d/lab.list").write_text(old_list.format(root=fresh))
            r = apt_update(fresh)
            r.pop("seconds")
            emit({"part": "lab_fresh_machine_old_key", "event": event, **r})
        groups = {}
        for m in machines:
            root = m["root"]
            r = apt_update(root)
            g = groups.setdefault(m["group"], {"machines": 0, "update_exit_codes": [], "signature_ok": 0,
                                               "expkeysig": 0, "previous_index_used": 0, "manual_fixes": 0,
                                               "after_fix_ok": 0, "key_expires_on_machines": set()})
            g["machines"] += 1
            g["update_exit_codes"].append(r["exit"])
            g["signature_ok"] += r["signature_ok"]
            g["expkeysig"] += bool(r["expkeysig_ids"])
            g["previous_index_used"] += r["previous_index_used"]
            g["key_expires_on_machines"].add(machine_key(root, m["method"])["expires"])
            if r["expkeysig_ids"]:
                g["expkeysig_id"] = r["expkeysig_ids"][0]
                if m["group"] == "A":
                    g.setdefault("first_message", r["first_message"])
            if not r["signature_ok"]:
                if m["method"] == "B":
                    heal = auto_upgrade(root)
                    g["self_heal_upgraded"] = g.get("self_heal_upgraded", 0) + heal["upgraded"]
                    g["self_heal_candidate"] = heal["candidate"]
                # 사람이 하는 복구 1회: A는 공개키를 다시 받아 덮어쓰고, B는 최신 .deb를 직접 받아 설치한다.
                if m["method"] == "A":
                    (root / "usr/share/keyrings/lab-archive-keyring.gpg").write_bytes((REPO / "lab.key").read_bytes())
                else:
                    dpkg_install(root, deb_v[-1])
                manual[m["group"]] += 1
                g["manual_fixes"] += 1
                g["after_fix_ok"] += apt_update(root)["signature_ok"]
            g.setdefault("fingerprints", set()).add(machine_key(root, m["method"])["fingerprint"])
        for g in groups.values():
            g["key_expires_on_machines"] = sorted(g["key_expires_on_machines"])
            g["distinct_fingerprints"] = len(g.pop("fingerprints"))
        emit({"part": "lab_post_expiry", "event": event, "old_key_expired": time.time() > current_exp,
              "groups": groups})

    fprs = {v["fingerprint"] for v in versions}
    return {"part": "lab_summary", "n_per_method": N_MACHINES, "k_events": K_EVENTS,
            "manual_actions_measured": manual,
            "model_prediction": {"A": N_MACHINES * K_EVENTS, "B": N_MACHINES, "B_offline": 1 + 1},
            "key_versions": [{"selfsig_created": v["selfsig_created"], "expires": v["expires"]} for v in versions],
            "distinct_fingerprints": len(fprs), "lab_long_key_id": versions[0]["long_key_id"],
            "lab_seconds": round(time.monotonic() - start, 2)}


def main() -> int:
    LAB.mkdir(parents=True, exist_ok=True)
    env = {"apt": run(["apt-get", "--version"]).stdout.splitlines()[0],
           "gpg": run(["gpg", "--version"]).stdout.splitlines()[0],
           "dpkg": run(["dpkg", "--version"]).stdout.splitlines()[0]}
    emit({"part": "env", **env, "ros_distro": os.environ.get("ROS_DISTRO")})
    emit(part_image())
    part_conflict()
    summary = part_lab()
    run(["gpgconf", "--homedir", str(GNUPG), "--kill", "all"])
    summary["total_seconds"] = round(time.monotonic() - T0, 2)
    emit(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
