#!/usr/bin/env python3
"""colcon build: 무엇이 '다시 빌드할 일'을 줄이는가를 ROS 2 Jazzy 컨테이너 안에서 직접 잰다.

질문
  Q1 바꾼 것이 없어도 colcon build는 선택된 패키지 수만큼 시간이 드는가?
  Q2 COLCON_IGNORE는 colcon이 찾는 패키지 수를 줄이고, 그만큼 무변경 빌드도 줄이는가?
  Q3 --symlink-install이면 Python 파일 수정이 다시 빌드 없이 설치본에 반영되는가?
  Q4 --cmake-args나 --symlink-install을 직전과 다르게 주면 CMake 재구성(configure)이 다시 도는가?
     colcon_defaults.yaml로 인자를 고정하면 재구성이 멈추는가?

모든 시간·개수는 실행 중에 측정한다. 작업공간은 /tmp 안에만 만든다.
결과는 한 줄에 JSON 하나씩 stdout으로 출력한다.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/tmp/colcon_lab")
CMAKE_PKGS = ["cm_1", "cm_2", "cm_3", "cm_4"]
SEQ = ["--executor", "sequential"]
failures = []


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def run(cmd, cwd, label):
    started = time.monotonic()
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    seconds = round(time.monotonic() - started, 3)
    if done.returncode != 0:
        failures.append(label)
        tail = (done.stdout + done.stderr)[-600:]
        emit(step=label, error="nonzero_exit", returncode=done.returncode, tail=tail)
    return seconds, done


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_cmake_pkg(src, name):
    write(src / name / "package.xml", f"""<?xml version="1.0"?>
<package format="3">
  <name>{name}</name>
  <version>0.0.1</version>
  <description>colcon lab cmake package</description>
  <maintainer email="lab@example.com">lab</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
""")
    write(src / name / "CMakeLists.txt", f"""cmake_minimum_required(VERSION 3.8)
project({name} CXX)
find_package(ament_cmake REQUIRED)
add_executable({name}_hello src/hello.cpp)
install(TARGETS {name}_hello DESTINATION lib/${{PROJECT_NAME}})
install(FILES config/params.yaml DESTINATION share/${{PROJECT_NAME}}/config)
if(BUILD_TESTING)
  add_executable({name}_selftest src/hello.cpp)
endif()
ament_package()
""")
    write(src / name / "src" / "hello.cpp", "#include <cstdio>\nint main() { std::puts(\"hello\"); return 0; }\n")
    write(src / name / "config" / "params.yaml", "gain: 1\n")


def make_py_pkg(src, name, value):
    write(src / name / "package.xml", f"""<?xml version="1.0"?>
<package format="3">
  <name>{name}</name>
  <version>0.0.1</version>
  <description>colcon lab python package</description>
  <maintainer email="lab@example.com">lab</maintainer>
  <license>Apache-2.0</license>
  <export><build_type>ament_python</build_type></export>
</package>
""")
    write(src / name / "setup.py", f"""from setuptools import setup
