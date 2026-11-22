#!/usr/bin/env python3
"""Stereo baseline from camera_info on ROS 2 Jazzy (rclpy + sensor_msgs + stereo_msgs, no network).

A "driver" node publishes left/right CameraInfo for a rectified horizontal pair
(right P built as Tx = -fx' * B, as CameraInfo.msg defines) plus a DisparityImage.
A separate "consumer" node receives them over real rclpy topics, reads p[0]/p[3],
computes the baseline with the correct formula and with common mistakes, projects
3D points through the *received* P matrices, turns the disparity back into depth
and measures what goes wrong under pixel rounding, binning, unequal cx' and
swapped topics. Only the camera/scene inputs below are fixed; every printed
number is computed at run time from received messages.
"""
import json
import math
import time

import numpy as np
import rclpy
import rclpy.executors
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image
from stereo_msgs.msg import DisparityImage

# Inputs chosen for explanation (same values as the research worked example; not a real camera).
WIDTH, HEIGHT = 640, 480
FX_RECT = 700.0          # fx' = fy' of the rectified P
CX_RECT, CY_RECT = 320.0, 240.0
K_FX = 750.0             # raw-image K fx, deliberately different from fx'
BASELINE_M = 0.12        # design baseline used to *build* the right P
CX_RIGHT_VERGED = 330.0  # right cx' for the unequal-cx' variant
POINT = (0.5, 0.0, 2.0)  # worked-example point, metres, left optical frame
DEPTH_SWEEP = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
BINNING = 2
QUANT_STEPS = {"1px": 1.0, "1_16px": 1.0 / 16.0}  # integer matcher vs 1/16-px (DisparityImage delta_d)
TOPICS = ["left", "right", "right_mm", "right_verged", "disparity"]


def emit(metric, **values):
    print(json.dumps({"metric": metric, **values}, ensure_ascii=False), flush=True)


def r(x, n=9):
    if x is None:
        return None
    x = float(x)
    return round(x, n) if math.isfinite(x) else str(x)


def camera_info(frame, tx, cx=CX_RECT):
    msg = CameraInfo()
    msg.header.frame_id = frame
    msg.width, msg.height = WIDTH, HEIGHT
    msg.distortion_model = "plumb_bob"
    msg.d = [0.0] * 5
    msg.k = [K_FX, 0.0, 318.0, 0.0, K_FX, 242.0, 0.0, 0.0, 1.0]
    msg.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    msg.p = [FX_RECT, 0.0, cx, tx, 0.0, FX_RECT, CY_RECT, 0.0, 0.0, 0.0, 1.0, 0.0]
    return msg


def disparity_msg(f, t):
    """Row of disparities for the depth sweep, cx' equal so d = -Tx/Z."""
    msg = DisparityImage()
    msg.header.frame_id = "left_optical"
    msg.f, msg.t = float(f), float(t)
    d = np.array([f * t / z for z in DEPTH_SWEEP], dtype=np.float32)
    msg.min_disparity, msg.max_disparity, msg.delta_d = 1.0, 128.0, 1.0 / 16.0
    img = Image()
    img.height, img.width = 1, len(d)
    img.encoding, img.is_bigendian, img.step = "32FC1", 0, 4 * len(d)
    img.data = d.tobytes()
    msg.image = img
    return msg


class Driver(Node):
    def __init__(self, qos):
        super().__init__("stereo_driver")
        tx = -FX_RECT * BASELINE_M
        self.msgs = {
            "left": camera_info("left_optical", 0.0),
            "right": camera_info("right_optical", tx),
            "right_mm": camera_info("right_optical", -FX_RECT * BASELINE_M * 1000.0),
            "right_verged": camera_info("right_optical", tx, cx=CX_RIGHT_VERGED),
        }
        self.pubs = {k: self.create_publisher(CameraInfo, f"/stereo/{k}/camera_info", qos) for k in self.msgs}
        self.pubs["disparity"] = self.create_publisher(DisparityImage, "/stereo/disparity", qos)
        self.msgs["disparity"] = disparity_msg(FX_RECT, BASELINE_M)
        self.sent = {}

    def publish_all(self):
        for k, pub in self.pubs.items():
            self.sent[k] = time.monotonic()
            pub.publish(self.msgs[k])


