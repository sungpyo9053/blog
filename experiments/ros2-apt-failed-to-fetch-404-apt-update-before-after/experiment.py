#!/usr/bin/env python3
"""Offline model of `E: Failed to fetch ... 404` from a ROS-like apt repository.

A loopback HTTP server (127.0.0.1, no network) serves a flat apt repository built from
dummy .deb packages. The server "syncs" like packages.ros.org: new versions replace old
ones and the old .deb files are deleted. We then count `E: Failed to fetch` lines and
installed packages before and after `apt-get update` under several conditions.

Every number printed below is measured at run time; nothing is hard-coded as a result.
Only tools already in the ros:jazzy-ros-base image are used (apt-get, dpkg-deb,
dpkg-scanpackages, dpkg-query, Python stdlib).
"""
from __future__ import annotations

import gzip
import hashlib
import http.server
import json
import os
import platform
import posixpath
import re
import shutil
import subprocess
import threading
import time
from email.utils import formatdate
from pathlib import Path

N_PACKAGES = 20   # packages per scenario (experimenter's setting, not ROS-representative)
K_SYNCED = 5      # packages replaced by a "sync" (old .deb deleted on the server)
ROOT = Path("/tmp/hl")
SERVE = ROOT / "srv"
DEBS = ROOT / "debs"
BASE_TIME = time.time() - 3600  # fixed origin for strictly increasing mtimes/Date fields
_generation = 0

REQUESTS: list[tuple[str, int]] = []   # (path, status) seen by the server
BLOCKED: set[str] = set()              # path prefixes the server answers with 404
SAMPLES: dict[str, list[str]] = {}    # first E:/W: lines per step kind, printed once
COMMANDS = ("update", "upgrade", "install")


def emit(record: dict) -> None:
    print(json.dumps(record, ensure_ascii=False), flush=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE), **kwargs)

    def send_head(self):
        if any(posixpath.normpath(self.path).startswith(prefix) for prefix in BLOCKED):
            self.send_error(404, "File not found")
            return None
        return super().send_head()

    def log_request(self, code="-", size="-"):
        try:
            REQUESTS.append((posixpath.normpath(self.path), int(getattr(code, "value", code))))
        except (TypeError, ValueError):
            pass

    def log_message(self, *args):  # keep stdout for JSON only
        pass


def start_server() -> int:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


def tick() -> float:
    global _generation
    _generation += 1
    return BASE_TIME + _generation * 10


def build_deb(name: str, version: str) -> Path:
    out = DEBS / f"{name}_{version}_all.deb"
    if out.exists():
        return out
    tree = ROOT / "build" / f"{name}_{version}"
    (tree / "DEBIAN").mkdir(parents=True, exist_ok=True)
    (tree / "DEBIAN" / "control").write_text(
        f"Package: {name}\nVersion: {version}\nArchitecture: all\n"
        "Maintainer: HuntLab Experiment <lab@example.invalid>\n"
        "Description: dummy package for an offline apt 404 experiment\n")
    subprocess.run(["dpkg-deb", "-Zgzip", "-z1", "--root-owner-group", "--build", str(tree), str(out)],
                   check=True, capture_output=True)
    return out


