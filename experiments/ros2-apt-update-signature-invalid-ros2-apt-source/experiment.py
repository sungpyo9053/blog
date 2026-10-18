#!/usr/bin/env python3
"""ros2-apt-source 단계가 무엇을 바꾸는지 오프라인 컨테이너에서 실제로 재는 실험.

1부 image: 이미지에 실제로 깔린 ros2-apt-source 파일·키·grep -r/-R 차이.
2부 conflict: 격리된 apt 설정에서 예전 ros2.list와 새 ros2.sources 조합별 apt-cache policy 결과.
3부 lab: 실험용 키와 file: 저장소로 "같은 키의 만료일 연장" 사건 k번을 초 단위로 압축해,
        수동 방식(A)과 패키지 방식(B)에서 사람이 손댄 횟수와 만료 후 apt-get update 결과를 센다.
모든 숫자는 실행 중에 측정해 JSON 줄로 출력한다.
"""
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

T0 = time.monotonic()
ROOT = Path("/tmp/lab")
ROS_URI = "http://packages.ros.org/ros2/ubuntu"
SOURCES_DIR = "/etc/apt/sources.list.d"
PKG_KEYRING = "/usr/share/keyrings/ros2-archive-keyring.gpg"
PKG_SOURCES = "/usr/share/ros-apt-source/ros2.sources"
OLD_KEYRING = "/usr/share/keyrings/ros-archive-keyring.gpg"
OLD_LIST = f"{SOURCES_DIR}/ros2.list"


def emit(**record):
    record["t"] = round(time.monotonic() - T0, 2)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def run(cmd, env=None, check=False):
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd}: {p.returncode} {p.stderr[-400:]}")
    return p


def messages(text, limit=3):
    """apt가 낸 W:/E: 줄(최대 limit개, 160자)."""
    return [line.strip()[:160] for line in text.splitlines() if line.startswith(("W:", "E:"))][:limit]


ALGO = {"1": "RSA", "22": "EdDSA"}


def key_info(path):
    out = run(["gpg", "--with-colons", "--show-keys", str(path)], check=True).stdout
    pub = next(line.split(":") for line in out.splitlines() if line.startswith("pub:"))
    fpr = next(line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:"))
    expires = int(pub[6]) if pub[6] else None
    return {"fingerprint": fpr, "long_id": fpr[-16:], "algo": ALGO.get(pub[3], pub[3]), "bits": int(pub[2]),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(pub[5]))),
            "expires_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires)) if expires else None}


# ---------------------------------------------------------------- 1부 image
def part_image():
    version = run(["dpkg-query", "-W", "-f", "${Version}", "ros2-apt-source"]).stdout
    entries = []
    for name in sorted(os.listdir(SOURCES_DIR)):
        path = os.path.join(SOURCES_DIR, name)
        owner = run(["dpkg", "-S", path])
        entries.append({"name": name, "is_symlink": os.path.islink(path),
                        "target": os.readlink(path) if os.path.islink(path) else None,
                        "dpkg_owner": owner.stdout.split(":")[0] if owner.returncode == 0 else None})
    emit(part="image", ros2_apt_source_version=version, sources_list_d=entries)
    emit(part="image", keyring=PKG_KEYRING, keyring_bytes=os.path.getsize(PKG_KEYRING),
         keyring_sha256=hashlib.sha256(Path(PKG_KEYRING).read_bytes()).hexdigest(), **key_info(PKG_KEYRING))
    # 내장 키 블록(Signed-By)에서 꺼낸 키와 키링 파일의 키가 같은지
    lines = Path(PKG_SOURCES).read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Signed-By:"))
    block = [lines[start].split(":", 1)[1].strip()]
    for line in lines[start + 1:]:
        if not line.startswith(" "):
            break
        block.append("" if line.strip() == "." else line.strip())
    embedded = ROOT / "embedded.asc"
    embedded.write_text("\n".join(block) + "\n")
    emb = key_info(embedded)
    emit(part="image", embedded_signed_by_fingerprint=emb["fingerprint"],
         embedded_equals_keyring=emb["fingerprint"] == key_info(PKG_KEYRING)["fingerprint"],
         old_list_exists=os.path.exists(OLD_LIST), old_keyring_exists=os.path.exists(OLD_KEYRING))
    for flag in ("-rl", "-Rl"):
        p = run(["grep", flag, "packages.ros.org", SOURCES_DIR + "/"])
        found = [line for line in p.stdout.splitlines() if line]
        emit(part="image", grep=f"grep {flag} packages.ros.org {SOURCES_DIR}/", exit_code=p.returncode,
             files_found=len(found), files=found)


