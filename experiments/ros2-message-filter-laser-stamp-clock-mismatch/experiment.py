#!/usr/bin/env python3
"""레이저 스탬프와 tf 스탬프가 서로 다른 시계에서 오면 무엇이 측정되는가 (ROS 2 Jazzy, rclpy·tf2_ros).

한 프로세스 안에서 다음 노드를 띄운다.
- clock_src: 시스템 시계 타이머로 /clock(시뮬레이션 시각)을 100 Hz로 발행하고, 같은 타이머로
  아래 노드들의 발행 시점을 구동한다(sim 시계 노드의 타이머는 /clock 없으면 멈추기 때문).
- tf_node_<경우>: odom->base_link(동적, 50 Hz)와 base_link->laser(정적)를 자기 시계 스탬프로 발행.
- laser_node_<경우>: LaserScan(20 Hz)을 자기 시계 스탬프로 발행.
- consumer: use_sim_time=True(시뮬레이션 속 RViz·slam_toolbox 같은 위치). tf2_ros.Buffer(기본 캐시
  10 s)와 TransformListener로 tf를 받고, 스캔이 올 때마다 tf2 Buffer에 그 스탬프의 변환을 묻는다.

드롭 판정은 tf2_ros::MessageFilter(C++)의 분기를 Python으로 단순화해 옮긴 판정기다.
  1) can_transform 성공 -> 통과
  2) 실패이고 (요청 시각 + 캐시 길이 < 경로의 최신 공통 시각) -> 즉시 드롭(OutTheBack 경로)
  3) 아니면 대기열(크기 QUEUE)에 넣고, tf가 올 때마다 다시 묻는다. 넘치면 가장 오래된 것 드롭(QueueFull 경로)
변환 가능 여부와 오류 문자열 자체는 실제 tf2 Buffer의 답이다. 모든 숫자는 실행 중에 잰다.
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
import tf2_ros

SIM_START = 120.0          # /clock 시작 값(초). 시뮬레이터가 0 근처에서 시작하는 상황의 대용
QUEUE = 5                  # 판정기 대기열 크기
CACHE_SEC = 10.0           # tf2 BufferCore 기본 캐시 길이와 같게 둔 Buffer 설정값
WINDOW = 2.0               # 경우마다 측정 창(초, 시스템 시계)

CASES = [
    # name, laser_sim, tf_sim, laser_clock_blocked
    ("same_sim", True, True, False),
    ("same_system", False, False, False),
    ("laser_system_tf_sim", False, True, False),
    ("laser_sim_tf_system", True, False, False),
    ("laser_no_clock_yet", True, True, True),
]


def sec(t):
    if hasattr(t, "nanoseconds"):
        return t.nanoseconds / 1e9
    return t.sec + t.nanosec / 1e9


def make_node(name, sim, extra_args=None):
    return Node(name, parameter_overrides=[Parameter("use_sim_time", value=sim)],
                cli_args=extra_args)


class FilterJudge:
    """tf2_ros::MessageFilter의 드롭 분기를 단순화한 판정기. 변환 가능 여부는 실제 tf2 Buffer가 답한다."""

    def __init__(self, buffer, target):
        self.buffer, self.target = buffer, target
        self.queue = []
        self.passed = self.dropped_immediate = self.dropped_queue_full = 0
        self.passed_after_wait = 0
        self.first_error = None

    def _can(self, frame, stamp):
        ok, err = self.buffer.can_transform_core(self.target, frame, stamp)
        if not ok and self.first_error is None:
            self.first_error = str(err)[:170]
        return ok

    def add(self, frame, stamp):
        if self._can(frame, stamp):
            self.passed += 1
            return
        try:
            latest = sec(self.buffer.get_latest_common_time(self.target, frame))
        except Exception:  # 경로가 아직 없으면 최신 시각을 알 수 없다 -> 대기
            latest = 0.0
        if latest != 0.0 and sec(stamp) + CACHE_SEC < latest:
            self.dropped_immediate += 1
            return
        self.queue.append((frame, stamp))
        if len(self.queue) > QUEUE:
            self.queue.pop(0)
            self.dropped_queue_full += 1

    def retry(self):
        keep = []
        for frame, stamp in self.queue:
            if self.buffer.can_transform_core(self.target, frame, stamp)[0]:
                self.passed += 1
                self.passed_after_wait += 1
            else:
                keep.append((frame, stamp))
        self.queue = keep

    def summary(self):
        return {"passed": self.passed, "passed_after_wait": self.passed_after_wait, "drop_immediate": self.dropped_immediate,
                "drop_queue_full": self.dropped_queue_full, "pending": len(self.queue),
                "first_tf2_error": self.first_error}


def measure_log_bracket():
    """sim time 노드가 드롭 로그와 같은 형식으로 한 줄을 찍을 때 대괄호 시각과 at time을 잰다."""
    child = r'''
import json, time, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time as T
rclpy.init()
n = Node("rviz_like", parameter_overrides=[Parameter("use_sim_time", value=True)])
p = Node("clock_src_child")
pub = p.create_publisher(Clock, "/clock", 10)
t0 = time.monotonic()
while n.get_clock().now().nanoseconds == 0 and time.monotonic() - t0 < 10:
    el = time.monotonic() - t0
    pub.publish(Clock(clock=T(sec=120 + int(el), nanosec=int((el % 1) * 1e9))))
    rclpy.spin_once(n, timeout_sec=0.05)
stamp = n.get_clock().now().nanoseconds / 1e9
before = time.time()
n.get_logger().info("Message Filter dropping message: frame 'laser' at time %.3f for reason 'probe'" % stamp)
after = time.time()
print(json.dumps({"stamp": stamp, "before": before, "after": after}), flush=True)
rclpy.shutdown()
'''
    env = dict(os.environ, ROS_DOMAIN_ID="77", RCUTILS_COLORIZED_OUTPUT="0")
    done = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=30, env=env)
    text = done.stdout + "\n" + done.stderr
    line = next((l for l in text.splitlines() if "Message Filter dropping message" in l), "")
    bracket = re.search(r"\[(\d+\.\d+)\]", line)
    at_time = re.search(r"at time (\d+\.\d+)", line)
    info = json.loads(next(l for l in done.stdout.splitlines() if l.startswith("{")))
    b = float(bracket.group(1)) if bracket else None
    a = float(at_time.group(1)) if at_time else None
    return {"kind": "log_bracket", "child_exit": done.returncode,
            "bracket_time": b, "at_time": a,
            "bracket_minus_at_time": round(b - a, 3) if b and a else None,
            "bracket_minus_system_time_s": round(b - info["before"], 4) if b else None,
            "system_time_window_s": round(info["after"] - info["before"], 4)}


def main():
    t_start = time.monotonic()
    print(json.dumps(measure_log_bracket()), flush=True)

    rclpy.init()
    ex = SingleThreadedExecutor()
    clock_src = make_node("clock_src", False)
    clock_pub = clock_src.create_publisher(Clock, "/clock", 10)
    consumer = make_node("consumer", True)
    buffer = tf2_ros.Buffer(cache_time=rclpy.duration.Duration(seconds=CACHE_SEC))
    tf2_ros.TransformListener(buffer, consumer, spin_thread=False)
    ex.add_node(clock_src)
    ex.add_node(consumer)
    t0 = time.monotonic()

    state = {"tick": 0, "case": None}
    latest_dyn = {}     # child frame -> 마지막으로 받은 동적 tf 스탬프(초)
    records = {}

    def on_tf(msg):
        for tr in msg.transforms:
            latest_dyn[tr.child_frame_id] = sec(tr.header.stamp)
        c = state["case"]
        if c:
            for j in records[c]["judges"].values():
                j.retry()

    consumer.create_subscription(TFMessage, "/tf", on_tf, 100)

    def on_scan(msg):
        c = state["case"]
        if not c or not msg.header.frame_id.startswith(c + "/"):
            return
        r = records[c]
        if not r["measuring"]:
            return
        stamp = Time.from_msg(msg.header.stamp)
        s = sec(msg.header.stamp)
        tf_latest = latest_dyn.get(c + "/base_link")
        r["scan_stamps"].append(s)
        if tf_latest is not None:
            r["diffs"].append(s - tf_latest)
            r["tf_latest"].append(tf_latest)
        for j in r["judges"].values():
            j.add(msg.header.frame_id, stamp)
        if r["zero_pair"] is None and s == 0.0:
            # 시각 0으로 조회하면 tf2가 어떤 시각의 변환을 돌려주는가
            try:
                got = buffer.lookup_transform_core(c + "/odom", msg.header.frame_id, stamp)
                r["zero_pair"] = {"lookup_at_0_returned_stamp": round(sec(got.header.stamp), 4),
                                  "tf_latest_at_that_moment": round(tf_latest, 4) if tf_latest else None}
            except Exception as e:
                r["zero_pair"] = {"lookup_error": str(e)[:170]}

    consumer.create_subscription(LaserScan, "/scan", on_scan, 100)

    def tick():
        state["tick"] += 1
        el = time.monotonic() - t0
        clock_pub.publish(Clock(clock=Time(seconds=SIM_START + el).to_msg()))
        c = state["case"]
        if not c:
            return
        r = records[c]
        if state["tick"] % 2 == 0:
            tr = TransformStamped()
            tr.header.stamp = r["tf_node"].get_clock().now().to_msg()
            tr.header.frame_id = c + "/odom"
            tr.child_frame_id = c + "/base_link"
            tr.transform.translation.x = 0.01 * state["tick"]
            tr.transform.rotation.w = 1.0
            r["tf_bc"].sendTransform(tr)
        if state["tick"] % 5 == 0:
            scan = LaserScan()
            scan.header.stamp = r["laser_node"].get_clock().now().to_msg()
            scan.header.frame_id = c + "/laser"
            scan.angle_min, scan.angle_max, scan.angle_increment = -0.5, 0.5, 0.25
            scan.range_min, scan.range_max = 0.1, 10.0
            scan.ranges = [1.0] * 5
            r["scan_pub"].publish(scan)

    clock_src.create_timer(0.01, tick)

    def spin_for(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ex.spin_once(timeout_sec=0.01)

    spin_for(0.5)
    for name, laser_sim, tf_sim, blocked in CASES:
        extra = ["--ros-args", "-r", "/clock:=/clock_not_published"] if blocked else None
        laser_node = make_node("laser_node_" + name, laser_sim, extra)
        tf_node = make_node("tf_node_" + name, tf_sim)
        ex.add_node(laser_node)
        ex.add_node(tf_node)
        static = TransformStamped()
        static.header.stamp = tf_node.get_clock().now().to_msg()
        static.header.frame_id = name + "/base_link"
        static.child_frame_id = name + "/laser"
        static.transform.rotation.w = 1.0
        static_bc = tf2_ros.StaticTransformBroadcaster(tf_node)
        records[name] = {
            "laser_node": laser_node, "tf_node": tf_node,
            "scan_pub": laser_node.create_publisher(LaserScan, "/scan", 10),
            "tf_bc": tf2_ros.TransformBroadcaster(tf_node),
            "judges": {"target_odom_dynamic": FilterJudge(buffer, name + "/odom"),
                       "target_base_link_static_only": FilterJudge(buffer, name + "/base_link")},
            "measuring": False, "scan_stamps": [], "diffs": [], "tf_latest": [], "zero_pair": None,
        }
        state["case"] = name
        # 준비: sim 노드가 /clock을 받고, consumer가 이 경우의 tf를 받을 때까지(최대 5 s)
        ready_deadline = time.monotonic() + 5.0
        while time.monotonic() < ready_deadline:
            static_bc.sendTransform(static)
            spin_for(0.1)
            if (name + "/base_link") in latest_dyn and (not tf_sim or tf_node.get_clock().now().nanoseconds > 0):
                break
        spin_for(0.3)
        r = records[name]
        laser_now = sec(laser_node.get_clock().now())
        tf_now = sec(tf_node.get_clock().now())
        r["measuring"] = True
        spin_for(WINDOW)
        r["measuring"] = False
        state["case"] = None
        d = r["diffs"]
        out = {
            "kind": "case", "case": name,
            "laser_use_sim_time": laser_sim, "tf_use_sim_time": tf_sim, "laser_clock_blocked": blocked,
            "laser_clock_now_s": round(laser_now, 3), "tf_clock_now_s": round(tf_now, 3),
            "scans": len(r["scan_stamps"]),
            "first_scan_stamp_s": round(r["scan_stamps"][0], 3) if r["scan_stamps"] else None,
            "tf_latest_at_first_scan_s": round(r["tf_latest"][0], 3) if r["tf_latest"] else None,
            "diff_laser_minus_tf_median_s": round(statistics.median(d), 4) if d else None,
            "diff_min_s": round(min(d), 4) if d else None,
            "diff_max_s": round(max(d), 4) if d else None,
            "judges": {k: j.summary() for k, j in r["judges"].items()},
        }
        if r["zero_pair"] is not None:
            out["stamp_zero_lookup"] = r["zero_pair"]
        print(json.dumps(out, ensure_ascii=False), flush=True)
        ex.remove_node(laser_node)
        ex.remove_node(tf_node)
        laser_node.destroy_node()
        tf_node.destroy_node()

    print(json.dumps({"kind": "meta", "queue": QUEUE, "cache_s": CACHE_SEC, "window_s": WINDOW,
                      "sim_start_s": SIM_START, "elapsed_s": round(time.monotonic() - t_start, 2)}), flush=True)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