class Repo:
    """One flat repository at http://127.0.0.1:<port>/<name>/ with pool/ like packages.ros.org."""

    def __init__(self, name: str, port: int):
        self.name, self.port = name, port
        self.dir = SERVE / name
        self.dir.mkdir(parents=True)
        self.versions: dict[str, str] = {}

    def put(self, package: str, version: str) -> None:
        old = self.versions.get(package)
        if old is not None:  # sync semantics: the older version is removed from the server
            self.pool_path(package, old).unlink()
        target = self.pool_path(package, version)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(build_deb(package, version), target)
        self.versions[package] = version

    def pool_path(self, package: str, version: str) -> Path:
        return self.dir / "pool" / "main" / package[0] / package / f"{package}_{version}_all.deb"

    def publish_index(self) -> None:
        scan = subprocess.run(["dpkg-scanpackages", "--multiversion", "pool", "/dev/null"],
                              cwd=self.dir, check=True, capture_output=True)
        packages = scan.stdout
        when = tick()
        files = {"Packages": packages, "Packages.gz": gzip.compress(packages, mtime=int(when))}
        for fname, data in files.items():
            (self.dir / fname).write_bytes(data)
        lines = [f" {hashlib.sha256(d).hexdigest()} {len(d)} {f}" for f, d in files.items()]
        release = (f"Origin: HuntLab-offline\nLabel: HuntLab-offline\n"
                   f"Date: {formatdate(when, usegmt=True)}\nSHA256:\n" + "\n".join(lines) + "\n")
        (self.dir / "Release").write_text(release)
        for fname in (*files, "Release"):
            os.utime(self.dir / fname, (when, when))

    def sources_line(self) -> str:
        return f"deb [trusted=yes] http://127.0.0.1:{self.port}/{self.name}/ ./"


class Client:
    """apt-get confined to this scenario's sources, lists and cache (system dpkg db shared)."""

    def __init__(self, repo: Repo):
        self.repo = repo
        base = ROOT / "apt" / repo.name
        for sub in ("lists/partial", "cache/archives/partial", "parts"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        (base / "sources.list").write_text(repo.sources_line() + "\n")
        self.opts = ["-o", f"Dir::Etc::sourcelist={base / 'sources.list'}",
                     "-o", f"Dir::Etc::sourceparts={base / 'parts'}",
                     "-o", f"Dir::State::Lists={base / 'lists'}",
                     "-o", f"Dir::Cache={base / 'cache'}",
                     "-o", "Acquire::Languages=none",
                     "-o", "APT::Sandbox::User=root"]

    def run(self, scenario: str, step: str, *args: str, setup: bool = False) -> dict:
        mark = len(REQUESTS)
        started = time.monotonic()
        done = subprocess.run(["apt-get", *self.opts, *args], capture_output=True, text=True,
                              env={**os.environ, "DEBIAN_FRONTEND": "noninteractive", "LC_ALL": "C"})
        seconds = time.monotonic() - started
        text = done.stdout + done.stderr
        lines = text.splitlines()
        seen = REQUESTS[mark:]
        release = [ln.split(":", 1)[0] for ln in lines
                   if re.match(r"^(Get|Hit|Ign|Err):\d+ ", ln)
                   and re.search(rf"/{self.repo.name}/? \./ Release\b", ln)]
        failed = [ln for ln in lines if ln.startswith("E: Failed to fetch")]
        diag = [ln for ln in lines if ln.startswith(("E:", "W:"))]
        record = {
            "scenario": scenario, "step": step,
            "command": "apt-get " + " ".join(a for a in args if a.startswith("--") or a in COMMANDS),
            "exit_code": done.returncode,
            "failed_fetch_lines": len(failed),
            "err_lines": sum(bool(re.match(r"^Err:\d+ ", ln)) for ln in lines),
            "unable_to_fetch_msg": any("Unable to fetch some archives" in ln for ln in lines),
            "old_ones_used_msg": any("old ones used instead" in ln for ln in lines),
            "release_line": release[0] if release else None,
            "srv_404_deb": sum(c == 404 and p.endswith(".deb") for p, c in seen),
            "srv_404_index": sum(c == 404 and "/Packages" in p for p, c in seen),
            "srv_200_deb": sum(c == 200 and p.endswith(".deb") for p, c in seen),
            "srv_304": sum(c == 304 for p, c in seen),
            "seconds": round(seconds, 3),
        }
        record.update(installed(self.repo))
        record["diag"] = diag
        if not setup or done.returncode != 0 or failed:
            out = {k: v for k, v in record.items() if k != "diag"}
            emit(out)
        if not SAMPLES.get(step) and diag and not setup:
            SAMPLES[step] = diag[:2] if step == "update_index_blocked" else diag[:1]
        return record


def installed(repo: Repo) -> dict:
    query = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${Version} ${db:Status-Abbrev}\n",
                            f"{repo.name}-*"], capture_output=True, text=True)
    versions: dict[str, int] = {}
    count = 0
    for line in query.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("ii"):
            count += 1
            versions[parts[1]] = versions.get(parts[1], 0) + 1
    return {"installed": count, "versions": dict(sorted(versions.items()))}


