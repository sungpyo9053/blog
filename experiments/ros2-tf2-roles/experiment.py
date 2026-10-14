#!/usr/bin/env python3
"""ROS 2 Jazzy: sensor topic vs tf2 data, latest (time 0) vs observation-time lookups.

One process, no network. Every printed line is a JSON object observed at run time. Output is kept compact
because the harness stores only the tail of stdout.
Numbers in this file (mount offset, robot speed, stamps 9.8/10.0/10.2/10.4, timeouts,
message counts) are experiment inputs and limits, not results.
"""
import json
import math
import threading
import time

import rclpy
from geometry_msgs.msg import PointStamped, TransformStamped
from rclpy.duration import Duration
from rclpy.event_handler import SubscriptionEventCallbacks
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from tf2_ros import Buffer, StaticTransformBroadcaster, TransformBroadcaster, TransformListener

T0 = time.monotonic()

# Inputs: sensor fixed to the body, robot moving along map x at constant speed.
MOUNT_XYZ = (0.2, 0.0, 0.1)
MOUNT_YAW = math.pi / 2
SPEED = 0.5  # m/s along map x
TF_STAMPS = (9.8, 10.0, 10.2)
LATE_STAMP = 10.4
OBS_STAMP = 10.0
OBS_POINT = (1.0, 0.0, 0.0)  # in sensor_link


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def rnd(v):
    return round(v, 6)


def stamp_s(stamp):
    return rnd(stamp.sec + stamp.nanosec * 1e-9)


def make_tf(parent, child, stamp, xyz, yaw):
    t = TransformStamped()
    t.header.frame_id = parent
    t.header.stamp = Time(seconds=stamp).to_msg()
    t.child_frame_id = child
    t.transform.translation.x, t.transform.translation.y, t.transform.translation.z = xyz
    t.transform.rotation.z = math.sin(yaw / 2)
    t.transform.rotation.w = math.cos(yaw / 2)
    return t


def body_tf(stamp):
    return make_tf("map", "base_link", stamp, (SPEED * stamp, 0.0, 0.0), 0.0)


def describe_tf(t):
    tr, q = t.transform.translation, t.transform.rotation
    return {"stamp_s": stamp_s(t.header.stamp), "xyz": [rnd(tr.x), rnd(tr.y), rnd(tr.z)],
            "qz_qw": [rnd(q.z), rnd(q.w)]}


def apply_manual(t, p):
    """p' = R p + t with quaternion R (independent of tf2_geometry_msgs)."""
    q, tr = t.transform.rotation, t.transform.translation
    x, y, z, w = q.x, q.y, q.z, q.w
    px, py, pz = p
    # v' = v + 2w (u x v) + 2 u x (u x v), u = (x, y, z)
    cx, cy, cz = y * pz - z * py, z * px - x * pz, x * py - y * px
    ccx, ccy, ccz = y * cz - z * cy, z * cx - x * cz, x * cy - y * cx
    return [rnd(px + 2 * w * cx + 2 * ccx + tr.x), rnd(py + 2 * w * cy + 2 * ccy + tr.y),
            rnd(pz + 2 * w * cz + 2 * ccz + tr.z)]


def point_msg(frame, stamp, xyz):
    p = PointStamped()
    p.header.frame_id = frame
    p.header.stamp = Time(seconds=stamp).to_msg()
    p.point.x, p.point.y, p.point.z = xyz
    return p


def wait_until(pred, timeout, step=0.01):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if pred():
            return True, rnd(time.monotonic() - start)
        time.sleep(step)
    return bool(pred()), rnd(time.monotonic() - start)


def lookup(buf, label, target, source, when, timeout=None):
    start = time.monotonic()
    try:
        if timeout is None:
            t = buf.lookup_transform(target, source, when)
        else:
            t = buf.lookup_transform(target, source, when, timeout=Duration(seconds=timeout))
    except Exception as exc:  # the exception itself is the measurement
        emit("lookup", label=label, pair=f"{target}<-{source}", requested_s=rnd(when.nanoseconds * 1e-9),
             timeout_s=timeout, ok=False, exception=type(exc).__name__, message=str(exc)[:120],
             elapsed_s=rnd(time.monotonic() - start))
        return None
    emit("lookup", label=label, pair=f"{target}<-{source}", requested_s=rnd(when.nanoseconds * 1e-9),
         timeout_s=timeout, ok=True, tf=describe_tf(t), elapsed_s=rnd(time.monotonic() - start))
    return t


def frames(buf):
    """Compact view of Buffer.all_frames_as_yaml(): child -> [parent, oldest, most_recent]."""
    import re
    out = {}
    for m in re.finditer(r"^(\S+): \n  parent: '([^']*)'.*?most_recent_transform: ([\d.]+)\n  oldest_transform: ([\d.]+)",
                         buf.all_frames_as_yaml(), re.S | re.M):
        out[m.group(1)] = [m.group(2), float(m.group(4)), float(m.group(3))]
    return out


