#!/usr/bin/env python3
"""ROS 2 Jazzy: does liveliness tell us a camera topic stopped, or only deadline does?

One monitor process subscribes to topics published by separate driver processes.
Each driver node publishes /<case>/camera at 20 Hz and /<case>/diagnostics at 1 Hz.
After a warm-up, the monitor stops part of each driver and records, with the shared
CLOCK_MONOTONIC, when Requested deadline missed / Liveliness changed / incompatible QoS
events and a last-receive watchdog fire. Every number printed is measured at runtime.

Cases
  A  camera only stops, diagnostics continue      (camera AUTOMATIC, lease 2000 ms, deadline 100 ms)
  B  every publisher stops, process + node alive   (same QoS as A)
  C  camera MANUAL_BY_TOPIC stops, diagnostics continue
  D  driver node destroyed, process alive          (same QoS as A)
  K  driver process SIGKILLed                      (same QoS as A)
  W  driver with default QoS camera; monitor uses a last-receive watchdog timer
  E  QoS compatibility: subscriptions that request stricter deadline/lease/kind
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time

CAMERA_PERIOD_S = 0.05      # 20 Hz
DIAG_PERIOD_S = 1.0         # 1 Hz
DEADLINE_MS = 100
LEASE_MS = 2000
E_OFFERED_LEASE_MS = 200
E_REQUESTED_LEASE_MS = (150, 300, 200)
WATCHDOG_THRESHOLD_MS = 100
WATCHDOG_CHECK_MS = 10
OBSERVE_S = 8.0             # 4 x lease after the stop command
WARMUP_TIMEOUT_S = 25.0
CASES = ("a", "b", "c", "d", "k", "w")


def ms(seconds):
    return None if seconds is None else round(seconds * 1000.0, 1)


def duration(milliseconds):
    from rclpy.duration import Duration
    return Duration(nanoseconds=int(milliseconds * 1_000_000))


def camera_qos(case):
    from rclpy.qos import LivelinessPolicy, QoSProfile
    if case == "w":
        return QoSProfile(depth=10)  # driver that only lets you pick a default profile
    kind = LivelinessPolicy.MANUAL_BY_TOPIC if case == "c" else LivelinessPolicy.AUTOMATIC
    return QoSProfile(depth=10, deadline=duration(DEADLINE_MS), liveliness=kind,
                      liveliness_lease_duration=duration(LEASE_MS))


def diag_qos():
    from rclpy.qos import LivelinessPolicy, QoSProfile
    return QoSProfile(depth=10, liveliness=LivelinessPolicy.AUTOMATIC,
                      liveliness_lease_duration=duration(LEASE_MS))


# --------------------------------------------------------------------------- driver
def driver(case):
    import rclpy
    from rclpy.event_handler import PublisherEventCallbacks
    from rclpy.node import Node
    from rclpy.qos import LivelinessPolicy, QoSProfile
    from std_msgs.msg import Float64

    rclpy.init()
    node = Node(f"driver_{case}")
    events, last_pub, pub_count, applied = [], {}, {}, {}
    commands, lock = [], threading.Lock()

    def pub_event(topic, kind):
        def callback(info):
            events.append({"topic": topic, "kind": kind, "t": time.monotonic(),
                           "total_count": info.total_count, "total_count_change": info.total_count_change})
        return callback

    def make_pub(topic, qos):
        callbacks = PublisherEventCallbacks(deadline=pub_event(topic, "offered_deadline_missed"),
                                            liveliness=pub_event(topic, "liveliness_lost"))
        publisher = node.create_publisher(Float64, topic, qos, event_callbacks=callbacks)

        def tick():
            msg = Float64()
            msg.data = time.monotonic()  # publish time on the shared monotonic clock
            publisher.publish(msg)
            last_pub[topic] = msg.data
            pub_count[topic] = pub_count.get(topic, 0) + 1
        return tick

    camera, diag = f"/{case}/camera", f"/{case}/diagnostics"
    timers = {camera: node.create_timer(CAMERA_PERIOD_S, make_pub(camera, camera_qos(case))),
              diag: node.create_timer(DIAG_PERIOD_S, make_pub(diag, diag_qos()))}
    if case == "w":
        lease_qos = QoSProfile(depth=10, liveliness=LivelinessPolicy.AUTOMATIC,
                               liveliness_lease_duration=duration(E_OFFERED_LEASE_MS))
        timers["/e/lease200"] = node.create_timer(CAMERA_PERIOD_S, make_pub("/e/lease200", lease_qos))

    def read_stdin():
        for line in sys.stdin:
            with lock:
                commands.append(line.strip())
    threading.Thread(target=read_stdin, daemon=True).start()

    alive, running = True, True
    while running:
        with lock:
            pending, commands[:] = list(commands), []
        for command in pending:
            if command == "stop_camera":
                timers[camera].cancel()
            elif command == "stop_all":
                for timer in timers.values():
                    timer.cancel()
            elif command == "destroy":
                node.destroy_node()   # publishers go away, the context/participant stays
                alive = False
            elif command == "exit":
                running = False
            applied[command] = time.monotonic()
        if alive:
            rclpy.spin_once(node, timeout_sec=0.005)
        else:
            time.sleep(0.005)
    print(json.dumps({"case": case, "last_pub": last_pub, "pub_count": pub_count,
                      "applied": applied, "events": events}), flush=True)
    if alive:
        node.destroy_node()
    rclpy.shutdown()


# --------------------------------------------------------------------------- monitor
def policy_name(kind):
    from rclpy.qos import QoSPolicyKind
    try:
        return QoSPolicyKind(int(kind)).name
    except Exception:
        return str(kind)


def monitor():
    import rclpy
    from rclpy.event_handler import SubscriptionEventCallbacks
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import LivelinessPolicy, QoSProfile
    from std_msgs.msg import Float64

    here = os.path.abspath(__file__)
    procs = {}
    for case in CASES:
        err = open(f"/tmp/driver_{case}.err", "w")
        procs[case] = subprocess.Popen([sys.executable, here, "driver", case], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=err, text=True)

    rclpy.init()
    node = Node("sensor_monitor")
    subs = {}

    def add_sub(key, topic, qos):
        record = {"topic": topic, "rx": [], "deadline": [], "liveliness": [], "incompatible": []}

        def on_msg(msg):
            record["rx"].append((time.monotonic(), msg.data))

        def on_deadline(info):
            record["deadline"].append({"t": time.monotonic(), "total_count": info.total_count,
                                       "total_count_change": info.total_count_change})

        def on_liveliness(info):
            record["liveliness"].append({"t": time.monotonic(), "alive_count": info.alive_count,
                                         "not_alive_count": info.not_alive_count,
                                         "alive_count_change": info.alive_count_change,
                                         "not_alive_count_change": info.not_alive_count_change})

        def on_incompatible(info):
            record["incompatible"].append({"t": time.monotonic(), "total_count": info.total_count,
                                           "policy": policy_name(info.last_policy_kind)})
        callbacks = SubscriptionEventCallbacks(deadline=on_deadline, liveliness=on_liveliness,
                                               incompatible_qos=on_incompatible)
        node.create_subscription(Float64, topic, on_msg, qos, event_callbacks=callbacks)
        subs[key] = record

    for case in ("a", "b", "c", "d", "k"):
        req = camera_qos(case)
        add_sub(f"{case}_camera", f"/{case}/camera", req)
        add_sub(f"{case}_diag", f"/{case}/diagnostics", diag_qos())
    add_sub("w_camera", "/w/camera", QoSProfile(depth=10))
    # E: what a monitor that "just adds deadline/lease" requests from a default-QoS publisher
    add_sub("e_deadline100_vs_default", "/w/camera", QoSProfile(depth=10, deadline=duration(DEADLINE_MS)))
    add_sub("e_lease150_vs_default", "/w/camera",
            QoSProfile(depth=10, liveliness=LivelinessPolicy.AUTOMATIC, liveliness_lease_duration=duration(150)))
    add_sub("e_manual_by_topic_vs_default", "/w/camera",
            QoSProfile(depth=10, liveliness=LivelinessPolicy.MANUAL_BY_TOPIC))
    for requested in E_REQUESTED_LEASE_MS:
        add_sub(f"e_lease{requested}_vs_offered{E_OFFERED_LEASE_MS}", "/e/lease200",
                QoSProfile(depth=10, liveliness=LivelinessPolicy.AUTOMATIC,
                           liveliness_lease_duration=duration(requested)))

    watchdog = {"stale": False, "fires": []}

    def check_watchdog():
        rx = subs["w_camera"]["rx"]
        if not rx:
            return
        now = time.monotonic()
        stale = now - rx[-1][0] > WATCHDOG_THRESHOLD_MS / 1000.0
        if stale and not watchdog["stale"]:
            watchdog["fires"].append({"t": now, "last_rx": rx[-1][0], "last_pub": rx[-1][1]})
        watchdog["stale"] = stale
    node.create_timer(WATCHDOG_CHECK_MS / 1000.0, check_watchdog)

    executor = SingleThreadedExecutor()
    executor.add_node(node)
    started = time.monotonic()

    def alive(key):
        live = subs[key]["liveliness"]
        return bool(live) and live[-1]["alive_count"] >= 1

    def baseline_ok():
        for case in ("a", "b", "c", "d", "k"):
            if len(subs[f"{case}_camera"]["rx"]) < 20 or len(subs[f"{case}_diag"]["rx"]) < 2:
                return False
            if not (alive(f"{case}_camera") and alive(f"{case}_diag")):
                return False
        return len(subs["w_camera"]["rx"]) >= 20

    while not baseline_ok() and time.monotonic() - started < WARMUP_TIMEOUT_S:
        executor.spin_once(timeout_sec=0.005)
    if not baseline_ok():
        status = {k: {"rx": len(v["rx"]), "liveliness": v["liveliness"][-1:] or None} for k, v in subs.items()}
        print(json.dumps({"error": "baseline_not_reached", "warmup_s": round(time.monotonic() - started, 2),
                          "status": status}), flush=True)
        for proc in procs.values():
            proc.kill()
        for case in CASES:
            sys.stderr.write(f"--- driver_{case}\n" + open(f"/tmp/driver_{case}.err").read()[-800:])
        return 1
    warmup_s = time.monotonic() - started

    baseline_rx = {k: len(v["rx"]) for k, v in subs.items()}
    sent = {}
    plan = {"a": "stop_camera", "b": "stop_all", "c": "stop_camera", "d": "destroy", "w": "stop_camera"}
    for case, command in plan.items():
        procs[case].stdin.write(command + "\n")
        procs[case].stdin.flush()
        sent[case] = time.monotonic()
    procs["k"].send_signal(signal.SIGKILL)
    sent["k"] = time.monotonic()
    t_stop = min(sent.values())
    t_end = t_stop + OBSERVE_S
    while time.monotonic() < t_end:
        executor.spin_once(timeout_sec=0.002)
    t_end = time.monotonic()
    graph_publishers = {topic: node.count_publishers(topic)
                        for topic in ("/a/camera", "/b/camera", "/d/camera", "/k/camera")}

    summaries = {}
    for case, proc in procs.items():
        if case == "k":
            proc.wait(timeout=5)
            continue
        try:
            out, _ = proc.communicate("exit\n", timeout=15)
            lines = [line for line in out.splitlines() if line.startswith("{")]
            summaries[case] = json.loads(lines[-1]) if lines else None
        except Exception as exc:  # report, do not hide
            proc.kill()
            summaries[case] = {"error": repr(exc)}
    executor.shutdown()
    node.destroy_node()
    rclpy.shutdown()

    # ------------------------------------------------------------------ analysis
    def last_rx(key):
        return subs[key]["rx"][-1] if subs[key]["rx"] else (None, None)

    def after(items, t0):
        return [e for e in items if e["t"] > t0]

    def rel(t, t0):
        return None if t is None or t0 is None else ms(t - t0)

    def liveliness_drops(key, t0):
        return [e for e in after(subs[key]["liveliness"], t0)
                if e["alive_count_change"] < 0 or e["not_alive_count_change"] > 0]

    def drop_view(e, *refs):
        if e is None:
            return None
        view = {k: e[k] for k in ("alive_count", "not_alive_count", "alive_count_change", "not_alive_count_change")}
        for name, ref in refs:
            view[name] = rel(e["t"], ref)
        return view

    def deadline_view(key, t_last_rx, t_last_pub):
        misses = after(subs[key]["deadline"], t_last_rx)
        return {"first_miss_after_last_rx_ms": rel(misses[0]["t"], t_last_rx) if misses else None,
                "first_miss_after_last_pub_ms": rel(misses[0]["t"], t_last_pub) if misses else None,
                "callbacks": len(misses),
                # total_count is cumulative since matching (it may include misses before the first sample);
                # the increase after the last receive is the sum of total_count_change
                "missed_after_last_rx": sum(m["total_count_change"] for m in misses),
                "cumulative_total_count_at_window_end": misses[-1]["total_count"] if misses else 0,
                "window_after_last_rx_ms": rel(t_end, t_last_rx)}

    def driver_events(case, kind, t0):
        summary = summaries.get(case) or {}
        return [e for e in summary.get("events", []) if e["kind"] == kind and e["t"] > t0]

    out_lines = []
    for case, label in (("a", "A_camera_only_stop_automatic"), ("b", "B_all_publishers_stop_process_alive"),
                        ("c", "C_camera_manual_by_topic_stop")):
        summary = summaries.get(case) or {}
        cam_key, diag_key = f"{case}_camera", f"{case}_diag"
        t_rx, t_pub_seen = last_rx(cam_key)
        t_pub = summary.get("last_pub", {}).get(f"/{case}/camera", t_pub_seen)
        t_diag_pub = summary.get("last_pub", {}).get(f"/{case}/diagnostics")
        # B stops every publisher, so its reference is the last publish on any topic of the node
        t_all_pub = max(t for t in (t_pub, t_diag_pub) if t is not None) if case == "b" else t_pub
        cam_drops, diag_drops = liveliness_drops(cam_key, t_pub), liveliness_drops(diag_key, sent[case])
        lost = driver_events(case, "liveliness_lost", t_pub)
        line = {"case": label,
                "baseline_camera_rx": baseline_rx[cam_key], "baseline_diag_rx": baseline_rx[diag_key],
                "camera_rx_after_stop_cmd": sum(1 for t, _ in subs[cam_key]["rx"] if t > sent[case]),
                "diag_rx_after_stop_cmd": sum(1 for t, _ in subs[diag_key]["rx"] if t > sent[case]),
                "last_camera_pub_relative_to_stop_cmd_ms": rel(t_pub, sent[case]),
                "camera_deadline": deadline_view(cam_key, t_rx, t_pub),
                "camera_liveliness_drop_events": len(cam_drops),
                "camera_first_drop": drop_view(cam_drops[0] if cam_drops else None,
                                               ("after_last_camera_pub_ms", t_pub)),
                "diag_liveliness_drop_events": len(diag_drops),
                "diag_first_drop": drop_view(diag_drops[0] if diag_drops else None,
                                             ("after_last_diag_pub_ms", t_diag_pub)),
                "observed_after_last_camera_pub_ms": rel(t_end, t_pub),
                "observed_after_last_pub_of_every_stopped_topic_ms": rel(t_end, t_all_pub),
                "driver_camera_liveliness_lost": [{"after_last_camera_pub_ms": rel(e["t"], t_pub),
                                                   "total_count": e["total_count"]}
                                                  for e in lost if e["topic"] == f"/{case}/camera"][:3],
                "driver_liveliness_lost_events_any_topic": len(driver_events(case, "liveliness_lost", t_pub)),
                "driver_camera_offered_deadline_missed_events": sum(
                    1 for e in driver_events(case, "offered_deadline_missed", t_pub) if e["topic"] == f"/{case}/camera")}
        out_lines.append(line)

    for case, label, t_ref_name in (("d", "D_node_destroyed_process_alive", "destroy"),
                                    ("k", "K_process_sigkill", "sigkill")):
        cam_key, diag_key = f"{case}_camera", f"{case}_diag"
        t_rx, t_pub = last_rx(cam_key)
        summary = summaries.get(case) or {}
        t_cmd = sent[case]  # monitor-side send time; D's destroy_node() may finish after the event arrives
        cam_events = after(subs[cam_key]["liveliness"], t_pub)
        diag_events = after(subs[diag_key]["liveliness"], t_pub)
        line = {"case": label,
                "baseline_camera_rx": baseline_rx[cam_key],
                f"last_camera_rx_relative_to_{t_ref_name}_cmd_ms": rel(t_rx, t_cmd),
                "camera_liveliness_events": [drop_view(e, (f"after_{t_ref_name}_cmd_ms", t_cmd),
                                                       ("after_last_camera_pub_ms", t_pub)) for e in cam_events][:4],
                "diag_liveliness_events": [drop_view(e, (f"after_{t_ref_name}_cmd_ms", t_cmd)) for e in diag_events][:4],
                "camera_deadline": deadline_view(cam_key, t_rx, t_pub),
                "graph_publishers_on_camera_at_window_end": graph_publishers[f"/{case}/camera"],
                "observed_after_cmd_ms": rel(t_end, t_cmd)}
        if case == "d":
            line["destroy_node_returned_after_cmd_ms"] = rel(summary.get("applied", {}).get("destroy"), t_cmd)
        out_lines.append(line)

    t_rx, t_pub = last_rx("w_camera")
    fires = [f for f in watchdog["fires"] if f["t"] > sent["w"] - 1.0 and f["last_rx"] >= t_rx - 1e-9]
    out_lines.append({"case": "W_watchdog_default_qos",
                      "threshold_ms": WATCHDOG_THRESHOLD_MS, "check_period_ms": WATCHDOG_CHECK_MS,
                      "baseline_rx": baseline_rx["w_camera"],
                      "fired": bool(fires),
                      "fire_after_last_rx_ms": rel(fires[0]["t"], t_rx) if fires else None,
                      "fire_after_last_pub_ms": rel(fires[0]["t"], t_pub) if fires else None,
                      "fires_during_warmup_and_run": len(watchdog["fires"]),
                      "fires_before_stop_gap_ms": [rel(f["t"], f["last_rx"]) for f in watchdog["fires"]
                                                   if f["t"] < sent["w"]]})

    for key in [k for k in subs if k.startswith("e_")]:
        record = subs[key]
        out_lines.append({"case": "E_compatibility", "subscription": key, "topic": record["topic"],
                          "messages_received": len(record["rx"]),
                          "requested_incompatible_events": len(record["incompatible"]),
                          "incompatible_total_count": record["incompatible"][-1]["total_count"]
                          if record["incompatible"] else 0,
                          "last_policy": record["incompatible"][-1]["policy"] if record["incompatible"] else None})

    try:
        from rclpy.utilities import get_rmw_implementation_identifier
        rmw = get_rmw_implementation_identifier()
    except Exception:
        rmw = os.environ.get("RMW_IMPLEMENTATION", "default")
    out_lines.append({"case": "run_info", "rmw": rmw, "warmup_s": round(warmup_s, 2),
                      "observe_s": round(t_end - t_stop, 2), "stop_command_spread_ms": rel(max(sent.values()), t_stop),
                      "driver_summaries_ok": sorted(c for c, s in summaries.items() if s and "events" in s)})
    for line in out_lines:
        print(json.dumps(line, ensure_ascii=False), flush=True)
    return 0 if len(out_lines) and all(summaries.get(c) and "events" in summaries[c] for c in plan) else 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "driver":
        driver(sys.argv[2])
    else:
        sys.exit(monitor())
