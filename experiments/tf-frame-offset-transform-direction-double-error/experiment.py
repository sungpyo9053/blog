#!/usr/bin/env python3
"""tf 변환을 거꾸로 발행하면 자식 원점이 오프셋의 몇 배만큼 벌어지는지 실제 tf2로 잰다.

모든 변환은 실제 /tf_static, /tf 토픽으로 발행하고 TransformListener가 받은 값을
lookup_transform으로 다시 읽는다. 출력 숫자는 모두 실행 중 조회한 결과에서 계산한다.
"""
import json
import math
import re
import time

import rclpy
from rclpy.time import Time
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformListener, StaticTransformBroadcaster, TransformBroadcaster

T0 = time.monotonic()


def emit(stamp_time=True, **record):
    if stamp_time:
        record["t_s"] = round(time.monotonic() - T0, 3)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def quat_yaw(deg):
    half = math.radians(deg) / 2.0
    return (0.0, 0.0, math.sin(half), math.cos(half))


def rotate(q, v):
    x, y, z, w = q
    # v' = q v q*  (벡터 회전 공식)
    tx = 2 * (y * v[2] - z * v[1])
    ty = 2 * (z * v[0] - x * v[2])
    tz = 2 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + (y * tz - z * ty),
            v[1] + w * ty + (z * tx - x * tz),
            v[2] + w * tz + (x * ty - y * tx))


def make(stamp, parent, child, xyz, yaw_deg=0.0):
    msg = TransformStamped()
    msg.header.stamp = stamp
    msg.header.frame_id = parent
    msg.child_frame_id = child
    msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z = xyz
    q = quat_yaw(yaw_deg)
    (msg.transform.rotation.x, msg.transform.rotation.y,
     msg.transform.rotation.z, msg.transform.rotation.w) = q
    return msg


def inverse(xyz, yaw_deg):
    """(R, t)의 역 (R^T, -R^T t) — 올바른 역변환을 발행하는 대조군용."""
    q = quat_yaw(-yaw_deg)
    r = rotate(q, xyz)
    return (-r[0], -r[1], -r[2]), -yaw_deg


# 시나리오: (이름, 의도한 부모→자식 이동량, 회전, 실제로 발행한 방식)
# kind: intended=의도대로, swap=부모·자식만 바꿈, sign=부호만 반대, omit=오프셋을 빠뜨림(값 자체 오류),
#       swap_true_inverse=부모·자식을 바꾸되 올바른 역변환 값, swap_neg_t=부모·자식을 바꾸고 이동량 부호만 뒤집음
SCENARIOS = []
for kind in ("intended", "swap", "sign"):
    SCENARIOS.append((f"z1m_{kind}", (0.0, 0.0, 1.0), 0.0, kind))
for kind in ("intended", "swap", "sign", "omit"):
    SCENARIOS.append((f"laser02_{kind}", (0.2, 0.0, 0.0), 0.0, kind))
for yaw in (90.0, 120.0, 180.0):
    for kind in ("swap", "sign", "swap_true_inverse", "swap_neg_t"):
        SCENARIOS.append((f"rot{int(yaw)}_{kind}", (0.2, 0.0, 0.0), yaw, kind))

PROBE_POINT = {"z1m": (0.0, 0.0, 0.5), "laser02": (0.5, 0.0, 0.0)}


def published(sid, xyz, yaw, kind, stamp):
    parent, child = f"{sid}_parent", f"{sid}_child"
    if kind == "intended":
        return make(stamp, parent, child, xyz, yaw)
    if kind == "swap":
        return make(stamp, child, parent, xyz, yaw)
    if kind == "sign":
        return make(stamp, parent, child, tuple(-c for c in xyz), yaw)
    if kind == "omit":
        return make(stamp, parent, child, (0.0, 0.0, 0.0), yaw)
    if kind == "swap_true_inverse":
        t, r = inverse(xyz, yaw)
        return make(stamp, child, parent, t, r)
    if kind == "swap_neg_t":
        return make(stamp, child, parent, tuple(-c for c in xyz), -yaw)
    raise ValueError(kind)


def parents_from_yaml(yaml_text):
    found = {}
    current = None
    for line in yaml_text.splitlines():
        m = re.match(r"^(\S[^:]*):\s*$", line)
        if m:
            current = m.group(1).strip().strip("'\"")
            continue
        m = re.match(r"^\s+parent:\s*'?([^']*)'?\s*$", line)
        if m and current:
            found[current] = m.group(1)
    return found


def spin_until(node, predicate, limit_s):
    end = time.monotonic() + limit_s
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        if predicate():
            return True
    return False


