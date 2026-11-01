#!/usr/bin/env python3
"""ROS 2 Jazzy: what survives when a PointCloud2 is moved laser -> base_link in Python?

One process (plus one short child python3 for the "no tf2_sensor_msgs import" case), no network.
Every printed line is a JSON object observed at run time. Numbers in this file are experiment
inputs (cloud sizes, offsets, the illustrative laser pose) and wait limits, not results.
Input clouds are packed by hand with NumPy, not with create_cloud, so the function under test
does not build its own input.
"""
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
from builtin_interfaces.msg import Time as TimeMsg
from geometry_msgs.msg import Transform, TransformStamped
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2, PointField
from sensor_msgs_py import point_cloud2 as pc2
from std_msgs.msg import Header
from tf2_ros import Buffer, StaticTransformBroadcaster, TransformListener

T0 = time.monotonic()

# Inputs (research.md "공통 입력").
N = 1000
SOURCE, TARGET = "laser", "base_link"
TRANSLATION = (0.25, 0.0, 0.125)
QZ = QW = float(np.sqrt(0.5))  # +90 deg about z
STAMP = (1700000000, 123456789)
PLAIN_STEP, PADDED_STEP = 16, 32
ORG_W, ORG_H = 4, 3
TOL = 1e-6
WAIT_S = 15.0


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def xyzi_fields():
    return [PointField(name=n, offset=4 * k, datatype=PointField.FLOAT32, count=1)
            for k, n in enumerate(("x", "y", "z", "intensity"))]


def make_cloud(width=N, height=1, point_step=PLAIN_STEP):
    """Hand-packed x,y,z,intensity float32 cloud; point 0 = (1.0, 0.5, 0.0)."""
    n = width * height
    dtype = np.dtype({"names": ["x", "y", "z", "intensity"], "formats": ["<f4"] * 4,
                      "offsets": [0, 4, 8, 12], "itemsize": point_step})
    arr = np.zeros(n, dtype=dtype)
    idx = np.arange(n, dtype=np.float64)
    arr["x"] = 1.0 + 0.001 * idx
    arr["y"] = 0.5 - 0.002 * idx
    arr["z"] = 0.0 + 0.0005 * idx
    arr["intensity"] = 10.0 + idx  # distinct per point
    msg = PointCloud2()
    msg.header = Header(stamp=TimeMsg(sec=STAMP[0], nanosec=STAMP[1]), frame_id=SOURCE)
    msg.height, msg.width = height, width
    msg.fields = xyzi_fields()
    msg.is_bigendian = False
    msg.point_step = point_step
    msg.row_step = point_step * width
    msg.data = arr.tobytes()
    msg.is_dense = True
    return msg


def transform_stamped():
    ts = TransformStamped()
    ts.header.frame_id, ts.child_frame_id = TARGET, SOURCE
    ts.transform.translation.x, ts.transform.translation.y, ts.transform.translation.z = TRANSLATION
    ts.transform.rotation.z, ts.transform.rotation.w = QZ, QW
    return ts


def rotation_matrix(q):
    x, y, z, w = q.x, q.y, q.z, q.w
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def reference_xyz(cloud):
    """Hand formula from the article: 90 deg about z is (x, y) -> (-y, x), then add t."""
    a = pc2.read_points_numpy(cloud, field_names=["x", "y", "z"]).astype(np.float64)
    return np.column_stack([-a[:, 1] + TRANSLATION[0], a[:, 0] + TRANSLATION[1], a[:, 2] + TRANSLATION[2]])


def describe(msg, original=None):
    """The article's pre-publish check, measured on a message."""
    d = {"fields": [f.name for f in msg.fields], "offsets": [f.offset for f in msg.fields],
         "point_step": msg.point_step, "row_step": msg.row_step, "height": msg.height, "width": msg.width,
         "len_data": len(msg.data), "w_h_step": msg.width * msg.height * msg.point_step,
         "frame_id": msg.header.frame_id, "stamp": [msg.header.stamp.sec, msg.header.stamp.nanosec],
         "is_dense": msg.is_dense}
    d["len_matches_w_h_step"] = d["len_data"] == d["w_h_step"]
    if original is not None:
        d["len_ratio_vs_original"] = round(len(msg.data) / len(original.data), 6)
        d["same_field_names"] = d["fields"] == [f.name for f in original.fields]
        d["same_shape"] = (msg.height, msg.width) == (original.height, original.width)
    return d


