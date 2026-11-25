#!/usr/bin/env python3
"""ROS 2 Jazzy: what /clock pause and backward/forward jumps do to dt, jump callbacks, timers and tf2 buffers.

One container, no network. Every printed line is a JSON object observed at run time; output is compact because
the harness keeps only the tail of stdout. Numbers in this file (/clock values, step sizes, real-time pacing,
timeouts, timer period, integrator x and v, jump thresholds, wait limits) are inputs and limits, not results.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import xml.etree.ElementTree as ET

import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.clock import Clock, ClockType, JumpThreshold
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMsg
from tf2_ros import Buffer, TransformBroadcaster, TransformListener

SEC = 1_000_000_000
DEADLINE_S = 55.0
STEADY = Clock(clock_type=ClockType.STEADY_TIME)
T0 = time.monotonic()
phase = "init"
wait_timeouts = 0


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def s(ns):
    return None if ns is None else round(ns / SEC, 6)


def watchdog():
    emit("error", reason="deadline", phase=phase, elapsed_s=round(time.monotonic() - T0, 2))
    os._exit(3)


threading.Timer(DEADLINE_S, watchdog).start()


def pkg_version(name):
    try:
        return ET.parse(f"/opt/ros/jazzy/share/{name}/package.xml").getroot().findtext("version")
    except Exception as exc:  # noqa: BLE001
        return f"unknown:{type(exc).__name__}"


# --- C++ tf2_ros::Buffer via tf2_echo, started first so its startup overlaps ours ---------------------------
echo_lines = []  # (phase, steady_s, stream, text)
echo_proc = None
echo_exe = "/opt/ros/jazzy/lib/tf2_ros/tf2_echo"
if os.path.exists(echo_exe):
    env = dict(os.environ, RCUTILS_LOGGING_BUFFERED_STREAM="1", RCUTILS_COLORIZED_OUTPUT="0")
    cmd = [echo_exe, "map", "base_link", "--ros-args", "-p", "use_sim_time:=true"]
    if shutil.which("stdbuf"):
        cmd = ["stdbuf", "-oL", "-eL"] + cmd
    echo_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                                 start_new_session=True)

    def reader(stream, name):
        for line in stream:
            echo_lines.append((phase, time.monotonic() - T0, name, line.rstrip()))

    for st, nm in ((echo_proc.stdout, "out"), (echo_proc.stderr, "err")):
        threading.Thread(target=reader, args=(st, nm), daemon=True).start()

rclpy.init()
emit("env", rclpy=pkg_version("rclpy"), rcl=pkg_version("rcl"), tf2_ros=pkg_version("tf2_ros"),
     tf2_ros_py=pkg_version("tf2_ros_py"), rmw=rclpy.get_rmw_implementation_identifier(),
     tf2_echo=bool(echo_proc))

clock_node = Node("sim_clock")
app = Node("app", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
clock_pub = clock_node.create_publisher(ClockMsg, "/clock", 10)
tf_pub = TransformBroadcaster(clock_node)
ros_clock = app.get_clock()

# 0. Before any /clock message.
emit("before_first_clock", now_ns=ros_clock.now().nanoseconds, ros_time_is_active=ros_clock.ros_time_is_active,
     clock_type=ros_clock.clock_type.name)

# Jump callbacks (registered before the first /clock so the 0 -> 10 s step is also visible).
jumps = []


def on_pre():
    jumps.append({"phase": phase, "cb": "pre", "clock_s": s(ros_clock.now().nanoseconds)})


def on_post(time_jump):
    jumps.append({"phase": phase, "cb": "post", "clock_s": s(ros_clock.now().nanoseconds),
                  "change": time_jump.clock_change.name, "delta_s": s(time_jump.delta.nanoseconds)})


jump_handle = ros_clock.create_jump_callback(
    JumpThreshold(min_forward=Duration(seconds=2), min_backward=Duration(nanoseconds=-1), on_clock_change=True),
    pre_callback=on_pre, post_callback=on_post)

# Python tf2 buffer on the sim-time node.
py_buffer = Buffer(node=app)
py_listener = TransformListener(py_buffer, app, spin_thread=False)

executor = SingleThreadedExecutor()
executor.add_node(clock_node)
executor.add_node(app)
spin_thread = threading.Thread(target=executor.spin, daemon=True)
spin_thread.start()


def publish_clock(ns):
    msg = ClockMsg()
    msg.clock = Time(nanoseconds=ns).to_msg()
    clock_pub.publish(msg)


def publish_tf(ns):
    t = TransformStamped()
    t.header.frame_id = "map"
    t.header.stamp = Time(nanoseconds=ns).to_msg()
    t.child_frame_id = "base_link"
    t.transform.translation.x = ns / SEC  # any value; only presence matters
    t.transform.rotation.w = 1.0
    tf_pub.sendTransform(t)


def set_clock(ns, with_tf=False):
    """Publish /clock=ns and wait until the app clock reads it. Returns publish->applied steady seconds."""
    global wait_timeouts
    start = time.monotonic()
    last_pub = -1.0
    while True:
        now = time.monotonic()
        if now - last_pub >= 0.05:
            publish_clock(ns)
            if with_tf:
                publish_tf(ns)
            last_pub = now
        if ros_clock.now().nanoseconds == ns:
            return now - start
        if now - start > 2.0:
            wait_timeouts += 1
            return None
        time.sleep(0.002)


# Wait until tf2_echo and our listener are subscribed to /tf and /clock.
start = time.monotonic()
need = 2 if echo_proc else 1
tf_topic_pub = tf_pub.pub_tf if hasattr(tf_pub, "pub_tf") else None
while time.monotonic() - start < 20.0:
    if echo_proc and echo_proc.poll() is not None:
        need = 1
    clock_subs = clock_pub.get_subscription_count()
    tf_subs = tf_topic_pub.get_subscription_count() if tf_topic_pub else need
    if clock_subs >= need and tf_subs >= need:
        break
    time.sleep(0.05)
time.sleep(0.5)
emit("graph", clock_subscribers=clock_pub.get_subscription_count(),
     tf_subscribers=tf_topic_pub.get_subscription_count() if tf_topic_pub else None,
     waited_s=round(time.monotonic() - start, 2))

# 1 s ROS-time timer, created once the clock reads 10.0 s.
timer_calls = []


def on_timer():
    timer_calls.append({"phase": phase, "ros_s": s(ros_clock.now().nanoseconds),
                        "steady": time.monotonic()})


phase = "first_clock"
set_clock(10 * SEC, with_tf=True)
ros_timer = app.create_timer(1.0, on_timer)  # clock=None -> node ROS clock
emit("timer_created", clock_type=ros_timer.clock.clock_type.name if hasattr(ros_timer, "clock") else None,
     at_s=s(ros_clock.now().nanoseconds), until_next_s=s(ros_timer.time_until_next_call()))


def run_steps(name, start_ns, step_ns, count, real_period, with_tf):
    """Advance /clock in fixed steps at a fixed real-time pace; return per-step ROS and steady dt."""
    global phase
    phase = name
    prev_ros, prev_steady = ros_clock.now(), STEADY.now()
    ros_dt, steady_dt, apply_s = [], [], []
    next_t = time.monotonic()
    for k in range(1, count + 1):
        next_t += real_period
        time.sleep(max(0.0, next_t - time.monotonic()))
        apply_s.append(set_clock(start_ns + k * step_ns, with_tf))
        now_ros, now_steady = ros_clock.now(), STEADY.now()
        ros_dt.append(s((now_ros - prev_ros).nanoseconds))
        steady_dt.append(s((now_steady - prev_steady).nanoseconds))
        prev_ros, prev_steady = now_ros, now_steady
    ok = [a for a in apply_s if a is not None]
    emit("steps", phase=name, ros_dt_s=ros_dt, steady_dt_s=[round(x, 4) for x in steady_dt],
         ros_over_steady=round(sum(ros_dt) / sum(steady_dt), 4),
         clock_apply_max_ms=round(1000 * max(ok), 2) if ok else None,
         end_s=s(ros_clock.now().nanoseconds))


# 1-2. Normal (0.1 s per 0.1 s real) and 2x (0.2 s per 0.1 s real).
run_steps("normal", 10 * SEC, SEC // 10, 10, 0.1, True)
run_steps("x2", 11 * SEC, SEC // 5, 5, 0.1, True)
time.sleep(0.2)


def py_lookup(when):
    try:
        t = py_buffer.lookup_transform("map", "base_link", when)
        return {"ok": True, "stamp_s": s(Time.from_msg(t.header.stamp).nanoseconds)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": type(exc).__name__}


def py_frames():
    return sorted(re.findall(r"^([^\s:]+):", py_buffer.all_frames_as_yaml(), re.M))


py_before = {"frames": py_frames(), "latest": py_lookup(Time()), "at_11.0": py_lookup(Time(nanoseconds=11 * SEC))}

# 3. Pause: hold 12.0 s for 5.5 s real, with a 5 s ROS timer and a 5 s steady timer.
phase = "pause"
pause_ns = 12 * SEC
timeout_calls = {"ros": 0, "steady": 0}
ros_to = app.create_timer(5.0, lambda: timeout_calls.__setitem__("ros", timeout_calls["ros"] + 1))
steady_to = app.create_timer(5.0, lambda: timeout_calls.__setitem__("steady", timeout_calls["steady"] + 1),
                             clock=Clock(clock_type=ClockType.STEADY_TIME))
last_ros, last_steady = ros_clock.now(), STEADY.now()
jumps_before_pause = len(jumps)
hold_until = time.monotonic() + 5.5
while time.monotonic() < hold_until:
    publish_clock(pause_ns)
    time.sleep(0.1)
ros_el, steady_el = ros_clock.now() - last_ros, STEADY.now() - last_steady
limit = Duration(seconds=5)
emit("pause", clock_s=s(pause_ns), ros_elapsed_s=s(ros_el.nanoseconds), steady_elapsed_s=round(s(steady_el.nanoseconds), 3),
     ros_expired=ros_el >= limit, steady_expired=steady_el >= limit,
     ros_timer_5s_calls=timeout_calls["ros"], steady_timer_5s_calls=timeout_calls["steady"],
     jump_callbacks_during_pause=len(jumps) - jumps_before_pause)
app.destroy_timer(ros_to)
app.destroy_timer(steady_to)

before_jump_calls = [c["ros_s"] for c in timer_calls]
until_before = ros_timer.time_until_next_call()

# 4. Backward jump 12.0 -> 9.0.
phase = "backward"
prev = ros_clock.now()
apply = set_clock(9 * SEC)
now = ros_clock.now()
until_after = ros_timer.time_until_next_call()
time.sleep(0.05)
until_after_50ms = ros_timer.time_until_next_call()
dt = now - prev
x, v = 10.0, 2.0
dt_s = dt.nanoseconds / SEC
time.sleep(0.3)
emit("backward_jump", from_s=s(prev.nanoseconds), to_s=s(now.nanoseconds), dt_s=s(dt.nanoseconds),
     dt_negative=dt < Duration(), x_next_m=round(x + v * dt_s, 6), x_next_clamped_m=round(x + v * max(dt_s, 0.0), 6),
     timer_calls_before_s=before_jump_calls, until_next_before_jump_s=s(until_before),
     until_next_immediately_s=s(until_after), until_next_after_50ms_s=s(until_after_50ms), apply_ms=None if apply is None else round(1000 * apply, 2),
     timer_calls_within_0_3s=[c["ros_s"] for c in timer_calls if c["phase"] == "backward"])
py_after = {"frames": py_frames(), "latest": py_lookup(Time()), "at_11.0": py_lookup(Time(nanoseconds=11 * SEC))}
emit("py_tf_buffer", before_jump=py_before, after_jump=py_after)

# 5. Replay 9.0 -> 11.0 s.
n_before = len(timer_calls)
run_steps("replay", 9 * SEC, SEC // 10, 20, 0.05, False)
time.sleep(0.1)
emit("replay_timer", calls_ros_s=[c["ros_s"] for c in timer_calls[n_before:]],
     until_next_s=s(ros_timer.time_until_next_call()))

# 6. Forward jump 11.0 -> 15.5.
phase = "forward"
n_before = len(timer_calls)
pub_t = time.monotonic()
apply = set_clock(15 * SEC + SEC // 2)
time.sleep(0.5)
calls = timer_calls[n_before:]
emit("forward_jump", to_s=s(ros_clock.now().nanoseconds), calls_ros_s=[c["ros_s"] for c in calls],
     first_call_after_publish_ms=round(1000 * (calls[0]["steady"] - pub_t), 2) if calls else None,
     until_next_s=s(ros_timer.time_until_next_call()))
phase = "end"
emit("jump_callbacks", calls=jumps)

# 8. Mixed clock types.
try:
    _ = ros_clock.now() - STEADY.now()
    mixed = "no_error"
except Exception as exc:  # noqa: BLE001
    mixed = type(exc).__name__
emit("mixed_clock_subtract", result=mixed)

# 7. Summarise tf2_echo (C++ tf2_ros::Buffer) output per phase.
if echo_proc:
    time.sleep(0.3)
    os.killpg(echo_proc.pid, signal.SIGINT)
    try:
        echo_proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(echo_proc.pid, signal.SIGKILL)
    time.sleep(0.2)
    summary = {}
    for ph, _, stream, text in list(echo_lines):
        d = summary.setdefault(ph, {"at_time_lines": 0, "last_at_time": None, "failure_lines": 0, "jump_msgs": [],
                                    "other": []})
        m = re.search(r"At time ([0-9.]+)", text)
        if m:
            d["at_time_lines"] += 1
            d["last_at_time"] = float(m.group(1))
        elif "jump" in text.lower():
            d["jump_msgs"].append(f"{stream}:{text[-110:]}")
        elif text.startswith("Failure at"):
            d["failure_lines"] += 1
            if d["failure_lines"] == 1:
                d["other"].append(f"{stream}:{text[-110:]}")
        elif re.fullmatch(r"[\s0-9.eE+-]*", text) or "Translation" in text or "Rotation" in text or text.strip().startswith("-") or not text.strip():
            continue
        elif len(d["other"]) < (6 if ph == "init" else 2):
            d["other"].append(f"{stream}:{text[-110:]}")
    emit("cpp_tf2_echo", exit_code=echo_proc.returncode, phases=summary)

emit("done", wait_timeouts=wait_timeouts, elapsed_s=round(time.monotonic() - T0, 2))
executor.shutdown(timeout_sec=1.0)
rclpy.try_shutdown()
os._exit(0)
