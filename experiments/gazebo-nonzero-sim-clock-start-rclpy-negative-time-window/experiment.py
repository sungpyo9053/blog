#!/usr/bin/env python3
"""rclpy Jazzy: now() - Duration around a simulated clock that starts at S seconds.

No Gazebo. A helper node publishes /clock from S in 10 ms sim steps; a use_sim_time
node computes now() - W in its constructor, in a STEADY (wall) timer and in two
sim-clock timers (10 Hz, 20 Hz), and records what actually happens. Every count
below is measured during the run and printed as one JSON object per line.
"""
import json
import math
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMsg

STEP_NS = 10_000_000          # sim step per /clock message (10 ms)
STEP_WALL = 0.005             # wall period of the /clock publisher (nominal r = 2)
PRE_CLOCK_WALL = 0.5          # wall seconds the subject runs before the first /clock
RUN_SIM_AFTER_START = 2.5     # sim seconds simulated after S
WINDOWS = [0.25, 1.0, 2.0]    # lookback windows W in sim seconds
RATES = [10, 20]              # sim-clock timer rates f in Hz
STARTS = [0.0, 0.5, 1.0, 100.0]
NEG_MSG = "Subtraction leads to negative time."


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def outcome(now, window):
    try:
        result = now - window
    except ValueError as exc:
        return "neg", str(exc)
    return ("zero" if result.nanoseconds == 0 else "pos"), result.nanoseconds


def static_checks():
    zero = Time(nanoseconds=0, clock_type=ClockType.ROS_TIME)
    one_s = Duration(seconds=1.0)
    rec = {"kind": "static"}
    try:
        zero - one_s
        rec["zero_minus_1s"] = "no_exception"
    except ValueError as exc:
        rec["zero_minus_1s"] = {"type": type(exc).__name__, "msg": str(exc),
                                "cause": str(exc.__cause__) if exc.__cause__ else None}
    r = Time(nanoseconds=1_000_000_000, clock_type=ClockType.ROS_TIME) - one_s
    rec["one_s_minus_1s_ns"] = r.nanoseconds
    d = Time(nanoseconds=0, clock_type=ClockType.ROS_TIME) - Time(
        nanoseconds=1_000_000_000, clock_type=ClockType.ROS_TIME)
    rec["time_minus_later_time"] = {"type": type(d).__name__, "ns": d.nanoseconds}
    try:
        _ = zero < one_s
        rec["time_lt_duration"] = "no_exception"
    except TypeError as exc:
        rec["time_lt_duration"] = {"type": "TypeError", "msg": str(exc)}
    emit(rec)


def tf2_zero_check():
    """Does a ROS_TIME Time of 0 (what now - W gives at now == W) mean 'latest' in tf2_ros?"""
    from geometry_msgs.msg import TransformStamped
    from tf2_ros import Buffer
    buf = Buffer(cache_time=Duration(seconds=30.0))
    for sec in (98, 99, 100):
        t = TransformStamped()
        t.header.frame_id = "world"
        t.child_frame_id = "base"
        t.header.stamp.sec = sec
        t.transform.translation.x = float(sec)
        t.transform.rotation.w = 1.0
        buf.set_transform(t, "experiment")
    rec = {"kind": "tf2_time_zero", "stored_stamps_s": [98, 99, 100]}
    for label, query in (("query_zero_ros_time", Time(nanoseconds=0, clock_type=ClockType.ROS_TIME)),
                         ("query_99s", Time(seconds=99, clock_type=ClockType.ROS_TIME))):
        try:
            got = buf.lookup_transform("world", "base", query)
            rec[label] = {"stamp_s": got.header.stamp.sec + got.header.stamp.nanosec * 1e-9,
                          "x": got.transform.translation.x}
        except Exception as exc:  # report the real failure type instead of hiding it
            rec[label] = {"error": type(exc).__name__, "msg": str(exc)[:200]}
    emit(rec)