def xyz_error(msg, ref):
    got = pc2.read_points_numpy(msg, field_names=["x", "y", "z"]).astype(np.float64)
    err = float(np.max(np.abs(got - ref)))
    return {"point0": [round(float(v), 7) for v in got[0]], "max_abs_err_vs_hand": err,
            "within_tol": err <= TOL}


def intensity_kept(msg, original):
    if "intensity" not in [f.name for f in msg.fields]:
        return {"intensity_field_present": False}
    a = pc2.read_points_numpy(msg, field_names=["intensity"]).ravel()
    b = pc2.read_points_numpy(original, field_names=["intensity"]).ravel()
    return {"intensity_field_present": True, "intensity_identical": bool(np.array_equal(a, b))}


def snapshot(msg):
    return bytes(msg.data), msg.header.frame_id, (msg.header.stamp.sec, msg.header.stamp.nanosec)


def try_case(name, fn):
    t = time.monotonic()
    try:
        out = fn()
        emit("case", case=name, ok=True, ms=round((time.monotonic() - t) * 1000, 2), **out)
    except Exception as exc:  # the exception itself is a measurement here
        emit("case", case=name, ok=False, ms=round((time.monotonic() - t) * 1000, 2),
             exception=type(exc).__name__, message=str(exc)[:300])


def pkg_version(name):
    try:
        root = ET.parse(f"/opt/ros/jazzy/share/{name}/package.xml").getroot()
        return root.findtext("version")
    except Exception as exc:
        return f"unreadable: {type(exc).__name__}"


def rebuild_in_target(cloud, xyz_target, target_frame):
    """research.md "발행 전 검사 패턴" candidate, executed here as case C."""
    pts = pc2.read_points(cloud).copy()
    pts["x"], pts["y"], pts["z"] = xyz_target.T
    header = Header(stamp=cloud.header.stamp, frame_id=target_frame)
    out = pc2.create_cloud(header, cloud.fields, pts, point_step=cloud.point_step)
    assert [f.name for f in out.fields] == [f.name for f in cloud.fields]
    assert out.point_step == cloud.point_step
    assert (out.height, out.width) == (1, cloud.width * cloud.height)
    assert len(out.data) == len(cloud.data) == out.width * out.height * out.point_step
    assert out.header.frame_id == target_frame
    return out


def manual_xyz(cloud, ts):
    """Read xyz, apply R*p + t from the TransformStamped."""
    xyz = pc2.read_points_numpy(cloud, field_names=["x", "y", "z"]).astype(np.float64)
    t = ts.transform.translation
    return xyz @ rotation_matrix(ts.transform.rotation).T + np.array([t.x, t.y, t.z])


