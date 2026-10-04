#!/usr/bin/env python3
"""ROS 2 Jazzy 컨테이너 안에서 '배포판 선택' 질문의 세 조건을 실행 시점에 잰다.

1. platform: 이 이미지가 실제로 어떤 배포판과 어떤 Ubuntu에 묶여 있는가
   (ROS_DISTRO, /etc/os-release, /opt/ros 아래 배포판 수, ros-* 패키지 이름·버전 접미사,
   apt 저장소 suite).
2. months: 컨테이너 시계의 오늘 날짜로 각 배포판의 EOL까지 남은 개월과
   프로젝트 기간별 여유(남은 개월 - 프로젝트 기간)를 계산한다.
   입력은 공식 Releases 표의 연·월뿐이고 결과는 실행 시점 날짜에 따라 달라진다.
3. same_distro_pubsub: 같은 Jazzy 설치에서 별도 프로세스 두 노드가 std_msgs/String을
   주고받는지(받은 개수, 첫 수신까지 시간, 지연)를 잰다. 배포판 간 통신은 시험하지 않는다.

모든 측정값은 실행 중에 얻어 JSON 한 줄씩 출력한다. 네트워크를 쓰지 않는다.
"""
from __future__ import annotations

import glob
import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

TOPIC = "/distro_check"
MESSAGES = 100

# 입력: ROS 2 공식 Releases 표(ros2_documentation@88573f7, 2026-10-04 확인)의 출시·EOL 연·월.
# Makoa는 출시 예정 배포판이라 지원 기간만 계산하고 남은 개월 판정에서는 '미출시'로 둔다.
OFFICIAL_TABLE = {
    "humble": {"release": (2022, 5), "eol": (2027, 5), "tier1_ubuntu": "22.04"},
    "iron": {"release": (2023, 5), "eol": (2024, 12), "tier1_ubuntu": "22.04"},
    "jazzy": {"release": (2024, 5), "eol": (2029, 5), "tier1_ubuntu": "24.04"},
    "kilted": {"release": (2025, 5), "eol": (2026, 12), "tier1_ubuntu": "24.04"},
    "lyrical": {"release": (2026, 5), "eol": (2031, 5), "tier1_ubuntu": "26.04"},
    "makoa": {"release": (2027, 5), "eol": (2028, 12), "tier1_ubuntu": None},
}
PROJECT_MONTHS = (6, 12, 18, 24, 36)


def emit(kind: str, **fields) -> None:
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def months_between(start: tuple[int, int], end: tuple[int, int]) -> int:
    return (end[0] - start[0]) * 12 + (end[1] - start[1])


def os_release() -> dict:
    values = {}
    with open("/etc/os-release", encoding="utf-8") as handle:
        for line in handle:
            if "=" in line:
                key, value = line.rstrip("\n").split("=", 1)
                values[key] = value.strip('"')
    return values