class Consumer(Node):
    def __init__(self, qos):
        super().__init__("stereo_consumer")
        self.got, self.at = {}, {}
        for k in TOPICS[:-1]:
            self.create_subscription(CameraInfo, f"/stereo/{k}/camera_info", self._cb(k), qos)
        self.create_subscription(DisparityImage, "/stereo/disparity", self._cb("disparity"), qos)

    def _cb(self, key):
        def cb(msg):
            if key not in self.got:
                self.got[key], self.at[key] = msg, time.monotonic()
        return cb


def P(msg):
    return np.array(msg.p, dtype=np.float64).reshape(3, 4)


def project(Pm, xyz):
    u, v, w = Pm @ np.array([*xyz, 1.0])
    return u / w, v / w


def binned(Pm, b):
    """image_geometry PinholeCameraModel rule: scale (0,0),(0,2),(0,3) and (1,1),(1,2),(1,3) by 1/b."""
    out = Pm.copy()
    out[0, 0] /= b; out[0, 2] /= b; out[0, 3] /= b
    out[1, 1] /= b; out[1, 2] /= b; out[1, 3] /= b
    return out


def main():
    t0 = time.monotonic()
    rclpy.init()
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    driver, consumer = Driver(qos), Consumer(qos)
    ex = rclpy.executors.SingleThreadedExecutor()
    ex.add_node(driver)
    ex.add_node(consumer)
    while time.monotonic() - t0 < 10 and not all(
            consumer.count_publishers(f"/stereo/{k}/camera_info") for k in TOPICS[:-1]):
        ex.spin_once(timeout_sec=0.05)
    discovery = time.monotonic() - t0
    driver.publish_all()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and len(consumer.got) < len(TOPICS):
        ex.spin_once(timeout_sec=0.05)
    got = consumer.got
    emit("transport", discovery_seconds=r(discovery, 3), received=sorted(got),
         missing=sorted(set(TOPICS) - set(got)),
         latency_ms={k: r((consumer.at[k] - driver.sent[k]) * 1000, 3) for k in got})
    if set(TOPICS) - set(got):
        raise SystemExit("missing messages")

    left, right = got["left"], got["right"]
    emit("received_p_exact", **{k: [float(a) for a in got[k].p] == [float(a) for a in driver.msgs[k].p]
                                for k in TOPICS[:-1]},
         p_field_type=type(right.p).__name__, p_len=len(right.p))

    # --- where the baseline lives ---------------------------------------------------------
    emit("p_fields", left_p0_fx=r(left.p[0]), left_p3_tx=r(left.p[3]), left_p7_ty=r(left.p[7]),
         right_p0_fx=r(right.p[0]), right_p2_cx=r(right.p[2]), right_p3_tx=r(right.p[3]),
         right_p7_ty=r(right.p[7]), right_k0_fx=r(right.k[0]),
         fields_named_baseline=[f for f in CameraInfo.get_fields_and_field_types() if "base" in f.lower()])

    b_ok = -right.p[3] / right.p[0]
    b_raw = -right.p[3]
    b_k = -right.p[3] / right.k[0]
    b_left = -left.p[3] / left.p[0] + 0.0  # avoid printing -0.0
    b_mm = -got["right_mm"].p[3] / got["right_mm"].p[0]
    emit("baseline", correct_minus_p3_over_p0=r(b_ok), wrong_raw_tx=r(b_raw),
         wrong_raw_over_correct=r(b_raw / b_ok, 6), wrong_k_fx=r(b_k),
         wrong_k_fx_error_m=r(b_k - b_ok), wrong_k_fx_error_pct=r((b_k - b_ok) / b_ok * 100, 4),
         wrong_left_info=r(b_left), mm_calibration=r(b_mm), mm_over_m=r(b_mm / b_ok, 6))

    # --- worked example: project through the received P, recover depth ---------------------
    Pl, Pr = P(left), P(right)
    xl, yl = project(Pl, POINT)
    xr, yr = project(Pr, POINT)
    d = xl - xr
    emit("worked_point", point_m=list(POINT), x_left=r(xl), x_right=r(xr), y_left=r(yl), y_right=r(yr),
         disparity_px=r(d), z_from_minus_tx_over_d=r(-right.p[3] / d),
         z_from_fx_b_over_d=r(right.p[0] * b_ok / d), z_true=POINT[2])

    # --- depth sweep: float exact, -1 px sensitivity, half-step quantization bounds ------
    rows = []
    for z in DEPTH_SWEEP:
        pt = (0.3, 0.0, z)
        xl, _ = project(Pl, pt)
        xr, _ = project(Pr, pt)
        d = xl - xr
        z_back = -right.p[3] / d
        z_minus1 = -right.p[3] / (d - 1) if d > 1 else float("inf")
        row = {"z_true": z, "disparity_px": r(d, 6), "z_back": r(z_back),
               "z_if_d_minus_1": r(z_minus1, 6), "one_px_step_m": r(z_minus1 - z, 6)}
        for name, q in QUANT_STEPS.items():
            # A matcher that reports disparity in steps of q is off by up to q/2.
            far = -right.p[3] / (d - q / 2) if d > q / 2 else float("inf")
            near = -right.p[3] / (d + q / 2)
            row[f"half_step_{name}_far_error_m"] = r(far - z, 6)
            row[f"half_step_{name}_near_error_m"] = r(near - z, 6)
        rows.append({**row,
                     "first_order_z2_over_ftx": r(z * z / -right.p[3], 6)})
    emit("depth_sweep", rows=rows)

    # --- fx' cancels / binning ---------------------------------------------------------------
    Plb, Prb = binned(Pl, BINNING), binned(Pr, BINNING)
    xlb, _ = project(Plb, POINT)
    xrb, _ = project(Prb, POINT)
    db = xlb - xrb
    emit("binning", binning=BINNING, binned_fx=r(Prb[0, 0]), binned_tx=r(Prb[0, 3]),
         baseline_from_binned=r(-Prb[0, 3] / Prb[0, 0]), disparity_binned_px=r(db),
         z_binned_tx=r(-Prb[0, 3] / db), z_unbinned_tx_wrong=r(-Pr[0, 3] / db))

    # --- unequal cx' (verged) ----------------------------------------------------------------
    Prv = P(got["right_verged"])
    xl, _ = project(Pl, POINT)
    xrv, _ = project(Prv, POINT)
    d_raw = xl - xrv
    d_fix = d_raw - (left.p[2] - Prv[0, 2])
    emit("unequal_cx", left_cx=r(left.p[2]), right_cx=r(Prv[0, 2]), raw_disparity_px=r(d_raw),
         z_raw_no_cx_correction=r(-Prv[0, 3] / d_raw),
         corrected_disparity_px=r(d_fix), z_cx_corrected=r(-Prv[0, 3] / d_fix))

    # --- swapped topics: consumer believes left is right -------------------------------------
    xs_l, _ = project(Pr, POINT)   # image it calls "left" really from right camera
    xs_r, _ = project(Pl, POINT)
    ds = xs_l - xs_r
    emit("swapped_topics", baseline_from_believed_right=r(-left.p[3] / left.p[0] + 0.0),
         baseline_from_believed_left=r(-right.p[3] / right.p[0]),
         disparity_px=r(ds), z_using_real_tx=r(-right.p[3] / ds))

    # --- DisparityImage: f, t are float32 ------------------------------------------------------
    dm = got["disparity"]
    dimg = np.frombuffer(bytes(dm.image.data), dtype=np.float32)
    z_msg = [dm.f * dm.t / float(v) for v in dimg]
    z_f64 = [-right.p[3] / (-right.p[3] / z) for z in DEPTH_SWEEP]
    emit("disparity_image", f=r(dm.f), t=float(dm.t), t_minus_baseline=float(dm.t - b_ok),
         t_rel_error=float((dm.t - b_ok) / b_ok), disparities=[float(v) for v in dimg],
         z_f_t_over_d=[r(z, 9) for z in z_msg],
         max_abs_z_error_vs_f64_m=float(max(abs(a - b) for a, b in zip(z_msg, z_f64))),
         z_min_from_max_disparity=r(dm.f * dm.t / dm.max_disparity, 6),
         z_max_from_min_disparity=r(dm.f * dm.t / dm.min_disparity, 6))

    # --- does the base image ship image_geometry? -------------------------------------------
    try:
        from image_geometry import StereoCameraModel
        m = StereoCameraModel()
        m.from_camera_info(left, right)
        emit("image_geometry", available=True, baseline=r(m.baseline()),
             get_z_42=r(m.get_z(42.0)))
    except ImportError as exc:
        emit("image_geometry", available=False, error=type(exc).__name__)

    emit("done", total_seconds=r(time.monotonic() - t0, 3))
    ex.shutdown()
    driver.destroy_node()
    consumer.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
