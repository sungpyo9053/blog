#!/usr/bin/env python3
"""새 터미널에서 overlay의 local_setup.bash / setup.bash 하나만 source하면 무엇이 보이는가.

하네스는 이 스크립트를 underlay(/opt/ros/jazzy)가 이미 source된 셸에서 시작한다.
1) 그 환경(= underlay를 source한 빌드 터미널)에서 /tmp/ws에 최소 ament_python 패키지를 만들고
   colcon build로 overlay를 빌드한다.
2) 생성된 install/setup.bash와 install/local_setup.bash에 어떤 상위 prefix가 적혔는지 읽는다.
3) `env -i`로 환경변수를 비운 하위 bash(= 아무것도 source하지 않은 새 터미널 흉내)를 여러 개 띄워
   각각 다른 source 줄을 실행한 뒤 ros2 존재 여부, `ros2 pkg list` 줄 수, ament 색인 직접 계수를 잰다.
모든 숫자는 실행 중에 측정하며, 결과는 JSON 줄로 stdout에 출력한다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

WS = Path("/tmp/ws")
OUT = Path("/tmp/measure")
UNDERLAY = "/opt/ros/jazzy"
PROBES = ["huntlab_probe_a", "huntlab_probe_b", "huntlab_probe_c"]
CLEAN_ENV = {"HOME": "/tmp", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}

# 새 터미널에서 실행할 source 줄. T0는 아무것도 source하지 않은 기준 셸.
TERMINALS = [
    ("T0_nothing", []),
    ("T1_underlay_setup", [f"{UNDERLAY}/setup.bash"]),
    ("T2_overlay_setup", [f"{WS}/install/setup.bash"]),
    ("T3_overlay_local_setup", [f"{WS}/install/local_setup.bash"]),
    ("T4_underlay_setup_then_overlay_local_setup", [f"{UNDERLAY}/setup.bash", f"{WS}/install/local_setup.bash"]),
]


def emit(kind: str, **fields) -> None:
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def write_package(name: str) -> None:
    root = WS / "src" / name
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / "resource").mkdir(exist_ok=True)
    (root / "resource" / name).write_text("")
    (root / name / "__init__.py").write_text("")
    (root / "package.xml").write_text(f"""<?xml version="1.0"?>
<package format="3">
  <name>{name}</name>
  <version>0.0.0</version>
  <description>overlay probe package for the local_setup vs setup experiment</description>
  <maintainer email="lab@example.com">huntlab</maintainer>
  <license>Apache-2.0</license>
  <exec_depend>rclpy</exec_depend>
  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
""")
    (root / "setup.py").write_text(f"""from setuptools import setup
