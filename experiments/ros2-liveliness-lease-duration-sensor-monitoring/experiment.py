#!/usr/bin/env python3
"""ROS 2 Jazzy liveliness experiment: does a stopped camera topic get detected?

The monitor (this process) and the "camera driver" (a child process started with
``--pub``) are separate processes, like a real driver and a separate watchdog node.
Every number printed is measured while the script runs; nothing is precomputed.

Cases (camera = 10 Hz std_msgs/String, lease = 0.5 s unless noted):
  E1 AUTOMATIC, lone publisher, publishing stops, process stays alive
  E2 AUTOMATIC, publisher process frozen with SIGSTOP
  E3 MANUAL_BY_TOPIC, lone publisher, publishing stops
  E4 same process keeps a 100 Hz IMU topic going while both camera topics stop
  E5 QoS compatibility: subscriber lease/kind vs publisher, real connection vs qos_check_compatible
  E6 MANUAL_BY_TOPIC with lease close to the period (0.05 / 0.1 / 0.2 s) while publishing normally
An application-level watchdog (receive-gap > 0.5 s, checked by a 10 ms timer) runs next
to the QoS events on the camera subscriptions for comparison.
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time

CAMERA_HZ = 10.0
IMU_HZ = 100.0
LEASE = 0.5
PUBLISH_S = 2.0
OBSERVE_S = 3.0
WATCHDOG_S = 0.5


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def ms(seconds):
    return None if seconds is None else round(seconds * 1000.0, 1)


def make_qos(kind, lease):
    from rclpy.duration import Duration
    from rclpy.qos import (DurabilityPolicy, HistoryPolicy, LivelinessPolicy, QoSProfile,
                           ReliabilityPolicy)
    profile = QoSProfile(depth=10, history=HistoryPolicy.KEEP_LAST,
                         reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.VOLATILE)
    if kind is not None:
        profile.liveliness = {"automatic": LivelinessPolicy.AUTOMATIC,
                              "manual": LivelinessPolicy.MANUAL_BY_TOPIC}[kind]
    if lease is not None:
        profile.liveliness_lease_duration = Duration(seconds=lease)
    return profile


# --------------------------------------------------------------------------- publisher
def run_publisher(cfg):
    import rclpy
    from rclpy.event_handler import PublisherEventCallbacks
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from std_msgs.msg import String

    rclpy.init()
    node = Node("pub_" + cfg["case"])
    state = {}

    def lost_cb(topic):
        def cb(info):
            emit({"ev": "liveliness_lost", "topic": topic, "t": time.monotonic(),
                  "total_count": info.total_count})
        return cb

    for t in cfg["topics"]:
        ev = PublisherEventCallbacks(liveliness=lost_cb(t["name"]))
        pub = node.create_publisher(String, t["name"], make_qos(t["kind"], t["lease"]),
                                    event_callbacks=ev)
        state[t["name"]] = {"pub": pub, "cfg": t, "count": 0, "last": None, "timer": None}

    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        if all(state[n]["pub"].get_subscription_count() > 0 for n in cfg["wait_for"]):
            break
        rclpy.spin_once(node, timeout_sec=0.05)
    matched = all(state[n]["pub"].get_subscription_count() > 0 for n in cfg["wait_for"])
    if not cfg["wait_for"]:
        time.sleep(1.0)
    t0 = time.monotonic()
    emit({"ev": "start", "t": t0, "matched": matched})

    def tick(name):
        def cb():
            s = state[name]
            stop_after = s["cfg"]["stop_after"]
            now = time.monotonic()
            if stop_after is not None and now - t0 >= stop_after:
                s["timer"].cancel()
                emit({"ev": "stopped", "topic": name, "t_last_pub": s["last"], "count": s["count"]})
                return
            msg = String()
            msg.data = str(s["count"])
            s["pub"].publish(msg)
            s["count"] += 1
            s["last"] = time.monotonic()
        return cb

    for name, s in state.items():
        s["timer"] = node.create_timer(1.0 / s["cfg"]["hz"], tick(name))
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
            rclpy.try_shutdown()
        except Exception:
            pass


# --------------------------------------------------------------------------- monitor
class Probe:
    def __init__(self, node, label, topic, kind, lease, watchdog):
        from rclpy.event_handler import SubscriptionEventCallbacks
        from std_msgs.msg import String
        self.label, self.topic, self.kind, self.lease = label, topic, kind, lease
        self.watchdog = watchdog
        self.recv = []
        self.live = []
        self.incompat = []
        self.wd_hits = []
        self._wd_armed = True
        ev = SubscriptionEventCallbacks(liveliness=self._on_live, incompatible_qos=self._on_incompat)
        self.sub = node.create_subscription(String, topic, self._on_msg, make_qos(kind, lease),
                                            event_callbacks=ev)

    def _on_msg(self, _msg):
        self.recv.append(time.monotonic())
        self._wd_armed = True

    def _on_live(self, info):
        self.live.append((time.monotonic(), info.alive_count, info.not_alive_count,
                          info.alive_count_change, info.not_alive_count_change))

    def _on_incompat(self, info):
        try:
            from rclpy.qos import QoSPolicyKind
            policy = QoSPolicyKind(info.last_policy_kind).name
        except Exception:
            policy = str(info.last_policy_kind)
        self.incompat.append((time.monotonic(), info.total_count, policy))

    def check_watchdog(self, now):
        if self.watchdog and self.recv and self._wd_armed and now - self.recv[-1] > WATCHDOG_S:
            self.wd_hits.append(now)
            self._wd_armed = False


def start_publisher(cfg):
    proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--pub", json.dumps(cfg)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    events, other = [], []

    def reader():
        for line in proc.stdout:
            line = line.strip()
            try:
                events.append(json.loads(line))
            except ValueError:
                if line:
                    other.append(line)
    threading.Thread(target=reader, daemon=True).start()
    return proc, events, other


def spin_for(executor, seconds, until=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        executor.spin_once(timeout_sec=0.005)
        if until is not None and until():
            return True
    return until() if until is not None else True


def stop_process(proc):
    try:
        os.kill(proc.pid, signal.SIGCONT)
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
        proc.wait()


def run_case(node, executor, case, topics, subs, mode):
    """mode: 'stop_publishing' | 'sigstop' | 'continuous'."""
    probes = [Probe(node, *s) for s in subs]
    watch = node.create_timer(0.01, lambda: [p.check_watchdog(time.monotonic()) for p in probes])
    cfg = {"case": case, "topics": topics,
           "wait_for": [t["name"] for t in topics if t.get("expect_match", True)]}
    proc, events, other = start_publisher(cfg)
    started = spin_for(executor, 20.0, lambda: any(e["ev"] == "start" for e in events))
    start = next((e for e in events if e["ev"] == "start"), None)
    result = {"case": case, "mode": mode, "publisher_matched": bool(start and start["matched"])}
    if not started:
        stop_process(proc)
        result.update({"error": "publisher did not start", "publisher_output": other[-5:]})
        node.destroy_timer(watch)
        for p in probes:
            node.destroy_subscription(p.sub)
        return result

    stop_times = {}
    if mode == "sigstop":
        spin_for(executor, PUBLISH_S)
        t_stop = time.monotonic()
        os.kill(proc.pid, signal.SIGSTOP)
        stop_times = {t["name"]: t_stop for t in topics}
        spin_for(executor, OBSERVE_S)
    elif mode == "stop_publishing":
        stopping = [t["name"] for t in topics if t["stop_after"] is not None]
        spin_for(executor, PUBLISH_S + 3.0,
                 lambda: all(any(e["ev"] == "stopped" and e["topic"] == n for e in events)
                             for n in stopping))
        for e in events:
            if e["ev"] == "stopped":
                stop_times[e["topic"]] = e["t_last_pub"]
        spin_for(executor, OBSERVE_S)
    else:
        spin_for(executor, PUBLISH_S + OBSERVE_S)
    t_end = time.monotonic()
    stop_process(proc)
    node.destroy_timer(watch)

    t_start = start["t"]
    out = []
    for p in probes:
        t_stop = stop_times.get(p.topic)
        # Every message on a stopped topic was sent before t_stop; the last one can still
        # arrive a little after it, so "last receive" is the latest receive in the window.
        received = [t for t in p.recv if t <= t_end]
        lost = [e for e in p.live if e[4] > 0 and t_start < e[0] <= t_end]
        lost_after_stop = [e for e in lost if t_stop is not None and e[0] > t_stop]
        last_rx = received[-1] if received else None
        first_lost = lost_after_stop[0][0] if lost_after_stop else None
        wd = [t for t in p.wd_hits if t_stop is not None and t_stop < t <= t_end]
        row = {
            "probe": p.label, "topic": p.topic, "sub_kind": p.kind or "system_default",
            "sub_lease_s": p.lease, "msgs_received": len([t for t in p.recv if t <= t_end]),
            "liveliness_events": len([e for e in p.live if e[0] <= t_end]),
            "not_alive_increments": len(lost),
            "incompatible_qos_events": len([e for e in p.incompat if e[0] <= t_end]),
        }
        if p.incompat:
            row["incompatible_policy"] = p.incompat[-1][2]
        if t_stop is not None:
            row.update({
                "msgs_before_stop": len(received),
                "last_rx_ms_after_stop": ms(last_rx - t_stop) if last_rx else None,
                "not_alive_after_stop": len(lost_after_stop),
                "detect_ms_from_stop": ms(first_lost - t_stop) if first_lost else None,
                "detect_ms_from_last_rx": ms(first_lost - last_rx) if first_lost and last_rx else None,
            })
            if p.watchdog:
                row["watchdog_ms_from_stop"] = ms(wd[0] - t_stop) if wd else None
                row["watchdog_ms_from_last_rx"] = ms(wd[0] - last_rx) if wd and last_rx else None
        if mode == "continuous" and len(p.recv) > 1:
            gaps = [b - a for a, b in zip(p.recv, p.recv[1:])]
            row["max_rx_gap_ms"] = ms(max(gaps))
        out.append(row)
    lost_pub = [e for e in events if e["ev"] == "liveliness_lost" and e["t"] <= t_end]
    result.update({
        "observe_s": round(t_end - (max(stop_times.values()) if stop_times else t_start), 2),
        "published": {e["topic"]: e["count"] for e in events if e["ev"] == "stopped"},
        "publisher_liveliness_lost": {n: len([e for e in lost_pub if e["topic"] == n])
                                      for n in sorted({e["topic"] for e in lost_pub})},
        "probes": out,
    })
    for p in probes:
        node.destroy_subscription(p.sub)
    return result


def topic(name, kind, lease, hz=CAMERA_HZ, stop_after=PUBLISH_S, expect_match=True):
    return {"name": name, "kind": kind, "lease": lease, "hz": hz, "stop_after": stop_after,
            "expect_match": expect_match}


def compat_rows():
    from rclpy.qos import qos_check_compatible
    pairs = [("pub_manual_0.5__sub_auto_0.3", ("manual", 0.5), ("automatic", 0.3)),
             ("pub_manual_0.5__sub_auto_1.0", ("manual", 0.5), ("automatic", 1.0)),
             ("pub_default__sub_auto_0.5", (None, None), ("automatic", 0.5)),
             ("pub_default__sub_default", (None, None), (None, None)),
             ("pub_auto_0.5__sub_manual_inf", ("automatic", 0.5), ("manual", None))]
    rows = {}
    for label, pq, sq in pairs:
        comp, reason = qos_check_compatible(make_qos(*pq), make_qos(*sq))
        rows[label] = {"check": getattr(comp, "name", str(comp)), "reason": reason}
    return rows


def main():
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node

    wall0 = time.monotonic()
    rclpy.init()
    node = Node("liveliness_monitor")
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    from rclpy.utilities import get_rmw_implementation_identifier
    emit({"ev": "env", "rmw": get_rmw_implementation_identifier(),
          "ros_distro": os.environ.get("ROS_DISTRO"), "camera_hz": CAMERA_HZ, "lease_s": LEASE,
          "publish_s": PUBLISH_S, "observe_s": OBSERVE_S, "watchdog_s": WATCHDOG_S})

    cases = [
        ("E1_auto_stop_publishing", [topic("/e1/camera", "automatic", LEASE)],
         [("camera_auto", "/e1/camera", "automatic", LEASE, True)], "stop_publishing"),
        ("E2_auto_sigstop", [topic("/e2/camera", "automatic", LEASE, stop_after=None)],
         [("camera_auto", "/e2/camera", "automatic", LEASE, True)], "sigstop"),
        ("E3_manual_stop_publishing", [topic("/e3/camera", "manual", LEASE)],
         [("camera_manual", "/e3/camera", "manual", LEASE, True)], "stop_publishing"),
        ("E4_imu_keeps_publishing",
         [topic("/e4/camera_auto", "automatic", LEASE), topic("/e4/imu_auto", "automatic", LEASE, IMU_HZ, None),
          topic("/e4/camera_manual", "manual", LEASE), topic("/e4/imu_manual", "manual", LEASE, IMU_HZ, None)],
         [("camera_auto", "/e4/camera_auto", "automatic", LEASE, True),
          ("imu_auto", "/e4/imu_auto", "automatic", LEASE, False),
          ("camera_manual", "/e4/camera_manual", "manual", LEASE, True),
          ("imu_manual", "/e4/imu_manual", "manual", LEASE, False)], "stop_publishing"),
        ("E5_compatibility",
         [topic("/e5/manual05", "manual", LEASE, stop_after=None),
          topic("/e5/default", None, None, stop_after=None),
          topic("/e5/auto05", "automatic", LEASE, stop_after=None, expect_match=False)],
         [("sub_auto_0.3_on_manual_0.5", "/e5/manual05", "automatic", 0.3, False),
          ("sub_auto_1.0_on_manual_0.5", "/e5/manual05", "automatic", 1.0, False),
          ("sub_auto_0.5_on_default", "/e5/default", "automatic", 0.5, False),
          ("sub_default_on_default", "/e5/default", None, None, False),
          ("sub_manual_inf_on_auto_0.5", "/e5/auto05", "manual", None, False)], "continuous"),
        ("E6_lease_near_period",
         [topic("/e6/lease_50ms", "manual", 0.05, stop_after=None),
          topic("/e6/lease_100ms", "manual", 0.1, stop_after=None),
          topic("/e6/lease_200ms", "manual", 0.2, stop_after=None)],
         [("manual_lease_0.05", "/e6/lease_50ms", "manual", 0.05, False),
          ("manual_lease_0.1", "/e6/lease_100ms", "manual", 0.1, False),
          ("manual_lease_0.2", "/e6/lease_200ms", "manual", 0.2, False)], "continuous"),
    ]
    results = []
    for case, topics, subs, mode in cases:
        res = run_case(node, executor, case, topics, subs, mode)
        if case == "E5_compatibility":
            res["qos_check_compatible"] = compat_rows()
        emit(res)
        results.append(res)

    def probe(case, label):
        res = next(r for r in results if r["case"] == case)
        return next((p for p in res.get("probes", []) if p["probe"] == label), {})

    valid = all(probe(c, l).get("msgs_before_stop", 0) > 0 for c, l in [
        ("E1_auto_stop_publishing", "camera_auto"), ("E2_auto_sigstop", "camera_auto"),
        ("E3_manual_stop_publishing", "camera_manual"), ("E4_imu_keeps_publishing", "camera_auto"),
        ("E4_imu_keeps_publishing", "camera_manual")])
    emit({"ev": "summary", "valid": valid,
          "E1_auto_stop_detected": probe("E1_auto_stop_publishing", "camera_auto").get("not_alive_after_stop"),
          "E2_sigstop_detected": probe("E2_auto_sigstop", "camera_auto").get("not_alive_after_stop"),
          "E2_detect_ms_from_stop": probe("E2_auto_sigstop", "camera_auto").get("detect_ms_from_stop"),
          "E3_manual_stop_detected": probe("E3_manual_stop_publishing", "camera_manual").get("not_alive_after_stop"),
          "E3_detect_ms_from_last_rx": probe("E3_manual_stop_publishing", "camera_manual").get("detect_ms_from_last_rx"),
          "E1_watchdog_ms_from_last_rx": probe("E1_auto_stop_publishing", "camera_auto").get("watchdog_ms_from_last_rx"),
          "E4_camera_auto_detected": probe("E4_imu_keeps_publishing", "camera_auto").get("not_alive_after_stop"),
          "E4_camera_manual_detected": probe("E4_imu_keeps_publishing", "camera_manual").get("not_alive_after_stop"),
          "elapsed_s": round(time.monotonic() - wall0, 2)})
    executor.remove_node(node)
    node.destroy_node()
    rclpy.shutdown()
    return 0 if valid else 2


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--pub":
        run_publisher(json.loads(sys.argv[2]))
    else:
        sys.exit(main())
