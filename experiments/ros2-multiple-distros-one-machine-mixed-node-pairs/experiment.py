#!/usr/bin/env python3
"""Jazzy 한 배포판만 있는 컨테이너에서 잴 수 있는 '여러 배포판 운용' 관련 사실을 측정한다.

1. 셸 source 상태별 환경 변수(source 안 함, Jazzy 1회, Jazzy 2회, 없는 배포판 source,
   Jazzy 뒤에 없는 배포판 source)
2. 설치되지 않은 RMW를 가리키는 셸에서 rclpy 노드 생성 결과
3. 같은 배포판·같은 RMW(보장 범위 안) 발행자 1개·구독자 1개 프로세스의 수신 개수

배포판 간 통신, RMW 간 통신, apt 공존은 이 컨테이너로 잴 수 없으므로 재지 않는다.
모든 값은 실행 중에 측정해 JSON 줄로 출력한다.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

N_MESSAGES = 200
PUBLISH_PERIOD_S = 0.01
MATCH_TIMEOUT_S = 15.0
RECEIVE_TIMEOUT_S = 20.0
TOPIC = "distro_check"
CLEAN_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
MISSING_DISTRO = "kilted"
MISSING_RMW = "rmw_cyclonedds_cpp"


def emit(record: dict) -> None:
    print(json.dumps(record, ensure_ascii=False), flush=True)


def split_paths(value: str | None) -> list[str]:
    return [p for p in (value or "").split(":") if p]


# ---------------------------------------------------------------- 1. 셸 상태
def shell_state(name: str, sources: list[str]) -> dict:
    """깨끗한 환경(env -i)의 bash에서 source를 차례로 실행한 뒤 환경을 읽는다."""
    lines = [f"source {s}; echo \"__RC_{i}=$?\" >&2" for i, s in enumerate(sources)]
    script = "\n".join(lines + [
        "printf '__ROS2=%s\\0' \"$(command -v ros2 || true)\"",
        "env -0",
    ])
    started = time.monotonic()
    done = subprocess.run(
        ["env", "-i", "HOME=/tmp", f"PATH={CLEAN_PATH}", "bash", "--noprofile", "--norc", "-c", script],
        capture_output=True, text=True, timeout=30)
    elapsed_ms = (time.monotonic() - started) * 1000
    env: dict[str, str] = {}
    ros2_path = ""
    for item in done.stdout.split("\0"):
        if item.startswith("__ROS2="):
            ros2_path = item[len("__ROS2="):]
        elif "=" in item:
            key, value = item.split("=", 1)
            env[key] = value
    source_rcs = []
    other_stderr = []
    for line in done.stderr.splitlines():
        if line.startswith("__RC_"):
            source_rcs.append(int(line.split("=", 1)[1]))
        elif line.strip():
            other_stderr.append(line.strip())
    ament = split_paths(env.get("AMENT_PREFIX_PATH"))
    path = split_paths(env.get("PATH"))
    pythonpath = split_paths(env.get("PYTHONPATH"))
    ld = split_paths(env.get("LD_LIBRARY_PATH"))
    return {
        "measure": "shell_state",
        "state": name,
        "sources": sources,
        "source_exit_codes": source_rcs,
        "bash_exit_code": done.returncode,
        "stderr_first_line": other_stderr[0][:200] if other_stderr else "",
        "ROS_DISTRO": env.get("ROS_DISTRO"),
        "ROS_VERSION": env.get("ROS_VERSION"),
        "RMW_IMPLEMENTATION": env.get("RMW_IMPLEMENTATION"),
        "ament_prefix_entries": len(ament),
        "ament_prefix_unique": len(set(ament)),
        "path_entries_opt_ros": sum(p.startswith("/opt/ros") for p in path),
        "path_entries_opt_ros_unique": len({p for p in path if p.startswith("/opt/ros")}),
        "pythonpath_entries_opt_ros": sum(p.startswith("/opt/ros") for p in pythonpath),
        "ld_library_path_entries_opt_ros": sum(p.startswith("/opt/ros") for p in ld),
        "ros_env_var_count": sum(k.startswith("ROS_") or k.startswith("AMENT_") for k in env),
        "ros2_on_path": bool(ros2_path),
        "elapsed_ms": round(elapsed_ms, 1),
    }


# ---------------------------------------------------------------- 2. 설치 목록
def inventory() -> dict:
    from ament_index_python.packages import get_packages_with_prefixes
    from ament_index_python import get_resources
    distros = sorted(d for d in os.listdir("/opt/ros") if os.path.isdir(os.path.join("/opt/ros", d)))
    # librmw_<구현>_cpp.so만 센다. 메시지 typesupport(__ 포함)와 공용 라이브러리(_shared_)는 제외.
    rmw_libs = sorted(os.path.basename(p) for p in glob.glob("/opt/ros/*/lib/librmw_*_cpp.so")
                      if "__" not in os.path.basename(p) and "_shared_" not in os.path.basename(p))
    rmw_resources = sorted(get_resources("rmw_typesupport").keys())
    return {
        "measure": "inventory",
        "opt_ros_distros": distros,
        "rmw_typesupport_resources": rmw_resources,
        "rmw_cpp_libraries": rmw_libs,
        "ament_package_count": len(get_packages_with_prefixes()),
        "python": sys.version.split()[0],
        "process_ROS_DISTRO": os.environ.get("ROS_DISTRO"),
    }


# ---------------------------------------------------------------- 3. RMW 선택
PROBE = r"""
import json, time, os
t0 = time.monotonic()
stage = "import"