def main():
    rclpy.init()
    node = rclpy.create_node("tf_direction_experiment")
    buffer = Buffer()
    TransformListener(buffer, node, spin_thread=False)
    static = StaticTransformBroadcaster(node)
    dynamic = TransformBroadcaster(node)
    stamp = node.get_clock().now().to_msg()

    messages = [published(sid, xyz, yaw, kind, stamp) for sid, xyz, yaw, kind in SCENARIOS]
    # 트리 충돌 대조: odom→base는 동적(/tf). ok_* 는 base→laser를 정상 발행, clash_* 는 laser→base로 뒤집어 발행.
    messages.append(make(stamp, "ok_base", "ok_laser", (0.2, 0.0, 0.0)))
    messages.append(make(stamp, "clash_laser", "clash_base", (0.2, 0.0, 0.0)))
    static.sendTransform(messages)
    emit(event="published", static_transforms=len(messages), scenarios=len(SCENARIOS))

    def odom_tick():
        now = node.get_clock().now().to_msg()
        dynamic.sendTransform([make(now, "odom", "ok_base", (1.0, 0.0, 0.0)),
                               make(now, "odom", "clash_base", (1.0, 0.0, 0.0))])
    node.create_timer(0.05, odom_tick)

    last = SCENARIOS[-1][0]
    ready = spin_until(node, lambda: buffer.can_transform(f"{last}_parent", f"{last}_child", Time())
                       and buffer.can_transform(f"{SCENARIOS[0][0]}_parent", f"{SCENARIOS[0][0]}_child", Time()),
                       15.0)
    emit(event="listener_ready", ready=ready)
    if not ready:
        raise SystemExit("static transforms never reached the listener")

    parents = parents_from_yaml(buffer.all_frames_as_yaml())
    for sid, xyz, yaw, kind in SCENARIOS:
        parent, child = f"{sid}_parent", f"{sid}_child"
        # target=의도한 부모, source=의도한 자식 → translation이 곧 부모 안 자식 원점 위치
        tf = buffer.lookup_transform(parent, child, Time())
        tr = tf.transform.translation
        rq = tf.transform.rotation
        origin = (tr.x, tr.y, tr.z)
        gap = math.dist(origin, xyz)
        offset = math.dist((0, 0, 0), xyz)
        tree_parent = parents.get(child)
        # 짧은 키: harness가 stdout 끝 8000자만 보존하므로 한 줄을 작게 유지한다.
        # off=의도 오프셋, org=조회한 자식 원점, gap=벌어짐, ratio=gap/off, cpar=트리에서 자식의 부모
        record = dict(s=sid, yaw=yaw, off=round(offset, 6), org=[round(c, 6) + 0.0 for c in origin],
                      gap=round(gap, 6), ratio=round(gap / offset, 6),
                      cpar=tree_parent[len(sid) + 1:] if tree_parent else "root")
        base = sid.split("_")[0]
        if base in PROBE_POINT:
            p = PROBE_POINT[base]
            moved = rotate((rq.x, rq.y, rq.z, rq.w), p)
            measured_point = tuple(moved[i] + origin[i] for i in range(3))
            intended_point = tuple(p[i] + xyz[i] for i in range(3))
            record.update(pt=list(p), pt_par=[round(c, 6) + 0.0 for c in measured_point],
                          pt_gap=round(math.dist(measured_point, intended_point), 6))
        emit(stamp_time=False, **record)

    emit(event="tree_before_odom", ok_base_parent=parents.get("ok_base", "missing"),
         clash_base_parent=parents.get("clash_base", "missing"),
         odom_known="odom" in parents.values())
    odom_ready = spin_until(node, lambda: "odom" in parents_from_yaml(buffer.all_frames_as_yaml()).values(), 10.0)
    emit(event="odom_ready", ready=odom_ready)

    # 트리 충돌: 3초 동안 odom→laser 조회 성공 횟수와 base의 부모를 표본으로 센다.
    samples = {"ok": {"tries": 0, "success": 0, "parents": {}, "errors": {}, "x": []},
               "clash": {"tries": 0, "success": 0, "parents": {}, "errors": {}, "x": []}}
    end = time.monotonic() + 3.0
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        tree = parents_from_yaml(buffer.all_frames_as_yaml())
        for key in samples:
            s = samples[key]
            s["tries"] += 1
            par = tree.get(f"{key}_base", "missing")
            s["parents"][par] = s["parents"].get(par, 0) + 1
            try:
                tf = buffer.lookup_transform("odom", f"{key}_laser", Time())
                s["success"] += 1
                s["x"].append(tf.transform.translation.x)
            except Exception as exc:  # noqa: BLE001 - 예외 종류 자체가 측정 대상
                name = type(exc).__name__
                s["errors"][name] = s["errors"].get(name, 0) + 1
                if "first_error" not in s:
                    s["first_error"] = str(exc).splitlines()[0][:200]
    for key, s in samples.items():
        xs = s.pop("x")
        emit(event="tree_clash_sample", case=key, odom_to_base_x_m=1.0, static_offset_m=0.2,
             laser_x_in_odom_min=round(min(xs), 6) if xs else None,
             laser_x_in_odom_max=round(max(xs), 6) if xs else None, **s)

    node.destroy_node()
    rclpy.shutdown()
    emit(event="done")


if __name__ == "__main__":
    main()
