#!/usr/bin/env python3
"""RGB-D back-projection check on ROS 2 Jazzy (rclpy + sensor_msgs only, no network).

A publisher node sends CameraInfo and two synthetic depth images of a ball-sized
disc (32FC1 metres and 16UC1 millimetres) over real rclpy topics. A subscriber
node finds the disc, reads its depth, back-projects the pixel with the correct
formula and with common mistakes, reprojects each result and measures what a
reprojection check catches and what it misses. Every number printed below is
computed at run time; only the scene inputs (K, ball position) are fixed.
"""
import json
import math
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image

# Scene inputs chosen for explanation (not measured from any real camera).
WIDTH, HEIGHT = 640, 480
FX = FY = 500.0
CX, CY = 320.0, 240.0
BALL_CENTER = (0.4, -0.2, 2.0)   # disc centre in the optical frame, metres
BALL_RADIUS = 0.05               # 0.1 m diameter ball
BACKGROUND_Z = 4.0               # wall behind the ball, metres
FOREGROUND_LIMIT = 3.0           # pixels nearer than this belong to the ball
INVALID_PIXEL = (100, 100)       # (u, v) forced to "no depth" (0 / NaN)
MISMATCHED_K = (610.0, 610.0, 316.0, 244.0)  # fx, fy, cx, cy of "another" camera
FRAME = "camera_color_optical_frame"


def emit(metric, **values):
    print(json.dumps({"metric": metric, **values}, ensure_ascii=False), flush=True)


def r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return round(x, n) if math.isfinite(x) else str(x)  # "inf", "-inf", "nan" kept visible


def camera_info(k0=FX):
    msg = CameraInfo()
    msg.header.frame_id = FRAME
    msg.width, msg.height = WIDTH, HEIGHT
    msg.distortion_model = "plumb_bob"
    msg.d = [0.0] * 5
    msg.k = [k0, 0.0, CX, 0.0, FY, CY, 0.0, 0.0, 1.0]
    msg.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    msg.p = [k0, 0.0, CX, 0.0, 0.0, FY, CY, 0.0, 0.0, 0.0, 1.0, 0.0]
    return msg


def render_depth_m():
    """Flat disc parallel to the image plane, built from its 3D definition."""
    u, v = np.meshgrid(np.arange(WIDTH, dtype=np.float64), np.arange(HEIGHT, dtype=np.float64))
    bx, by, bz = BALL_CENTER
    on_ball = ((u - CX) * bz / FX - bx) ** 2 + ((v - CY) * bz / FY - by) ** 2 <= BALL_RADIUS ** 2
    depth = np.where(on_ball, bz, BACKGROUND_Z)
    return depth


def render_sphere_m(center, radius):
    """Ray-cast a real sphere: each pixel stores the Z of the first surface hit."""
    u, v = np.meshgrid(np.arange(WIDTH, dtype=np.float64), np.arange(HEIGHT, dtype=np.float64))
    dx, dy = (u - CX) / FX, (v - CY) / FY          # ray with z = 1, so t is Z
    cx_, cy_, cz_ = center
    a = dx * dx + dy * dy + 1.0
    b = -2.0 * (dx * cx_ + dy * cy_ + cz_)
    c = cx_ * cx_ + cy_ * cy_ + cz_ * cz_ - radius * radius
    disc = b * b - 4 * a * c
    hit = disc >= 0
    t = np.where(hit, (-b - np.sqrt(np.where(hit, disc, 0.0))) / (2 * a), BACKGROUND_Z)
    return t


def image_msg(array, encoding):
    msg = Image()
    msg.header.frame_id = FRAME
    msg.height, msg.width = array.shape
    msg.encoding = encoding
    msg.is_bigendian = 0
    msg.step = array.shape[1] * array.dtype.itemsize
    msg.data = array.tobytes()
    return msg


def decode_depth(msg):
    """Return (raw array, metres array, valid mask) following REP-118 encodings."""
    if msg.encoding == "16UC1":
        raw = np.frombuffer(bytes(msg.data), dtype=np.uint16).reshape(msg.height, msg.width)
        return raw, raw.astype(np.float64) * 0.001, raw != 0
    if msg.encoding == "32FC1":
        raw = np.frombuffer(bytes(msg.data), dtype=np.float32).reshape(msg.height, msg.width)
        return raw, raw.astype(np.float64), np.isfinite(raw)
    raise ValueError(f"unsupported encoding {msg.encoding}")


def intrinsics_from_k(k):
    if k[0] == 0.0:
        raise ValueError("uncalibrated camera: K[0] == 0")
    return k[0], k[4], k[2], k[5]


def back_project(u, v, z, fx, fy, cx, cy):
    return (u - cx) * z / fx, (v - cy) * z / fy, z


