#!/usr/bin/env python3
"""launch 파일 하나로 로봇 노드와 `ros2 bag record`를 함께 띄웠을 때 bag에서 빠지는 메시지를 잰다.

각 사례마다 /tmp에 Python launch 파일을 만들고 `ros2 launch`로 실행한다. launch 안에는
(1) 로봇 노드 역할의 발행 프로세스(robot.py)와 (2) ExecuteProcess로 띄운 `ros2 bag record`가 있다.
robot.py는 발행할 때마다 자기 발행자의 구독 수를 확인해 "녹화기 구독이 생긴 순간"과
그 전에 이미 보낸 메시지 수를 기록한다. 끝나면 bag을 rosbag2_py로 읽어 실제로 남은 개수와 비교한다.
모든 숫자는 실행 중에 측정하며, 결과는 사례별 JSON 한 줄과 요약 한 줄로 출력한다.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/tmp/rosbag_launch_exp")

ROBOT = r'''
import json, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt32
from rosgraph_msgs.msg import Clock
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster

cfg = json.loads(sys.argv[1])
log = open(cfg["log"], "a", buffering=1)


def emit(**kw):
    kw["t"] = time.monotonic()
    log.write(json.dumps(kw) + "\n")


rclpy.init()
node = Node("robot")
pubs = {name: node.create_publisher(UInt32, name, 10) for name in cfg["rates"]}
static = None
if cfg["tf_static"]:
    static = StaticTransformBroadcaster(node)
    tf = TransformStamped()
    tf.header.stamp = node.get_clock().now().to_msg()
    tf.header.frame_id = "base_link"
    tf.child_frame_id = "camera_link"
    tf.transform.rotation.w = 1.0
    static.sendTransform(tf)
    emit(ev="tf_static_sent")
clock_pub = node.create_publisher(Clock, "/clock", 10) if cfg["clock_wait"] is not None else None

start = time.monotonic()
emit(ev="start")
counts = {n: 0 for n in pubs}
due = {n: start for n in pubs}
matched = {}
recorder_alive = first_clock = None
clock_due = 0.0
clock_count = 0
timed_out = False
while True:
    now = time.monotonic()
    for name, pub in pubs.items():
        if name not in matched and pub.get_subscription_count() > 0:
            matched[name] = now
            emit(ev="matched", topic=name, published_before=counts[name])
        # 일정한 주기를 유지한다: CPU가 밀리면 밀린 만큼 이어서 보낸다.
        while due[name] <= now:
            pub.publish(UInt32(data=counts[name]))
            counts[name] += 1
            due[name] += 1.0 / cfg["rates"][name]
    if static is not None and "/tf_static" not in matched and static.pub_tf.get_subscription_count() > 0:
        matched["/tf_static"] = now
        emit(ev="matched", topic="/tf_static", published_before=1)
    if clock_pub is not None:
        if recorder_alive is None and clock_pub.get_subscription_count() > 0:
            # use_sim_time 노드는 생성 직후 /clock을 구독한다 = 녹화기 노드가 살아 있다는 신호
            recorder_alive = now
            emit(ev="recorder_clock_subscribed", cam_published=counts.get("/cam", 0))
        if recorder_alive is not None and first_clock is None and now >= recorder_alive + cfg["clock_wait"]:
            first_clock = now
            clock_due = now
            emit(ev="first_clock", cam_published=counts.get("/cam", 0), sim_start_s=cfg["sim_start_s"])
        while first_clock is not None and clock_due <= now:
            sim = cfg["sim_start_s"] + (clock_due - first_clock)
            msg = Clock()
            msg.clock.sec = int(sim)
            msg.clock.nanosec = int(round((sim - int(sim)) * 1e9)) % 1000000000
            clock_pub.publish(msg)
            clock_count += 1
            clock_due += 1.0 / cfg["clock_hz"]
    watched = list(pubs) + (["/tf_static"] if static is not None else [])
    if all(w in matched for w in watched) and now >= max(matched[w] for w in watched) + cfg["tail_s"]:
        break
    if now - start > cfg["cap_s"]:
        timed_out = True
        break
    time.sleep(0.001)

emit(ev="done", counts=counts, clock_count=clock_count, timed_out=timed_out)
node.destroy_node()
rclpy.shutdown()
'''

LAUNCH = '''
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction


def generate_launch_description():
    robot = ExecuteProcess(cmd={robot_cmd!r}, output="screen")
    recorder = ExecuteProcess(cmd={rec_cmd!r}, output="screen")
    delay = {delay!r}
    return LaunchDescription([robot, TimerAction(period=delay, actions=[recorder]) if delay > 0 else recorder])
'''

OVERRIDE_YAML = """/tf_static:
  history: keep_last
  depth: 1
  reliability: reliable
  durability: volatile
