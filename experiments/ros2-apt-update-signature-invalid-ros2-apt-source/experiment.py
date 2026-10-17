#!/usr/bin/env python3
"""ros2-apt-source가 바꾸는 것과 키 만료일 연장 때 사람 손이 필요한 횟수를 오프라인으로 잰다.

1부: 이미지에 설치된 ros2-apt-source가 소유한 파일, 내장 키와 키링 파일의 지문·만료일.
2부: 옛 형식 ros2.list를 추가했을 때 apt가 sources를 읽는지(종료 코드, E: 줄).
3부: file: 저장소 + 수명이 짧은 자체 키로 "같은 키 ID, 만료일만 연장"을 두 번 재현하고,
     수동 키 복사(A)와 키링 패키지(B) 기계에서 사람이 손댄 횟수를 apt 결과로 센다.
모든 숫자는 실행 중에 측정한다. 실제 packages.ros.org와 실제 ROS 서명은 쓰지 않는다.
"""
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

T0 = time.monotonic()
WORK = Path("/tmp/exp")
GNUPG = WORK / "gnupg"
REPO = WORK / "repo"
ENV = dict(os.environ, GNUPGHOME=str(GNUPG), LC_ALL="C")
GPG = ["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase", ""]


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False, separators=(",", ":")), flush=True)


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=30, **kw)
    return p.returncode, p.stdout + p.stderr


def key_info(path):
    home = WORK / "showkeys"
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    rc, out = run(["gpg", "--homedir", str(home), "--show-keys", "--with-colons", str(path)])
    pub = next((l.split(":") for l in out.splitlines() if l.startswith("pub:")), None)
    fpr = next((l.split(":")[9] for l in out.splitlines() if l.startswith("fpr:")), "")
    if pub is None:
        return {"rc": rc, "fpr": ""}
    created, expires = int(pub[5]), int(pub[6] or 0)
    return {"fpr": fpr, "keyid": fpr[-16:],
            "created_utc": time.strftime("%Y-%m-%d", time.gmtime(created)),
            "expires_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(expires)) if expires else None,
            "expires_epoch": expires}


# ---------------------------------------------------------------- 1부
def part1():
    rc, out = run(["dpkg-query", "-W", "-f=${Version}", "ros2-apt-source"])
    version = out.strip()
    _, listing = run(["dpkg", "-L", "ros2-apt-source"])
    owned = [p for p in listing.split() if Path(p).is_symlink() or Path(p).is_file()]
    link = "/etc/apt/sources.list.d/ros2.sources"
    emit(part=1, item="package", version=version, owned_files=owned, owned_file_count=len(owned),
         sources_link=os.readlink(link) if os.path.islink(link) else None)
    # Signed-By 블록(deb822 연속 줄, " ."은 빈 줄)을 꺼내 키링 파일과 비교한다.
    text = Path("/usr/share/ros-apt-source/ros2.sources").read_text()
    block, inside = [], False
    for line in text.splitlines():
        if line.startswith("Signed-By:"):
            inside, rest = True, line.split(":", 1)[1].strip()
            if rest:
                block.append(rest)
            continue
        if inside:
            if not line.startswith(" "):
                break
            s = line.strip()
            block.append("" if s == "." else s)
    embedded = WORK / "embedded.asc"
    embedded.write_text("\n".join(block) + "\n")
    e = key_info(embedded)
    k = key_info("/usr/share/keyrings/ros2-archive-keyring.gpg")
    now = int(time.time())
    emit(part=1, item="keys", embedded=e, keyring=k, signed_by_is_inline_key=block[:1] == ["-----BEGIN PGP PUBLIC KEY BLOCK-----"],
         same_fingerprint=e["fpr"] == k["fpr"] and bool(e["fpr"]),
         same_expiry=e.get("expires_epoch") == k.get("expires_epoch"),
         days_until_expiry=round((e.get("expires_epoch", 0) - now) / 86400, 1))


# ---------------------------------------------------------------- 2부
OLD_LINE = "deb [arch=amd64 signed-by={key}] http://packages.ros.org/ros2/ubuntu noble main\n"