# ------------------------------------------------------- apt 격리 환경 도우미
def apt_env(machine: Path):
    """machine 디렉터리만 보는 apt 설정. 시스템 sources·trusted 키·lists를 쓰지 않는다."""
    for sub in ("sources.list.d", "state/lists/partial", "cache/archives/partial", "conf.d", "pref.d", "trusted.d"):
        (machine / sub).mkdir(parents=True, exist_ok=True)
    (machine / "sources.list").touch()
    (machine / "status").touch()
    conf = machine / "apt.conf"
    conf.write_text("\n".join([
        f'Dir::Etc::SourceList "{machine}/sources.list";',
        f'Dir::Etc::SourceParts "{machine}/sources.list.d";',
        f'Dir::Etc::Parts "{machine}/conf.d";',
        f'Dir::Etc::Preferences "{machine}/preferences";',
        f'Dir::Etc::PreferencesParts "{machine}/pref.d";',
        f'Dir::Etc::Trusted "{machine}/trusted.gpg";',
        f'Dir::Etc::TrustedParts "{machine}/trusted.d";',
        f'Dir::State "{machine}/state";',
        f'Dir::State::Status "{machine}/status";',
        f'Dir::Cache "{machine}/cache";',
        'APT::Architecture "amd64";',
        'APT::Sandbox::User "root";',
        'Acquire::Languages "none";',
        'Acquire::http::Proxy "false";',
    ]) + "\n")
    env = dict(os.environ, APT_CONFIG=str(conf), LC_ALL="C")
    return env


# ---------------------------------------------------------------- 2부 conflict
def part_conflict():
    old_key = ROOT / "conflict" / "ros-archive-keyring.gpg"   # 예전 방식 키 파일(같은 키의 사본)
    old_key.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PKG_KEYRING, old_key)
    new_sources = Path(PKG_SOURCES).read_text()
    old_line = f"deb [arch=amd64 signed-by={old_key}] {ROS_URI} noble main\n"
    old_line_pkgkey = f"deb [arch=amd64 signed-by={PKG_KEYRING}] {ROS_URI} noble main\n"
    cases = {
        "new_only": {"ros2.sources": new_sources},
        "old_only": {"ros2.list": old_line},
        "old_and_new": {"ros2.list": old_line, "ros2.sources": new_sources},
        "old_pointing_pkg_keyring_and_new": {"ros2.list": old_line_pkgkey, "ros2.sources": new_sources},
        "old_line_twice_same_key": {"ros2.list": old_line, "ros-copy.list": old_line},
    }
    for name, files in cases.items():
        machine = ROOT / "conflict" / name
        env = apt_env(machine)
        for fname, text in files.items():
            (machine / "sources.list.d" / fname).write_text(text)
        p = run(["apt-cache", "policy"], env=env)
        text = p.stdout + p.stderr
        emit(part="conflict", case=name, files=sorted(files), exit_code=p.returncode,
             first_message=(messages(text, 1) or [""])[0],
             conflicting_signed_by="Conflicting values set for option Signed-By" in text,
             configured_multiple_times="configured multiple times" in text)


