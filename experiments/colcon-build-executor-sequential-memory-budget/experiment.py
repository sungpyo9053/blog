#!/usr/bin/env python3
"""colcon 동시 빌드 수 실험: executor·--parallel-workers·MAKEFLAGS가 각각 무엇을 줄이는가.

ros:jazzy-ros-base 안의 실제 colcon·CMake·make·gcc로 /tmp에 작은 CMake 패키지 4개를 만들고
여러 설정으로 다시 빌드한다. 각 C 파일 컴파일은 CMAKE_C_COMPILER_LAUNCHER로 감싼 런처를 거친다.
런처는 시작·종료 시각과 자기 최대 RSS(VmHWM)를 기록하고, 컴파일 한 건이 무거운 C++ 파일처럼
잠시 메모리를 잡고 시간을 쓰도록 정해진 "부하"(밸러스트 메모리 + 대기 또는 CPU 소모)를 더한다.
부하 크기는 입력 조건이며, 동시 작업 수·벽시계 시간·메모리 합계·ru_maxrss는 모두 실행 중에 잰다.
출력: 측정 한 건마다 JSON 한 줄.
"""
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/tmp/colcon_exp")
LAUNCHER = ROOT / "launch.py"
# 교육용 예제의 패키지 시간 30/40/50/60초를 200분의 1로 줄인 컴파일 한 건의 부하(초).
PACKAGES = {"p30": 0.15, "p40": 0.20, "p50": 0.25, "p60": 0.30}
FILES_PER_PACKAGE = 4
BALLAST_MIB = 16
# CPU 소모 조건은 실행 시간을 60초 안에 맞추려고 부하를 절반으로 줄인다.
CPU_HOLD_SCALE = 0.5

LAUNCHER_SRC = r'''
import json, os, subprocess, sys, time
pkg, hold = sys.argv[1], float(sys.argv[2])
cmd = sys.argv[3:]
t0 = time.monotonic()
ballast = bytearray(b"\x01") * (int(os.environ["EXP_BALLAST_MIB"]) * 1024 * 1024)
if os.environ.get("EXP_HOLD_MODE") == "cpu":
    end = time.process_time() + hold * float(os.environ["EXP_HOLD_SCALE"])
    x = 0
    while time.process_time() < end:
        x += 1
else:
    time.sleep(hold)
rc = subprocess.call(cmd)
hwm = 0
with open("/proc/self/status") as f:
    for line in f:
        if line.startswith("VmHWM:"):
            hwm = int(line.split()[1])
t1 = time.monotonic()
line = json.dumps({"pkg": pkg, "start": t0, "end": t1, "rc": rc, "vmhwm_kib": hwm, "ballast": len(ballast)})
fd = os.open(os.environ["EXP_LAUNCH_LOG"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
os.write(fd, (line + "\n").encode())
os.close(fd)
sys.exit(rc)
'''

WRAPPER_SRC = (
    "import json,resource,subprocess,sys\n"
    "with open(sys.argv[1],'w') as out:\n"
    "    rc=subprocess.call(sys.argv[2:],stdout=out,stderr=subprocess.STDOUT)\n"
    "print(json.dumps({'rc':rc,'ru_maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}))\n"
)


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def make_workspace(name, chain):
    ws = ROOT / name
    names = list(PACKAGES)
    for i, pkg in enumerate(names):
        d = ws / "src" / pkg
        d.mkdir(parents=True)
        dep = f"  <depend>{names[i - 1]}</depend>\n" if chain and i > 0 else ""
        (d / "package.xml").write_text(
            '<?xml version="1.0"?>\n<package format="3">\n'
            f"  <name>{pkg}</name>\n  <version>0.0.0</version>\n  <description>exp</description>\n"
            "  <maintainer email=\"exp@example.com\">exp</maintainer>\n  <license>MIT</license>\n"
            f"{dep}  <export><build_type>cmake</build_type></export>\n</package>\n")
        sources = [f"s{k}.c" for k in range(FILES_PER_PACKAGE)]
        for k, src in enumerate(sources):
            (d / src).write_text(f"int {pkg}_f{k}(int x) {{ return x * {k + 1}; }}\n")
        (d / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.10)\n"
            f"project({pkg} C)\n"
            f"set(CMAKE_C_COMPILER_LAUNCHER {sys.executable} {LAUNCHER} {pkg} {PACKAGES[pkg]})\n"
            f"add_library({pkg} STATIC {' '.join(sources)})\n"
            f"install(TARGETS {pkg} DESTINATION lib)\n")
    return ws