setup(
    name='{name}',
    version='0.0.1',
    packages=['{name}'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/{name}']),
                ('share/{name}', ['package.xml'])],
    zip_safe=True,
)
""")
    write(src / name / "resource" / name, "")
    write(src / name / name / "__init__.py", "")
    write(src / name / name / "core.py", f"VALUE = '{value}'\n")


def cache_mtimes(ws):
    return {p: (ws / "build" / p / "CMakeCache.txt").stat().st_mtime_ns
            for p in CMAKE_PKGS if (ws / "build" / p / "CMakeCache.txt").exists()}


def command_kinds(ws, pkg):
    """colcon이 log/latest_build/<pkg>/command.log에 남긴 호출을 configure/build/install로 분류한다."""
    log = ws / "log" / "latest_build" / pkg / "command.log"
    kinds = []
    for ln in log.read_text().splitlines() if log.exists() else []:
        if not ln.startswith("Invoking command") or "bin/cmake " not in ln:
            continue
        kinds.append("build" if "cmake --build" in ln else "install" if "cmake --install" in ln else "configure")
    return kinds


def configure_invocations(ws):
    return {p: "configure" in command_kinds(ws, p) for p in CMAKE_PKGS}


def cache_value(ws, pkg, key):
    cache = ws / "build" / pkg / "CMakeCache.txt"
    for line in cache.read_text().splitlines() if cache.exists() else []:
        if line.startswith(key + ":"):
            return line.split("=", 1)[1]
    return None


def build(ws, label, extra=(), show_cmake_state=False):
    """colcon build를 한 번 돌리고 시간과 '재구성된 CMake 패키지 수'를 기록한다."""
    before = cache_mtimes(ws)
    seconds, done = run(["colcon", "build", *SEQ, *extra], ws, label)
    after = cache_mtimes(ws)
    configured = configure_invocations(ws)
    record = dict(step=label, args=" ".join(["colcon", "build", *SEQ, *extra]), seconds=seconds,
                  packages_finished=done.stdout.count("Finished <<<"),
                  cmake_configure_invoked=sum(bool(v) for v in configured.values()),
                  cmake_cache_rewritten=sum(before.get(p) != after[p] for p in after))
    if show_cmake_state:
        record["cm_1_BUILD_TESTING_in_cache"] = cache_value(ws, "cm_1", "BUILD_TESTING")
        record["cm_1_AMENT_CMAKE_SYMLINK_INSTALL_in_cache"] = cache_value(ws, "cm_1", "AMENT_CMAKE_SYMLINK_INSTALL")
        makefile = ws / "build" / "cm_1" / "Makefile"
        record["cm_1_selftest_in_generated_makefile"] = makefile.exists() and "cm_1_selftest" in makefile.read_text()
        record["cm_1_commands"] = command_kinds(ws, "cm_1")
    emit(**record)
    return seconds


def repeated(ws, label, cmd, times=3):
    """같은 무변경 빌드를 여러 번 재고 중앙값을 남긴다(한 번만 재면 흔들림이 크다)."""
    samples, finished = [], 0
    for i in range(times):
        seconds, done = run(cmd, ws, f"{label}#{i + 1}")
        samples.append(seconds)
        finished = done.stdout.count("Finished <<<")
    emit(step=label, args=" ".join(cmd), samples_seconds=samples,
         median_seconds=sorted(samples)[len(samples) // 2], packages_finished=finished,
         cmake_configure_invoked=sum(bool(v) for v in configure_invocations(ws).values()),
         cm_1_commands=command_kinds(ws, "cm_1"))


def colcon_list_count(ws):
    _, done = run(["colcon", "list", "--names-only"], ws, "colcon_list")
    return sorted(done.stdout.split())


def installed_value(ws, name):
    """재빌드 없이 install 환경을 source한 새 셸에서 모듈 값을 읽는다."""
    cmd = (f"source {ws}/install/setup.bash && "
           f"python3 -c 'import {name}.core as c; print(c.VALUE)'")
    done = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    return done.stdout.strip() or ("ERROR: " + done.stderr.strip()[-200:])


def main():
    total_started = time.monotonic()
    shutil.rmtree(ROOT, ignore_errors=True)
    colcon_ver = subprocess.run(["bash", "-c", "dpkg-query -W -f='${Version}' python3-colcon-core"],
                                capture_output=True, text=True).stdout.strip()
    emit(step="environment", ros_distro=os.environ.get("ROS_DISTRO"), colcon_core=colcon_ver,
         os_cpu_count=os.cpu_count(), sched_affinity=len(os.sched_getaffinity(0)),
         python=sys.version.split()[0])

    # ---- Q1/Q2/Q4: CMake 패키지 4개 작업공간 -------------------------------------------
    ws = ROOT / "ws_cmake"
    for name in CMAKE_PKGS:
        make_cmake_pkg(ws / "src", name)

    found = colcon_list_count(ws)
    emit(step="discover_all", packages_found=len(found), names=found)

    build(ws, "clean_build_4pkgs", show_cmake_state=True)
    repeated(ws, "nochange_rebuild_4pkgs", ["colcon", "build", *SEQ])
    repeated(ws, "nochange_select_1pkg", ["colcon", "build", *SEQ, "--packages-select", "cm_1"])
    # 기본 실행기(병렬): 같은 무변경 빌드를 병렬로 했을 때의 벽시계 시간
    repeated(ws, "nochange_rebuild_4pkgs_default_executor", ["colcon", "build"])

    # Q2: COLCON_IGNORE 2개
    for name in ("cm_3", "cm_4"):
        (ws / "src" / name / "COLCON_IGNORE").touch()
    found = colcon_list_count(ws)
    emit(step="discover_with_colcon_ignore", ignore_files=2, packages_found=len(found), names=found)
    repeated(ws, "nochange_rebuild_after_ignore_2pkgs", ["colcon", "build", *SEQ])
    for name in ("cm_3", "cm_4"):
        (ws / "src" / name / "COLCON_IGNORE").unlink()
    emit(step="discover_after_ignore_removed", packages_found=len(colcon_list_count(ws)))

    # Q4: 인자를 바꾸면 재구성, 같은 인자를 유지하면 재구성 없음
    build(ws, "nochange_args_changed_BUILD_TESTING_0", ["--cmake-args", "-DBUILD_TESTING=0"], True)
    build(ws, "nochange_args_same_BUILD_TESTING_0", ["--cmake-args", "-DBUILD_TESTING=0"], True)
    build(ws, "nochange_args_dropped_back_to_default", show_cmake_state=True)
    build(ws, "nochange_symlink_install_added", ["--symlink-install"], True)
    build(ws, "nochange_symlink_install_same", ["--symlink-install"], True)

    # colcon_defaults.yaml로 symlink-install을 고정하고 명령줄에서는 빼기
    write(ws / "colcon_defaults.yaml", "build:\n  symlink-install: true\n")
    build(ws, "nochange_defaults_yaml_symlink_fixed", show_cmake_state=True)

    # ament_cmake 설치 자원(YAML)도 symlink인지 확인
    installed_yaml = ws / "install" / "cm_1" / "share" / "cm_1" / "config" / "params.yaml"
    emit(step="ament_cmake_installed_yaml", is_symlink=installed_yaml.is_symlink(),
         points_to_src=str(installed_yaml.resolve()).startswith(str(ws / "src")))

    # ---- Q3: Python 파일 수정이 재빌드 없이 반영되는가 -------------------------------------
    for mode, extra in (("copy", []), ("symlink", ["--symlink-install"])):
        pws = ROOT / f"ws_py_{mode}"
        make_py_pkg(pws / "src", "py_demo", "v1")
        build(pws, f"py_clean_build_{mode}", extra)
        first = installed_value(pws, "py_demo")
        (pws / "src" / "py_demo" / "py_demo" / "core.py").write_text("VALUE = 'v2'\n")
        after_edit = installed_value(pws, "py_demo")
        emit(step=f"py_edit_without_rebuild_{mode}", before_edit=first, after_edit_no_rebuild=after_edit,
             reflected=(after_edit == "v2"))
        if mode == "copy":
            build(pws, "py_rebuild_copy_after_edit", extra)
            emit(step="py_after_rebuild_copy", value=installed_value(pws, "py_demo"))

    emit(step="summary", failures=failures, total_seconds=round(time.monotonic() - total_started, 3))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