setup(
    name={name!r},
    version='0.0.0',
    packages=[{name!r}],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/{name}']),
        ('share/{name}', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
)
""")
    (root / "setup.cfg").write_text(f"[develop]\nscript_dir=$base/lib/{name}\n"
                                    f"[install]\ninstall_scripts=$base/lib/{name}\n")


def index_names(ament_prefix_path: str) -> set[str]:
    """ament_index_python과 같은 규칙: 각 prefix의 packages 색인에서 점으로 시작하지 않는 파일 이름."""
    names: set[str] = set()
    for prefix in filter(None, ament_prefix_path.split(":")):
        folder = Path(prefix) / "share/ament_index/resource_index/packages"
        if not folder.is_dir():
            continue
        for entry in folder.iterdir():
            if not entry.name.startswith(".") and entry.is_file():
                names.add(entry.name)
    return names


def chain_lines(script: Path) -> list[str]:
    return [line.strip() for line in script.read_text().splitlines()
            if line.strip().startswith("COLCON_CURRENT_PREFIX=")]


def colcon_versions() -> dict:
    done = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${Version}\\n",
                           "python3-colcon-core", "python3-colcon-bash", "python3-colcon-ros"],
                          capture_output=True, text=True)
    return dict(line.split(" ", 1) for line in done.stdout.splitlines() if " " in line)


def run_terminal(label: str, scripts: list[str]) -> dict:
    listing, errors = OUT / f"{label}.list", OUT / f"{label}.err"
    body = "".join(f'source "{s}"\necho "@@SOURCE_EXIT={s}=$?"\n' for s in scripts) + f"""
if command -v ros2 >/dev/null 2>&1; then echo "@@ROS2_PATH=$(command -v ros2)"; else echo "@@ROS2_PATH="; fi
ros2 pkg list >"{listing}" 2>"{errors}"
echo "@@PKG_EXIT=$?"
printf '@@AMENT=%s\\n' "$AMENT_PREFIX_PATH"
printf '@@COLCON=%s\\n' "$COLCON_PREFIX_PATH"
"""
    started = time.monotonic()
    done = subprocess.run(["env", "-i", *[f"{k}={v}" for k, v in CLEAN_ENV.items()],
                           "bash", "--noprofile", "--norc", "-c", body],
                          capture_output=True, text=True, timeout=40)
    seconds = round(time.monotonic() - started, 2)
    marks: dict[str, list[str]] = {}
    for line in done.stdout.splitlines():
        if line.startswith("@@") and "=" in line:
            key, value = line[2:].split("=", 1)
            marks.setdefault(key, []).append(value)
    pkg_exit = int(marks.get("PKG_EXIT", ["-1"])[0])
    listed = [n for n in listing.read_text().splitlines() if n.strip()] if listing.exists() else []
    ament = marks.get("AMENT", [""])[0]
    indexed = index_names(ament)
    err_text = errors.read_text().strip() if errors.exists() else ""
    return {
        "terminal": label,
        "sourced": scripts,
        "source_exit_codes": [int(v.rsplit("=", 1)[1]) for v in marks.get("SOURCE_EXIT", [])],
        "ros2_path": marks.get("ROS2_PATH", [""])[0] or None,
        "ros2_pkg_list_exit": pkg_exit,
        "ros2_pkg_list_lines": len(listed) if pkg_exit == 0 else None,
        "ros2_pkg_list_stderr_head": err_text.splitlines()[0][:160] if err_text else "",
        "index_count": len(indexed),
        "probes_in_index": sum(p in indexed for p in PROBES),
        "probes_in_pkg_list": sum(p in listed for p in PROBES) if pkg_exit == 0 else None,
        "rclpy_in_index": "rclpy" in indexed,
        "ament_prefix_entries": len([p for p in ament.split(":") if p]),
        "underlay_in_ament_prefix_path": UNDERLAY in ament.split(":"),
        "colcon_prefix_path": marks.get("COLCON", [""])[0],
        "shell_seconds": seconds,
        "_names": indexed,
    }


def main() -> int:
    total_started = time.monotonic()
    shutil.rmtree(WS, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for name in PROBES:
        write_package(name)

    emit("environment", ros_distro=os.environ.get("ROS_DISTRO", ""),
         parent_ament_prefix_path=os.environ.get("AMENT_PREFIX_PATH", ""),
         parent_colcon_prefix_path=os.environ.get("COLCON_PREFIX_PATH", ""),
         colcon_packages=colcon_versions())

    started = time.monotonic()
    build = subprocess.run(["colcon", "build", "--parallel-workers", "1", "--event-handlers", "console_direct-"],
                           cwd=WS, capture_output=True, text=True, timeout=120)
    build_seconds = round(time.monotonic() - started, 2)
    emit("build", exit_code=build.returncode, seconds=build_seconds, packages=len(PROBES),
         stdout_tail=build.stdout[-400:], stderr_tail=build.stderr[-400:])
    if build.returncode != 0:
        return 1

    setup, local_setup = WS / "install/setup.bash", WS / "install/local_setup.bash"
    emit("generated_scripts",
         setup_bash_prefix_assignments=chain_lines(setup),
         local_setup_bash_prefix_assignments=chain_lines(local_setup),
         setup_bash_mentions_underlay=UNDERLAY in setup.read_text(),
         local_setup_bash_mentions_underlay=UNDERLAY in local_setup.read_text())

    results = {}
    for label, scripts in TERMINALS:
        record = run_terminal(label, scripts)
        results[label] = record
        emit("terminal", **{k: v for k, v in record.items() if not k.startswith("_")})

    # 판정: U = T1(underlay만)에서 보이는 패키지 수, M = overlay install 폴더 색인에 실제로 설치된 패키지 수.
    # 가설 1(underlay까지 불러옴) 예측 U+M-겹침, 가설 2(overlay만) 예측 M, 기준선 = 두 예측의 중간 (U+M+M)/2.
    u = results["T1_underlay_setup"]["index_count"]
    overlay_names = {f.name for f in (WS / "install").glob("*/share/ament_index/resource_index/packages/*")
                     if f.is_file() and not f.name.startswith(".")}
    m = len(overlay_names)
    overlap = len(results["T1_underlay_setup"]["_names"] & overlay_names)
    baseline = (u + m + m) / 2

    def verdict(label: str) -> dict:
        r = results[label]
        count = r["ros2_pkg_list_lines"] if r["ros2_pkg_list_lines"] is not None else r["index_count"]
        return {"terminal": label, "ros2_available": r["ros2_path"] is not None,
                "count_used": count, "count_source": "ros2_pkg_list" if r["ros2_pkg_list_lines"] is not None
                else "ament_index", "above_baseline": count > baseline,
                "verdict": "underlay_and_overlay_visible" if count > baseline and r["probes_in_index"] == len(PROBES)
                else "overlay_only"}

    cross_check = {label: r["ros2_pkg_list_lines"] == r["index_count"]
                   for label, r in results.items() if r["ros2_pkg_list_lines"] is not None}
    emit("verdict", U=u, M=m, name_overlap=overlap, baseline=baseline,
         hypothesis_underlay_included=u + m - overlap, hypothesis_overlay_only=m,
         T2=verdict("T2_overlay_setup"), T3=verdict("T3_overlay_local_setup"),
         T4_equals_T2=results["T4_underlay_setup_then_overlay_local_setup"]["_names"]
         == results["T2_overlay_setup"]["_names"],
         pkg_list_matches_index=cross_check,
         total_seconds=round(time.monotonic() - total_started, 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