def measure_platform() -> dict:
    release = os_release()
    codename = release.get("VERSION_CODENAME", "")
    installed = sorted(os.path.basename(p) for p in glob.glob("/opt/ros/*") if os.path.isdir(p))
    rows = subprocess.run(["dpkg-query", "-W", "-f=${db:Status-Abbrev}\t${Package}\t${Version}\n", "ros-*"],
                          capture_output=True, text=True, check=True).stdout.split("\n")
    # dpkg는 의존성으로 이름만 알려진 미설치 패키지도 돌려준다. 설치 상태(ii)만 센다.
    entries = [row.split("\t") for row in rows if row.count("\t") == 2]
    packages = [[name, version] for status, name, version in entries if status.strip() == "ii"]
    known_not_installed = sorted(name for status, name, _ in entries if status.strip() != "ii")
    prefixes: dict[str, int] = {}
    for name, _ in packages:
        parts = name.split("-")
        prefix = parts[1] if len(parts) > 2 else "(none)"
        prefixes[prefix] = prefixes.get(prefix, 0) + 1
    # ROS 빌드팜 데비안 버전은 '<upstream>-<rev><ubuntu codename>.<YYYYMMDD>.<HHMMSS>' 꼴이다.
    stamp = re.compile(r"-\d+([a-z]+)\.(\d{8})\.(\d{6})$")
    suffix_codenames: dict[str, int] = {}
    build_dates = []
    unstamped = []
    for name, version in packages:
        found = stamp.search(version)
        if found:
            suffix_codenames[found.group(1)] = suffix_codenames.get(found.group(1), 0) + 1
            build_dates.append(found.group(2))
        else:
            unstamped.append(f"{name}={version}")
    rclpy = dict(packages).get("ros-jazzy-rclpy", "")
    suites = set()
    for path in glob.glob("/etc/apt/sources.list.d/*") + ["/etc/apt/sources.list"]:
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if "packages.ros.org" not in text:
            continue
        for line in text.splitlines():
            if line.startswith("deb ") and "packages.ros.org" in line:
                suites.add(line.split()[-2] if len(line.split()) >= 4 else line)
            elif line.startswith("Suites:"):
                suites.update(line.split(":", 1)[1].split())
    result = {
        "ros_distro_env": os.environ.get("ROS_DISTRO", ""),
        "ubuntu_version_id": release.get("VERSION_ID", ""),
        "ubuntu_codename": codename,
        "opt_ros_distros": installed,
        "opt_ros_distro_count": len(installed),
        "ros_packages_total": len(packages),
        "ros_packages_known_not_installed": known_not_installed,
        "ros_packages_by_distro_prefix": prefixes,
        "version_suffix_codenames": suffix_codenames,
        "packages_with_build_stamp": len(build_dates),
        "packages_without_build_stamp": unstamped,
        "oldest_build_date": min(build_dates) if build_dates else None,
        "newest_build_date": max(build_dates) if build_dates else None,
        "distinct_build_dates": len(set(build_dates)),
        "rclpy_deb_version": rclpy,
        "ros_apt_suites": sorted(suites),
    }
    distro = result["ros_distro_env"]
    expected = (OFFICIAL_TABLE.get(distro) or {}).get("tier1_ubuntu")
    result["official_tier1_for_running_distro"] = expected
    result["running_ubuntu_matches_official_tier1"] = expected == result["ubuntu_version_id"]
    return result


def measure_months(running_distro: str) -> dict:
    now = datetime.now(timezone.utc)
    today = (now.year, now.month)
    distros = {}
    for name, row in OFFICIAL_TABLE.items():
        released = months_between(row["release"], today) >= 0
        entry = {"support_months_from_table": months_between(row["release"], row["eol"]),
                 "released_by_today": released}
        if released:
            remaining = months_between(today, row["eol"])
            entry["months_remaining"] = remaining
            entry["slack_by_project_months"] = {str(m): remaining - m for m in PROJECT_MONTHS}
        distros[name] = entry
    fits = {str(m): sorted(n for n, e in distros.items()
                           if e.get("released_by_today") and e["months_remaining"] - m >= 0)
            for m in PROJECT_MONTHS}
    eol = OFFICIAL_TABLE[running_distro]["eol"] if running_distro in OFFICIAL_TABLE else None
    latest_start_18 = None
    if eol:
        index = eol[0] * 12 + (eol[1] - 1) - 18
        latest_start_18 = f"{index // 12:04d}-{index % 12 + 1:02d}"
    return {"clock_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reference_year_month": f"{today[0]:04d}-{today[1]:02d}",
            "distros": distros, "released_distros_fitting_project": fits,
            "running_distro": running_distro,
            "running_distro_months_remaining": distros.get(running_distro, {}).get("months_remaining"),
            "running_distro_latest_start_for_18_month_project": latest_start_18}


def run_publisher() -> int:
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String

    rclpy.init()
    node = rclpy.create_node("distro_check_publisher")
    qos = QoSProfile(depth=MESSAGES, reliability=ReliabilityPolicy.RELIABLE)
    publisher = node.create_publisher(String, TOPIC, qos)
    distro = os.environ.get("ROS_DISTRO", "")
    deadline = time.monotonic() + 20.0
    while publisher.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    if publisher.get_subscription_count() < 1:
        node.destroy_node()
        rclpy.shutdown()
        return 2
    for seq in range(MESSAGES):
        msg = String()
        msg.data = f"{distro}|{seq}|{time.monotonic_ns()}"
        publisher.publish(msg)
        time.sleep(0.01)
    time.sleep(1.5)
    node.destroy_node()
    rclpy.shutdown()
    return 0