class Sampler(threading.Thread):
    """/proc를 주기적으로 읽어 동시에 살아 있는 런처의 RSS 합과 단일 프로세스 최대 RSS를 잰다."""

    def __init__(self, period=0.02):
        super().__init__(daemon=True)
        self.period = period
        self.stop_flag = threading.Event()
        self.page_kib = os.sysconf("SC_PAGE_SIZE") // 1024
        self.me = os.getpid()
        self.peak_launcher_sum_kib = 0
        self.peak_launcher_count = 0
        self.peak_all_sum_kib = 0
        self.max_single_kib = 0
        self.max_single_name = ""
        self.samples = 0

    def run(self):
        while not self.stop_flag.is_set():
            procs = {}
            for entry in os.listdir("/proc"):
                if not entry.isdigit() or int(entry) == self.me:
                    continue
                pid = int(entry)
                try:
                    with open(f"/proc/{pid}/stat") as f:
                        fields = f.read().rsplit(")", 1)[1].split()
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
                except (OSError, IndexError):
                    continue
                # stat의 ")" 뒤: [0]=state, [1]=ppid, [21]=rss(페이지)
                procs[pid] = (int(fields[1]), int(fields[21]) * self.page_kib, cmd)
            launcher_sum = launcher_n = all_sum = 0
            for pid, (ppid, rss, cmd) in procs.items():
                all_sum += rss
                parent_cmd = procs.get(ppid, (0, 0, ""))[2]
                # fork 직후 exec 전의 자식은 부모 cmdline을 잠시 물려받으므로 런처의 자식은 제외한다.
                if str(LAUNCHER) in cmd and str(LAUNCHER) not in parent_cmd:
                    launcher_sum += rss
                    launcher_n += 1
                if rss > self.max_single_kib:
                    self.max_single_kib = rss
                    self.max_single_name = " ".join(cmd.split(" ")[:2])[:60] or "?"
            self.samples += 1
            self.peak_launcher_sum_kib = max(self.peak_launcher_sum_kib, launcher_sum)
            self.peak_launcher_count = max(self.peak_launcher_count, launcher_n)
            self.peak_all_sum_kib = max(self.peak_all_sum_kib, all_sum)
            time.sleep(self.period)