class ClockPublisher(Node):
    def __init__(self, start_ns, end_ns, context):
        super().__init__("fake_sim_clock", context=context)
        self.pub = self.create_publisher(ClockMsg, "/clock", 10)
        self.start_ns, self.end_ns = start_ns, end_ns
        self.k = 0
        self.matched_at = None
        self.started = False
        self.first_pub_wall = None
        self.timer = self.create_timer(STEP_WALL, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def tick(self):
        if not self.started:
            if self.pub.get_subscription_count() < 1:
                return
            if self.matched_at is None:
                self.matched_at = time.monotonic()
            if time.monotonic() - self.matched_at < PRE_CLOCK_WALL:
                return
            self.started = True
            self.first_pub_wall = time.monotonic()
        ns = self.start_ns + self.k * STEP_NS
        if ns > self.end_ns:
            return
        msg = ClockMsg()
        msg.clock.sec, msg.clock.nanosec = divmod(ns, 1_000_000_000)
        self.pub.publish(msg)
        self.k += 1


class Subject(Node):
    def __init__(self, context):
        super().__init__("subject", context=context,
                         parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        now = self.get_clock().now()
        self.ctor = {"now_ns": now.nanoseconds}
        kind, val = outcome(now, Duration(seconds=1.0))
        self.ctor["minus_1s"] = kind if kind != "neg" else {"neg": val}
        self.first_clock_ns = None
        self.first_clock_wall = None
        self.create_subscription(ClockMsg, "/clock", self.on_clock, 10)
        self.wall = {"calls_now0": 0, "exc_now0": 0, "calls_after_clock": 0, "exc_after_clock": 0}
        self.create_timer(0.05, self.on_wall, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.ticks = {f: [] for f in RATES}
        for f in RATES:
            self.create_timer(1.0 / f, lambda f=f: self.on_sim(f))

    def on_clock(self, msg):
        if self.first_clock_ns is None:
            self.first_clock_ns = msg.clock.sec * 1_000_000_000 + msg.clock.nanosec
            self.first_clock_wall = time.monotonic()

    def on_wall(self):
        now = self.get_clock().now()
        bucket = "now0" if now.nanoseconds == 0 else "after_clock"
        self.wall[f"calls_{bucket}"] += 1
        if outcome(now, Duration(seconds=1.0))[0] == "neg":
            self.wall[f"exc_{bucket}"] += 1

    def on_sim(self, f):
        now = self.get_clock().now()
        self.ticks[f].append((now.nanoseconds, time.monotonic()))


def summarize(start_s, f, ticks, first_clock_wall):
    period_ns = round(1e9 / f)
    rows = {}
    for w in WINDOWS:
        win = Duration(seconds=w)
        counts = {"neg": 0, "zero": 0, "pos": 0}
        first_pos = None
        first_neg_msg = None
        le_guard = {"skipped": 0, "exceptions": 0, "zero_results": 0}
        lt_guard = {"skipped": 0, "exceptions": 0, "zero_results": 0}
        for ns, wall in ticks:
            now = Time(nanoseconds=ns, clock_type=ClockType.ROS_TIME)
            kind, val = outcome(now, win)
            counts[kind] += 1
            if kind == "neg" and first_neg_msg is None:
                first_neg_msg = val
            if kind == "pos" and first_pos is None:
                first_pos = {"now_s": ns / 1e9, "wall_after_first_clock_s":
                             round(wall - first_clock_wall, 3) if first_clock_wall else None}
            # guard A: skip when now <= W ; guard B: skip when now == 0 or now < W
            for guard, skip in ((le_guard, ns <= win.nanoseconds),
                                (lt_guard, ns == 0 or ns < win.nanoseconds)):
                if skip:
                    guard["skipped"] += 1
                    continue
                k2 = outcome(now, win)[0]
                guard["exceptions"] += k2 == "neg"
                guard["zero_results"] += k2 == "zero"
        row = {"neg": counts["neg"], "zero": counts["zero"], "pos": counts["pos"],
               "pos1_now_s": first_pos and first_pos["now_s"],
               "pos1_wall_s": first_pos and first_pos["wall_after_first_clock_s"],
               "le_guard_exc_zero": [le_guard["exceptions"], le_guard["zero_results"]],
               "lt_guard_exc_zero": [lt_guard["exceptions"], lt_guard["zero_results"]]}
        if start_s == 0.0:
            row["model_exc_zero"] = [math.ceil(round(w * f, 9)) - 1,
                                     1 if abs(w * f - round(w * f)) < 1e-9 else 0]
        if first_neg_msg is not None and first_neg_msg != NEG_MSG:
            row["other_neg_msg"] = first_neg_msg
        rows[str(w)] = row
    late = [ns - round(ns / period_ns) * period_ns for ns, _ in ticks if ns > 0]
    return rows, [sum(1 for d in late if d != 0), max(late) / 1e6 if late else None]


def run_scenario(start_s, domain_id):
    ctx = rclpy.Context()
    rclpy.init(context=ctx, domain_id=domain_id)
    start_ns = round(start_s * 1e9)
    end_ns = start_ns + round(RUN_SIM_AFTER_START * 1e9)
    executor = SingleThreadedExecutor(context=ctx)
    created = time.monotonic()
    subject = Subject(ctx)
    pub = ClockPublisher(start_ns, end_ns, ctx)
    executor.add_node(subject)
    executor.add_node(pub)
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.01)
        if subject.get_clock().now().nanoseconds >= end_ns:
            break
    sim_end_wall = time.monotonic()
    reached = subject.get_clock().now().nanoseconds
    first_wall = subject.first_clock_wall
    rec = {"kind": "scenario", "S_s": start_s, "domain_id": domain_id,
           "ctor": subject.ctor, "wall_timer_20hz": subject.wall,
           "pre_clock_wall_s": round(first_wall - created, 3) if first_wall else None,
           "first_clock_received_s": subject.first_clock_ns / 1e9 if subject.first_clock_ns is not None else None,
           "sim_reached_s": reached / 1e9,
           "measured_r": round((reached - (subject.first_clock_ns or 0)) / 1e9 / (sim_end_wall - first_wall), 3)
           if first_wall and sim_end_wall > first_wall else None,
           "timers": {}}
    for f in RATES:
        ticks = subject.ticks[f]
        rows, grid = summarize(start_s, f, ticks, first_wall)
        before = sum(1 for ns, w in ticks if ns == 0 or (first_wall and w < first_wall))
        rec["timers"][f"{f}Hz"] = {"calls": len(ticks), "calls_before_first_clock": before,
                                   "first_call_now_s": ticks[0][0] / 1e9 if ticks else None,
                                   "off_grid_calls_max_ms": grid, "W": rows}
    executor.shutdown()
    subject.destroy_node()
    pub.destroy_node()
    rclpy.shutdown(context=ctx)
    emit(rec)
    return rec


def main():
    t0 = time.monotonic()
    emit({"kind": "env", "rclpy_file": rclpy.__file__})
    static_checks()
    tf2_zero_check()
    recs = [run_scenario(s, 40 + i) for i, s in enumerate(STARTS)]
    emit({"kind": "summary", "scenarios": len(recs),
          "all_reached_end": all(r["sim_reached_s"] >= r["S_s"] + RUN_SIM_AFTER_START for r in recs),
          "ctor_exceptions": sum(isinstance(r["ctor"]["minus_1s"], dict) for r in recs),
          "elapsed_wall_s": round(time.monotonic() - t0, 2)})


if __name__ == "__main__":
    main()
