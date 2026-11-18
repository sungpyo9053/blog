#!/usr/bin/env python3
"""ROS 2 Jazzy: normalize device velocity to m/s at the input boundary and check it by distance.

A device node streams raw TwistStamped samples whose numbers are in the device unit. Four adapter
nodes (one correct, three deliberately wrong) normalize them with a `source_unit` parameter and
republish TwistStamped. Odometry nodes integrate dx = v * dt from header stamps and broadcast /tf;
a checker reads the distance back from a tf2 buffer. Every printed line is a JSON object observed
at run time.

Numbers in this file are inputs (the article's case values and hold times, control period, SI
prefix exponents, the wrong adapter's /1000), wait limits, and the article's claimed distances,
which are used only as the test oracle and never printed as results.
"""
import importlib
import json
import math
import os
import re
import statistics
import subprocess
import struct
import sys
import threading
import time

import rclpy
from geometry_msgs.msg import TransformStamped, Twist, TwistStamped, Vector3
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.serialization import deserialize_message, serialize_message
from rclpy.time import Time
from std_msgs.msg import String
from tf2_ros import Buffer, TransformBroadcaster, TransformListener

T_START = time.monotonic()

CONTROL_NS = 50_000_000                  # 20 Hz control period
# Article's cases: id, raw device number, source unit, hold time [ns].
CASES = [
    ("A", 250.0, "mm/s", 400_000_000),
    ("B", 0.25, "m/s", 400_000_000),
    ("C_missing", 250.0, "", 400_000_000),
    ("C_unsupported", 250.0, "kn", 400_000_000),
    ("D", 500.0, "mm/s", 200_000_000),
    ("E", 80.0, "cm/s", 500_000_000),
]
# Article's claims, used only as the oracle the test compares against.
ARTICLE_EXPECTED_M = {"A": 0.1, "B": 0.1, "D": 0.1, "E": 0.4}
ARTICLE_FAILURE_M = {("no_convert", "A"): 100.0, ("always_div", "B"): 0.0001,
                     ("no_convert", "D"): 100.0, ("no_convert", "E"): 40.0}
ISCLOSE_REL = 1e-9                       # article's arithmetic comparison tolerance (math.isclose default)

SI_PREFIX_EXP = {"m/s": 0, "cm/s": -2, "mm/s": -3}   # BIPM: centi 10^-2, milli 10^-3

SYNTH_BASE_NS = 1_000_000_000_000       # tf2 treats stamp 0 as "latest": synthetic stamps start at 1000 s
SYNTH_GAP_NS = 10_000_000_000
REPEATS = 10
WAIT_S = 5.0
QOS = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False, separators=(",", ":")), flush=True)


def r(x, n=6):
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return float(f"{x:.{n}g}")


def bits(x):
    return struct.pack("<d", x)


def version_of(pkg):
    try:
        from ament_index_python.packages import get_package_share_directory
        xml = open(get_package_share_directory(pkg) + "/package.xml").read()
        return re.search(r"<version>([^<]+)</version>", xml).group(1)
    except Exception as exc:  # noqa: BLE001
        return f"unknown:{type(exc).__name__}"


# ---------------------------------------------------------------- normalizers under test
def normalize_correct(value, unit):
    if unit not in SI_PREFIX_EXP:
        raise ValueError(f"missing or unsupported unit {unit!r}")
    return value / 10 ** -SI_PREFIX_EXP[unit]


def normalize_no_convert(value, unit):
    return value                         # reads the raw number as m/s


def normalize_always_div(value, unit):
    return value / 1000                  # divides even inputs that are already SI


def normalize_silent_default(value, unit):
    return normalize_correct(value, unit if unit in SI_PREFIX_EXP else "m/s")


ADAPTERS = {"correct": normalize_correct, "no_convert": normalize_no_convert,
            "always_div": normalize_always_div, "silent_default": normalize_silent_default}