"""

CASES = [
    # 공식 README처럼 녹화기를 노드와 같은 launch에 지연 없이 넣는다.
    {"name": "A_same_launch_no_timer", "delay": 0.0, "rates": {"/cam": 30, "/imu": 200},
     "tf_static": True, "clock_wait": None, "override": False},
    # 공식 튜토리얼의 TimerAction(period=2.0)으로 녹화기만 2초 늦춘다.
    {"name": "B_timer_2s", "delay": 2.0, "rates": {"/cam": 30, "/imu": 200},
     "tf_static": True, "clock_wait": None, "override": False},
    # --use-sim-time: 녹화기 노드가 뜬 뒤 3초 지나서야 첫 /clock을 보낸다.
    {"name": "C_use_sim_time_first_clock_3s", "delay": 0.0, "rates": {"/cam": 30},
     "tf_static": False, "clock_wait": 3.0, "override": False},
    # QoS override 파일이 /tf_static을 volatile로 덮는다. 녹화기는 1초 늦게 뜬다.
    {"name": "D_override_volatile_tf_static", "delay": 1.0, "rates": {"/cam": 30},
     "tf_static": True, "clock_wait": None, "override": True},
]


def read_events(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_bag(uri):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    meta = (uri / "metadata.yaml").read_text()
    storage = re.search(r"storage_identifier:\s*(\S+)", meta).group(1)
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(uri), storage_id=storage),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: get_message(t.type) for t in reader.get_all_topics_and_types()}
    seqs, stamps = {}, {}
    while reader.has_next():
        topic, data, stamp = reader.read_next()
        msg = deserialize_message(data, types[topic])
        seqs.setdefault(topic, []).append(getattr(msg, "data", None))
        stamps.setdefault(topic, []).append(stamp)
    return storage, seqs, stamps


def run_case(index, case):
    work = ROOT / case["name"]
    work.mkdir(parents=True)
    log = work / "events.jsonl"
    robot_py = work / "robot.py"
    robot_py.write_text(ROBOT)
    cfg = {"log": str(log), "rates": case["rates"], "tf_static": case["tf_static"],
           "clock_wait": case["clock_wait"], "clock_hz": 100, "sim_start_s": 100.0,
           "tail_s": 1.5, "cap_s": 14.0}
    rec_cmd = ["ros2", "bag", "record", "-o", str(work / "bag"), "--topics", *case["rates"]]
    if case["tf_static"]:
        rec_cmd.append("/tf_static")
    if case["clock_wait"] is not None:
        rec_cmd.append("--use-sim-time")
    if case["override"]:
        (work / "override.yaml").write_text(OVERRIDE_YAML)
        rec_cmd += ["--qos-profile-overrides-path", str(work / "override.yaml")]
    launch_file = work / "record.launch.py"
    launch_file.write_text(LAUNCH.format(robot_cmd=["python3", str(robot_py), json.dumps(cfg)],
                                         rec_cmd=rec_cmd, delay=case["delay"]))

    env = dict(os.environ, ROS_DOMAIN_ID=str(20 + index), PYTHONUNBUFFERED="1")
    out = open(work / "launch.out", "w")
    launched = time.monotonic()
    proc = subprocess.Popen(["ros2", "launch", str(launch_file)], stdout=out, stderr=subprocess.STDOUT,
                            env=env, cwd=str(work), start_new_session=True)
    deadline = launched + cfg["cap_s"] + 20
    while time.monotonic() < deadline and not any(e["ev"] == "done" for e in read_events(log)):
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    time.sleep(0.3)
    stop_sent = time.monotonic()
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)  # 터미널의 Ctrl+C와 같은 신호
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
    stopped = time.monotonic()
    out.close()

    events = read_events(log)
    ev = {}
    for e in events:
        ev.setdefault(e["ev"] if e["ev"] != "matched" else "matched:" + e["topic"], e)
    start = ev.get("start", {}).get("t")
    done = ev.get("done", {})
    text = (work / "launch.out").read_text(errors="replace")
    result = {"case": case["name"], "recorder_timer_delay_s": case["delay"],
              "use_sim_time": case["clock_wait"] is not None, "qos_override_volatile_tf_static": case["override"],
              "launch_to_robot_first_publish_s": round(start - launched, 3) if start else None,
              "robot_timed_out": done.get("timed_out"),
              "sigint_to_launch_exit_s": round(stopped - stop_sent, 3),
              "launch_exit_code": proc.returncode}
    try:
        storage, seqs, stamps = read_bag(work / "bag")
        result["bag_storage"] = storage
    except Exception as exc:  # bag이 마무리되지 않았으면 그 사실 자체가 결과다
        seqs, stamps = {}, {}
        result["bag_error"] = f"{type(exc).__name__}: {exc}"

    topics = {}
    for name, rate in case["rates"].items():
        m = ev.get("matched:" + name)
        published = done.get("counts", {}).get(name)
        in_bag = seqs.get(name, [])
        first = min(in_bag) if in_bag else None
        expected_after_first = set(range(first, published)) if first is not None and published else set()
        topics[name] = {
            "rate_hz": rate,
            "published_total": published,
            "recorder_subscribed_s_after_robot_start": round(m["t"] - start, 3) if m and start else None,
            "recorder_subscribed_s_after_launch_start": round(m["t"] - launched, 3) if m else None,
            "published_before_recorder_subscribed": m["published_before"] if m else None,
            "in_bag": len(in_bag),
            "missing_from_bag": (published - len(in_bag)) if published is not None else None,
            "first_seq_in_bag": first,
            "holes_after_first_seq": len(expected_after_first - set(in_bag)),
            "rate_x_timer_delay": round(rate * case["delay"], 3),
        }
    result["topics"] = topics
    if case["tf_static"]:
        m = ev.get("matched:/tf_static")
        sent = ev.get("tf_static_sent", {}).get("t")
        result["tf_static"] = {
            "sent_count": 1,
            "recorder_subscribed_s_after_send": round(m["t"] - sent, 3) if m and sent else None,
            "in_bag": len(seqs.get("/tf_static", [])),
        }
    if case["clock_wait"] is not None:
        alive, first_clock = ev.get("recorder_clock_subscribed"), ev.get("first_clock")
        cam = ev.get("matched:/cam")
        cam_in_bag = seqs.get("/cam", [])
        sim = {"clock_wait_after_recorder_node_s": case["clock_wait"],
               "recorder_node_alive_s_after_robot_start": round(alive["t"] - start, 3) if alive else None,
               "first_clock_s_after_robot_start": round(first_clock["t"] - start, 3) if first_clock else None,
               "cam_subscribed_s_after_first_clock": round(cam["t"] - first_clock["t"], 3)
               if cam and first_clock else None,
               "cam_subscription_existed_before_first_clock": bool(cam and first_clock and cam["t"] < first_clock["t"]),
               "clock_msgs_published": done.get("clock_count")}
        if alive and first_clock:
            lo, hi = alive["cam_published"], first_clock["cam_published"]
            sim["cam_published_while_waiting_for_clock"] = hi - lo
            sim["of_those_in_bag"] = sum(lo <= s < hi for s in cam_in_bag)
            sim["cam_published_before_first_clock"] = hi
            sim["cam_before_first_clock_in_bag"] = sum(s < hi for s in cam_in_bag)
            sim["rate_x_clock_wait"] = round(case["rates"]["/cam"] * case["clock_wait"], 3)
        cam_stamps = stamps.get("/cam", [])
        sim["bag_first_cam_receive_stamp_s"] = round(min(cam_stamps) / 1e9, 3) if cam_stamps else None
        sim["sim_time_of_first_clock_s"] = 100.0
        result["sim_time"] = sim
    result["log_markers"] = {
        "waiting_for_clock": "waiting for /clock before starting recording" in text,
        "clock_found": "Sim time /clock found, starting recording" in text,
        "latched_warning": "latched messages will not be retrieved" in text,
        "all_topics_subscribed": "All requested topics are subscribed" in text,
    }
    exits = re.findall(r"\[(ros2-\d+|python3-\d+)\]: (process has finished cleanly|process has died[^\n]*)", text)
    result["launch_process_exits"] = [f"{n}: {s.strip()}" for n, s in exits]
    codes = re.findall(r"process has died \[pid \d+, exit code (-?\d+), cmd 'ros2 bag record", text)
    result["recorder_exit_code_after_sigint"] = int(codes[0]) if codes else (
        0 if re.search(r"\[ros2-\d+\]: process has finished cleanly", text) else None)
    if "bag_error" in result or not events:
        result["launch_output_tail"] = text[-1500:]
    return result


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    began = time.monotonic()
    results = []
    for index, case in enumerate(CASES):
        r = run_case(index, case)
        results.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)
    summary = {"summary": True, "total_seconds": round(time.monotonic() - began, 2), "cases": {}}
    for r in results:
        summary["cases"][r["case"]] = {
            "missing": {k: v["missing_from_bag"] for k, v in r["topics"].items()},
            "published_before_subscribed": {k: v["published_before_recorder_subscribed"]
                                            for k, v in r["topics"].items()},
            "tf_static_in_bag": r.get("tf_static", {}).get("in_bag"),
            "bag_ok": "bag_error" not in r,
        }
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if all("bag_error" not in r for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
