#!/usr/bin/env python3
"""rclpy Time()/from_msg()/get_clock().now() clock_type mix: what raises TypeError and what does not.

Runs in one process with no network. Every line printed is a JSON object observed at run time.
Inputs (1.5 s, 42.25 s on /clock, timer period) are experiment inputs, not results.
"""
import json
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMsg

T0 = time.monotonic()


def emit(kind, **fields):
    fields = {"kind": kind, **fields}
    print(json.dumps(fields, ensure_ascii=False), flush=True)


def describe(value):
    if isinstance(value, Time):
        return {"type": "Time", "clock_type": value.clock_type.name,
                "nanoseconds": value.nanoseconds, "repr": repr(value)}
    if isinstance(value, Duration):
        return {"type": "Duration", "nanoseconds": value.nanoseconds}
    return {"type": type(value).__name__, "value": value}


def probe(label, expr, fn):
    try:
        out = fn()
    except Exception as exc:  # the exception itself is the measurement
        emit("op", label=label, expr=expr, raised=True,
             exception=type(exc).__name__, message=str(exc))
        return None
    emit("op", label=label, expr=expr, raised=False, result=describe(out))
    return out


def rclpy_version():
    try:
        from importlib.metadata import version
        return version("rclpy")
    except Exception:
        pass
    try:
        import re
        from ament_index_python.packages import get_package_share_directory
        xml = open(get_package_share_directory("rclpy") + "/package.xml").read()
        return re.search(r"<version>([^<]+)</version>", xml).group(1)
    except Exception as exc:
        return f"unknown:{type(exc).__name__}"


