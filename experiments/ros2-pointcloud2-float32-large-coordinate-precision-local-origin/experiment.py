#!/usr/bin/env python3
"""ROS 2 Jazzy: what happens to a ~4,000,000 m coordinate in a FLOAT32 PointCloud2 field?

One process, no network. Clouds are built with sensor_msgs_py.point_cloud2.create_cloud from
Python floats (binary64), sent through CDR serialization and a real rclpy publisher/subscriber
on the loopback transport, and read back with read_points. Every printed line is a JSON object
observed at run time. Numbers in this file are experiment inputs (coordinates, origin, sweep
step, wait limits), not results. Reference values are computed at run time with Fraction:
"nearest" = round to the nearest float32 grid point (ties to even), "trunc" = cut toward zero.
"""
import json
import math
import sys
import time
import warnings
from fractions import Fraction

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.serialization import deserialize_message, serialize_message
from rclpy.utilities import get_rmw_implementation_identifier
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Header

T0 = time.monotonic()

# Inputs (research.md "자체 예제의 가정·절차·검산" + discriminating extras).
ORIGIN = 3999900.0                   # local origin subtracted in float64 (research example)
CASES = [
    ("x_4000000.3", 4000000.3),
    ("x_4000000.05", 4000000.05),
    ("x_4000000.10", 4000000.10),
    ("x_4000000.2", 4000000.2),      # nearest -> .25, trunc -> .0: tells the rounding rule
    ("x_4000000.125", 4000000.125),  # exact midpoint between .0 and .25
    ("x_4000000.375", 4000000.375),  # exact midpoint between .25 and .5
    ("x_3000000.3", 3000000.3),
    ("x_4194303.9", 4194303.9),      # just below 2^22
    ("x_4194304.3", 4194304.3),      # just above 2^22
    ("x_5000000.3", 5000000.3),
    ("x_100.3", 100.3),
]
PAIR = (4000000.05, 4000000.10)      # two points 5 cm apart
SWEEP_STEP_MM = 1                    # 1 mm steps over one metre
SWEEP_STARTS = [4000000.0, 5000000.0]
WAIT_S = 15.0


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def fields_of(datatype):
    size = 4 if datatype == PointField.FLOAT32 else 8
    return [PointField(name=n, offset=size * k, datatype=datatype, count=1)
            for k, n in enumerate(("x", "y", "z"))]


F32, F64 = fields_of(PointField.FLOAT32), fields_of(PointField.FLOAT64)
HEADER = Header(frame_id="map")


def grid(value):
    """Exact float32 spacing for |value| (normal range), from 24 significand bits."""
    q = abs(Fraction(value))
    if q == 0:
        return None
    k = math.floor(math.log2(q))
    while Fraction(2) ** k > q:
        k -= 1
    while Fraction(2) ** (k + 1) <= q:
        k += 1
    return k, Fraction(2) ** (k - 23)


def reference(value):
    k, ulp = grid(value)
    q = Fraction(value) / ulp
    nearest = round(q) * ulp          # Fraction.__round__ -> ties to even
    trunc = math.floor(q) * ulp
    return k, ulp, nearest, trunc


def xs(cloud):
    return [float(p[0]) for p in pc2.read_points(cloud, field_names=("x",), skip_nans=False)]


def roundtrip(cloud):
    """CDR serialize -> deserialize, the same bytes a publisher puts on the wire."""
    raw = serialize_message(cloud)
    back = deserialize_message(raw, PointCloud2)
    return back, len(raw), bytes(back.data) == bytes(cloud.data)


def f(v):
    return float(v)