# Odometry implementations: name -> (adapter feeding it, seconds per stamp nanosecond).
ODOMS = {"correct": ("correct", 1e-9), "no_convert": ("no_convert", 1e-9),
         "always_div": ("always_div", 1e-9), "silent_default": ("silent_default", 1e-9),
         "dt_ms": ("correct", 1e-6)}     # stamp difference taken as milliseconds, used as seconds

CV = threading.Condition()
COUNT = {}                               # cumulative message counters, guarded by CV


def bump(key):
    with CV:
        COUNT[key] = COUNT.get(key, 0) + 1
        CV.notify_all()


# ---------------------------------------------------------------- nodes
class Device(Node):
    def __init__(self):
        super().__init__("device")
        self.pub = self.create_publisher(TwistStamped, "/device/raw_twist", QOS)

    def send(self, value, stamp_ns=None):
        msg = TwistStamped()
        msg.header.stamp = (Time(nanoseconds=stamp_ns) if stamp_ns is not None else self.get_clock().now()).to_msg()
        msg.header.frame_id = "device_link"
        msg.twist.linear.x = value
        self.pub.publish(msg)
        return Time.from_msg(msg.header.stamp).nanoseconds


class Adapter(Node):
    def __init__(self, impl):
        super().__init__(f"adapter_{impl}")
        self.impl, self.normalize = impl, ADAPTERS[impl]
        self.declare_parameter("source_unit", "m/s")
        self.pub = self.create_publisher(TwistStamped, f"/{impl}/cmd_vel", QOS)
        self.err = self.create_publisher(String, "/unit_error", QOS)
        self.create_subscription(TwistStamped, "/device/raw_twist", self.on_raw, QOS)

    def on_raw(self, msg):
        unit = self.get_parameter("source_unit").value
        try:
            v = self.normalize(msg.twist.linear.x, unit)
        except ValueError as exc:
            self.err.publish(String(data=f"{self.impl}: {exc}"))
            bump(f"err:{self.impl}")
        else:
            out = TwistStamped()
            out.header = msg.header
            out.twist.linear.x = v
            self.pub.publish(out)
            bump(f"pub:{self.impl}")
        bump(f"proc:{self.impl}")


class Odom(Node):
    def __init__(self, impl):
        super().__init__(f"odom_{impl}")
        self.impl = impl
        source, self.dt_scale = ODOMS[impl]
        self.lock = threading.Lock()
        self.reset()
        self.pub = self.create_publisher(Odometry, f"/odom_{impl}", QOS)
        self.tf = TransformBroadcaster(self)
        self.create_subscription(TwistStamped, f"/{source}/cmd_vel", self.on_cmd, QOS)

    def reset(self):
        with self.lock:
            self.prev, self.x, self.x_recv, self.n = None, 0.0, 0.0, 0

    def on_cmd(self, msg):
        t_ns = Time.from_msg(msg.header.stamp).nanoseconds
        recv_ns = self.get_clock().now().nanoseconds
        with self.lock:
            if self.prev is not None:
                pt, pv, pr = self.prev
                self.x += pv * (t_ns - pt) * self.dt_scale          # hold previous command until this stamp
                self.x_recv += pv * (recv_ns - pr) * 1e-9
            self.prev = (t_ns, msg.twist.linear.x, recv_ns)
            self.n += 1
            x = self.x
        od = Odometry()
        od.header.stamp = msg.header.stamp
        od.header.frame_id = f"odom_{self.impl}"
        od.child_frame_id = f"base_{self.impl}"
        od.pose.pose.position.x = x
        od.pose.pose.orientation.w = 1.0
        od.twist.twist.linear.x = msg.twist.linear.x
        self.pub.publish(od)
        tf = TransformStamped()
        tf.header = od.header
        tf.child_frame_id = od.child_frame_id
        tf.transform.translation.x = x
        tf.transform.rotation.w = 1.0
        self.tf.sendTransform(tf)
        bump(f"odom:{self.impl}")