def sub_topics(node):
    out = []
    for s in node.subscriptions:
        qos = getattr(s, "qos_profile", None)
        out.append({"topic": s.topic_name,
                    "durability": qos.durability.name if qos else None,
                    "reliability": qos.reliability.name if qos else None})
    return sorted(out, key=lambda d: d["topic"])


def version_of(pkg):
    try:
        import re
        from ament_index_python.packages import get_package_share_directory
        xml = open(get_package_share_directory(pkg) + "/package.xml").read()
        return re.search(r"<version>([^<]+)</version>", xml).group(1)
    except Exception as exc:
        return f"unknown:{type(exc).__name__}"


def main():
    rclpy.init()
    emit("env", rclpy=version_of("rclpy"), tf2_ros_py=version_of("tf2_ros_py"))

    talker = Node("tf2_roles_talker")
    app = Node("tf2_roles_app")
    ex = MultiThreadedExecutor(num_threads=4)
    for n in (talker, app):
        ex.add_node(n)
    threading.Thread(target=ex.spin, daemon=True).start()

    # --- 1) Sensor topic alone: the point arrives, tf2 is a separate connection.
    received = []
    app.create_subscription(PointStamped, "obs", received.append, 10)
    topics_before = sub_topics(app)
    buf = Buffer(node=app)
    TransformListener(buf, app, spin_thread=False)
    emit("subscriptions", node=app.get_name(), before_listener=topics_before, after_listener=sub_topics(app))

    obs_pub = talker.create_publisher(PointStamped, "obs", 10)
    obs = point_msg("sensor_link", OBS_STAMP, OBS_POINT)

    def got_point():
        if not received:
            obs_pub.publish(obs)
        return bool(received)

    ok, waited = wait_until(got_point, 10.0, step=0.1)
    first = received[0] if received else None
    emit("sensor_topic", received=ok, wait_s=waited, count=len(received),
         frame_id=first.header.frame_id if first else None,
         stamp_s=stamp_s(first.header.stamp) if first else None,
         point=[first.point.x, first.point.y, first.point.z] if first else None)
    emit("buffer_frames", phase="no_broadcaster", frames=frames(buf))
    lookup(buf, "no_broadcaster", "map", "sensor_link", Time())
    lookup(buf, "no_broadcaster_timeout", "map", "sensor_link", Time(), timeout=1.0)

    # --- 2) Only the fixed body->sensor relation (static, /tf_static).
    static_bc = StaticTransformBroadcaster(talker)
    static_bc.sendTransform(make_tf("base_link", "sensor_link", 0.0, MOUNT_XYZ, MOUNT_YAW))
    ok, waited = wait_until(lambda: buf.can_transform("base_link", "sensor_link", Time()), 10.0)
    emit("static_arrived", ok=ok, wait_s=waited)
    lookup(buf, "static_only_body_sensor", "base_link", "sensor_link", Time())
    lookup(buf, "static_only_map_sensor", "map", "sensor_link", Time())

    # --- 3) Dynamic map->base_link at three stamps (/tf).
    dyn_bc = TransformBroadcaster(talker)
    matched, match_wait = wait_until(lambda: talker.count_subscribers("/tf") >= 1, 5.0)
    time.sleep(0.5)  # graph count can precede DDS matching
    emit("tf_publisher_ready", graph_subscribers_seen=matched, wait_s=match_wait)
    for s in TF_STAMPS:
        dyn_bc.sendTransform(body_tf(s))
    ok, waited = wait_until(lambda: buf.can_transform("map", "base_link", Time(seconds=TF_STAMPS[-1])), 3.0)
    retried = not ok
    if not ok:  # discovery may drop the first /tf burst; republish once
        for s in TF_STAMPS:
            dyn_bc.sendTransform(body_tf(s))
        ok, waited = wait_until(lambda: buf.can_transform("map", "base_link", Time(seconds=TF_STAMPS[-1])), 10.0)
    have_all = all(buf.can_transform("map", "base_link", Time(seconds=s)) for s in TF_STAMPS)
    emit("dynamic_arrived", ok=ok, wait_s=waited, retried=retried, all_stamps_available=have_all)
    emit("buffer_frames", phase="static_and_dynamic", frames=frames(buf))

    t_latest = lookup(buf, "latest_time0", "map", "sensor_link", Time())
    t_obs = lookup(buf, "at_observation", "map", "sensor_link", Time(seconds=OBS_STAMP))
    lookup(buf, "interpolated", "map", "sensor_link", Time(seconds=10.1))
    lookup(buf, "future_no_timeout", "map", "sensor_link", Time(seconds=10.5))
    lookup(buf, "past_no_timeout", "map", "sensor_link", Time(seconds=9.0))
    lookup(buf, "past_timeout", "map", "sensor_link", Time(seconds=9.0), timeout=0.5)
    now = app.get_clock().now()
    lookup(buf, "clock_now", "map", "sensor_link", Time(nanoseconds=now.nanoseconds))
    t_rev = lookup(buf, "reversed_order", "sensor_link", "map", Time(seconds=OBS_STAMP))
    for s in (0.0, TF_STAMPS[0], OBS_STAMP, TF_STAMPS[-1], 1000.0):
        lookup(buf, f"static_at_{s}", "base_link", "sensor_link", Time(seconds=s))

    # Apply transforms to the observed point (stamp OBS_STAMP).
    try:
        from tf2_geometry_msgs import do_transform_point
    except Exception as exc:
        do_transform_point = None
        emit("tf2_geometry_msgs", available=False, exception=type(exc).__name__)
    results = {}
    for name, t in (("with_observation_time", t_obs), ("with_latest_time0", t_latest)):
        if t is None:
            continue
        lib = None
        if do_transform_point is not None:
            r = do_transform_point(obs, t)
            lib = [rnd(r.point.x), rnd(r.point.y), rnd(r.point.z)]
        results[name] = apply_manual(t, OBS_POINT)
        emit("point_in_map", method=name, tf_stamp_s=stamp_s(t.header.stamp), manual=results[name],
             tf2_geometry_msgs=lib)
    relabeled = point_msg("map", OBS_STAMP, OBS_POINT)
    emit("point_frame_id_relabel", frame_id=relabeled.header.frame_id,
         point=[relabeled.point.x, relabeled.point.y, relabeled.point.z])
    if "with_observation_time" in results:
        ref = results["with_observation_time"]
        dist = lambda a: rnd(math.dist(a, ref))
        emit("point_error_vs_observation_time",
             latest_time0_m=dist(results["with_latest_time0"]) if "with_latest_time0" in results else None,
             frame_id_relabel_m=dist(list(OBS_POINT)))
    if t_rev is not None and do_transform_point is not None:
        back = do_transform_point(point_msg("map", OBS_STAMP, results.get("with_observation_time", OBS_POINT)), t_rev)
        emit("roundtrip_map_to_sensor", point=[rnd(back.point.x), rnd(back.point.y), rnd(back.point.z)])

    # --- 4) Late data: timeout waits for data that is published later.
    lookup(buf, "late_before_publish", "map", "sensor_link", Time(seconds=LATE_STAMP))
    sent_at = {}

    def late_publish():
        sent_at["t"] = time.monotonic()
        dyn_bc.sendTransform(body_tf(LATE_STAMP))

    timer = threading.Timer(0.3, late_publish)
    call_t = time.monotonic()
    timer.start()
    lookup(buf, "late_with_timeout", "map", "sensor_link", Time(seconds=LATE_STAMP), timeout=2.0)
    timer.join()
    emit("late_publish", published_after_call_s=rnd(sent_at["t"] - call_t) if "t" in sent_at else None)
    lookup(buf, "latest_time0_after_late", "map", "sensor_link", Time())

    # --- 5) A listener that joins after everything was sent.
    late = Node("tf2_roles_late_app")
    late_buf = Buffer(node=late)
    TransformListener(late_buf, late, spin_thread=False)
    ex.add_node(late)
    st_ok, st_wait = wait_until(lambda: late_buf.can_transform("base_link", "sensor_link", Time()), 3.0)
    dyn_ok, dyn_wait = wait_until(lambda: late_buf.can_transform("map", "base_link", Time()), 2.0)
    emit("late_joiner", static_received=st_ok, static_wait_s=st_wait,
         dynamic_received=dyn_ok, dynamic_wait_s=dyn_wait, frames=frames(late_buf))

    # --- 6) Same topic name, incompatible QoS.
    events = []
    be_pub = talker.create_publisher(PointStamped, "obs_qos",
                                     QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
    got = {"reliable_sub": 0, "best_effort_sub": 0}
    app.create_subscription(PointStamped, "obs_qos", lambda m: got.__setitem__("reliable_sub", got["reliable_sub"] + 1),
                            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE),
                            event_callbacks=SubscriptionEventCallbacks(
                                incompatible_qos=lambda e: events.append(e)))
    app.create_subscription(PointStamped, "obs_qos",
                            lambda m: got.__setitem__("best_effort_sub", got["best_effort_sub"] + 1),
                            QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
    wait_until(lambda: be_pub.get_subscription_count() >= 1, 5.0)  # incompatible subs are not counted
    time.sleep(1.0)
    sent = 0
    for _ in range(20):
        be_pub.publish(obs)
        sent += 1
        time.sleep(0.05)
    time.sleep(0.5)
    ev = events[-1] if events else None
    emit("qos", publisher="BEST_EFFORT", sent=sent, graph_subscription_count=be_pub.get_subscription_count(),
         received=dict(got), incompatible_qos_events=len(events),
         last_policy=getattr(getattr(ev, "last_policy_kind", None), "name", None) if ev else None,
         total_count=getattr(ev, "total_count", None) if ev else None)

    ex.shutdown()
    for n in (late, app, talker):
        n.destroy_node()
    rclpy.shutdown()
    emit("done", elapsed_s=rnd(time.monotonic() - T0))


if __name__ == "__main__":
    main()
