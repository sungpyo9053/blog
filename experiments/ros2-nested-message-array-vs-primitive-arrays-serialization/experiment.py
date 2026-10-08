#!/usr/bin/env python3
"""Foo[] vs uint64[]+uint32[]: count non-primitive elements and measure rclpy publish path.

Runs inside ros:jazzy-ros-base (network none, 1 CPU). Stages:
  1. build: generate the DDS-tuning example package (Foo, FooArray, FooSplit and a Time
     variant) under /var/tmp (the harness /tmp is noexec) and cmake-build it.
  2. measure: re-exec this script with the install prefix on the ROS paths; every number printed is
     measured at run time and emitted as one JSON line.
  3. subscriber: two child processes (raw-only and deserializing) that count arrivals, so one
     mode's callbacks never wait in the other mode's executor.
"""
import array
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import threading
import time

WS = "/var/tmp/foo_ws"
PKG = "foo_msgs"
N = 10000                 # elements per message (same N as the foundation example)
SIZE_NS = (0, 1, 2, 3, N)
REPS = 9                  # timed repetitions for construct/serialize/deserialize
RATE_HZ = 30
RATE_SECONDS = 1.2
SOLO_PUBLISHES = 10
SUB_MODES = {"solo": ("raw",), "rate": ("raw", "deserialized")}  # one subscriber process per mode
TYPES = ("FooArray", "FooSplit", "FooStampedArray", "FooStampedSplit")

MSGS = {
    "Foo.msg": "uint64 foo_1\nuint32 foo_2\n",
    "FooArray.msg": "Foo[] my_large_array\n",
    "FooSplit.msg": "uint64[] foo_1_array\nuint32[] foo_2_array\n",
    "FooStamped.msg": "uint64 foo_1\nuint32 foo_2\nbuiltin_interfaces/Time stamp\n",
    "FooStampedArray.msg": "FooStamped[] my_large_array\n",
    "FooStampedSplit.msg": ("uint64[] foo_1_array\nuint32[] foo_2_array\n"
                            "int32[] stamp_sec\nuint32[] stamp_nanosec\n"),
}
CMAKE = """cmake_minimum_required(VERSION 3.8)
project(foo_msgs)
find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
%s
  DEPENDENCIES builtin_interfaces)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
"""
PACKAGE_XML = """<?xml version="1.0"?>
<package format="3">
  <name>foo_msgs</name>
  <version>0.0.1</version>
  <description>DDS tuning Foo[] example</description>
  <maintainer email="user@example.com">user</maintainer>
  <license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <depend>builtin_interfaces</depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
"""


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, separators=(",", ":")), flush=True)