# ---------------------------------------------------------------- 3부 lab
class Repo:
    """실험용 서명 키 하나와 file: 저장소 하나. 운영자(Open Robotics 역할)."""

    def __init__(self, base: Path):
        self.base = base
        self.home = base / "gnupg"
        self.home.mkdir(parents=True, mode=0o700)
        self.repo = base / "repo"
        (self.repo / "pool").mkdir(parents=True)
        (self.repo / "dists/lab/main/binary-amd64").mkdir(parents=True)
        self.env = dict(os.environ, GNUPGHOME=str(self.home))
        self.packages = []
        self.serial = 0

    def gpg(self, *args):
        return run(["gpg", "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase", "", *args],
                   env=self.env, check=True)

    def create_key(self, lifetime):
        self.gpg("--quick-gen-key", "HuntLab Lab Archive <lab@example.invalid>", "ed25519", "sign",
                 f"seconds={lifetime}")
        out = run(["gpg", "--with-colons", "--list-keys"], env=self.env, check=True).stdout
        self.fpr = next(line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:"))

    def extend(self, lifetime):
        """같은 키(같은 지문)의 만료일만 늘린다. 비밀키는 그대로다."""
        self.gpg("--quick-set-expire", self.fpr, f"seconds={lifetime}")

    def public_key(self) -> bytes:
        return subprocess.run(["gpg", "--export", self.fpr], env=self.env, capture_output=True,
                              check=True).stdout

    def build_source_package(self, version):
        """ros2-apt-source를 흉내 낸 lab-apt-source: 키링 + 그 키링을 쓰는 .sources."""
        root = self.base / f"build-{version}"
        (root / "DEBIAN").mkdir(parents=True)
        (root / "usr/share/keyrings").mkdir(parents=True)
        (root / "usr/share/lab-apt-source").mkdir(parents=True)
        (root / "usr/share/keyrings/lab-archive-keyring.gpg").write_bytes(self.public_key())
        (root / "DEBIAN/control").write_text(
            f"Package: lab-apt-source\nVersion: {version}\nArchitecture: all\n"
            "Maintainer: lab <lab@example.invalid>\nDescription: lab source and key\n")
        deb = self.repo / "pool" / f"lab-apt-source_{version}_all.deb"
        run(["dpkg-deb", "--root-owner-group", "-Zgzip", "--build", str(root), str(deb)], check=True)
        data = deb.read_bytes()
        self.packages = [
            f"Package: lab-apt-source\nVersion: {version}\nArchitecture: all\nMaintainer: lab\n"
            f"Filename: pool/{deb.name}\nSize: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n"
            "Description: lab source and key\n"]
        self.sign_release()

    def sign_release(self):
        """색인을 다시 쓰고 InRelease에 새로 서명한다(실제 저장소가 매일 동기화하는 것처럼)."""
        self.serial += 1
        body = "\n".join(self.packages).encode()
        files = {"main/binary-amd64/Packages": body, "main/binary-amd64/Packages.gz": gzip.compress(body, mtime=0)}
        dist = self.repo / "dists/lab"
        for rel, content in files.items():
            (dist / rel).write_bytes(content)
        date = time.strftime("%a, %d %b %Y %H:%M:%S UTC", time.gmtime(time.time() - 5))
        release = (f"Origin: HuntLab\nLabel: lab\nSuite: lab\nCodename: lab\nVersion: {self.serial}\nDate: {date}\n"
                   "Architectures: amd64 all\nComponents: main\nSHA256:\n" +
                   "".join(f" {hashlib.sha256(c).hexdigest()} {len(c)} {rel}\n" for rel, c in files.items()))
        (dist / "Release").write_text(release)
        self.gpg("--local-user", self.fpr, "--clearsign", "--digest-algo", "SHA256",
                 "-o", str(dist / "InRelease"), str(dist / "Release"))

    def expiry(self):
        out = run(["gpg", "--with-colons", "--list-keys", self.fpr], env=self.env, check=True).stdout
        return int(next(line.split(":") for line in out.splitlines() if line.startswith("pub:"))[6])


class Machine:
    def __init__(self, base: Path, name: str, group: str, repo: Repo):
        self.name, self.group, self.repo = name, group, repo
        self.dir = base / "machines" / name
        self.env = apt_env(self.dir)
        self.root = self.dir / "root"     # 패키지 파일이 풀리는 기계의 / 역할
        self.human_touches = 0
        self.online = True
        self.installed = None

    # 예전 공식 문서 방식: 사람이 키 파일을 받아 쓰고, signed-by 한 줄 .list를 만든다
    def manual_key_copy(self):
        (self.dir / "ros-archive-keyring.gpg").write_bytes(self.repo.public_key())
        self.human_touches += 1

    def manual_setup(self):
        self.manual_key_copy()
        (self.dir / "sources.list.d/lab.list").write_text(
            f"deb [signed-by={self.dir}/ros-archive-keyring.gpg] file:{self.repo.repo} lab main\n")

    # 이전 작업 1회: 예전 저장소로 패키지 설치 → 예전 파일 삭제 → 패키지 소스로 교체(사람 1회)
    def migrate_to_package(self):
        assert self.update()["exit_code"] == 0
        self.install_candidate()
        (self.dir / "sources.list.d/lab.list").unlink()
        (self.dir / "ros-archive-keyring.gpg").unlink()
        (self.dir / "sources.list.d/lab.sources").write_text(
            f"Types: deb\nURIs: file:{self.repo.repo}\nSuites: lab\nComponents: main\n"
            f"Signed-By: {self.root}/usr/share/keyrings/lab-archive-keyring.gpg\n")
        self.human_touches += 1

    def install_candidate(self):
        """apt가 고른 후보 버전을 내려받아 키링을 기계 루트에 푼다(dpkg-deb -x)."""
        policy = run(["apt-cache", "policy", "lab-apt-source"], env=self.env).stdout
        candidate = next(line.split()[-1] for line in policy.splitlines() if "Candidate:" in line)
        if candidate in ("(none)", self.installed):
            return False
        cache = self.dir / "cache/archives"
        subprocess.run(["apt-get", "download", f"lab-apt-source={candidate}"], env=self.env, cwd=cache,
                       capture_output=True, text=True, check=True)
        deb = next(cache.glob(f"lab-apt-source_{candidate.replace(':', '%3a')}_all.deb"))
        run(["dpkg-deb", "-x", str(deb), str(self.root)], check=True)
        self.installed = candidate
        return True

    # 무인 갱신(사람 손 없음): 켜져 있는 패키지 방식 기계만 apt update 후 새 버전을 받는다
    def unattended_upgrade(self):
        if not self.online:
            return None
        self.update()
        return self.install_candidate()

    def update(self):
        p = run(["apt-get", "update"], env=self.env)
        text = p.stdout + p.stderr
        return {"exit_code": p.returncode, "expkeysig": "EXPKEYSIG" in text,
                "previous_index_used": "previous index files will be used" in text,
                "not_signed": "is not signed" in text, "messages": messages(text)}


def part_lab(n_per_group=3, k=2, lifetime=6):
    repo = Repo(ROOT / "lab")
    repo.create_key(lifetime)
    repo.build_source_package("1.0")
    created_fpr = repo.fpr
    machines = [Machine(ROOT / "lab", f"A{i}", "A_manual", repo) for i in range(1, n_per_group + 1)]
    machines += [Machine(ROOT / "lab", f"B{i}", "B_package", repo) for i in range(1, n_per_group + 1)]
    machines.append(Machine(ROOT / "lab", "B_off", "B_package_offline_at_event1", repo))
    for m in machines:
        m.manual_setup()                     # 출발점: 모두 예전 수동 방식으로 이미 설정됨
        m.human_touches = 0                  # 출발 전 설정은 비교에서 제외(두 방식 공통)
        assert m.update()["exit_code"] == 0
    for m in machines:
        if m.group.startswith("B"):
            m.migrate_to_package()
    emit(part="lab", stage="migrated", key_long_id=repo.fpr[-16:], key_algo=key_info(
             machines[0].dir / "ros-archive-keyring.gpg")["algo"],
         lifetime_seconds=lifetime, machines=len(machines),
         touches={m.name: m.human_touches for m in machines})

    for event in range(1, k + 1):
        old_expiry = repo.expiry()
        # 만료 전: 운영자가 같은 키의 만료일을 연장하고, 새 키링을 담은 패키지 새 버전을 저장소에 올린다
        repo.extend(lifetime * 2)
        repo.build_source_package(f"1.{event}")
        same_fpr = repo.fpr == created_fpr
        for m in machines:
            if m.name == "B_off":
                m.online = event != 1        # 사건 1 때만 꺼져 있었다
            if m.group == "A_manual":
                m.manual_key_copy()          # 사람이 기계마다 키 파일을 다시 받아 덮어쓴다
        upgraded = {m.name: m.unattended_upgrade() for m in machines if m.group.startswith("B")}
        upgrades_before_old_expiry = time.time() < old_expiry
        # 예전 사본의 만료 시각이 지날 때까지 기다린 뒤, 저장소가 다시 동기화(재서명)된다
        while time.time() <= old_expiry + 1:
            time.sleep(0.2)
        repo.sign_release()
        for m in machines:
            m.online = True
        after = {m.name: m.update() for m in machines}
        repairs = []
        for m in machines:
            if after[m.name]["exit_code"] != 0 or after[m.name]["expkeysig"]:
                # 사람이 고친다: 기계에 직접 새 패키지 파일을 받아 풀거나(B) 키를 다시 받는다(A)
                if m.group.startswith("B"):
                    run(["dpkg-deb", "-x", str(next(repo.repo.glob(f"pool/*_1.{event}_all.deb"))),
                         str(m.root)], check=True)
                    m.installed = f"1.{event}"
                    m.human_touches += 1
                else:
                    m.manual_key_copy()
                repairs.append(m.name)
        recheck = {m.name: m.update()["exit_code"] for m in machines if m.name in repairs}
        emit(part="lab", stage=f"event{event}", same_fingerprint_as_created=same_fpr,
             upgraded_by_apt={name: v for name, v in upgraded.items()},
             upgrades_finished_before_old_expiry=upgrades_before_old_expiry,
             after_expiry_update_exit={name: r["exit_code"] for name, r in after.items()},
             expkeysig_machines=[name for name, r in after.items() if r["expkeysig"]],
             previous_index_used_machines=[name for name, r in after.items() if r["previous_index_used"]],
             failed_messages={name: r["messages"] for name, r in after.items() if r["exit_code"] or r["expkeysig"]},
             repaired_by_human=repairs, recheck_exit_after_repair=recheck)
        copies = {"A1": machines[0].dir / "ros-archive-keyring.gpg",
                  "B1": machines[n_per_group].root / "usr/share/keyrings/lab-archive-keyring.gpg",
                  "B_off": machines[-1].root / "usr/share/keyrings/lab-archive-keyring.gpg"}
        infos = {name: key_info(path) for name, path in copies.items()}
        emit(part="lab", stage=f"event{event}_key_copies", repo_key_expires_utc=time.strftime(
                 "%Y-%m-%dT%H:%M:%SZ", time.gmtime(repo.expiry())),
             copies_same_fingerprint=all(i["fingerprint"] == created_fpr for i in infos.values()),
             copy_expires_utc={name: i["expires_utc"] for name, i in infos.items()})

    # 이전 색인이 없는 새 기계: 만료된(연장 전) 키 사본만 가진 채 처음 apt-get update
    stale = ROOT / "lab" / "stale-key.gpg"
    stale_repo = Repo(ROOT / "lab-stale")
    stale_repo.create_key(3)
    stale_repo.build_source_package("1.0")
    stale.write_bytes(stale_repo.public_key())
    fresh_old = Machine(ROOT / "lab-stale", "fresh_with_index", "x", stale_repo)
    fresh_new = Machine(ROOT / "lab-stale", "fresh_no_index", "x", stale_repo)
    line = f"deb [signed-by={stale}] file:{stale_repo.repo} lab main\n"
    (fresh_old.dir / "sources.list.d/lab.list").write_text(line)
    first = fresh_old.update()
    stale_expiry = stale_repo.expiry()
    while time.time() <= stale_expiry + 1:
        time.sleep(0.2)
    stale_repo.extend(60)            # 운영자는 연장했지만 두 기계의 사본은 옛것 그대로
    stale_repo.sign_release()
    (fresh_new.dir / "sources.list.d/lab.list").write_text(line)
    with_index = fresh_old.update()
    no_index = fresh_new.update()

    def lists(machine):
        return len([p for p in (machine.dir / "state/lists").iterdir() if p.is_file() and p.name != "lock"])

    def pkg_visible(machine):
        policy = run(["apt-cache", "policy", "lab-apt-source"], env=machine.env).stdout
        return "Candidate:" in policy and "Candidate: (none)" not in policy

    emit(part="lab", stage="stale_key_index", before_expiry_exit=first["exit_code"],
         machine_with_previous_index={**{k_: with_index[k_] for k_ in ("exit_code", "expkeysig",
                                                                         "previous_index_used", "not_signed")},
                                      "list_files": lists(fresh_old), "package_visible": pkg_visible(fresh_old),
                                      "messages": with_index["messages"]},
         machine_without_index={**{k_: no_index[k_] for k_ in ("exit_code", "expkeysig",
                                                                 "previous_index_used", "not_signed")},
                                "list_files": lists(fresh_new), "package_visible": pkg_visible(fresh_new),
                                "messages": no_index["messages"]})

    totals = {}
    for m in machines:
        totals.setdefault(m.group, []).append(m.human_touches)
    emit(part="lab", stage="summary", n_per_group=n_per_group, k_events=k,
         human_touches_by_machine={m.name: m.human_touches for m in machines},
         human_touches_by_group={g: sum(v) for g, v in totals.items()},
         A_total_3_machines=sum(totals["A_manual"]),
         B_total_3_online_machines=sum(totals["B_package"]),
         B_offline_machine_total=sum(totals["B_package_offline_at_event1"]),
         one_A_machine_total=totals["A_manual"][0])


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True)
    os.chmod(ROOT, 0o755)
    part_image()
    part_conflict()
    part_lab()
    emit(part="done", total_seconds=round(time.monotonic() - T0, 2))


if __name__ == "__main__":
    main()