def names(repo: Repo) -> list[str]:
    return [f"{repo.name}-{i:02d}" for i in range(1, N_PACKAGES + 1)]


def seed(repo: Repo, version: str = "1.0") -> None:
    for name in names(repo):
        repo.put(name, version)
    repo.publish_index()


def sync(repo: Repo, version: str, *, reindex: bool = True) -> None:
    for name in names(repo)[:K_SYNCED]:
        repo.put(name, version)
    if reindex:
        repo.publish_index()


def ratio(before: int, after: int):
    return None if before == 0 else round((before - after) / before, 3)


def scenario_stale_list(port: int) -> dict:
    """A: lists are older than the server; update is healthy."""
    repo = Repo("hla", port); seed(repo); apt = Client(repo)
    apt.run("A_stale_list", "update_initial", "update", setup=True)
    sync(repo, "2.0")
    before = apt.run("A_stale_list", "install_before_update", "-y", "install", *names(repo))
    upd = apt.run("A_stale_list", "update_after_sync", "update")
    after = apt.run("A_stale_list", "install_after_update", "-y", "install", *names(repo))
    return {"before": before["failed_fetch_lines"], "after": after["failed_fetch_lines"],
            "update_release_line": upd["release_line"],
            "installed_before": before["installed"], "installed_after": after["installed"]}


def scenario_upgrade_first(port: int) -> dict:
    """B: like the original question - `apt upgrade` with lists that point to a deleted build."""
    repo = Repo("hlb", port); seed(repo); apt = Client(repo)
    apt.run("B_upgrade_first", "update_initial", "update", setup=True)
    apt.run("B_upgrade_first", "install_baseline", "-y", "install", *names(repo), setup=True)
    sync(repo, "1.1")
    apt.run("B_upgrade_first", "update_sees_1.1", "update", setup=True)
    sync(repo, "1.2")  # next sync deletes 1.1 before the machine upgrades
    before = apt.run("B_upgrade_first", "upgrade_before_update", "-y", "upgrade")
    upd = apt.run("B_upgrade_first", "update_after_sync", "update")
    after = apt.run("B_upgrade_first", "upgrade_after_update", "-y", "upgrade")
    return {"before": before["failed_fetch_lines"], "after": after["failed_fetch_lines"],
            "update_release_line": upd["release_line"],
            "versions_before": before["versions"], "versions_after": after["versions"]}


def scenario_index_404(port: int) -> dict:
    """C: update runs but the new Packages index cannot be downloaded (404)."""
    repo = Repo("hlc", port); seed(repo); apt = Client(repo)
    apt.run("C_index_404", "update_initial", "update", setup=True)
    sync(repo, "2.0")
    BLOCKED.update({f"/{repo.name}/Packages"})
    before = apt.run("C_index_404", "install_before_update", "-y", "install", *names(repo))
    upd = apt.run("C_index_404", "update_index_blocked", "update")
    after = apt.run("C_index_404", "install_after_update", "-y", "install", *names(repo))
    BLOCKED.clear()
    return {"before": before["failed_fetch_lines"], "after": after["failed_fetch_lines"],
            "update_release_line": upd["release_line"],
            "update_exit_code": upd["exit_code"], "update_failed_fetch_lines": upd["failed_fetch_lines"],
            "old_ones_used_msg": upd["old_ones_used_msg"]}