def max_overlap(intervals):
    events = sorted([(s, 1) for s, _ in intervals] + [(e, -1) for _, e in intervals], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


def max_packages_overlap(jobs):
    best = 0
    for j in jobs:
        t = j["start"]
        active = {k["pkg"] for k in jobs if k["start"] <= t < k["end"]}
        best = max(best, len(active))
    return best


def base_env():
    env = dict(os.environ)
    env.pop("MAKEFLAGS", None)
    env.pop("CMAKE_BUILD_PARALLEL_LEVEL", None)
    env["EXP_BALLAST_MIB"] = str(BALLAST_MIB)
    return env


def colcon(ws, args, env, log_name):
    log = ROOT / f"{log_name}.colcon.txt"
    cmd = [sys.executable, "-c", WRAPPER_SRC, str(log), "colcon", "--log-base", str(ws / "log"), "build",
           "--build-base", str(ws / "build"), "--install-base", str(ws / "install"), *args]
    t0 = time.monotonic()
    done = subprocess.run(cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=50)
    wall = time.monotonic() - t0
    info = json.loads(done.stdout.strip().splitlines()[-1])
    return wall, info, log.read_text()


def measure(label, ws, args, makeflags=None, hold_mode="sleep", note=""):
    for src in ws.glob("src/*/*.c"):
        os.utime(src)  # 소스를 고친 것처럼 갱신해 모든 C 파일을 다시 컴파일하게 한다.
    launch_log = ROOT / f"{label}.jobs.jsonl"
    env = base_env()
    env["EXP_LAUNCH_LOG"] = str(launch_log)
    env["EXP_HOLD_MODE"] = hold_mode
    env["EXP_HOLD_SCALE"] = str(CPU_HOLD_SCALE)
    if makeflags is not None:
        env["MAKEFLAGS"] = makeflags
    load_before = os.getloadavg()[0]
    sampler = Sampler()
    sampler.start()
    wall, info, out = colcon(ws, args, env, label)
    sampler.stop_flag.set()
    sampler.join()
    jobs = [json.loads(line) for line in launch_log.read_text().splitlines()] if launch_log.exists() else []
    finished = {m.group(1): float(m.group(2)) for m in re.finditer(r"Finished <<< (\S+) \[([\d.]+)s\]", out)}
    make_j = set()
    for cmd_log in (ws / "log" / "latest_build").glob("*/command.log"):
        make_j.update(re.findall(r"cmake --build \S+ -- (-j\d+ -l\d+)", cmd_log.read_text()))
    emit(kind="condition", label=label, colcon_args=" ".join(args), makeflags=makeflags, hold_mode=hold_mode,
         note=note, exit_code=info["rc"], wall_s=round(wall, 3),
         jobs_total=len(jobs), jobs_failed=sum(j["rc"] != 0 for j in jobs),
         max_concurrent_jobs=max_overlap([(j["start"], j["end"]) for j in jobs]) if jobs else 0,
         max_concurrent_packages=max_packages_overlap(jobs) if jobs else 0,
         sampled_peak_launchers=sampler.peak_launcher_count,
         sum_job_s=round(sum(j["end"] - j["start"] for j in jobs), 3),
         sum_finished_s=round(sum(finished.values()), 2), finished_s=finished,
         sampled_peak_launcher_rss_sum_mib=round(sampler.peak_launcher_sum_kib / 1024, 1),
         sampled_peak_all_rss_sum_mib=round(sampler.peak_all_sum_kib / 1024, 1),
         sampled_max_single_rss_mib=round(sampler.max_single_kib / 1024, 1),
         sampled_max_single_proc=sampler.max_single_name,
         max_job_vmhwm_mib=round(max((j["vmhwm_kib"] for j in jobs), default=0) / 1024, 1),
         ru_maxrss_children_mib=round(info["ru_maxrss_kib"] / 1024, 1),
         loadavg1_before=load_before, sampler_samples=sampler.samples,
         colcon_added_make_args=sorted(make_j))
    if info["rc"] != 0:
        sys.stderr.write(out[-3000:])
        raise SystemExit(f"colcon build failed in {label}")


def main():
    t_start = time.monotonic()
    shutil.rmtree(ROOT, ignore_errors=True)
    ROOT.mkdir(parents=True)
    LAUNCHER.write_text(LAUNCHER_SRC)
    import colcon_core
    try:
        cpu_max = Path("/sys/fs/cgroup/cpu.max").read_text().strip()
    except OSError:
        cpu_max = "unknown"
    pkgs = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${Version}\\n", "python3-colcon-core",
                           "python3-colcon-cmake", "python3-colcon-parallel-executor", "cmake", "make", "gcc"],
                          capture_output=True, text=True).stdout.strip().splitlines()
    emit(kind="environment", os_cpu_count=os.cpu_count(), sched_affinity=len(os.sched_getaffinity(0)),
         cgroup_cpu_max=cpu_max, colcon_core=colcon_core.__version__, packages=pkgs,
         packages_in_workspace=len(PACKAGES), files_per_package=FILES_PER_PACKAGE,
         hold_s=PACKAGES, ballast_mib=BALLAST_MIB, cpu_hold_scale=CPU_HOLD_SCALE)

    indep = make_workspace("indep", chain=False)
    chain = make_workspace("chain", chain=True)
    for ws in (indep, chain):
        env = base_env()
        env["EXP_LAUNCH_LOG"] = str(ROOT / f"warmup_{ws.name}.jobs.jsonl")
        env["EXP_HOLD_MODE"] = "sleep"
        env["EXP_BALLAST_MIB"] = "0"
        wall, info, out = colcon(ws, [], env, f"warmup_{ws.name}")
        emit(kind="warmup", workspace=ws.name, exit_code=info["rc"], wall_s=round(wall, 3),
             note="첫 빌드(CMake configure 포함), 비교에서 제외")
        if info["rc"] != 0:
            sys.stderr.write(out[-3000:])
            raise SystemExit("warmup build failed")

    measure("default", indep, [], note="기본 colcon build")
    measure("sequential", indep, ["--executor", "sequential"])
    measure("sequential_makeflags_j1", indep, ["--executor", "sequential"], makeflags="-j1")
    measure("parallel_workers_1", indep, ["--parallel-workers", "1"])
    measure("quad_core_defaults", indep, ["--parallel-workers", "4"], makeflags="-j4 -l4",
            note="4코어 보드에서 colcon이 쓸 기본값(작업자 4, make -j4 -l4)을 명시적으로 준 조건")
    measure("chain_default", chain, [], note="p30→p40→p50→p60 일렬 의존")
    measure("chain_sequential", chain, ["--executor", "sequential"], note="일렬 의존")
    measure("cpu_default", indep, [], hold_mode="cpu", note="부하를 대기 대신 CPU 소모로(부하 0.5배)")
    measure("cpu_sequential", indep, ["--executor", "sequential"], hold_mode="cpu", note="부하를 대기 대신 CPU 소모로(부하 0.5배)")
    emit(kind="done", total_s=round(time.monotonic() - t_start, 2))


if __name__ == "__main__":
    main()