def reproject(x, y, z, fx, fy, cx, cy):
    return fx * x / z + cx, fy * y / z + cy


def unit_ray(u, v, fx, fy, cx, cy):
    """Same as image_geometry PinholeCameraModel.project_pixel_to_3d_ray (unit vector)."""
    x, y = (u - cx) / fx, (v - cy) / fy
    norm = math.sqrt(x * x + y * y + 1.0)
    return x / norm, y / norm, 1.0 / norm


def detect_ball(metres, valid):
    mask = valid & (metres < FOREGROUND_LIMIT)
    vs, us = np.nonzero(mask)
    return float(us.mean()), float(vs.mean()), int(mask.sum())


class Camera(Node):
    def __init__(self):
        super().__init__("fake_rgbd_camera")
        self.info_pub = self.create_publisher(CameraInfo, "camera_info", 10)
        self.info_uncal_pub = self.create_publisher(CameraInfo, "camera_info_uncalibrated", 10)
        self.f32_pub = self.create_publisher(Image, "depth_32fc1", 10)
        self.u16_pub = self.create_publisher(Image, "depth_16uc1", 10)
        self.sphere_pub = self.create_publisher(Image, "depth_sphere_32fc1", 10)


class Consumer(Node):
    def __init__(self):
        super().__init__("ball_locator")
        self.got = {}
        self.arrival = {}
        for topic, kind in (("camera_info", CameraInfo), ("camera_info_uncalibrated", CameraInfo),
                            ("depth_32fc1", Image), ("depth_16uc1", Image), ("depth_sphere_32fc1", Image)):
            self.create_subscription(kind, topic, self._store(topic), 10)

    def _store(self, topic):
        def callback(msg):
            self.got[topic] = msg
            self.arrival[topic] = time.perf_counter()
        return callback


