#!/usr/bin/env python3
"""colcon build 뒤 이미 열어 둔 터미널은 새 패키지를 보는가: 기본 설치와 --merge-install 비교.

질문
  빌드 전에 install/setup.bash를 source한 터미널 T가, 다른 터미널에서 colcon build로
  (1) 기존 패키지만 고쳐 다시 빌드했을 때와 (2) 새 패키지를 추가해 빌드했을 때,
  다시 source하지 않고도 그 결과를 보는가? 기본(isolated) 설치와 merged 설치에서 다른가?

방법
  터미널 T는 계속 살아 있는 bash 프로세스 하나다(환경변수가 명령 사이에 유지된다).
  빌드는 T와 무관한, underlay만 source한 별도 bash에서 한다(공식 권고: 빌드 터미널 분리).
  T에서 각 시점마다 `ros2 pkg list`, AMENT_PREFIX_PATH, `ros2 pkg prefix`, `ros2 run`을 실행해
  나온 값을 그대로 센다. 모든 개수·종료 코드·시간은 실행 중에 측정한다.
  작업공간은 /tmp 안에만 만든다. 결과는 한 줄에 JSON 하나씩 stdout으로 출력한다.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 하네스의 /tmp는 noexec tmpfs라 설치된 실행 파일을 ros2 run이 찾지 못한다(시험 실행에서 확인).
# 그래서 작업공간은 컨테이너 자체 파일시스템(/var/tmp, --rm으로 실행 후 사라짐)에 만든다.
ROOT = Path("/var/tmp/source_lab")
TEMPLATES = ROOT / "templates"
UNDERLAY = "/opt/ros/jazzy/setup.bash"
CLEAN_ENV = {"HOME": "/tmp", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8",
             "ROS_LOG_DIR": "/tmp/roslog"}
INITIAL = ["probe_a", "probe_b", "probe_c"]
NEW = "probe_d"
STARTED = time.monotonic()
failures = []


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def build_shell(script, label, timeout=120):
    """T와 환경을 공유하지 않는 새 bash(underlay만 source)에서 명령을 실행한다."""
    started = time.monotonic()
    done = subprocess.run(["bash", "--noprofile", "--norc", "-c", f"source {UNDERLAY} && {script}"],
                          env=CLEAN_ENV, cwd="/tmp", capture_output=True, text=True, timeout=timeout)
    seconds = round(time.monotonic() - started, 2)
    if done.returncode != 0:
        failures.append(label)
        emit(event="error", step=label, returncode=done.returncode,
             tail=(done.stdout + done.stderr)[-800:])
    return done.returncode, seconds


class Terminal:
    """이미 열려 있는 터미널 T. 같은 bash 프로세스에 명령을 차례로 보낸다."""

    def __init__(self):
        self.proc = subprocess.Popen(["bash", "--noprofile", "--norc"], env=CLEAN_ENV, cwd="/tmp",
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.count = 0

    def run(self, command):
        self.count += 1
        marker = f"__T_DONE_{self.count}__"
        # 자식 명령이 T의 stdin(다음 명령)을 읽지 않도록 </dev/null을 붙인다.
        self.proc.stdin.write(f"{{ {command} ; }} </dev/null\nprintf '\\n{marker} %s\\n' \"$?\"\n")
        self.proc.stdin.flush()
        lines = []
        for line in self.proc.stdout:
            if line.startswith(marker):
                return int(line.split()[1]), "".join(lines).strip("\n")
            lines.append(line)
        raise RuntimeError("terminal T closed unexpectedly")

    def close(self):
        self.proc.stdin.write("exit\n")
        self.proc.stdin.flush()
        self.proc.wait(timeout=10)


def node_file(ws, name):
    return ws / "src" / name / name / f"{name}_node.py"


def set_edit_mark(ws, name, mark):
    path = node_file(ws, name)
    text = path.read_text()
    old = next(line for line in text.splitlines() if "print(" in line)
    path.write_text(text.replace(old, f"    print('Hi from {name}. edit={mark}')"))


def index_markers_on_disk(ws):
    """install/ 아래 어디든 생긴 probe_* 색인 파일 수(터미널과 무관한 디스크 사실)."""
    return len(list((ws / "install").glob("**/share/ament_index/resource_index/packages/probe_*")))


def observe(term, ws, layout, point, checks):
    started = time.monotonic()
    code, listing = term.run("ros2 pkg list 2>/dev/null")
    names = [line.strip() for line in listing.splitlines() if line.strip()]
    probes = sorted(n for n in names if n.startswith("probe_"))
    _, value = term.run('printf "%s" "$AMENT_PREFIX_PATH"')
    entries = [e for e in value.strip().split(":") if e]
    record = {"event": "observe", "layout": layout, "point": point, "pkg_list_exit": code,
              "pkg_total": len(names), "probe_count": len(probes), "probe_pkgs": probes,
              "probe_index_files_on_disk": index_markers_on_disk(ws),
              "ament_prefix_entries": len(entries),
              "overlay_entries": sum(e.startswith(str(ws)) for e in entries),
              "underlay_entries": sum(e.startswith("/opt/ros/") for e in entries),
              "duplicate_entries": len(entries) - len(set(entries)),
              "overlay_entry_paths": [e[len(str(ws)) + 1:] for e in entries if e.startswith(str(ws))]}
    if "run_a" in checks:
        code, out = term.run("timeout 20 ros2 run probe_a probe_a_node 2>&1")
        record["run_probe_a_exit"] = code
        record["run_probe_a_output"] = out.strip()[-80:]
    if "new" in checks:
        code, out = term.run(f"timeout 20 ros2 pkg prefix {NEW} 2>&1")
        record["prefix_probe_d_exit"] = code
        record["prefix_probe_d_output"] = out.strip()[-80:]
        code, out = term.run(f"timeout 20 ros2 run {NEW} {NEW}_node 2>&1")
        record["run_probe_d_exit"] = code
        record["run_probe_d_output"] = out.strip()[-80:]
    record["observe_seconds"] = round(time.monotonic() - started, 2)
    emit(**record)
    return record


def scenario(layout):
    ws = ROOT / ("ws_iso" if layout == "isolated" else "ws_mrg")
    flag = " --merge-install" if layout == "merged" else ""
    (ws / "src").mkdir(parents=True)
    for name in INITIAL:
        shutil.copytree(TEMPLATES / name, ws / "src" / name)
        set_edit_mark(ws, name, 1)
    code, seconds = build_shell(f"cd {ws} && colcon build{flag}", f"{layout}:initial_build")
    layout_marker = (ws / "install" / ".colcon_install_layout")
    emit(event="build", layout=layout, step="initial_build", packages=INITIAL, exit=code,
         seconds=seconds, install_layout_marker=layout_marker.read_text().strip()
         if layout_marker.is_file() else None)
    if code != 0:
        return {}

    term = Terminal()
    term.run(f"source {UNDERLAY}")
    code, _ = term.run(f"source {ws}/install/setup.bash")
    emit(event="terminal_T_sourced", layout=layout, exit=code)
    points = {"before": observe(term, ws, layout, "T_sourced_before_any_rebuild", {"run_a"})}

    # 대조군: 기존 패키지 파일만 고쳐 다른 셸에서 다시 빌드한다(새 prefix 없음).
    set_edit_mark(ws, "probe_a", 2)
    code, seconds = build_shell(f"cd {ws} && colcon build{flag} --packages-select probe_a",
                                f"{layout}:edit_rebuild")
    emit(event="build", layout=layout, step="edit_existing_probe_a_rebuild", exit=code, seconds=seconds)
    points["edit"] = observe(term, ws, layout, "after_edit_rebuild_no_resource", {"run_a"})

    # 새 패키지 추가: 다른 셸에서 빌드하고, T는 다시 source하지 않는다.
    shutil.copytree(TEMPLATES / NEW, ws / "src" / NEW)
    set_edit_mark(ws, NEW, 1)
    code, seconds = build_shell(f"cd {ws} && colcon build{flag} --packages-select {NEW}",
                                f"{layout}:new_package_build")
    emit(event="build", layout=layout, step="new_package_probe_d_build", exit=code, seconds=seconds)
    points["new"] = observe(term, ws, layout, "after_new_pkg_build_no_resource", {"new"})

    # 같은 터미널 T에서 다시 source한다.
    code, _ = term.run(f"source {ws}/install/setup.bash")
    emit(event="terminal_T_resourced", layout=layout, exit=code)
    points["resourced"] = observe(term, ws, layout, "after_resource_same_terminal", {"new"})
    term.close()
    return points


def main():
    TEMPLATES.mkdir(parents=True)
    code, _ = build_shell(
        "ros2 pkg -h >/dev/null && dpkg-query -W -f='${Package} ${Version}\\n' "
        "python3-colcon-core python3-colcon-ros ros-jazzy-ros2pkg ros-jazzy-ament-index-python "
        f"> {ROOT}/versions.txt", "versions")
    versions = (ROOT / "versions.txt").read_text().split("\n") if code == 0 else []
    mounts = {}
    for line in Path("/proc/mounts").read_text().splitlines():
        fields = line.split()
        if fields[1] in ("/tmp", "/"):
            mounts[fields[1]] = {"fstype": fields[2], "noexec": "noexec" in fields[3].split(",")}
    emit(event="env", versions=[" ".join(v.split()[:2]).split("-1noble")[0] for v in versions if v],
         workspace_root=str(ROOT), mounts=mounts)

    pkgs = " ".join(INITIAL + [NEW])
    code, seconds = build_shell(
        f"cd {TEMPLATES} && for p in {pkgs}; do ros2 pkg create --build-type ament_python "
        "--license Apache-2.0 --node-name ${p}_node $p >/dev/null || exit 1; done", "pkg_create")
    emit(event="pkg_create", packages=INITIAL + [NEW], exit=code, seconds=seconds)
    if code != 0:
        emit(event="summary", failures=failures)
        return 1

    summary = {}
    for layout in ("isolated", "merged"):
        points = scenario(layout)
        summary[layout] = {key: {"probe_count": p["probe_count"], "overlay_entries": p["overlay_entries"],
                                 "probe_index_files_on_disk": p["probe_index_files_on_disk"],
                                 **{k: p[k] for k in ("run_probe_a_exit", "prefix_probe_d_exit",
                                                      "run_probe_d_exit") if k in p}}
                           for key, p in points.items()}
    emit(event="summary", layouts=summary, failures=failures,
         total_seconds=round(time.monotonic() - STARTED, 2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