def part2():
    lst = Path("/etc/apt/sources.list.d/ros2.list")
    cases = [("baseline_package_only", None),
             ("old_list_old_keyring_path", OLD_LINE.format(key="/usr/share/keyrings/ros-archive-keyring.gpg")),
             ("old_list_new_keyring_path", OLD_LINE.format(key="/usr/share/keyrings/ros2-archive-keyring.gpg")),
             ("old_list_no_signed_by", "deb http://packages.ros.org/ros2/ubuntu noble main\n"),
             ("old_list_removed", None)]
    for name, content in cases:
        if content is None:
            lst.unlink(missing_ok=True)
        else:
            lst.write_text(content)
        started = time.monotonic()
        rc, out = run(["apt-cache", "policy"])
        errors = [l[:200] for l in out.splitlines() if l.startswith(("E:", "W:"))]
        owner_rc = run(["dpkg", "-S", str(lst)])[0] if lst.exists() else None
        emit(part=2, case=name, apt_cache_policy_rc=rc, error_lines=errors,
             ros2_list_owned_by_package=(owner_rc == 0) if owner_rc is not None else None,
             seconds=round(time.monotonic() - started, 3))
    # 충돌 상태에서 무관한 Ubuntu 저장소까지 막히는지: apt-get update도 sources 단계에서 멈추는지 본다.
    lst.write_text(OLD_LINE.format(key="/usr/share/keyrings/ros-archive-keyring.gpg"))
    started = time.monotonic()
    rc, out = run(["apt-get", "update"])
    emit(part=2, case="apt_get_update_with_old_list", rc=rc,
         error_lines=[l[:200] for l in out.splitlines() if l.startswith("E:")],
         network_fetch_attempted=any(l.startswith(("Ign:", "Err:", "Get:", "Hit:")) for l in out.splitlines()),
         seconds=round(time.monotonic() - started, 3))
    lst.unlink(missing_ok=True)


# ---------------------------------------------------------------- 3부
FPR = ""
SEQ = [0]
CURRENT = [0]   # 지금 저장소가 배포 중인 공개 키의 만료 시각


def gpg(*args):
    rc, out = run(GPG + list(args))
    if rc != 0:
        raise RuntimeError(f"gpg {args[:2]} rc={rc}: {out[-300:]}")
    return out


def export_pub(dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["gpg", "--export", FPR], capture_output=True, env=ENV, check=True)
    dest.write_bytes(p.stdout)


def build_keyring_deb(version):
    root = WORK / f"pkg-{version}"
    export_pub(root / "usr/share/keyrings/huntlab-archive-keyring.gpg")
    (root / "DEBIAN").mkdir(parents=True, exist_ok=True)
    (root / "DEBIAN/control").write_text(
        f"Package: huntlab-apt-source\nVersion: {version}\nArchitecture: all\n"
        "Maintainer: HuntLab <test@example.invalid>\nDescription: test keyring package\n")
    pool = REPO / "pool"
    pool.mkdir(parents=True, exist_ok=True)
    deb = pool / f"huntlab-apt-source_{version}_all.deb"
    rc, out = run(["dpkg-deb", "--root-owner-group", "-Zgzip", "--build", str(root), str(deb)])
    if rc != 0:
        raise RuntimeError(out)
    return deb


def publish(debs):
    """Packages/Release를 다시 쓰고 현재 키로 InRelease에 서명한다(실제 저장소의 주기적 재서명)."""
    SEQ[0] += 1
    stanzas = []
    for deb in debs:
        data = deb.read_bytes()
        _, control = run(["dpkg-deb", "-f", str(deb)])
        stanzas.append(control.strip() + f"\nFilename: pool/{deb.name}\nSize: {len(data)}\n"
                       f"SHA256: {hashlib.sha256(data).hexdigest()}\n")
    pkgdir = REPO / "dists/noble/main/binary-amd64"
    pkgdir.mkdir(parents=True, exist_ok=True)
    packages = ("\n".join(stanzas)).encode()
    (pkgdir / "Packages").write_bytes(packages)
    release = REPO / "dists/noble/Release"
    release.write_text(
        "Origin: HuntLab\nLabel: HuntLab\nSuite: noble\nCodename: noble\n"
        f"Date: {time.strftime('%a, %d %b %Y %H:%M:%S UTC', time.gmtime())}\n"
        f"X-Sequence: {SEQ[0]}\nArchitectures: amd64\nComponents: main\nSHA256:\n"
        f" {hashlib.sha256(packages).hexdigest()} {len(packages)} main/binary-amd64/Packages\n")
    gpg("--local-user", FPR, "--clearsign", "-o", str(REPO / "dists/noble/InRelease"), str(release))