def main():
    import tf2_sensor_msgs
    from tf2_sensor_msgs import do_transform_cloud

    emit("env", python=sys.version.split()[0], numpy=np.__version__,
         sensor_msgs_py=pkg_version("sensor_msgs_py"), tf2_sensor_msgs=pkg_version("tf2_sensor_msgs"),
         tf2_ros_py=pkg_version("tf2_ros_py"), tf2_sensor_msgs_file=tf2_sensor_msgs.__file__,
         byteorder=sys.byteorder)

    ts = transform_stamped()
    emit("input", n_points=N, fields=[f.name for f in xyzi_fields()], point_step=PLAIN_STEP,
         len_data=len(make_cloud().data), frame_id=SOURCE, transform_parent=ts.header.frame_id,
         transform_child=ts.child_frame_id, translation=list(TRANSLATION), rotation_zw=[QZ, QW])

    xyz3 = [PointField(name=n, offset=4 * k, datatype=PointField.FLOAT32, count=1)
            for k, n in enumerate(("x", "y", "z"))]

    # A: xyz only, original header -> what the naive rebuild produces.
    def case_a():
        cloud = make_cloud()
        before = snapshot(cloud)
        out = pc2.create_cloud(cloud.header, xyz3, manual_xyz(cloud, ts))
        r = {**describe(out, cloud), **xyz_error(out, reference_xyz(cloud)), **intensity_kept(out, cloud),
             "header_is_same_object": out.header is cloud.header, "original_unchanged": snapshot(cloud) == before}
        # A': trust the old intensity offset (12) on the new 12-byte layout.
        raw = np.frombuffer(bytes(out.data), dtype="<f4")
        step_f = out.point_step // 4
        old_off_f = 12 // 4
        idx = np.arange(out.width - 1)
        read_at_old = raw[idx * step_f + old_off_f]
        next_x = raw[(idx + 1) * step_f + 0]
        r["old_offset12_byte_for_point2"] = 2 * out.point_step + 12
        r["point3_x_byte"] = 3 * out.point_step + 0
        r["old_offset12_equals_next_x_count"] = int(np.sum(read_at_old == next_x))
        r["old_offset12_compared"] = int(idx.size)
        return r

    try_case("A_xyz_only_original_header", case_a)

    # A2: alias check - fixing frame_id after passing the original header object.
    def case_a2():
        cloud = make_cloud()
        out = pc2.create_cloud(cloud.header, xyz3, manual_xyz(cloud, ts))
        out.header.frame_id = TARGET
        return {"out_frame_id": out.header.frame_id, "original_frame_id_after": cloud.header.frame_id}

    try_case("A2_set_frame_id_on_shared_header", case_a2)

    # B: N x 3 array with the original 4 fields.
    def case_b():
        cloud = make_cloud()
        out = pc2.create_cloud(cloud.header, cloud.fields, manual_xyz(cloud, ts))
        return describe(out, cloud)

    try_case("B_xyz_array_with_4_fields", case_b)

    # C: copy full points, replace xyz, new header, point_step passed (research candidate code).
    def case_c(step=PLAIN_STEP, width=N, height=1):
        cloud = make_cloud(width, height, step)
        before = snapshot(cloud)
        out = rebuild_in_target(cloud, manual_xyz(cloud, ts), TARGET)
        return {**describe(out, cloud), **xyz_error(out, reference_xyz(cloud)), **intensity_kept(out, cloud),
                "original_unchanged": snapshot(cloud) == before}

    try_case("C_full_fields_point_step_new_header", case_c)

    # C0: read_points is a view - writing without copy changes the original message?
    def case_c0():
        cloud = make_cloud()
        before = snapshot(cloud)
        pts = pc2.read_points(cloud)
        writable = bool(pts.flags.writeable)
        if writable:
            pts["x"][0] = pts["x"][0] + 100.0
        return {"read_points_writeable": writable, "read_points_shape": list(pts.shape),
                "original_data_changed": bytes(cloud.data) != before[0]}

    try_case("C0_read_points_no_copy_write", case_c0)

    # D: official do_transform_cloud with TransformStamped.
    def case_d(step=PLAIN_STEP, width=N, height=1):
        cloud = make_cloud(width, height, step)
        before = snapshot(cloud)
        out = do_transform_cloud(cloud, ts)
        r = {**describe(out, cloud), **xyz_error(out, reference_xyz(cloud)), **intensity_kept(out, cloud),
             "original_unchanged": snapshot(cloud) == before, "header_is_same_object": out.header is cloud.header}
        if step == PLAIN_STEP and height == 1:
            c = rebuild_in_target(make_cloud(), manual_xyz(make_cloud(), ts), TARGET)
            r["bytes_identical_to_C"] = bytes(out.data) == bytes(c.data)
            r["max_abs_xyz_diff_vs_C"] = float(np.max(np.abs(
                pc2.read_points_numpy(out, ["x", "y", "z"]).astype(np.float64)
                - pc2.read_points_numpy(c, ["x", "y", "z"]).astype(np.float64))))
        return r

    try_case("D_do_transform_cloud_stamped", case_d)

    # D': plain Transform instead of TransformStamped.
    def case_d2():
        cloud = make_cloud()
        tr = Transform(translation=ts.transform.translation, rotation=ts.transform.rotation)
        out = do_transform_cloud(cloud, tr)
        return {**describe(out, cloud), **xyz_error(out, reference_xyz(cloud))}

    try_case("D2_do_transform_cloud_plain_transform", case_d2)

    # E: tail-padded cloud (point_step 32) through the official function.
    try_case("E_do_transform_cloud_padded32", lambda: case_d(step=PADDED_STEP))
    # E': same padded cloud, rebuilt with point_step passed.
    try_case("E2_rebuild_point_step_padded32", lambda: case_c(step=PADDED_STEP))
    # E'': padded cloud, xyz-only naive rebuild (padding disappears too).
    try_case("E3_xyz_only_padded32", lambda: (lambda c: describe(
        pc2.create_cloud(c.header, xyz3, manual_xyz(c, ts)), c))(make_cloud(point_step=PADDED_STEP)))

    # F: organized cloud (height > 1).
    try_case("F_do_transform_cloud_organized", lambda: case_d(width=ORG_W, height=ORG_H))

    # G: tf2_ros.Buffer.transform after import tf2_sensor_msgs (in-memory static transform).
    def case_g():
        buf = Buffer()
        buf.set_transform_static(transform_stamped(), "experiment")
        cloud = make_cloud()
        out = buf.transform(cloud, TARGET, timeout=Duration(seconds=1.0))
        return {**describe(out, cloud), **xyz_error(out, reference_xyz(cloud)), **intensity_kept(out, cloud)}

    try_case("G_buffer_transform_with_import", case_g)

    # G0: same call in a fresh interpreter that never imports tf2_sensor_msgs.
    child = r'''
import json, sys
import tf2_ros
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Header
b = tf2_ros.Buffer()
ts = TransformStamped(); ts.header.frame_id = "base_link"; ts.child_frame_id = "laser"; ts.transform.rotation.w = 1.0
b.set_transform_static(ts, "x")
c = PointCloud2(); c.header = Header(frame_id="laser")
r = {"tf2_sensor_msgs_loaded": "tf2_sensor_msgs" in sys.modules}
try:
    b.transform(c, "base_link", timeout=Duration(seconds=1.0)); r["ok"] = True
except Exception as e:
    r["ok"] = False; r["exception"] = type(e).__name__; r["message"] = str(e)[:300]
print(json.dumps(r))
'''
    t = time.monotonic()
    p = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=40)
    try:
        g0 = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        g0 = {"ok": None, "child_exit": p.returncode, "child_stderr": p.stderr[-300:]}
    emit("case", case="G0_buffer_transform_without_import", ms=round((time.monotonic() - t) * 1000, 2), **g0)

    # H: over real topics - static tf on /tf_static, cloud on /cloud_laser, transformer node publishes
    # /cloud_base via Buffer.transform, a checker node measures what arrived after serialization.
    rclpy.init()
    talker, app, checker = Node("cloud_talker"), Node("cloud_transformer"), Node("cloud_checker")
    StaticTransformBroadcaster(talker).sendTransform(transform_stamped())
    buf = Buffer()
    TransformListener(buf, app, spin_thread=False)
    pub_laser = talker.create_publisher(PointCloud2, "cloud_laser", 10)
    pub_base = app.create_publisher(PointCloud2, "cloud_base", 10)
    state = {"received": None, "transform_error": None, "tf_ready_s": None}

    def on_laser(msg):
        try:
            pub_base.publish(buf.transform(msg, TARGET, timeout=Duration(seconds=0)))
        except Exception as exc:
            state["transform_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    app.create_subscription(PointCloud2, "cloud_laser", on_laser, 10)
    checker.create_subscription(PointCloud2, "cloud_base", lambda m: state.__setitem__("received", m), 10)
    ex = SingleThreadedExecutor()
    for n in (talker, app, checker):
        ex.add_node(n)
    sent = make_cloud()
    start = time.monotonic()
    while time.monotonic() - start < WAIT_S and state["received"] is None:
        ex.spin_once(timeout_sec=0.05)
        if state["tf_ready_s"] is None and buf.can_transform(TARGET, SOURCE, Time()):
            state["tf_ready_s"] = round(time.monotonic() - start, 3)
        if state["tf_ready_s"] is not None:
            pub_laser.publish(sent)
    got = state["received"]
    if got is None:
        emit("case", case="H_topic_roundtrip", ok=False, tf_ready_s=state["tf_ready_s"],
             transform_error=state["transform_error"], waited_s=round(time.monotonic() - start, 3))
    else:
        emit("case", case="H_topic_roundtrip", ok=True, tf_ready_s=state["tf_ready_s"],
             roundtrip_s=round(time.monotonic() - start, 3), transform_error=state["transform_error"],
             **describe(got, sent), **xyz_error(got, reference_xyz(sent)), **intensity_kept(got, sent))
    ex.shutdown()
    for n in (talker, app, checker):
        n.destroy_node()
    rclpy.shutdown()

    emit("done", total_s=round(time.monotonic() - T0, 3), tolerance=TOL)


if __name__ == "__main__":
    main()