def main():
    rclpy.init()
    emit("environment", rmw=get_rmw_implementation_identifier(), numpy=np.__version__,
         python=sys.version.split()[0], float32_nmant=int(np.finfo(np.float32).nmant),
         float64_nmant=int(np.finfo(np.float64).nmant),
         datatype_float32=int(PointField.FLOAT32), datatype_float64=int(PointField.FLOAT64),
         sensor_msgs_py_float32_dtype=str(pc2._DATATYPES[PointField.FLOAT32]))

    # 1) Single values through create_cloud -> serialize -> read_points.
    points = [(v, 0.0, 0.0) for _, v in CASES]
    cloud = pc2.create_cloud(HEADER, F32, points)
    back, nbytes, same = roundtrip(cloud)
    stored = xs(back)
    emit("cloud_layout", point_step=cloud.point_step, width=cloud.width, data_len=len(cloud.data),
         serialized_len=nbytes, data_bytes_equal_after_cdr=same,
         field_dtypes=[str(pc2.read_points(back).dtype.fields[n][0]) for n in ("x", "y", "z")])
    rule_hits = {"nearest": 0, "trunc": 0}
    for (_, value), s in zip(CASES, stored):
        k, ulp, nearest, trunc = reference(value)
        s32 = np.float32(s)
        up, down = np.nextafter(s32, np.float32(np.inf)), np.nextafter(s32, np.float32(-np.inf))
        hit_n, hit_t = Fraction(s) == nearest, Fraction(s) == trunc
        rule_hits["nearest"] += hit_n
        rule_hits["trunc"] += hit_t
        emit("case", input=repr(value), stored=repr(s), err_m=f(Fraction(s) - Fraction(value)),
             k=k, band_spacing_m=f(ulp), np_spacing_m=f(np.spacing(s32)),
             gap_below_m=f(Fraction(s) - Fraction(float(down))),
             gap_above_m=f(Fraction(float(up)) - Fraction(s)),
             nearest=hit_n, trunc=hit_t)
    emit("rounding_rule", cases=len(CASES), **rule_hits)

    # 2) Two points 5 cm apart.
    pair_cloud, _, _ = roundtrip(pc2.create_cloud(HEADER, F32, [(v, 0.0, 0.0) for v in PAIR]))
    a, b = xs(pair_cloud)
    emit("pair_5cm", input_gap_m=f(Fraction(PAIR[1]) - Fraction(PAIR[0])), stored_a=repr(a),
         stored_b=repr(b), stored_gap_m=b - a, identical=a == b)

    # 3) One-metre sweep in 1 mm steps: how many distinct stored values, worst error.
    n = 1000 // SWEEP_STEP_MM
    for start in SWEEP_STARTS:
        for label, origin in (("raw", 0.0), ("origin_first_f64", ORIGIN)):
            exact = [Fraction(start) + Fraction(i * SWEEP_STEP_MM, 1000) for i in range(n)]
            inputs = [float(e - Fraction(origin)) for e in exact]
            c, _, _ = roundtrip(pc2.create_cloud(HEADER, F32, [(v, 0.0, 0.0) for v in inputs]))
            got = xs(c)
            errs = [abs(Fraction(g) + Fraction(origin) - e) for g, e in zip(got, exact)]
            uniq = sorted(set(got))
            steps = sorted({f(Fraction(y) - Fraction(x)) for x, y in zip(uniq, uniq[1:])})
            emit("sweep_1m", start_m=start, origin_m=origin, label=label, points=n,
                 input_step_m=SWEEP_STEP_MM / 1000, distinct=len(uniq),
                 steps_m=steps[:4], max_err_m=f(max(errs)), mean_err_m=f(sum(errs) / len(errs)))

    # 4) Order: subtract the origin before vs after the float32 storage.
    for _, value in CASES[:4]:
        exact_local = Fraction(value) - Fraction(ORIGIN)
        after = pc2.create_cloud(HEADER, F32, [(value, 0.0, 0.0)])
        after_local = float(np.float64(xs(roundtrip(after)[0])[0])) - ORIGIN
        before = pc2.create_cloud(HEADER, F32, [(value - ORIGIN, 0.0, 0.0)])
        before_local = xs(roundtrip(before)[0])[0]
        emit("origin_order", input=repr(value), origin_m=ORIGIN, exact_local_m=f(exact_local),
             after_f32_m=after_local, err_after_m=f(Fraction(after_local) - exact_local),
             before_f32_m=before_local, err_before_m=f(Fraction(before_local) - exact_local),
             local_spacing_m=f(np.spacing(np.float32(before_local))))

    # 5) FLOAT64 fields as the alternative: error and size.
    c64, n64, _ = roundtrip(pc2.create_cloud(HEADER, F64, points))
    got64 = xs(c64)
    emit("float64_fields", point_step=c64.point_step, data_len=len(c64.data), serialized_len=n64,
         float32_point_step=cloud.point_step, float32_data_len=len(cloud.data),
         max_err_m=f(max(abs(Fraction(g) - Fraction(v)) for g, (_, v) in zip(got64, CASES))))

    # 6) Input paths: does anything warn or refuse when a float64 value is narrowed?
    paths = {
        "list_of_tuples": lambda: pc2.create_cloud(HEADER, F32, [(CASES[0][1], 0.0, 0.0)]),
        "numpy_unstructured_f64": lambda: pc2.create_cloud(
            HEADER, F32, np.array([[CASES[0][1], 0.0, 0.0]], dtype=np.float64)),
        "numpy_structured_f64": lambda: pc2.create_cloud(
            HEADER, F32, np.array([(CASES[0][1], 0.0, 0.0)],
                                  dtype=[("x", "<f8"), ("y", "<f8"), ("z", "<f8")])),
        "create_cloud_xyz32": lambda: pc2.create_cloud_xyz32(HEADER, [(CASES[0][1], 0.0, 0.0)]),
    }
    for label, build in paths.items():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                c = build()
                result = dict(ok=True, stored_repr=repr(xs(c)[0]), point_step=c.point_step)
            except Exception as exc:  # recorded, not hidden
                result = dict(ok=False, exception=type(exc).__name__,
                              message=" ".join(str(exc).split())[:90])
        emit("input_path", path=label, input=repr(CASES[0][1]), warnings=len(caught),
             warning_types=sorted({w.category.__name__ for w in caught}), **result)

    # 7) Real publish/subscribe on loopback: the received bytes and values.
    node = rclpy.create_node("float32_origin_probe")
    got = {}
    node.create_subscription(PointCloud2, "/cloud_raw", lambda m: got.setdefault("raw", m), 10)
    node.create_subscription(PointCloud2, "/cloud_local", lambda m: got.setdefault("local", m), 10)
    pub_raw = node.create_publisher(PointCloud2, "/cloud_raw", 10)
    pub_local = node.create_publisher(PointCloud2, "/cloud_local", 10)
    raw_msg = pc2.create_cloud(HEADER, F32, points[:4])
    local_msg = pc2.create_cloud(HEADER, F32, [(v - ORIGIN, 0.0, 0.0) for _, v in CASES[:4]])
    ex = SingleThreadedExecutor()
    ex.add_node(node)
    start = time.monotonic()
    while len(got) < 2 and time.monotonic() - start < WAIT_S:
        pub_raw.publish(raw_msg)
        pub_local.publish(local_msg)
        ex.spin_once(timeout_sec=0.1)
    waited = round(time.monotonic() - start, 3)
    if len(got) == 2:
        raw_vals, local_vals = xs(got["raw"]), xs(got["local"])
        emit("pubsub", received=True, waited_s=waited,
             raw_bytes_equal=bytes(got["raw"].data) == bytes(raw_msg.data),
             local_bytes_equal=bytes(got["local"].data) == bytes(local_msg.data),
             rows=[dict(input=repr(v), raw=repr(r), raw_err_m=f(Fraction(r) - Fraction(v)),
                        local=repr(lv), local_err_m=f(Fraction(lv) + Fraction(ORIGIN) - Fraction(v)))
                   for (_, v), r, lv in zip(CASES[:4], raw_vals, local_vals)])
    else:
        emit("pubsub", received=False, waited_s=waited, topics=sorted(got))
    ex.shutdown()
    node.destroy_node()
    rclpy.shutdown()
    emit("done", seconds=round(time.monotonic() - T0, 3))


if __name__ == "__main__":
    main()
