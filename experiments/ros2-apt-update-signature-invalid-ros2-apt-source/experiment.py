#!/usr/bin/env python3
"""ros2-apt-source가 바꾸는 것: 키·저장소 설정의 관리 주체와 사람 손이 가는 횟수.

1부(실제 이미지): ros:jazzy-ros-base에 설치된 ros2-apt-source가 어떤 파일을 소유하는지,
ros2.sources 안의 키 ID와 만료일, 옛 ros2.list를 남겼을 때 apt가 보이는 출력을 네트워크
없이 apt-cache policy로 확인한다.

2부(로컬 서명 저장소): 짧게 만료되는 키로 서명한 file: 저장소를 만들고 기계 여러 대의
apt 설정을 /tmp 아래에 따로 둔다. 키 만료일을 k번 연장하면서 수동 방식(A: 손으로 만든
.list + 키 파일)과 패키지 방식(B: 키를 담은 .deb가 sources를 소유)이 apt update를 다시
통과하려면 사람이 몇 번 손대야 하는지 실제 apt/gpgv 판정으로 센다.
모든 수치는 실행 중에 측정해 JSON 줄로 출력한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path

N_MACHINES = 6          # 방식마다 기계 대수 n
K_CHANGES = 2           # 키 만료일 연장(저장소 키 변경) 횟수 k
SAFETY = 2.0            # 만료 시각을 잡을 때 측정 소요 시간에 곱하는 여유 배수
ROOT = Path("/tmp/aptlab")
GNUPG = ROOT / "gnupg"
REPO = ROOT / "repo"
RELEASES = ROOT / "releases"   # GitHub 릴리스 .deb에 해당하는 저장소 밖 배포 위치
SUITE = "noble"
PKG = "huntlab-apt-source"
T0 = time.monotonic()


def emit(kind: str, **data) -> None:
    print(json.dumps({"kind": kind, "t": round(time.monotonic() - T0, 2), **data}, ensure_ascii=False), flush=True)


def run(cmd, text=True, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=text, **kw)


def must(cmd, **kw) -> subprocess.CompletedProcess:
    p = run(cmd, **kw)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd[:3]} rc={p.returncode}: {str(p.stdout + p.stderr)[-800:]}")
    return p


def iso(ts: int | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def key_info(path: Path) -> dict:
    out = must(["gpg", "--homedir", str(ROOT / "showkeys"), "--batch", "--show-keys", "--with-colons",
                str(path)]).stdout
    info = {}
    for line in out.splitlines():
        f = line.split(":")
        if f[0] == "pub" and "keyid" not in info:
            info.update(keyid=f[4], created=int(f[5]), expires=int(f[6]) if f[6] else None)
        elif f[0] == "fpr" and "fingerprint" not in info:
            info["fingerprint"] = f[9]
    return info


def apt_flags(p: subprocess.CompletedProcess) -> dict:
    text = p.stdout + p.stderr
    return {"rc": p.returncode, "EXPKEYSIG": "EXPKEYSIG" in text, "NO_PUBKEY": "NO_PUBKEY" in text,
            "not_signed": "is not signed" in text,
            "signed_by_conflict": "Conflicting values set for option Signed-By" in text,
            "sources_unreadable": "list of sources could not be read" in text,
            "previous_index_used": "previous index files will be used" in text,
            "signature_problem": any(s in text for s in ("EXPKEYSIG", "NO_PUBKEY", "is not signed")),
            "error_lines": [l.strip() for l in text.splitlines() if l.startswith(("E:", "W:"))][:4]}


# ---------------------------------------------------------------- 1부: 실제 이미지
def inspect_real_image() -> None:
    version = run(["dpkg-query", "-W", "-f=${Version}", "ros2-apt-source"]).stdout
    owned = [l for l in run(["dpkg", "-L", "ros2-apt-source"]).stdout.splitlines()
             if Path(l).is_file() or Path(l).is_symlink()]
    link = Path("/etc/apt/sources.list.d/ros2.sources")
    sources = link.read_text()
    block = sources[sources.index("-----BEGIN"):sources.index("-----END")]
    block = block + "-----END PGP PUBLIC KEY BLOCK-----\n"
    lines = [l[1:] if l.startswith(" ") else l for l in block.splitlines()]
    inline = ROOT / "inline-key.asc"
    inline.write_text("\n".join("" if l == "." else l for l in lines) + "\n")
    inline_key = key_info(inline)
    ring_key = key_info(Path("/usr/share/keyrings/ros2-archive-keyring.gpg"))
    field = lambda name: next((l.split(":", 1)[1].strip() for l in sources.splitlines()
                               if l.startswith(name + ":")), None)
    other_ros_entries = [p.name for p in Path("/etc/apt/sources.list.d").iterdir()
                         if p.name != "ros2.sources" and "packages.ros.org" in p.read_text()]
    emit("real_image_package", ros2_apt_source_version=version, owned_files=owned,
         sources_symlink=str(link), symlink_target=os.readlink(link), types=field("Types"),
         uris=field("URIs"), suites=field("Suites"), signed_by_inline_key=bool(lines),
         other_files_pointing_to_packages_ros_org=other_ros_entries)
    emit("real_image_key", inline_keyid=inline_key["keyid"], inline_fingerprint=inline_key["fingerprint"],
         inline_created=iso(inline_key["created"]), inline_expires=iso(inline_key["expires"]),
         keyring_keyid=ring_key["keyid"], keyring_expires=iso(ring_key["expires"]),
         same_fingerprint=inline_key["fingerprint"] == ring_key["fingerprint"],
         days_until_expiry_from_run=round((inline_key["expires"] - time.time()) / 86400, 1))

    old = Path("/etc/apt/sources.list.d/ros2.list")
    variants = {
        "baseline_no_old_list": None,
        "old_tutorial_keyring_path": "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] "
                                     f"http://packages.ros.org/ros2/ubuntu {SUITE} main\n",
        "old_list_pointing_to_package_keyring": "deb [arch=amd64 signed-by=/usr/share/keyrings/"
                                                f"ros2-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu {SUITE} main\n",
        "old_apt_key_style_no_signed_by": f"deb http://packages.ros.org/ros2/ubuntu {SUITE} main\n",
    }
    for name, line in variants.items():
        if line:
            old.write_text(line)
        p = run(["apt-cache", "policy"])
        emit("real_image_conflict", variant=name, **apt_flags(p))
        old.unlink(missing_ok=True)
    emit("real_image_conflict", variant="after_removing_old_list", **apt_flags(run(["apt-cache", "policy"])))


# ---------------------------------------------------------------- 2부: 로컬 저장소
def gpg(*args) -> str:
    return must(["gpg", "--homedir", str(GNUPG), "--batch", "--yes", "--pinentry-mode", "loopback",
                 "--passphrase", "", *args]).stdout


class Maintainer:
    """저장소 운영자: 키를 만들고 만료일을 늘리고, 저장소와 키 패키지를 배포한다."""

    def __init__(self, expires_at: float):
        gpg("--quick-gen-key", "HuntLab apt lab <lab@example.invalid>", "ed25519", "sign",
            f"seconds={int(expires_at - time.time()) + 1}")
        self.fpr = next(l.split(":")[9] for l in gpg("--list-keys", "--with-colons").splitlines()
                        if l.startswith("fpr"))
        self.versions: list[str] = []
        self.publish_key()

    def publish_key(self) -> None:
        """현재 공개 키를 rosdistro ros.key처럼 외부 위치에 둔다(사람이 curl로 받는 파일)."""
        self.binary_key = ROOT / "published" / "lab.gpg"
        self.binary_key.parent.mkdir(parents=True, exist_ok=True)
        if self.binary_key.exists():   # 연장 전 공개 키: 새로 설치하는 기계가 옛 튜토리얼 캐시로 받는 파일
            shutil.copy(self.binary_key, ROOT / "published" / "lab-previous.gpg")
        self.binary_key.write_bytes(must(["gpg", "--homedir", str(GNUPG), "--export", self.fpr],
                                         text=False).stdout)
        self.armored = gpg("--armor", "--export", self.fpr)
        self.info = key_info(self.binary_key)

    def extend(self, expires_at: float) -> None:
        gpg("--quick-set-expire", self.fpr, f"seconds={int(expires_at - time.time()) + 1}")
        self.publish_key()

    def build_package(self, version: str) -> Path:
        tree = ROOT / "build" / version
        shutil.rmtree(tree, ignore_errors=True)
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / "DEBIAN" / "control").write_text(
            f"Package: {PKG}\nVersion: {version}\nArchitecture: all\nMaintainer: HuntLab <lab@example.invalid>\n"
            "Description: test source and key configuration for a local apt repository\n")
        share = tree / "usr/share" / PKG
        share.mkdir(parents=True)
        key_lines = "\n".join(" " + (l if l else ".") for l in self.armored.strip().splitlines())
        (share / "lab.sources").write_text(
            f"Types: deb\nURIs: file:{REPO}\nSuites: {SUITE}\nComponents: main\nSigned-By:\n{key_lines}\n")
        keyrings = tree / "usr/share/keyrings"
        keyrings.mkdir(parents=True)
        shutil.copy(self.binary_key, keyrings / "huntlab-lab-archive-keyring.gpg")
        parts = tree / "etc/apt/sources.list.d"
        parts.mkdir(parents=True)
        (parts / "lab.sources").symlink_to(f"../../../usr/share/{PKG}/lab.sources")
        RELEASES.mkdir(parents=True, exist_ok=True)
        deb = RELEASES / f"{PKG}_{version}_all.deb"
        must(["dpkg-deb", "-Zgzip", "--root-owner-group", "--build", str(tree), str(deb)])
        self.versions.append(version)
        return deb

    def publish_repo(self) -> None:
        pool = REPO / "pool"
        index = REPO / "dists" / SUITE / "main" / "binary-amd64"
        pool.mkdir(parents=True, exist_ok=True)
        index.mkdir(parents=True, exist_ok=True)
        stanzas = []
        for version in self.versions:
            name = f"{PKG}_{version}_all.deb"
            data = (RELEASES / name).read_bytes()
            (pool / name).write_bytes(data)
            stanzas.append(f"Package: {PKG}\nVersion: {version}\nArchitecture: all\n"
                           f"Maintainer: HuntLab <lab@example.invalid>\nFilename: pool/{name}\n"
                           f"Size: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n"
                           "Description: test source and key configuration for a local apt repository\n")
        packages = "\n".join(stanzas).encode()
        (index / "Packages").write_bytes(packages)
        release = (f"Origin: HuntLab\nLabel: HuntLab apt lab\nSuite: {SUITE}\nCodename: {SUITE}\n"
                   f"Date: {formatdate(usegmt=True)}\nArchitectures: amd64 all\nComponents: main\nSHA256:\n"
                   f" {hashlib.sha256(packages).hexdigest()} {len(packages)} main/binary-amd64/Packages\n")
        (REPO / "dists" / SUITE / "Release").write_text(release)
        gpg("--local-user", self.fpr, "--clearsign", "-o", str(REPO / "dists" / SUITE / "InRelease"),
            str(REPO / "dists" / SUITE / "Release"))


class Machine:
    def __init__(self, name: str, mode: str):
        self.name, self.mode, self.manual = name, mode, 0
        self.root = ROOT / "m" / name
        for d in ("etc/apt/sources.list.d", "state/lists/partial", "cache/archives/partial",
                  "var/lib/dpkg/updates", "var/lib/dpkg/info", "keys", "dl"):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        (self.root / "etc/apt/sources.list").write_text("")
        (self.root / "var/lib/dpkg/status").write_text("")
        self.keyring = self.root / "keys/lab-archive-keyring.gpg"
        self.old_list = self.root / "etc/apt/sources.list.d/lab.list"

    def apt(self, *args, cwd=None, tool="apt-get") -> subprocess.CompletedProcess:
        r = self.root
        return run([tool, "-q", "-o", f"Dir::Etc::SourceList={r}/etc/apt/sources.list",
                    "-o", f"Dir::Etc::SourceParts={r}/etc/apt/sources.list.d",
                    "-o", f"Dir::Etc::Trusted={ROOT}/empty/trusted.gpg",
                    "-o", f"Dir::Etc::TrustedParts={ROOT}/empty/trusted.gpg.d",
                    "-o", f"Dir::State={r}/state", "-o", f"Dir::State::status={r}/var/lib/dpkg/status",
                    "-o", f"Dir::Cache={r}/cache", "-o", "APT::Sandbox::User=root",
                    "-o", "Debug::NoLocking=1", "-o", "Acquire::Languages=none", *args], cwd=cwd)

    def update(self) -> dict:
        return apt_flags(self.apt("update"))

    def candidate(self) -> str:
        """apt가 지금 아는 최신 패키지 버전(인덱스가 갱신됐는지 보는 지표)."""
        p = self.apt("policy", PKG, tool="apt-cache")
        return next((l.split(":", 1)[1].strip() for l in p.stdout.splitlines()
                     if l.strip().startswith("Candidate:")), "unknown")

    def dpkg_install(self, deb: Path) -> None:
        must(["dpkg", f"--root={self.root}", "--force-script-chrootless", "--force-bad-path", "-i", str(deb)])

    def installed(self) -> str:
        return run(["dpkg-query", f"--admindir={self.root}/var/lib/dpkg", "-W", "-f=${Version}", PKG]).stdout

    def manual_setup(self, maint: Maintainer) -> None:
        """옛 튜토리얼 방식: 사람이 키 파일을 받고 한 줄짜리 .list를 쓴다(초기 설정, 세지 않음)."""
        shutil.copy(maint.binary_key, self.keyring)
        self.old_list.write_text(f"deb [signed-by={self.keyring}] file:{REPO} {SUITE} main\n")

    def manual_key_refresh(self, maint: Maintainer) -> None:
        """방식 A의 사람 작업 1회: 갱신된 공개 키를 다시 받아 같은 경로에 덮어쓴다."""
        shutil.copy(maint.binary_key, self.keyring)
        self.manual += 1

    def auto_upgrade(self) -> dict:
        """방식 B의 무인 작업: apt update → 저장소에서 새 키 패키지 받기 → 설치(사람 작업 아님)."""
        res = self.update()
        before = self.installed()
        for f in (self.root / "dl").glob("*.deb"):
            f.unlink()
        dl = self.apt("download", PKG, cwd=self.root / "dl")
        debs = sorted((self.root / "dl").glob("*.deb"))
        if res["rc"] == 0 and dl.returncode == 0 and debs:
            self.dpkg_install(debs[-1])
        return {"update_rc": res["rc"], "download_rc": dl.returncode, "before": before, "after": self.installed()}


def simulate() -> None:
    for d in ("empty/trusted.gpg.d", "showkeys"):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    GNUPG.mkdir(mode=0o700, parents=True, exist_ok=True)
    (ROOT / "showkeys").chmod(0o700)

    # 첫 만료 시각은 설정·이행·첫 연장 배포를 마칠 시간을 잰 뒤 정할 수 없으므로 넉넉히 둔다.
    first_window = 10.0
    maint = Maintainer(time.time() + first_window)
    key0 = dict(maint.info)
    deb = maint.build_package("1.0")
    maint.publish_repo()

    a = [Machine(f"A{i}", "manual") for i in range(1, N_MACHINES + 1)]
    b = [Machine(f"B{i}", "package") for i in range(1, N_MACHINES + 1)]
    offline = Machine("B_offline", "package_offline")
    machines = a + b + [offline]
    started = time.monotonic()
    for m in machines:
        m.manual_setup(maint)
    baseline = [m.update()["rc"] for m in machines]
    per_update = (time.monotonic() - started) / len(machines)
    emit("setup", machines=len(machines), baseline_update_rc=sorted(set(baseline)),
         key_id=key0["keyid"], key_lifetime_s=key0["expires"] - key0["created"],
         seconds_per_apt_update=round(per_update, 3))

    # 방식 B로 이행: .deb 설치 + 옛 .list·키 파일 삭제를 사람 작업 1회로 센다.
    started = time.monotonic()
    conflict_seen = []
    for m in b + [offline]:
        m.dpkg_install(deb)
        conflict_seen.append(m.update())
        m.old_list.unlink()
        m.keyring.unlink()
        m.manual += 1
        after = m.update()
        if after["rc"] != 0:
            raise RuntimeError(f"{m.name} 이행 후 update 실패: {after}")
    per_migration = (time.monotonic() - started) / (N_MACHINES + 1)
    emit("migration", machines=N_MACHINES + 1,
         update_rc_before_removing_old_list=sorted({c["rc"] for c in conflict_seen}),
         signed_by_conflict_before_removing=sum(c["signed_by_conflict"] for c in conflict_seen),
         sources_unreadable_before_removing=sum(c["sources_unreadable"] for c in conflict_seen),
         example_error=conflict_seen[0]["error_lines"], seconds_per_migration=round(per_migration, 3),
         first_expiry_still_ahead_s=round(key0["expires"] - time.time(), 1))

    expiry = key0["expires"]
    for change in range(1, K_CHANGES + 1):
        old_info = dict(maint.info)
        refresh_est = per_migration * N_MACHINES
        check_est = per_update * len(machines) * 2 + per_migration * (N_MACHINES + 2)
        if change < K_CHANGES:
            new_expiry = max(time.time() + refresh_est * SAFETY, expiry) + SAFETY * (check_est + refresh_est) + 2
        else:
            new_expiry = time.time() + 365 * 86400
        maint.extend(new_expiry)
        new_deb = maint.build_package(f"1.{change}")
        maint.publish_repo()
        upgrades = [m.auto_upgrade() for m in b]            # 오프라인 기계는 이 기간에 꺼져 있다
        refresh_done = time.time()
        emit("change_published", change=change, old_keyid=old_info["keyid"], new_keyid=maint.info["keyid"],
             same_keyid=old_info["keyid"] == maint.info["keyid"],
             same_fingerprint=old_info["fingerprint"] == maint.info["fingerprint"],
             expiry_extended_by_s=maint.info["expires"] - old_info["expires"],
             online_b_upgraded=sum(u["after"] == f"1.{change}" for u in upgrades),
             online_b_upgrade_finished_before_old_expiry=refresh_done < expiry,
             offline_version=offline.installed())

        wait = max(0.0, expiry - time.time() + 1.5)
        time.sleep(wait)
        maint.publish_repo()   # 저장소는 계속 새로 서명된다(Date 갱신)
        after_expiry = {m.name: m.update() for m in machines}
        stale_candidates = sorted({m.candidate() for m in a + [offline]})
        # 인덱스가 없는 새 기계가 연장 전 키 파일(옛 캐시)로 설정되면 apt는 어떻게 끝나는가.
        fresh = Machine(f"fresh{change}", "manual")
        fresh.manual_setup(maint)
        shutil.copy(ROOT / "published" / "lab-previous.gpg", fresh.keyring)
        fresh_res = fresh.update()
        fixes = {"manual": 0, "package": 0, "package_offline": 0}
        retry_ok = 0
        for m in machines:
            res = after_expiry[m.name]
            if res["rc"] == 0 and not res["signature_problem"]:
                continue
            if m.mode == "manual":
                m.manual_key_refresh(maint)
            else:
                # 저장소를 검증할 수 없으니 apt로는 새 패키지를 못 받는다 → 릴리스 .deb로 다시 설치.
                m.dpkg_install(new_deb)
                m.manual += 1
            fixes[m.mode] += 1
            retry = m.update()
            retry_ok += retry["rc"] == 0 and not retry["signature_problem"]
        summary = lambda group: {
            "machines": len(group),
            "rc_nonzero": sum(after_expiry[m.name]["rc"] != 0 for m in group),
            "EXPKEYSIG": sum(after_expiry[m.name]["EXPKEYSIG"] for m in group),
            "not_signed": sum(after_expiry[m.name]["not_signed"] for m in group),
            "previous_index_used": sum(after_expiry[m.name]["previous_index_used"] for m in group),
            "rc_values": sorted({after_expiry[m.name]["rc"] for m in group})}
        failing = next((after_expiry[m.name] for m in machines if after_expiry[m.name]["signature_problem"]), None)
        emit("after_old_key_expired", change=change, waited_s=round(wait, 1),
             manual_A=summary(a), package_B=summary(b), package_B_offline=summary([offline]),
             candidate_seen_by_failing_machines_before_fix=stale_candidates, published_version=f"1.{change}",
             candidate_after_fix=sorted({m.candidate() for m in a + [offline]}),
             manual_fixes=fixes, retry_succeeded=retry_ok,
             example_failure=failing["error_lines"] if failing else None,
             fresh_machine_with_pre_extension_key={k: fresh_res[k] for k in
                                                   ("rc", "EXPKEYSIG", "not_signed", "error_lines")})
        expiry = maint.info["expires"]

    final = {m.name: m.update() for m in machines}
    emit("result", n=N_MACHINES, k=K_CHANGES,
         manual_work_A=sum(m.manual for m in a), manual_work_B=sum(m.manual for m in b),
         manual_work_B_offline_machine=offline.manual,
         final_update_all_ok=all(r["rc"] == 0 and not r["signature_problem"] for r in final.values()),
         b_installed_versions=sorted({m.installed() for m in b}),
         elapsed_s=round(time.monotonic() - T0, 1))


if __name__ == "__main__":
    shutil.rmtree(ROOT, ignore_errors=True)
    (ROOT / "showkeys").mkdir(parents=True, mode=0o700)
    inspect_real_image()
    simulate()