def scenario_stale_index_hit(port: int) -> dict:
    """D: pool already synced but the server still serves the old index (update prints Hit)."""
    repo = Repo("hld", port); seed(repo); apt = Client(repo)
    apt.run("D_stale_index_hit", "update_initial", "update", setup=True)
    sync(repo, "2.0", reindex=False)
    before = apt.run("D_stale_index_hit", "install_before_update", "-y", "install", *names(repo))
    upd = apt.run("D_stale_index_hit", "update_index_unchanged", "update")
    after = apt.run("D_stale_index_hit", "install_after_update", "-y", "install", *names(repo))
    return {"before": before["failed_fetch_lines"], "after": after["failed_fetch_lines"],
            "update_release_line": upd["release_line"], "update_exit_code": upd["exit_code"]}


def scenario_no_sync(port: int) -> dict:
    """E: boundary - nothing synced, old lists are still correct."""
    repo = Repo("hle", port); seed(repo); apt = Client(repo)
    apt.run("E_no_sync", "update_initial", "update", setup=True)
    rec = apt.run("E_no_sync", "install_without_new_update", "-y", "install", *names(repo))
    return {"before": rec["failed_fetch_lines"], "installed": rec["installed"]}


def scenario_fix_missing(port: int) -> dict:
    """F: `--fix-missing` with stale lists (no update)."""
    repo = Repo("hlf", port); seed(repo); apt = Client(repo)
    apt.run("F_fix_missing", "update_initial", "update", setup=True)
    sync(repo, "2.0")
    rec = apt.run("F_fix_missing", "install_fix_missing", "-y", "--fix-missing", "install", *names(repo))
    return {"failed_fetch_lines": rec["failed_fetch_lines"], "exit_code": rec["exit_code"],
            "installed": rec["installed"], "versions": rec["versions"]}


def environment() -> None:
    def first_line(cmd: list[str]) -> str:
        done = subprocess.run(cmd, capture_output=True, text=True)
        return (done.stdout or done.stderr).splitlines()[0] if (done.stdout or done.stderr) else ""

    ros_sources = []
    for path in sorted(Path("/etc/apt/sources.list.d").glob("*")):
        for line in path.read_text(errors="replace").splitlines():
            if "packages.ros.org" in line:
                ros_sources.append(f"{path.name}: {line.strip()}")
    lists = Path("/var/lib/apt/lists")
    image_lists = [p.name for p in lists.iterdir() if p.is_file()] if lists.is_dir() else []
    emit({"environment": True, "apt": first_line(["apt-get", "--version"]),
          "dpkg": first_line(["dpkg", "--version"]), "python": platform.python_version(),
          "ros_distro": os.environ.get("ROS_DISTRO"), "uid": os.getuid(),
          "image_ros_source_lines": ros_sources,
          "image_var_lib_apt_lists_files": len(image_lists),
          "n_packages": N_PACKAGES, "k_synced": K_SYNCED})


def main() -> None:
    started = time.monotonic()
    for d in (SERVE, DEBS):
        d.mkdir(parents=True, exist_ok=True)
    environment()
    port = start_server()
    results = {"A_stale_list": scenario_stale_list(port),
               "B_upgrade_first": scenario_upgrade_first(port),
               "C_index_404": scenario_index_404(port),
               "D_stale_index_hit": scenario_stale_index_hit(port),
               "E_no_sync": scenario_no_sync(port),
               "F_fix_missing": scenario_fix_missing(port)}
    for key in ("A_stale_list", "B_upgrade_first", "C_index_404", "D_stale_index_hit"):
        r = results[key]
        r["explained_ratio"] = ratio(r["before"], r["after"])
    emit({"diagnostic_samples": SAMPLES})
    emit({"summary": True, "results": results, "total_seconds": round(time.monotonic() - started, 2)})


if __name__ == "__main__":
    main()