class Machine:
    def __init__(self, name, mode, misses):
        self.name, self.mode, self.misses = name, mode, set(misses)
        self.dir = WORK / "machines" / name
        for sub in ("lists/partial", "cache/archives/partial", "parts", "dl", "root"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        (self.dir / "status").write_text("")
        self.human_actions = 0
        if mode == "A":   # 사람이 curl로 받아 둔 키 사본
            self.keyring = self.dir / "manual-keyring.gpg"
        else:             # 패키지가 소유한 키링
            self.keyring = self.dir / "root/usr/share/keyrings/huntlab-archive-keyring.gpg"
        (self.dir / "parts/huntlab.sources").write_text(
            f"Types: deb\nURIs: file:{REPO}\nSuites: noble\nComponents: main\nSigned-By: {self.keyring}\n")

    def apt(self, *args):
        opts = ["-o", f"Dir::Etc::sourcelist={self.dir}/none.list", "-o", f"Dir::Etc::sourceparts={self.dir}/parts",
                "-o", f"Dir::State::lists={self.dir}/lists", "-o", f"Dir::Cache={self.dir}/cache",
                "-o", f"Dir::State::status={self.dir}/status", "-o", "APT::Sandbox::User=root",
                "-o", "Debug::NoLocking=1", "-o", "Dir::Etc::preferencesparts=/nonexistent"]
        return run([args[0]] + opts + list(args[1:]), cwd=self.dir / "dl")

    def update(self):
        rc, out = self.apt("apt-get", "update")
        tags = [t for t in ("EXPKEYSIG", "NO_PUBKEY", "is not signed", "BADSIG") if t in out]
        return rc, tags, out

    def candidate(self):
        _, out = self.apt("apt-cache", "policy", "huntlab-apt-source")
        line = next((l for l in out.splitlines() if "Candidate:" in l), "")
        return line.split(":", 1)[1].strip() if line else "(not found)"

    def package_upgrade(self):
        """apt upgrade 대용: 검증된 색인으로 최신 키링 패키지를 받아 파일을 풀어 놓는다."""
        rc, out = self.apt("apt-get", "download", "huntlab-apt-source")
        debs = sorted((self.dir / "dl").glob("huntlab-apt-source_*.deb"))
        if rc != 0 or not debs:
            return rc
        newest = max(debs, key=lambda p: p.stat().st_mtime)
        rc2, _ = run(["dpkg-deb", "-x", str(newest), str(self.dir / "root")])
        return rc2

    def manual_copy(self, count=True):
        export_pub(self.keyring)
        self.human_actions += 1 if count else 0

    def keyring_current(self):
        return self.keyring.is_file() and key_info(self.keyring).get("expires_epoch") == CURRENT[0]


def part3():
    global FPR
    GNUPG.mkdir(parents=True, mode=0o700)
    t_start = time.time()
    gpg("--quick-gen-key", "HuntLab Test Repo <test@example.invalid>", "ed25519", "sign", "seconds=6")
    out = run(["gpg", "--list-keys", "--with-colons"])[1]
    FPR = next(l.split(":")[9] for l in out.splitlines() if l.startswith("fpr:"))
    debs = [build_keyring_deb("1")]
    publish(debs)
    snap = WORK / "pub-v1.gpg"
    export_pub(snap)
    emit(part=3, item="key_v1", keyid=FPR[-16:], lifetime_s=key_info(snap)["expires_epoch"] - int(t_start))

    # n=4 기계 × 방식 2개. misses = 만료 전 갱신 창을 놓치는 변경 번호.
    schedule = [("on1", []), ("on2", []), ("miss1", [1]), ("missall", [1, 2])]
    machines = [Machine(f"{mode}-{name}", mode, miss) for mode in "AB" for name, miss in schedule]
    CURRENT[0] = key_info(snap)["expires_epoch"]
    for m in machines:   # 최초 설정: A는 이미 손으로 받아 둔 키(세지 않음), B는 패키지 이전(1회)
        if m.mode == "A":
            m.manual_copy(count=False)
        else:   # 공식 문서의 dpkg -i 단계 대용: 받은 .deb의 파일을 그대로 풀어 놓는다
            run(["dpkg-deb", "-x", str(debs[0]), str(m.dir / "root")])
            m.human_actions += 1
        rc, tags, _ = m.update()
        assert rc == 0, (m.name, tags)
    emit(part=3, item="initial_setup", all_update_rc0=True, machines=len(machines))

    # 오래 꺼 둔 기계(=Docker 캐시에 옛 키가 남은 이미지)와 색인 유무 비교용
    fresh = Machine("C-fresh-old-key", "A", [])
    shutil.copy(snap, fresh.keyring)

    samples = {}
    for change in (1, 2):
        old_deadline = key_info(snap)["expires_epoch"]
        extend = 10 if change == 1 else 40
        gpg("--quick-set-expire", FPR, f"seconds={extend + max(0, old_deadline - int(time.time()))}")
        debs.append(build_keyring_deb(str(change + 1)))
        publish(debs)
        snap = WORK / f"pub-v{change + 1}.gpg"
        export_pub(snap)
        info = key_info(snap)
        CURRENT[0] = info["expires_epoch"]
        emit(part=3, item="change_published", change=change, repo_latest=str(change + 1),
             same_keyid=info["keyid"] == FPR[-16:], new_minus_old_expiry_s=info["expires_epoch"] - old_deadline,
             seconds_before_old_expiry=old_deadline - int(time.time()))
        # 만료 전 갱신 창: 켜져 있는 기계만 행동한다. B는 사람 없이 update+패키지 갱신.
        window = {}
        for m in machines:
            if change in m.misses:
                continue
            if m.mode == "A":
                m.manual_copy()
            else:
                rc, tags, _ = m.update()
                urc = m.package_upgrade()
                window[m.name] = {"update_rc": rc, "pkg_rc": urc, "keyring_current": m.keyring_current()}
        emit(part=3, item="window_auto_B", change=change, machines=window)
        while time.time() < old_deadline + 1.5:
            time.sleep(0.2)
        publish(debs)   # 저장소는 만료 뒤에도 계속 재서명된다
        for m in machines + ([fresh] if change == 1 else []):
            had_lists = any((m.dir / "lists").glob("*InRelease"))
            rc, tags, out = m.update()
            failed = rc != 0 or bool(tags)
            row = dict(part=3, item="after_expiry", change=change, m=m.name, lists=had_lists,
                       rc=rc, sig=tags, cand=m.candidate())
            kind = "with_lists" if had_lists else "fresh"
            if failed and kind not in samples:
                samples[kind] = [l.replace(str(WORK), "<tmp>")[:140] for l in out.splitlines()
                                 if l.startswith(("E:", "W:", "Err:"))][:5]
            if failed and m is not fresh:
                # 복구: 사람이 새 공개 키를 받아 같은 경로에 둔다(curl ... ros.key 대응)
                m.manual_copy()
                rc2, tags2, _ = m.update()
                row.update(fix_rc=rc2, fix_sig=tags2)
                if m.mode == "B":
                    m.package_upgrade()
                row.update(fix_cand=m.candidate())
            emit(**row)
    for kind, lines in samples.items():
        emit(part=3, item="sample_failure_output", kind=kind, lines=lines)

    n, k = len(schedule), 2
    for mode in "AB":
        group = [m for m in machines if m.mode == mode]
        m_missed = sum(len(m.misses) for m in group)
        emit(part=3, item="human_actions", mode=mode, n=n, k=k, missed_pairs=m_missed,
             measured_total=sum(m.human_actions for m in group),
             per_machine={m.name: m.human_actions for m in group},
             model=n * k if mode == "A" else n + m_missed)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    for name, fn in (("part1", part1), ("part2", part2), ("part3", part3)):
        started = time.monotonic()
        fn()
        emit(stage=name, seconds=round(time.monotonic() - started, 2))
    emit(stage="total", seconds=round(time.monotonic() - T0, 2))