def reached(name):
    # 단계마다 즉시 출력해 두어, 예외 없이 프로세스가 끝나도 마지막 도달 단계를 알 수 있게 한다.
    print(json.dumps({"reached": name, "elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}), flush=True)


try:
    reached("start")
    import rclpy
    reached("import_ok")
    stage = "init"
    rclpy.init()
    reached("init_ok")
    stage = "create_node"
    node = rclpy.create_node("rmw_probe")
    reached("create_node_ok")
    stage = "done"
    ident = rclpy.get_rmw_implementation_identifier()
    node.destroy_node()
    rclpy.shutdown()
    print(json.dumps({"ok": True, "stage": stage, "rmw_identifier": ident,
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}))
except Exception as exc:
    print(json.dumps({"ok": False, "stage": stage, "exception": type(exc).__name__,
                      "message": str(exc).splitlines()[0][:240] if str(exc) else "",
                      "elapsed_ms": round((time.monotonic() - t0) * 1000, 1)}))
    raise SystemExit(3)
"""


def rmw_probe(rmw: str | None) -> dict:
    env = dict(os.environ)
    env.pop("RMW_IMPLEMENTATION", None)
    if rmw:
        env["RMW_IMPLEMENTATION"] = rmw
    started = time.monotonic()
    done = subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True, env=env, timeout=40)
    wall_ms = (time.monotonic() - started) * 1000
    result: dict = {}
    reached: list[str] = []
    for line in done.stdout.splitlines():
        if line.startswith("{"):
            item = json.loads(line)
            if "reached" in item:
                reached.append(item["reached"])
            else:
                result = item
    stderr_lines = [l.strip() for l in done.stderr.splitlines() if l.strip()]
    rmw_lines = [l for l in stderr_lines if "rmw" in l.lower() or "librmw" in l.lower()]
    return {
        "measure": "rmw_probe",
        "RMW_IMPLEMENTATION": rmw if rmw else "(unset)",
        "exit_code": done.returncode,
        "stages_reached": reached,
        "python_exception_reported": bool(result) and not result.get("ok", False),
        **{f"probe_{k}": v for k, v in result.items()},
        "stderr_line_count": len(stderr_lines),
        "stderr_first_rmw_line": rmw_lines[0][:240] if rmw_lines else "",
        "wall_ms": round(wall_ms, 1),
    }


# ---------------------------------------------------------------- 4. 같은 묶음 발행·구독
def role_subscriber() -> None:
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from std_msgs.msg import String
    rclpy.init()
    node = rclpy.create_node("baseline_listener")
    qos = QoSProfile(depth=N_MESSAGES, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
    seen: list[int] = []
    first_at = [None]

    def on_msg(msg):
        if first_at[0] is None:
            first_at[0] = time.monotonic()
        seen.append(int(msg.data.split(":", 1)[1]))

    node.create_subscription(String, TOPIC, on_msg, qos)
    print(json.dumps({"ready": True}), flush=True)
    deadline = time.monotonic() + RECEIVE_TIMEOUT_S + MATCH_TIMEOUT_S
    while len(seen) < N_MESSAGES and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    last_at = time.monotonic()
    out_of_order = sum(1 for a, b in zip(seen, seen[1:]) if b < a)
    print(json.dumps({
        "role": "subscriber", "received": len(seen), "unique": len(set(seen)),
        "duplicates": len(seen) - len(set(seen)), "out_of_order": out_of_order,
        "first_seq": seen[0] if seen else None, "last_seq": seen[-1] if seen else None,
        "receive_span_ms": round((last_at - first_at[0]) * 1000, 1) if first_at[0] else None,
        "ROS_DISTRO": os.environ.get("ROS_DISTRO"),
        "rmw_identifier": rclpy.get_rmw_implementation_identifier(),
    }), flush=True)
    node.destroy_node()
    rclpy.shutdown()


def role_publisher() -> None:
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from std_msgs.msg import String
    rclpy.init()
    node = rclpy.create_node("baseline_talker")
    qos = QoSProfile(depth=N_MESSAGES, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
    pub = node.create_publisher(String, TOPIC, qos)
    t0 = time.monotonic()
    while pub.get_subscription_count() < 1 and time.monotonic() - t0 < MATCH_TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.05)
    match_ms = (time.monotonic() - t0) * 1000
    matched = pub.get_subscription_count()
    info = node.get_subscriptions_info_by_topic(TOPIC)
    type_hash = ""
    if info:
        type_hash = str(getattr(info[0], "topic_type_hash", ""))
    sent = 0
    send_start = time.monotonic()
    if matched:
        for i in range(N_MESSAGES):
            pub.publish(String(data=f"seq:{i}"))
            sent += 1
            time.sleep(PUBLISH_PERIOD_S)
    send_ms = (time.monotonic() - send_start) * 1000
    linger_end = time.monotonic() + 2.0
    while time.monotonic() < linger_end:
        rclpy.spin_once(node, timeout_sec=0.05)
    print(json.dumps({
        "role": "publisher", "matched_subscriptions": matched, "match_wait_ms": round(match_ms, 1),
        "sent": sent, "send_ms": round(send_ms, 1),
        "subscription_endpoint_count": len(info),
        "subscription_type_hash_prefix": type_hash.split("_", 1)[0] if type_hash else "",
        "subscription_type_hash_len": len(type_hash),
        "ROS_DISTRO": os.environ.get("ROS_DISTRO"),
        "rmw_identifier": rclpy.get_rmw_implementation_identifier(),
    }), flush=True)
    node.destroy_node()
    rclpy.shutdown()


def last_json(text: str) -> dict:
    found: dict = {}
    for line in text.splitlines():
        if line.startswith("{"):
            try:
                found = json.loads(line)
            except json.JSONDecodeError:
                pass
    return found


def baseline_pair() -> dict:
    env = dict(os.environ)
    env.pop("RMW_IMPLEMENTATION", None)
    started = time.monotonic()
    sub = subprocess.Popen([sys.executable, __file__, "--role", "sub"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, env=env)
    ready_line = sub.stdout.readline()
    pub = subprocess.Popen([sys.executable, __file__, "--role", "pub"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, env=env)
    pub_out, pub_err = pub.communicate(timeout=MATCH_TIMEOUT_S + RECEIVE_TIMEOUT_S + 10)
    sub_out, sub_err = sub.communicate(timeout=MATCH_TIMEOUT_S + RECEIVE_TIMEOUT_S + 10)
    p, s = last_json(pub_out), last_json(sub_out)
    return {
        "measure": "baseline_same_distro_same_rmw",
        "messages_planned": N_MESSAGES,
        "subscriber_ready_signal": bool(ready_line.strip()),
        "publisher_exit_code": pub.returncode,
        "subscriber_exit_code": sub.returncode,
        "publisher": p,
        "subscriber": s,
        "received_ratio": round(s.get("received", 0) / p["sent"], 4) if p.get("sent") else None,
        "pub_stderr_tail": pub_err.strip().splitlines()[-1][:200] if pub_err.strip() else "",
        "sub_stderr_tail": sub_err.strip().splitlines()[-1][:200] if sub_err.strip() else "",
        "wall_ms": round((time.monotonic() - started) * 1000, 1),
    }


def main() -> int:
    total_start = time.monotonic()
    emit(inventory())
    jazzy = "/opt/ros/jazzy/setup.bash"
    missing = f"/opt/ros/{MISSING_DISTRO}/setup.bash"
    for name, sources in [
        ("no_source", []),
        ("jazzy_once", [jazzy]),
        ("jazzy_twice", [jazzy, jazzy]),
        ("missing_distro_only", [missing]),
        ("jazzy_then_missing_distro", [jazzy, missing]),
    ]:
        emit(shell_state(name, sources))
    for rmw in (None, "rmw_fastrtps_cpp", MISSING_RMW):
        emit(rmw_probe(rmw))
    pair = baseline_pair()
    emit(pair)
    emit({"measure": "summary", "total_wall_s": round(time.monotonic() - total_start, 2)})
    ok = pair["publisher_exit_code"] == 0 and pair["subscriber_exit_code"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--role":
        role_subscriber() if sys.argv[2] == "sub" else role_publisher()
        raise SystemExit(0)
    raise SystemExit(main())