class Checker(Node):
    def __init__(self):
        super().__init__("checker")
        self.buffer = Buffer(cache_time=Duration(seconds=60))
        self.listener = TransformListener(self.buffer, self)
        self.odom_x, self.raw, self.errors, self.frames = {}, [], [], {}
        for impl in ODOMS:
            self.create_subscription(Odometry, f"/odom_{impl}", lambda m, i=impl: self.on_odom(i, m), QOS)
        self.create_subscription(String, "/unit_error", self.on_err, QOS)
        self.create_subscription(TwistStamped, "/device/raw_twist", self.on_raw, QOS)

    def on_odom(self, impl, msg):
        with CV:
            self.odom_x[(impl, Time.from_msg(msg.header.stamp).nanoseconds)] = msg.pose.pose.position.x
            self.frames[impl] = (msg.header.frame_id, msg.child_frame_id)
        bump(f"chk_odom:{impl}")

    def on_err(self, msg):
        with CV:
            self.errors.append(msg.data)
        bump("chk_err")

    def on_raw(self, msg):
        with CV:
            self.raw.append(msg.twist.linear.x)
        bump("chk_raw")


# ---------------------------------------------------------------- message-level checks
def field_walk(type_name, seen, unit_fields):
    base = re.sub(r"\[.*\]$", "", type_name.replace("sequence<", "").rstrip(">"))
    if "/" not in base or base in seen:
        return
    pkg, name = base.split("/")
    cls = getattr(importlib.import_module(f"{pkg}.msg"), name)
    fields = cls.get_fields_and_field_types()
    seen[base] = fields
    for fname, ftype in fields.items():
        if "unit" in fname.lower():
            unit_fields.append(f"{base}.{fname}")
        field_walk(ftype, seen, unit_fields)