def measure_pubsub() -> dict:
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String

    rclpy.init()
    node = rclpy.create_node("distro_check_subscriber")
    received: list[tuple[str, int, int, int]] = []

    def on_message(msg: String) -> None:
        arrived = time.monotonic_ns()
        distro, seq, sent = msg.data.split("|")
        received.append((distro, int(seq), int(sent), arrived))

    qos = QoSProfile(depth=MESSAGES, reliability=ReliabilityPolicy.RELIABLE)
    node.create_subscription(String, TOPIC, on_message, qos)
    started = time.monotonic_ns()
    child = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--publisher"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    endpoint = None
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline and len(received) < MESSAGES:
        rclpy.spin_once(node, timeout_sec=0.05)
        # 발견 초기에는 노드 이름이 _NODE_NAME_UNKNOWN_으로 보일 수 있어 이름이 잡힐 때까지 다시 읽는다.
        if endpoint is None or endpoint["node_name"] == "_NODE_NAME_UNKNOWN_":
            infos = node.get_publishers_info_by_topic(TOPIC)
            if infos:
                info = infos[0]
                type_hash = getattr(info, "topic_type_hash", None)
                reliability = info.qos_profile.reliability
                endpoint = {"node_name": info.node_name, "topic_type": info.topic_type,
                            "topic_type_hash": str(type_hash) if type_hash is not None else None,
                            "reliability": getattr(reliability, "name", str(reliability))}
        if child.poll() is not None and len(received) < MESSAGES:
            # 발행자가 끝난 뒤 남은 메시지를 잠깐 더 받는다.
            for _ in range(20):
                rclpy.spin_once(node, timeout_sec=0.05)
            break
    try:
        child_code = child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child_code = -9
    stderr_tail = child.stderr.read()[-300:] if child.stderr else ""
    node.destroy_node()
    rclpy.shutdown()

    latencies = sorted((arrived - sent) / 1e6 for _, _, sent, arrived in received)
    seqs = [seq for _, seq, _, _ in received]
    result = {
        "rmw_implementation_env": os.environ.get("RMW_IMPLEMENTATION") or "(unset: default)",
        "sent": MESSAGES,
        "received": len(received),
        "unique_seq": len(set(seqs)),
        "in_order": seqs == sorted(seqs),
        "publisher_distros_seen": sorted({d for d, _, _, _ in received}),
        "seconds_to_first_message": round((received[0][3] - started) / 1e9, 3) if received else None,
        "latency_ms_median": round(statistics.median(latencies), 3) if latencies else None,
        "latency_ms_p95": round(latencies[int(0.95 * (len(latencies) - 1))], 3) if latencies else None,
        "latency_ms_max": round(latencies[-1], 3) if latencies else None,
        "publisher_endpoint": endpoint,
        "publisher_exit_code": child_code,
    }
    if child_code != 0:
        result["publisher_stderr_tail"] = stderr_tail
    return result


def main() -> int:
    if "--publisher" in sys.argv:
        return run_publisher()
    began = time.monotonic()
    platform = measure_platform()
    emit("platform", **platform)
    months = measure_months(platform["ros_distro_env"])
    emit("months", **months)
    pubsub = measure_pubsub()
    emit("same_distro_pubsub", **pubsub)
    ok = (pubsub["received"] > 0 and pubsub["publisher_distros_seen"] == [platform["ros_distro_env"]])
    emit("summary", ok=ok, running_distro=platform["ros_distro_env"],
         ubuntu=platform["ubuntu_version_id"],
         tier1_match=platform["running_ubuntu_matches_official_tier1"],
         months_remaining=months["running_distro_months_remaining"],
         received=pubsub["received"], sent=pubsub["sent"],
         elapsed_seconds=round(time.monotonic() - began, 2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