def main():
    started = time.perf_counter()
    rclpy.init()
    cam, consumer = Camera(), Consumer()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(cam)
    executor.add_node(consumer)

    pubs = [cam.info_pub, cam.info_uncal_pub, cam.f32_pub, cam.u16_pub, cam.sphere_pub]
    deadline = time.perf_counter() + 20
    while any(p.get_subscription_count() < 1 for p in pubs) and time.perf_counter() < deadline:
        executor.spin_once(timeout_sec=0.05)
    discovery_s = time.perf_counter() - started

    depth_m = render_depth_m()
    depth_f32 = depth_m.astype(np.float32)
    depth_f32[INVALID_PIXEL[1], INVALID_PIXEL[0]] = np.nan
    depth_u16 = np.rint(depth_m * 1000.0).astype(np.uint16)
    depth_u16[INVALID_PIXEL[1], INVALID_PIXEL[0]] = 0
    ray_u, ray_v = (BALL_CENTER[0] / BALL_CENTER[2]), (BALL_CENTER[1] / BALL_CENTER[2])
    sphere_center_z = BALL_CENTER[2] + BALL_RADIUS
    sphere_center = (ray_u * sphere_center_z, ray_v * sphere_center_z, sphere_center_z)
    sphere = render_sphere_m(sphere_center, BALL_RADIUS).astype(np.float32)

    outgoing = {"camera_info": (cam.info_pub, camera_info()),
                "camera_info_uncalibrated": (cam.info_uncal_pub, camera_info(k0=0.0)),
                "depth_32fc1": (cam.f32_pub, image_msg(depth_f32, "32FC1")),
                "depth_16uc1": (cam.u16_pub, image_msg(depth_u16, "16UC1")),
                "depth_sphere_32fc1": (cam.sphere_pub, image_msg(sphere, "32FC1"))}
    sent_at = {}
    deadline = time.perf_counter() + 20
    while len(consumer.got) < len(outgoing) and time.perf_counter() < deadline:
        for topic, (pub, msg) in outgoing.items():
            if topic not in consumer.got:
                sent_at[topic] = time.perf_counter()
                pub.publish(msg)
        end = time.perf_counter() + 0.5
        while len(consumer.got) < len(outgoing) and time.perf_counter() < end:
            executor.spin_once(timeout_sec=0.05)
    missing = sorted(set(outgoing) - set(consumer.got))
    emit("transport", discovery_seconds=r(discovery_s, 3), received=sorted(consumer.got), missing=missing,
         latency_ms={t: r((consumer.arrival[t] - sent_at[t]) * 1000, 3) for t in consumer.got},
         bytes={t: len(consumer.got[t].data) for t in consumer.got if t.startswith("depth")})
    if missing:
        emit("abort", reason="messages_not_received", missing=missing)
        return 1

    # 1. Intrinsics from the received CameraInfo, by index.
    info = consumer.got["camera_info"]
    k_type, k_dtype = type(info.k).__name__, str(getattr(info.k, "dtype", ""))
    k, p = [float(c) for c in info.k], [float(c) for c in info.p]
    fx, fy, cx, cy = intrinsics_from_k(k)
    emit("k_indices", frame_id=info.header.frame_id, fx_k0=fx, cx_k2=cx, fy_k4=fy, cy_k5=cy,
         k_len=len(k), p_len=len(p), rclpy_field_type=k_type, rclpy_field_dtype=k_dtype)
    emit("p_indices", fx_p0=p[0], cx_p2=p[2], fy_p5=p[5], cy_p6=p[6],
         p_rect_equals_k=[p[0], p[1], p[2], p[4], p[5], p[6], p[8], p[9], p[10]] == k)
    # Same mistake twice: once with the message's own numpy elements, once with plain Python floats.
    for label, src in (("numpy_elements_from_msg", info.p), ("python_floats", p)):
        wrong_fy, wrong_cy = src[4], src[5]
        with np.errstate(divide="ignore", invalid="ignore"):
            try:
                xyz = back_project(420.0, 190.0, 2.0, src[0], wrong_fy, src[2], wrong_cy)
                emit("p_with_k_indices", source=label, fy_from_p4=r(wrong_fy), cy_from_p5=r(wrong_cy),
                     exception=None, xyz=[r(c) for c in xyz])
            except ZeroDivisionError as exc:
                emit("p_with_k_indices", source=label, fy_from_p4=r(wrong_fy), cy_from_p5=r(wrong_cy),
                     exception=type(exc).__name__, xyz=None)

    # 5. Uncalibrated guard.
    try:
        intrinsics_from_k(list(consumer.got["camera_info_uncalibrated"].k))
        emit("uncalibrated_guard", k0=consumer.got["camera_info_uncalibrated"].k[0], refused=False)
    except ValueError as exc:
        emit("uncalibrated_guard", k0=consumer.got["camera_info_uncalibrated"].k[0], refused=True, reason=str(exc))

    # 2. Find the ball in each received depth image and read its depth.
    readings = {}
    for topic in ("depth_32fc1", "depth_16uc1"):
        msg = consumer.got[topic]
        raw, metres, valid = decode_depth(msg)
        u_c, v_c, n_px = detect_ball(metres, valid)
        ui, vi = int(round(u_c)), int(round(v_c))
        readings[topic] = (u_c, v_c, raw[vi, ui].item(), float(metres[vi, ui]))
        emit("ball_detection", topic=topic, encoding=msg.encoding, dtype=str(raw.dtype),
             center_u=r(u_c, 3), center_v=r(v_c, 3), ball_pixels=n_px,
             raw_value_at_center=r(raw[vi, ui].item(), 4), metres_at_center=r(metres[vi, ui], 4),
             background_raw=r(raw[0, WIDTH - 1].item(), 4))

    # 3. Back-projection variants, reprojection residual and Z check.
    u_c, v_c, raw_mm, z_m = readings["depth_16uc1"]
    truth = BALL_CENTER

    def case(name, xyz, reproj_k=(fx, fy, cx, cy), z_expected=z_m):
        x, y, z = xyz
        try:
            ru, rv = reproject(x, y, z, *reproj_k)
            res_u, res_v = ru - u_c, rv - v_c
            reproj_pass = bool(math.hypot(res_u, res_v) < 0.5)
        except ZeroDivisionError:
            ru = rv = res_u = res_v = None
            reproj_pass = False
        z_pass = bool(abs(z - z_expected) < 0.005)
        err3d = math.dist((x, y, z), truth)
        emit("case", name=name, xyz=[r(x), r(y), r(z)], reproj_uv=[r(ru, 4), r(rv, 4)],
             residual_px=[r(res_u, 4), r(res_v, 4)], reprojection_pass=reproj_pass,
             z_minus_depth=r(z - z_expected), z_check_pass=z_pass, error_vs_truth_m=r(err3d),
             caught_by_reprojection=not reproj_pass, caught_by_z_check=not z_pass)

    case("correct", back_project(u_c, v_c, z_m, fx, fy, cx, cy))
    case("principal_point_omitted", ((u_c) * z_m / fx, (v_c) * z_m / fy, z_m))
    case("16uc1_mm_used_consistently", back_project(u_c, v_c, float(raw_mm), fx, fy, cx, cy))
    case("mm_xy_but_metre_z", ((u_c - cx) * raw_mm / fx, (v_c - cy) * raw_mm / fy, z_m))
    ray = unit_ray(u_c, v_c, fx, fy, cx, cy)
    case("unit_ray_times_depth", tuple(c * z_m for c in ray))
    case("unit_ray_rescaled_to_z", tuple(c * (z_m / ray[2]) for c in ray))
    case("mismatched_k_reprojected_with_same_k", back_project(u_c, v_c, z_m, *MISMATCHED_K),
         reproj_k=MISMATCHED_K)
    case("mismatched_k_reprojected_with_message_k", back_project(u_c, v_c, z_m, *MISMATCHED_K))

    f_u, f_v, f_raw, f_z = readings["depth_32fc1"]
    x32 = back_project(f_u, f_v, f_z, fx, fy, cx, cy)
    x16 = back_project(u_c, v_c, z_m, fx, fy, cx, cy)
    emit("encoding_agreement", xyz_32fc1=[r(c) for c in x32], xyz_16uc1=[r(c) for c in x16],
         max_abs_diff_m=r(max(abs(a - b) for a, b in zip(x32, x16)), 9))

    # Depth is the Z component, not the ray length.
    for (u, v) in ((u_c, v_c), (0.0, 0.0)):
        ray = unit_ray(u, v, fx, fy, cx, cy)
        z_bad = ray[2] * z_m
        x, y, z = back_project(u, v, z_m, fx, fy, cx, cy)
        emit("depth_is_z", pixel=[r(u, 3), r(v, 3)], depth_m=r(z_m, 4), unit_ray_z=r(z_bad),
             z_short_percent=r((z_m - z_bad) / z_m * 100, 3), euclidean_distance_m=r(math.sqrt(x*x + y*y + z*z)))

    # 4. One pixel of detection error at several depths.
    for z in (0.5, 1.0, 2.0, 4.0):
        x0 = back_project(u_c, v_c, z, fx, fy, cx, cy)[0]
        x1 = back_project(u_c + 1.0, v_c, z, fx, fy, cx, cy)[0]
        emit("one_pixel_error", z_m=z, delta_x_m=r(x1 - x0))

    # 6. Invalid depth handling (16UC1 0 and 32FC1 NaN).
    iu, iv = INVALID_PIXEL
    for topic in ("depth_16uc1", "depth_32fc1"):
        raw, metres, valid = decode_depth(consumer.got[topic])
        naive_z = float(metres[iv, iu])
        try:
            naive = [r(c, 4) for c in reproject(*back_project(iu, iv, naive_z, fx, fy, cx, cy), fx, fy, cx, cy)]
        except ZeroDivisionError:
            naive = "ZeroDivisionError"
        emit("invalid_depth", topic=topic, raw=r(raw[iv, iu].item(), 4), naive_z=r(naive_z),
             naive_reprojection=naive, guarded_skipped=not bool(valid[iv, iu]))

    # Editor note check: centre pixel of a real sphere reads the surface, not the centre.
    s_raw, s_m, s_valid = decode_depth(consumer.got["depth_sphere_32fc1"])
    proj_u, proj_v = reproject(*sphere_center, fx, fy, cx, cy)
    su, sv, sn = detect_ball(s_m, s_valid)
    z_surface = float(s_m[int(round(proj_v)), int(round(proj_u))])
    emit("sphere_surface_vs_center", sphere_center_xyz=[r(c) for c in sphere_center], radius_m=BALL_RADIUS,
         center_projects_to=[r(proj_u, 3), r(proj_v, 3)], depth_at_that_pixel=r(z_surface),
         center_z_minus_surface_z=r(sphere_center[2] - z_surface), mask_centroid=[r(su, 3), r(sv, 3)],
         ball_pixels=sn)

    # Cost of the formula: one point vs a whole 640x480 depth image (vectorised numpy).
    n = 20000
    t0 = time.perf_counter()
    for _ in range(n):
        back_project(u_c, v_c, z_m, fx, fy, cx, cy)
    per_point_us = (time.perf_counter() - t0) / n * 1e6
    _, metres, valid = decode_depth(consumer.got["depth_16uc1"])
    uu, vv = np.meshgrid(np.arange(WIDTH), np.arange(HEIGHT))
    t0 = time.perf_counter()
    for _ in range(10):
        z = np.where(valid, metres, np.nan)
        cloud = np.stack(((uu - cx) * z / fx, (vv - cy) * z / fy, z), axis=-1)
    full_ms = (time.perf_counter() - t0) / 10 * 1000
    emit("timing", per_point_us=r(per_point_us, 3), full_image_ms=r(full_ms, 3),
         cloud_points=int(np.isfinite(cloud[..., 2]).sum()))

    emit("done", total_seconds=r(time.perf_counter() - started, 3), python=sys.version.split()[0],
         numpy=np.__version__)
    executor.shutdown()
    cam.destroy_node()
    consumer.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