def message_checks():
    seen, unit_fields = {}, []
    for t in ("geometry_msgs/TwistStamped", "nav_msgs/Odometry"):
        field_walk(t, seen, unit_fields)
    emit("schema", Vector3=seen["geometry_msgs/Vector3"], Twist=seen["geometry_msgs/Twist"],
         TwistStamped=seen["geometry_msgs/TwistStamped"], Odometry=seen["nav_msgs/Odometry"],
         types_walked=len(seen), unit_fields=len(unit_fields), unit_field_names=unit_fields)

    wire = {}
    for label, value in (("raw_250", 250.0), ("si_0.25", 0.25)):
        msg = Twist()
        msg.linear.x = value
        data = serialize_message(msg)
        back = deserialize_message(data, Twist)
        wire[label] = {"bytes": len(data), "roundtrip_bits_equal": bits(back.linear.x) == bits(value)}

    # A wrong Python type can abort the C serializer, so each probe runs in its own child process.
    probe = ("import sys\nfrom geometry_msgs.msg import Vector3\nfrom rclpy.serialization import serialize_message\n"
             "value, kw = eval(sys.argv[1]), eval(sys.argv[2])\n"
             "try:\n    msg = Vector3(x=value, **kw)\nexcept Exception as exc:\n"
             "    print('construct:' + type(exc).__name__); sys.exit(0)\n"
             "print('constructed', flush=True)\nserialize_message(msg)\nprint('serialized')\n")

    def attempt(value, **kw):
        """Construct a Vector3, then serialize it: which step (if any) rejects the value, and how?"""
        try:
            done = subprocess.run([sys.executable, "-c", probe, repr(value), repr(kw)],
                                  capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return "timeout"
        out = done.stdout.split()
        if out and out[-1].startswith("construct:"):
            return out[-1]
        if out[-1:] == ["serialized"]:
            return "accepted"
        tail = done.stderr.strip().splitlines()[-1:] or [""]
        return f"serialize:exit{done.returncode}:{tail[0][-60:]}"
    emit("wire", serialized=wire, same_length=wire["raw_250"]["bytes"] == wire["si_0.25"]["bytes"],
         ROS_PYTHON_CHECK_FIELDS=os.environ.get("ROS_PYTHON_CHECK_FIELDS"),
         default={"int": attempt(250), "str": attempt("250 mm/s"), "float": attempt(250.0)},
         check_fields={"int": attempt(250, check_fields=True), "str": attempt("250 mm/s", check_fields=True),
                       "float": attempt(250.0, check_fields=True)})


# ---------------------------------------------------------------- one case through the ROS graph
def snapshot():
    with CV:
        return dict(COUNT)


def wait_drained(before, sent, stats):
    """Block until every adapter, odometry and checker callback has handled this case's messages."""
    def done():
        d = {k: COUNT.get(k, 0) - before.get(k, 0) for k in set(COUNT) | set(before)}
        if any(d.get(f"proc:{a}", 0) < sent for a in ADAPTERS) or d.get("chk_raw", 0) < sent:
            return False
        if any(d.get(f"odom:{o}", 0) < d.get(f"pub:{src}", 0) for o, (src, _) in ODOMS.items()):
            return False
        if any(d.get(f"chk_odom:{o}", 0) < d.get(f"odom:{o}", 0) for o in ODOMS):
            return False
        return d.get("chk_err", 0) >= sum(d.get(f"err:{a}", 0) for a in ADAPTERS)
    with CV:
        if not CV.wait_for(done, timeout=WAIT_S):
            stats["timeouts"] += 1
        return {k: COUNT.get(k, 0) - before.get(k, 0) for k in COUNT}


def run_case(case, nodes, mode, stats, synth_base_ns=None):
    cid, value, unit, hold_ns = case
    device, adapters, odoms, checker = nodes
    for a in adapters.values():
        a.set_parameters([Parameter("source_unit", Parameter.Type.STRING, unit)])
    for o in odoms.values():
        o.reset()
    n = hold_ns // CONTROL_NS
    assert n * CONTROL_NS == hold_ns
    raw_before = len(checker.raw)
    before = snapshot()
    stamps = []
    t0 = time.monotonic()
    for k in range(n + 1):
        v = value if k < n else 0.0                       # last sample: explicit zero-velocity stop
        if mode == "synthetic":
            stamps.append(device.send(v, synth_base_ns + k * CONTROL_NS))
        else:
            delay = t0 + k * CONTROL_NS * 1e-9 - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            stamps.append(device.send(v))
    d = wait_drained(before, n + 1, stats)
    with CV:
        raw_ok = all(bits(x) == bits(value if i < n else 0.0)
                     for i, x in enumerate(checker.raw[raw_before:raw_before + n + 1]))
    stop_ns = stamps[-1]
    out = {"case": cid, "dt_s": (stop_ns - stamps[0]) * 1e-9, "raw_bits_equal": raw_ok,
           "errors": {a: d.get(f"err:{a}", 0) for a in ADAPTERS}, "impl": {}}
    for impl, (src, _) in ODOMS.items():
        node = odoms[impl]
        with node.lock:
            got, x_recv, x_internal = node.n, node.x_recv, node.x
        row = {"cmds": got, "src_errors": d.get(f"err:{src}", 0)}
        if got:
            try:
                tf = checker.buffer.lookup_transform(f"odom_{impl}", f"base_{impl}", Time(nanoseconds=stop_ns),
                                                     timeout=Duration(seconds=2))
                row["tf_x"] = tf.transform.translation.x
            except Exception as exc:  # noqa: BLE001
                stats["timeouts"] += 1
                row["tf_error"] = type(exc).__name__
            with CV:
                odom_x = checker.odom_x.get((impl, stop_ns))
            row["odom_minus_tf"] = (odom_x - row["tf_x"]) if odom_x is not None and "tf_x" in row else None
            row["internal_minus_tf"] = (x_internal - row["tf_x"]) if "tf_x" in row else None
            row["recv_x"] = x_recv
        out["impl"][impl] = row
    return out


def passes(cid, row):
    """The article's test: a numeric case must match its distance; a C case must give an error, no number."""
    if cid.startswith("C"):
        return row["cmds"] == 0 and row["src_errors"] > 0
    return "tf_x" in row and math.isclose(row["tf_x"], ARTICLE_EXPECTED_M[cid], rel_tol=ISCLOSE_REL)


def main():
    emit("env", python=sys.version.split()[0], rclpy=version_of("rclpy"), tf2_ros=version_of("tf2_ros_py"),
         geometry_msgs=version_of("geometry_msgs"), nav_msgs=version_of("nav_msgs"),
         rmw=rclpy.utilities.get_rmw_implementation_identifier())
    rclpy.init()
    message_checks()

    device = Device()
    adapters = {a: Adapter(a) for a in ADAPTERS}
    odoms = {o: Odom(o) for o in ODOMS}
    checker = Checker()
    all_nodes = [device, *adapters.values(), *odoms.values(), checker]
    ex = SingleThreadedExecutor()
    for node in all_nodes:
        ex.add_node(node)

    def spin():
        try:
            ex.spin()
        except ExternalShutdownException:
            pass

    spinner = threading.Thread(target=spin, daemon=True)
    spinner.start()

    def matched():
        return (device.pub.get_subscription_count() >= len(ADAPTERS) + 1
                and all(a.pub.get_subscription_count() >= sum(s == a.impl for s, _ in ODOMS.values())
                        for a in adapters.values())
                and all(o.pub.get_subscription_count() >= 1 for o in odoms.values())
                and all(a.err.get_subscription_count() >= 1 for a in adapters.values())
                and device.count_subscribers("/tf") >= 1)
    deadline = time.monotonic() + 10
    while not matched() and time.monotonic() < deadline:
        time.sleep(0.05)
    stats = {"timeouts": 0, "graph_matched": matched()}
    time.sleep(0.3)

    # ---- synthetic stamps: exact 50 ms intervals, logic only
    synth = {}
    for idx, case in enumerate(CASES):
        synth[case[0]] = run_case(case, (device, adapters, odoms, checker), "synthetic", stats,
                                  SYNTH_BASE_NS + idx * SYNTH_GAP_NS)
    rows = []
    for cid, res in synth.items():
        for impl, row in res["impl"].items():
            x = row.get("tf_x")
            claim = ARTICLE_FAILURE_M.get((impl, cid))
            rows.append([cid, impl, row["cmds"], row["src_errors"], r(x, 12),
                         r(x / ARTICLE_EXPECTED_M[cid], 6) if x is not None and cid in ARTICLE_EXPECTED_M else None,
                         r(abs(x - ARTICLE_EXPECTED_M[cid]), 3) if x is not None and cid in ARTICLE_EXPECTED_M else None,
                         passes(cid, row),
                         math.isclose(x, claim, rel_tol=ISCLOSE_REL) if claim is not None and x is not None else None,
                         row.get("odom_minus_tf"), row.get("internal_minus_tf")])
    emit("synthetic", control_s=CONTROL_NS * 1e-9,
         dt_s={cid: r(res["dt_s"], 12) for cid, res in synth.items()},
         raw_bits_equal=all(res["raw_bits_equal"] for res in synth.values()),
         cols=["case", "impl", "cmds", "src_err", "tf_x_m", "x_over_article", "abs_err_m", "pass",
               "matches_article_failure", "odom_minus_tf", "internal_minus_tf"], rows=rows)
    a_ratio = synth["A"]["impl"]["no_convert"].get("tf_x", math.nan) / synth["A"]["impl"]["correct"].get("tf_x", math.nan)
    e_ratio = synth["E"]["impl"]["no_convert"].get("tf_x", math.nan) / synth["E"]["impl"]["correct"].get("tf_x", math.nan)
    a_diff = synth["A"]["impl"]["no_convert"].get("tf_x", math.nan) - synth["A"]["impl"]["correct"].get("tf_x", math.nan)
    emit("factors", A_no_convert_over_correct=r(a_ratio, 12), A_abs_difference_m=r(a_diff, 12),
         E_no_convert_over_correct=r(e_ratio, 12),
         B_correct_over_always_div=r(synth["B"]["impl"]["correct"].get("tf_x", math.nan)
                                     / synth["B"]["impl"]["always_div"].get("tf_x", math.nan), 12))
    with CV:
        err_sample = sorted(set(checker.errors))[:3]
        frames = dict(checker.frames)
    emit("unit_errors", samples=err_sample, odom_frames=frames)

    suites = {"A_only": ["A"], "A+B": ["A", "B"], "A+B+C": ["A", "B", "C_missing", "C_unsupported"],
              "all": [c[0] for c in CASES]}
    emit("suites", cols=["suite", *ODOMS],
         rows=[[s, *[not all(passes(c, synth[c]["impl"][impl]) for c in cs) for impl in ODOMS]]
               for s, cs in suites.items()],
         note="true = the suite catches (fails) this implementation")

    # ---- real clock: 20 Hz sleep schedule, header stamps from the node clock
    real = {case[0]: run_case(case, (device, adapters, odoms, checker), "realtime", stats) for case in CASES}
    rrows = []
    for cid, res in real.items():
        c = res["impl"]["correct"]
        x, xr = c.get("tf_x"), c.get("recv_x")
        nc = res["impl"]["no_convert"].get("tf_x")
        rrows.append([cid, r(res["dt_s"], 9),
                      r(x, 9), r(x - ARTICLE_EXPECTED_M[cid], 4) if x is not None and cid in ARTICLE_EXPECTED_M else None,
                      r(xr - ARTICLE_EXPECTED_M[cid], 4) if xr is not None and c["cmds"] and cid in ARTICLE_EXPECTED_M else None,
                      passes(cid, c), r(nc / x, 12) if nc is not None and x else None,
                      [impl for impl in ODOMS if not passes(cid, res["impl"][impl])]])
    emit("realtime", cols=["case", "dt_s", "correct_tf_x_m", "stamp_dev_m", "recv_dev_m", "isclose_pass",
                           "no_convert_over_correct", "failing_impls"], rows=rrows)

    reps = [run_case(CASES[0], (device, adapters, odoms, checker), "realtime", stats) for _ in range(REPEATS)]
    hold_s = CASES[0][3] * 1e-9
    dt_excess = [(p["dt_s"] - hold_s) * 1e3 for p in reps]
    dev_stamp = [(p["impl"]["correct"]["tf_x"] - ARTICLE_EXPECTED_M["A"]) * 1e3 for p in reps if "tf_x" in p["impl"]["correct"]]
    dev_recv = [(p["impl"]["correct"]["recv_x"] - ARTICLE_EXPECTED_M["A"]) * 1e3 for p in reps]
    ratio = [p["impl"]["no_convert"]["tf_x"] / p["impl"]["correct"]["tf_x"] for p in reps
             if "tf_x" in p["impl"]["no_convert"] and "tf_x" in p["impl"]["correct"]]

    def spread(xs, n=4):
        return [r(min(xs), n), r(statistics.median(xs), n), r(max(xs), n)] if xs else None
    emit("realtime_repeat", case="A", repeats=REPEATS, cols="min, median, max",
         dt_excess_ms=spread(dt_excess), stamp_dev_mm=spread(dev_stamp), recv_dev_mm=spread(dev_recv),
         isclose_pass=sum(passes("A", p["impl"]["correct"]) for p in reps),
         no_convert_over_correct=spread(ratio, 12))

    emit("ros", timeouts=stats["timeouts"], graph_matched=stats["graph_matched"], nodes=len(all_nodes))
    # Stop the spin thread before tearing down nodes (destroying them mid-spin can abort the process).
    rclpy.try_shutdown()
    spinner.join(timeout=5)
    ex.shutdown(timeout_sec=2)
    for node in all_nodes:
        node.destroy_node()
    emit("done", seconds=r(time.monotonic() - T_START, 4))
    return 0 if stats["timeouts"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