def main():
    rclpy.init()
    emit("env", rclpy_version=rclpy_version())

    node = Node("clock_type_probe")
    sim = Node("clock_type_probe_sim",
               parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
    emit("param", node="clock_type_probe", use_sim_time=node.get_parameter("use_sim_time").value)
    emit("param", node="clock_type_probe_sim", use_sim_time=sim.get_parameter("use_sim_time").value)

    # 1) Objects made by each construction path.
    objs = {
        "A": ("Time()", lambda: Time()),
        "B": ("Time(seconds=1.5)", lambda: Time(seconds=1.5)),
        "B2": ("Time(seconds=2, nanoseconds=500000000)", lambda: Time(seconds=2, nanoseconds=500000000)),
        "D": ("node.get_clock().now()  # use_sim_time=False", lambda: node.get_clock().now()),
        "E": ("sim.get_clock().now()  # use_sim_time=True, before any /clock", lambda: sim.get_clock().now()),
        "F": ("Clock().now()", lambda: Clock().now()),
        "G": ("Time(seconds=1.5, clock_type=node.get_clock().clock_type)",
              lambda: Time(seconds=1.5, clock_type=node.get_clock().clock_type)),
    }
    made = {}
    for key, (expr, fn) in objs.items():
        made[key] = probe(f"make_{key}", expr, fn)
    A, B, D, E, F, G = (made[k] for k in ("A", "B", "D", "E", "F", "G"))

    msg = B.to_msg()
    emit("msg", expr="Time(seconds=1.5).to_msg()", sec=msg.sec, nanosec=msg.nanosec)
    msg2 = made["B2"].to_msg()
    emit("msg", expr="Time(seconds=2, nanoseconds=500000000).to_msg()", sec=msg2.sec, nanosec=msg2.nanosec)
    C = probe("make_C", "Time.from_msg(Time(seconds=1.5).to_msg())", lambda: Time.from_msg(msg))
    emit("clock_objects", node_clock=type(node.get_clock()).__name__,
         node_clock_type=node.get_clock().clock_type.name,
         sim_clock=type(sim.get_clock()).__name__, sim_clock_type=sim.get_clock().clock_type.name,
         sim_ros_time_override=sim.get_clock().ros_time_is_active)

    # 2) Operations between them.
    ops = [
        ("B==C", "B == C", lambda: B == C),
        ("B!=C", "B != C", lambda: B != C),
        ("B<C", "B < C", lambda: B < C),
        ("B<=C", "B <= C", lambda: B <= C),
        ("B>C", "B > C", lambda: B > C),
        ("B>=C", "B >= C", lambda: B >= C),
        ("B-C", "B - C", lambda: B - C),
        ("B.ns==C.ns", "B.nanoseconds == C.nanoseconds", lambda: B.nanoseconds == C.nanoseconds),
        ("D-A", "D - A  # now() minus Time()", lambda: D - A),
        ("A<D", "A < D", lambda: A < D),
        ("A==E", "A == E  # both 0 ns?", lambda: A == E),
        ("A.ns==E.ns", "A.nanoseconds == E.nanoseconds", lambda: A.nanoseconds == E.nanoseconds),
        ("C==G", "C == G", lambda: C == G),
        ("D-C", "D - C", lambda: D - C),
        ("D-E", "D - E  # same ROS_TIME, different time source", lambda: D - E),
        ("F-D", "F - D  # Clock().now() minus node now()", lambda: F - D),
        ("B+Dur", "B + Duration(seconds=1)", lambda: B + Duration(seconds=1)),
        ("C-Dur", "C - Duration(seconds=1)", lambda: C - Duration(seconds=1)),
        ("A==None", "A == None", lambda: A == None),  # noqa: E711
        ("A<None", "A < None", lambda: A < None),
        ("positional", "Time(1, 500000000)", lambda: Time(1, 500000000)),
        ("from_msg_sys", "Time.from_msg(msg, clock_type=ClockType.SYSTEM_TIME) == B",
         lambda: Time.from_msg(msg, clock_type=ClockType.SYSTEM_TIME) == B),
    ]
    for label, expr, fn in ops:
        probe(label, expr, fn)

    # 3) use_sim_time=True node after a /clock message arrives: value source vs clock_type.
    pub_node = Node("clock_publisher")
    pub = pub_node.create_publisher(ClockMsg, "/clock", 10)
    ex = SingleThreadedExecutor()
    ex.add_node(sim)
    ex.add_node(pub_node)
    stamp = ClockMsg()
    stamp.clock.sec = 42
    stamp.clock.nanosec = 250000000
    start = time.monotonic()
    published = 0
    received = False
    while time.monotonic() - start < 15.0:
        pub.publish(stamp)
        published += 1
        ex.spin_once(timeout_sec=0.1)
        if sim.get_clock().now().nanoseconds != 0:
            received = True
            break
    waited = time.monotonic() - start
    E2 = sim.get_clock().now()
    emit("sim_clock", published_msgs=published, received=received, waited_s=round(waited, 3),
         after=describe(E2))
    probe("E2-A", "sim now() after /clock minus Time()", lambda: E2 - A)
    probe("E2-C", "sim now() after /clock minus Time.from_msg(...)", lambda: E2 - C)
    ex.remove_node(sim)
    ex.remove_node(pub_node)

    # 4) rosbridge pattern: a timer callback subtracting a Time() cache stamp from node now().
    for variant, make_last in (("Time() cache", lambda n: Time()),
                               ("now() cache", lambda n: n.get_clock().now())):
        tn = Node("cache_cleanup_" + ("bad" if variant.startswith("Time") else "good"))
        last_used = make_last(tn)
        calls = {"n": 0, "ages_ns": []}

        def cleanup(tn=tn, last_used=last_used, calls=calls):
            calls["n"] += 1
            age = tn.get_clock().now() - last_used
            calls["ages_ns"].append(age.nanoseconds)

        tn.create_timer(0.05, cleanup)
        tex = SingleThreadedExecutor()
        tex.add_node(tn)
        escaped = None
        t_start = time.monotonic()
        try:
            while calls["n"] < 5 and time.monotonic() - t_start < 5.0:
                tex.spin_once(timeout_sec=0.5)
        except Exception as exc:
            escaped = {"exception": type(exc).__name__, "message": str(exc)}
        emit("timer", variant=variant, last_used=describe(last_used), callbacks_entered=calls["n"],
             callbacks_completed=len(calls["ages_ns"]),
             min_age_ns=min(calls["ages_ns"]) if calls["ages_ns"] else None,
             exception_escaped_spin_once=escaped)
        tex.remove_node(tn)
        tn.destroy_node()

    pub_node.destroy_node()
    sim.destroy_node()
    node.destroy_node()
    rclpy.shutdown()
    emit("done", elapsed_s=round(time.monotonic() - T0, 3))


if __name__ == "__main__":
    main()