def stats_us(samples_ns):
    s = sorted(samples_ns)
    p90 = s[max(0, -(-len(s) * 9 // 10) - 1)]
    return {"n": len(s), "median_us": round(statistics.median(s) / 1000, 1),
            "p90_us": round(p90 / 1000, 1)}


# ---------------------------------------------------------------- stage 1: build
def build():
    started = time.perf_counter()
    shutil.rmtree(WS, ignore_errors=True)
    src = os.path.join(WS, "src", PKG, "msg")
    os.makedirs(src)
    for name, body in MSGS.items():
        with open(os.path.join(src, name), "w") as f:
            f.write(body)
    with open(os.path.join(WS, "src", PKG, "CMakeLists.txt"), "w") as f:
        f.write(CMAKE % "\n".join(f'  "msg/{m}"' for m in MSGS))
    with open(os.path.join(WS, "src", PKG, "package.xml"), "w") as f:
        f.write(PACKAGE_XML)
    pkg_dir, build_dir, prefix = os.path.join(WS, "src", PKG), os.path.join(WS, "build"), os.path.join(WS, "install")
    generator = ["-G", "Ninja"] if shutil.which("ninja") else []
    phases = {}
    for phase, cmd in (
            ("configure", ["cmake", "-S", pkg_dir, "-B", build_dir, *generator, "-DBUILD_TESTING=OFF",
                           f"-DCMAKE_INSTALL_PREFIX={prefix}"]),
            ("compile", ["cmake", "--build", build_dir, "--parallel", "2"]),
            ("install", ["cmake", "--install", build_dir])):
        t0 = time.perf_counter()
        done = subprocess.run(cmd, capture_output=True, text=True)
        phases[phase] = round(time.perf_counter() - t0, 1)
        if done.returncode != 0:
            sys.stderr.write(done.stdout[-3000:] + done.stderr[-3000:])
            raise SystemExit(f"{phase} failed: {done.returncode}")
    emit("build", seconds=round(time.perf_counter() - started, 1), phases_s=phases,
         generator="ninja" if generator else "make", msg_files=len(MSGS), workspace=WS)
    # what `source install/setup.bash` would add, without needing colcon
    env = dict(os.environ)
    pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    for key, path in (("AMENT_PREFIX_PATH", prefix), ("LD_LIBRARY_PATH", os.path.join(prefix, "lib")),
                      ("PYTHONPATH", os.path.join(prefix, "lib", pyver, "site-packages"))):
        env[key] = path + (os.pathsep + env[key] if env.get(key) else "")
    child = subprocess.run([sys.executable, os.path.abspath(__file__), "--measure"], env=env)
    return child.returncode


# ---------------------------------------------------------------- helpers (measure side)
def count_non_primitive(msg):
    """Count nested message instances reachable from msg (msg itself not counted)."""
    total = 0
    for field in msg.get_fields_and_field_types():
        value = getattr(msg, field)
        items = value if isinstance(value, (list, tuple)) else [value]
        for item in items:
            if hasattr(item, "get_fields_and_field_types"):
                total += 1 + count_non_primitive(item)
    return total


def declared_field_bytes(msg):
    """Sum of declared primitive field widths (what the foundation example adds up)."""
    widths = {"uint64": 8, "int64": 8, "uint32": 4, "int32": 4}
    total = 0
    for field, ftype in msg.get_fields_and_field_types().items():
        value = getattr(msg, field)
        base = ftype.split("<")[-1].rstrip(">") if ftype.startswith("sequence<") else ftype
        if base in widths:
            total += widths[base] * (len(value) if ftype.startswith("sequence<") else 1)
        else:
            items = value if isinstance(value, (list, tuple)) else [value]
            total += sum(declared_field_bytes(i) for i in items)
    return total


def make_values(n, seed):
    rng = random.Random(seed)
    return ([rng.getrandbits(64) for _ in range(n)], [rng.getrandbits(32) for _ in range(n)],
            [rng.randrange(0, 2 ** 31) for _ in range(n)], [rng.randrange(0, 10 ** 9) for _ in range(n)])


def builders(m, Time):
    def foo_array(v):
        return m.FooArray(my_large_array=[m.Foo(foo_1=a, foo_2=b) for a, b in zip(v[0], v[1])])

    def foo_split(v):
        return m.FooSplit(foo_1_array=array.array("Q", v[0]), foo_2_array=array.array("I", v[1]))

    def foo_split_list(v):
        return m.FooSplit(foo_1_array=v[0], foo_2_array=v[1])

    def stamped_array(v):
        return m.FooStampedArray(my_large_array=[
            m.FooStamped(foo_1=a, foo_2=b, stamp=Time(sec=s, nanosec=ns))
            for a, b, s, ns in zip(*v)])

    def stamped_split(v):
        return m.FooStampedSplit(foo_1_array=array.array("Q", v[0]), foo_2_array=array.array("I", v[1]),
                                 stamp_sec=array.array("i", v[2]), stamp_nanosec=array.array("I", v[3]))

    return {"FooArray": foo_array, "FooSplit": foo_split, "FooSplit(list)": foo_split_list,
            "FooStampedArray": stamped_array, "FooStampedSplit": stamped_split}


def as_tuples(msg):
    """Normalize either layout to a list of per-element tuples to prove the values are equal."""
    if hasattr(msg, "my_large_array"):
        out = []
        for e in msg.my_large_array:
            t = (e.foo_1, e.foo_2)
            if hasattr(e, "stamp"):
                t += (e.stamp.sec, e.stamp.nanosec)
            out.append(t)
        return out
    cols = [msg.foo_1_array, msg.foo_2_array]
    if hasattr(msg, "stamp_sec"):
        cols += [msg.stamp_sec, msg.stamp_nanosec]
    return list(zip(*cols))


def timed(fn, reps):
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter_ns()
        fn()
        samples.append(time.perf_counter_ns() - t0)
    return samples


# ---------------------------------------------------------------- stage 2: measure
def measure():
    t_start = time.perf_counter()
    import rclpy
    from builtin_interfaces.msg import Time
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.serialization import deserialize_message, serialize_message
    from rclpy.utilities import get_rmw_implementation_identifier
    import foo_msgs.msg as m

    emit("env", rmw=get_rmw_implementation_identifier(),
         ROS_PYTHON_CHECK_FIELDS=os.environ.get("ROS_PYTHON_CHECK_FIELDS"),
         RMW_FASTRTPS_PUBLICATION_MODE=os.environ.get("RMW_FASTRTPS_PUBLICATION_MODE"),
         python=sys.version.split()[0], cpu_count=os.cpu_count())
    build = builders(m, Time)

    # (1) count + size: same values in both layouts, small N first to check the formula
    for n in SIZE_NS:
        v = make_values(n, seed=n + 1)
        built = {name: build[name](v) for name in TYPES}
        size, count, fields, roundtrip = {}, {}, {}, True
        for name, msg in built.items():
            data = serialize_message(msg)
            roundtrip &= as_tuples(deserialize_message(data, type(msg))) == as_tuples(msg)
            size[name], count[name], fields[name] = (len(data), count_non_primitive(msg),
                                                     declared_field_bytes(msg))
        same = (as_tuples(built["FooArray"]) == as_tuples(built["FooSplit"])
                and as_tuples(built["FooStampedArray"]) == as_tuples(built["FooStampedSplit"]))
        emit("size", N=n, serialized_bytes=size, non_primitive=count, field_bytes=fields,
             same_values=same, roundtrip_equal=roundtrip)

    v = make_values(N, seed=7)
    # (2) construction time from the same Python int lists
    for name in ("FooArray", "FooSplit", "FooSplit(list)", "FooStampedArray", "FooStampedSplit"):
        fn = build[name]
        fn(v)  # warm-up
        emit("construct", type=name, N=N, **stats_us(timed(lambda: fn(v), REPS)))

    msgs = {name: build[name](v) for name in TYPES}
    # (3) serialize_message (= convert_from_py + rmw_serialize) and deserialize_message
    for name, msg in msgs.items():
        serialize_message(msg)
        ser = stats_us(timed(lambda: serialize_message(msg), REPS))
        data = serialize_message(msg)
        deserialize_message(data, type(msg))
        des = stats_us(timed(lambda: deserialize_message(data, type(msg)), REPS))
        emit("serdes", type=name, N=N, serialize=ser, deserialize=des)

    # (4)+(5) publish() with an out-of-process subscriber
    #   solo_*: only the raw subscriber process listens (no Python deserialization on the receive side)
    #   rate_*: the raw and the deserializing subscriber processes both listen (like `ros2 topic hz`
    #           without and with --filter) and compete with the publisher for the single CPU
    rclpy.init()
    node = rclpy.create_node("foo_pub")
    subs = {mode: subprocess.Popen([sys.executable, os.path.abspath(__file__), "--subscriber", mode],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            for mode in ("raw", "deserialized")}
    pubs = {}
    for phase in SUB_MODES:
        for name in TYPES:
            pubs[(phase, name)] = node.create_publisher(type(msgs[name]), f"/{phase}_{name.lower()}",
                                                        qos_profile_sensor_data)
    t_wait = time.perf_counter()
    while any(p.get_subscription_count() < len(SUB_MODES[phase]) for (phase, _), p in pubs.items()):
        if time.perf_counter() - t_wait > 20:
            raise SystemExit("subscriber did not match within 20 s")
        time.sleep(0.05)
    emit("matched", seconds=round(time.perf_counter() - t_wait, 2))

    def paced(pub, msg, stop):
        """Publish at RATE_HZ until stop(sent, elapsed); return publish() durations and elapsed s."""
        pub.publish(msg)  # warm-up on a fresh writer; the subscriber drops its first arrival
        time.sleep(0.1)
        samples, period = [], 1.0 / RATE_HZ
        t0 = time.perf_counter()
        while not stop(len(samples), time.perf_counter() - t0):
            delay = t0 + len(samples) * period - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            s = time.perf_counter_ns()
            pub.publish(msg)
            samples.append(time.perf_counter_ns() - s)
        return samples, time.perf_counter() - t0

    published = {}
    for name, msg in msgs.items():  # (4) publish() cost with a raw-only reader
        samples, _ = paced(pubs[("solo", name)], msg, lambda sent, _t: sent >= SOLO_PUBLISHES)
        published[f"solo_{name.lower()}"] = len(samples)
        emit("publish_solo", type=name, N=N, publish=stats_us(samples))
        time.sleep(0.15)

    for name, msg in msgs.items():  # (5) 30 Hz for RATE_SECONDS with raw + deserializing readers
        samples, elapsed = paced(pubs[("rate", name)], msg, lambda _s, t: t >= RATE_SECONDS)
        published[f"rate_{name.lower()}"] = len(samples)
        emit("publish_paced", type=name, N=N, target_hz=RATE_HZ, sent=len(samples),
             achieved_hz=round(len(samples) / elapsed, 2), publish=stats_us(samples),
             budget_share_median=round(statistics.median(samples) / 1e9 * RATE_HZ, 3))
        time.sleep(0.15)

    for proc in subs.values():
        proc.stdin.close()  # EOF on stdin tells each subscriber to drain and report
    received = {}
    for mode, proc in subs.items():
        out = proc.stdout.read()
        proc.wait(timeout=20)
        for topic, r in json.loads(out.strip().splitlines()[-1]).items():
            received.setdefault(topic, {})[mode] = r
    for topic, modes in received.items():
        sent = published.get(topic)
        # count/rate exclude the first arrival (normally the warm-up); arrived_incl_warmup is the
        # raw total, to compare with sent + 1 when the warm-up itself may have been dropped
        emit("receive", topic=topic, sent=sent, **{
            mode: {"count": r["count"], "arrived_incl_warmup": r["arrived"], "rate_hz": r["rate_hz"],
                   "share_of_sent": round(r["count"] / sent, 3) if sent else None}
            for mode, r in modes.items()})
    node.destroy_node()
    rclpy.shutdown()
    emit("done", measure_seconds=round(time.perf_counter() - t_start, 1))


# ---------------------------------------------------------------- stage 3: subscriber
def subscriber(mode):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    import foo_msgs.msg as m

    rclpy.init()
    node = rclpy.create_node(f"foo_sub_{mode}")
    stats = {}

    def make_cb(topic):
        arrivals = stats.setdefault(topic, [])

        def cb(_msg):
            arrivals.append(time.perf_counter())
        return cb

    keep = []
    for phase, modes in SUB_MODES.items():
        for name in TYPES:
            topic = f"{phase}_{name.lower()}"
            if mode in modes:
                keep.append(node.create_subscription(getattr(m, name), "/" + topic, make_cb(topic),
                                                     qos_profile_sensor_data, raw=(mode == "raw")))
    stop = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.read(), stop.set()), daemon=True).start()
    while not stop.is_set():
        rclpy.spin_once(node, timeout_sec=0.05)
    deadline = time.perf_counter() + 0.4  # drain what is already queued
    while time.perf_counter() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    result = {}
    for topic, arrivals in stats.items():
        # the first arrival is the warm-up publish; drop it from count and rate
        measured = arrivals[1:]
        span = measured[-1] - measured[0] if len(measured) > 1 else 0
        result[topic] = {"count": len(measured), "arrived": len(arrivals),
                         "rate_hz": round((len(measured) - 1) / span, 2) if span > 0 else None}
    print(json.dumps(result, separators=(",", ":")), flush=True)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    if "--measure" in sys.argv:
        measure()
    elif "--subscriber" in sys.argv:
        subscriber(sys.argv[sys.argv.index("--subscriber") + 1])
    else:
        raise SystemExit(build())
