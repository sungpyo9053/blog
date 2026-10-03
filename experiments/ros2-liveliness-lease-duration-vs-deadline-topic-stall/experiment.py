#!/usr/bin/env python3
"""Does liveliness tell a monitor that one sensor topic stopped? (ROS 2 Jazzy, rclpy)

The monitor (this process) and the "driver" (a child process = separate DDS participant)
talk over std_msgs/UInt32. The driver publishes camera at 20 Hz and diagnostics at 1 Hz.
Every number printed below is measured with time.monotonic() during the run
(CLOCK_MONOTONIC is shared by both processes on Linux).

Cases
  A  camera stops, diagnostics keeps going (Automatic, lease 2000 ms, deadline 100 ms)
  B  every publisher stops, process and node stay alive (Automatic, lease 2000 ms)
  C  camera stops with MANUAL_BY_TOPIC (lease 2000 ms), diagnostics keeps going
  D  driver node is destroyed, process stays alive (Automatic, lease 2000 ms)
  K  driver process is SIGKILLed (Automatic, lease 2000 ms)
  E  QoS compatibility: monitor asks for deadline/lease the driver does not offer,
     plus a subscriber-side watchdog timer on a default-QoS subscription
"""
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

import rclpy
from rclpy.duration import Duration
from rclpy.event_handler import PublisherEventCallbacks, SubscriptionEventCallbacks
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSLivelinessPolicy, QoSProfile
from std_msgs.msg import UInt32

AUTO = QoSLivelinessPolicy.AUTOMATIC
MANUAL = QoSLivelinessPolicy.MANUAL_BY_TOPIC
CAMERA_PERIOD = 1.0 / 20   # 20 Hz
DIAG_PERIOD = 1.0          # 1 Hz
LEASE_MS = 2000
DEADLINE_MS = 100
WATCHDOG_MS = 100


def ms(x):
    return Duration(nanoseconds=int(x * 1_000_000))


def qos(liveliness=None, lease_ms=None, deadline_ms=None):
    kwargs = {"depth": 10}
    if liveliness is not None:
        kwargs["liveliness"] = liveliness
    if lease_ms is not None:
        kwargs["liveliness_lease_duration"] = ms(lease_ms)
    if deadline_ms is not None:
        kwargs["deadline"] = ms(deadline_ms)
    return QoSProfile(**kwargs)


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def r(x):
    return None if x is None else round(x, 1)


# ---------------------------------------------------------------- driver (child process)
# name -> list of (pub_name, topic_suffix, qos, period)
DRIVER_CONFIGS = {
    "A": [("camera", "camera", lambda: qos(AUTO, LEASE_MS, DEADLINE_MS), CAMERA_PERIOD),
          ("diag", "diagnostics", lambda: qos(AUTO, LEASE_MS), DIAG_PERIOD)],
    "C": [("camera", "camera", lambda: qos(MANUAL, LEASE_MS), CAMERA_PERIOD),
          ("diag", "diagnostics", lambda: qos(AUTO, LEASE_MS), DIAG_PERIOD)],
    "D": [("camera", "camera", lambda: qos(AUTO, LEASE_MS), CAMERA_PERIOD),
          ("diag", "diagnostics", lambda: qos(AUTO, LEASE_MS), DIAG_PERIOD)],
    "E": [("default", "cam_default", lambda: qos(), CAMERA_PERIOD),
          ("lease200", "cam_lease200", lambda: qos(AUTO, 200), CAMERA_PERIOD)],
}


def run_driver(config, prefix):
    rclpy.init()
    node = Node("driver")
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    state = {}

    for name, suffix, make_qos, period in DRIVER_CONFIGS[config]:
        s = {"seq": 0, "last_pub_t": None, "timer": None}

        def on_lost(info, name=name):
            emit({"drv": "liveliness_lost", "pub": name, "t": time.monotonic(),
                  "total_count": info.total_count})

        def on_offered_deadline(info, name=name):
            emit({"drv": "offered_deadline_missed", "pub": name, "t": time.monotonic(),
                  "total_count": info.total_count})

        pub = node.create_publisher(UInt32, f"/{prefix}/{suffix}", make_qos(),
                                    event_callbacks=PublisherEventCallbacks(
                                        liveliness=on_lost, deadline=on_offered_deadline))

        def tick(s=s, pub=pub):
            msg = UInt32()
            msg.data = s["seq"]
            pub.publish(msg)
            s["seq"] += 1
            s["last_pub_t"] = time.monotonic()

        s["timer"] = node.create_timer(period, tick)
        state[name] = s

    commands = queue.Queue()
    threading.Thread(target=lambda: [commands.put(line.strip()) for line in sys.stdin],
                     daemon=True).start()
    emit({"drv": "ready", "t": time.monotonic(), "pid": os.getpid()})
    destroyed = False
    while True:
        executor.spin_once(timeout_sec=0.005)
        try:
            cmd = commands.get_nowait()
        except queue.Empty:
            continue
        if cmd == "exit":
            break
        if cmd.startswith("stop "):
            names = list(state) if cmd == "stop all" else [cmd.split()[1]]
            for name in names:
                state[name]["timer"].cancel()
                emit({"drv": "stopped", "pub": name, "t": time.monotonic(),
                      "last_pub_t": state[name]["last_pub_t"], "published": state[name]["seq"]})
        elif cmd == "destroy" and not destroyed:
            last = state["camera"]["last_pub_t"]
            t_begin = time.monotonic()
            executor.remove_node(node)
            node.destroy_node()
            destroyed = True
            emit({"drv": "destroyed", "t_begin": t_begin, "t": time.monotonic(), "last_pub_t": last})
    if not destroyed:
        node.destroy_node()
    rclpy.shutdown()


# ---------------------------------------------------------------- monitor (this process)
class Driver:
    def __init__(self, config, prefix):
        self.proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "driver", config, prefix],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.events = []
        self.lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            with self.lock:
                self.events.append(ev)

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def find(self, kind, pub=None):
        with self.lock:
            return [e for e in self.events if e.get("drv") == kind and (pub is None or e.get("pub") == pub)]

    def close(self):
        if self.proc.poll() is None:
            try:
                self.send("exit")
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
                self.proc.wait()


class Watch:
    """One subscription with every QoS event callback recorded at arrival time."""

    def __init__(self, node, topic, profile, watchdog_ms=None):
        self.count = 0
        self.last_recv_t = None
        self.deadline = []
        self.liveliness = []
        self.incompatible = []
        self.watchdog_t = None
        callbacks = SubscriptionEventCallbacks(deadline=self._deadline, liveliness=self._live,
                                               incompatible_qos=self._incompat)
        node.create_subscription(UInt32, topic, self._msg, profile, event_callbacks=callbacks)
        if watchdog_ms is not None:
            limit = watchdog_ms / 1000.0

            def check():
                now = time.monotonic()
                if self.watchdog_t is None and self.last_recv_t is not None and now - self.last_recv_t > limit:
                    self.watchdog_t = now
            node.create_timer(0.01, check)

    def _msg(self, _msg):
        self.count += 1
        self.last_recv_t = time.monotonic()
        self.watchdog_t = None  # re-arm while data flows

    def _deadline(self, info):
        self.deadline.append({"t": time.monotonic(), "total_count": info.total_count,
                              "total_count_change": info.total_count_change})

    def _live(self, info):
        self.liveliness.append({"t": time.monotonic(), "alive_count": info.alive_count,
                                "not_alive_count": info.not_alive_count,
                                "alive_count_change": info.alive_count_change,
                                "not_alive_count_change": info.not_alive_count_change})

    def _incompat(self, info):
        try:
            from rclpy.qos import qos_policy_name_from_kind
            kind = qos_policy_name_from_kind(info.last_policy_kind)
        except Exception:
            kind = str(info.last_policy_kind)
        self.incompatible.append({"t": time.monotonic(), "total_count": info.total_count, "policy": kind})

    def live_after(self, t0):
        return [{"after_stop_ms": r((e["t"] - t0) * 1000), **{k: v for k, v in e.items() if k != "t"}}
                for e in self.liveliness if e["t"] >= t0]


class Case:
    def __init__(self, executor, name):
        self.executor = executor
        self.node = Node(f"monitor_{name.lower()}")
        executor.add_node(self.node)

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.executor.spin_once(timeout_sec=0.005)

    def spin_until(self, pred, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if pred():
                return True
            self.executor.spin_once(timeout_sec=0.005)
        return pred()

    def close(self):
        self.executor.remove_node(self.node)
        self.node.destroy_node()


def alive(*watches):
    return all(w.liveliness and w.liveliness[-1]["alive_count"] >= 1 for w in watches)


def alive_at_end(w):
    return w.liveliness[-1]["alive_count"] if w.liveliness else None


def stop_and_wait(case, driver, cmd, pub):
    driver.send(cmd)
    case.spin_until(lambda: driver.find("stopped", pub), 3)
    found = driver.find("stopped", pub)
    return found[0] if found else None


def case_a(executor):
    case, drv = Case(executor, "A"), Driver("A", "a")
    cam = Watch(case.node, "/a/camera", qos(AUTO, LEASE_MS, DEADLINE_MS))
    diag = Watch(case.node, "/a/diagnostics", qos(AUTO, LEASE_MS))
    ok = case.spin_until(lambda: cam.count >= 20 and diag.count >= 1 and alive(cam, diag), 15)
    case.spin_for(0.3)
    deadline_before = len(cam.deadline)
    stopped = stop_and_wait(case, drv, "stop camera", "camera")
    t_cmd = time.monotonic()
    diag_before = diag.count
    case.spin_for(4.5)
    drv.close()
    case.close()
    t0 = stopped["last_pub_t"] if stopped else t_cmd
    after = [e for e in cam.deadline if e["t"] >= t0]
    first = after[0]["t"] if after else None
    return {"case": "A_camera_stops_diag_continues",
            "setup_ok": ok, "observe_s": 4.5,
            "camera_msgs_before_stop": cam.count,
            "deadline_callbacks_before_stop": deadline_before,
            "last_pub_to_last_recv_ms": r((cam.last_recv_t - t0) * 1000) if cam.last_recv_t else None,
            "last_recv_to_first_deadline_missed_ms": r((first - cam.last_recv_t) * 1000) if first else None,
            "deadline_callbacks_after_stop": len(after),
            "deadline_total_count_at_end": cam.deadline[-1]["total_count"] if cam.deadline else 0,
            "diag_msgs_during_observe": diag.count - diag_before,
            "camera_liveliness_events_after_stop": cam.live_after(t0),
            "camera_liveliness_events_total": len(cam.liveliness),
            "camera_alive_count_at_end": alive_at_end(cam),
            "driver_liveliness_lost": len(drv.find("liveliness_lost")),
            "driver_offered_deadline_missed_events": len(drv.find("offered_deadline_missed", "camera"))}


def case_b(executor):
    case, drv = Case(executor, "B"), Driver("A", "b")
    cam = Watch(case.node, "/b/camera", qos(AUTO, LEASE_MS, DEADLINE_MS))
    diag = Watch(case.node, "/b/diagnostics", qos(AUTO, LEASE_MS))
    ok = case.spin_until(lambda: cam.count >= 20 and diag.count >= 1 and alive(cam, diag), 15)
    case.spin_for(0.3)
    stopped = stop_and_wait(case, drv, "stop all", "diag")
    t0 = time.monotonic()
    case.spin_for(6.5)
    publishers_at_end = case.node.count_publishers("/b/camera")
    drv.close()
    case.close()
    last_pub = max(e["last_pub_t"] for e in drv.find("stopped") if e["last_pub_t"]) if stopped else t0
    return {"case": "B_all_publishing_stops_process_alive",
            "setup_ok": ok, "observe_s": 6.5,
            "observe_vs_lease_ratio": round(6.5 * 1000 / LEASE_MS, 2),
            "msgs_after_stop": sum(1 for w in (cam, diag) if w.last_recv_t and w.last_recv_t > t0),
            "camera_liveliness_events_after_stop": cam.live_after(last_pub),
            "diag_liveliness_events_after_stop": diag.live_after(last_pub),
            "camera_alive_count_at_end": alive_at_end(cam),
            "diag_alive_count_at_end": alive_at_end(diag),
            "camera_publishers_seen_at_end": publishers_at_end,
            "camera_deadline_callbacks_after_stop": len([e for e in cam.deadline if e["t"] >= last_pub]),
            "driver_liveliness_lost": len(drv.find("liveliness_lost"))}


def case_c(executor):
    case, drv = Case(executor, "C"), Driver("C", "c")
    cam = Watch(case.node, "/c/camera", qos(MANUAL, LEASE_MS))
    diag = Watch(case.node, "/c/diagnostics", qos(AUTO, LEASE_MS))
    ok = case.spin_until(lambda: cam.count >= 20 and diag.count >= 1 and alive(cam, diag), 15)
    case.spin_for(0.3)
    alive_before = cam.liveliness[-1]["alive_count"] if cam.liveliness else None
    stopped = stop_and_wait(case, drv, "stop camera", "camera")
    diag_before = diag.count
    case.spin_for(4.0)
    t0 = stopped["last_pub_t"] if stopped else time.monotonic()
    lost = drv.find("liveliness_lost", "camera")
    events = cam.live_after(t0)
    first_not_alive = next((e for e in events if e["not_alive_count_change"] > 0), None)
    drv.close()
    case.close()
    return {"case": "C_manual_by_topic_camera_stops",
            "setup_ok": ok, "observe_s": 4.0,
            "camera_alive_count_before_stop": alive_before,
            "camera_liveliness_events_after_stop": events,
            "last_pub_to_first_not_alive_ms": first_not_alive["after_stop_ms"] if first_not_alive else None,
            "not_alive_minus_lease_ms": r(first_not_alive["after_stop_ms"] - LEASE_MS) if first_not_alive else None,
            "last_pub_to_driver_liveliness_lost_ms": r((lost[0]["t"] - t0) * 1000) if lost else None,
            "diag_msgs_during_observe": diag.count - diag_before,
            "diag_liveliness_events_after_stop": diag.live_after(t0)}


def case_d(executor):
    case, drv = Case(executor, "D"), Driver("D", "d")
    cam = Watch(case.node, "/d/camera", qos(AUTO, LEASE_MS))
    ok = case.spin_until(lambda: cam.count >= 20 and alive(cam), 15)
    case.spin_for(0.3)
    publishers_before = case.node.count_publishers("/d/camera")
    drv.send("destroy")
    case.spin_until(lambda: drv.find("destroyed"), 3)
    ev = drv.find("destroyed")
    t0 = ev[0]["t_begin"] if ev else time.monotonic()
    count_at_destroy = cam.count
    case.spin_for(4.0)
    publishers_after = case.node.count_publishers("/d/camera")
    drv.close()
    case.close()
    return {"case": "D_driver_node_destroyed_process_alive",
            "setup_ok": ok, "observe_s": 4.0,
            "camera_publishers_seen_before": publishers_before,
            "camera_publishers_seen_after": publishers_after,
            "camera_msgs_after_destroy": cam.count - count_at_destroy,
            "destroy_node_call_ms": r((ev[0]["t"] - ev[0]["t_begin"]) * 1000) if ev else None,
            "camera_liveliness_events_after_destroy": cam.live_after(t0),
            "camera_alive_count_at_end": alive_at_end(cam)}


def case_k(executor):
    case, drv = Case(executor, "K"), Driver("D", "k")
    cam = Watch(case.node, "/k/camera", qos(AUTO, LEASE_MS))
    ok = case.spin_until(lambda: cam.count >= 20 and alive(cam), 15)
    case.spin_for(0.3)
    t0 = time.monotonic()
    os.kill(drv.proc.pid, signal.SIGKILL)
    drv.proc.wait()
    case.spin_for(5.0)
    publishers_after = case.node.count_publishers("/k/camera")
    case.close()
    events = cam.live_after(t0)
    first_not_alive = next((e for e in events if e["not_alive_count_change"] > 0), None)
    first_alive_drop = next((e for e in events if e["alive_count_change"] < 0), None)
    return {"case": "K_driver_process_sigkill",
            "setup_ok": ok, "observe_s": 5.0,
            "last_recv_before_kill_ms": r((t0 - cam.last_recv_t) * 1000) if cam.last_recv_t else None,
            "camera_liveliness_events_after_kill": events,
            "kill_to_first_alive_drop_ms": first_alive_drop["after_stop_ms"] if first_alive_drop else None,
            "kill_to_first_not_alive_ms": first_not_alive["after_stop_ms"] if first_not_alive else None,
            "camera_publishers_seen_after": publishers_after}


def case_e(executor):
    case, drv = Case(executor, "E"), Driver("E", "e")
    subs = {
        "pub_default__sub_deadline100": Watch(case.node, "/e/cam_default", qos(deadline_ms=100)),
        "pub_default__sub_lease150": Watch(case.node, "/e/cam_default", qos(AUTO, 150)),
        "pub_default__sub_manual_by_topic": Watch(case.node, "/e/cam_default", qos(MANUAL)),
        "pub_lease200__sub_lease150": Watch(case.node, "/e/cam_lease200", qos(AUTO, 150)),
        "pub_lease200__sub_lease300": Watch(case.node, "/e/cam_lease200", qos(AUTO, 300)),
        "pub_lease200__sub_lease200": Watch(case.node, "/e/cam_lease200", qos(AUTO, 200)),
        "pub_default__sub_default_watchdog": Watch(case.node, "/e/cam_default", qos(), watchdog_ms=WATCHDOG_MS),
    }
    dog = subs["pub_default__sub_default_watchdog"]
    ok = case.spin_until(lambda: dog.count >= 20 and subs["pub_lease200__sub_lease300"].count >= 20, 15)
    case.spin_for(1.0)
    compat = {k: {"msgs": w.count, "incompatible_events": w.incompatible[-1]["total_count"] if w.incompatible else 0,
                  "incompatible_policy": w.incompatible[-1]["policy"] if w.incompatible else None}
              for k, w in subs.items()}
    stopped = stop_and_wait(case, drv, "stop default", "default")
    case.spin_for(1.0)
    drv.close()
    case.close()
    t0 = stopped["last_pub_t"] if stopped else None
    return {"case": "E_compatibility_and_watchdog", "setup_ok": ok,
            "subscriptions": compat,
            "watchdog_limit_ms": WATCHDOG_MS,
            "watchdog_last_recv_to_fire_ms": r((dog.watchdog_t - dog.last_recv_t) * 1000) if dog.watchdog_t else None,
            "watchdog_last_pub_to_fire_ms": r((dog.watchdog_t - t0) * 1000) if dog.watchdog_t and t0 else None}


def main():
    started = time.monotonic()
    rclpy.init()
    emit({"case": "env", "rmw": rclpy.get_rmw_implementation_identifier(),
          "ros_distro": os.environ.get("ROS_DISTRO"), "python": sys.version.split()[0],
          "lease_ms": LEASE_MS, "deadline_ms": DEADLINE_MS,
          "camera_hz": round(1 / CAMERA_PERIOD), "diag_hz": round(1 / DIAG_PERIOD)})
    executor = SingleThreadedExecutor()
    failures = 0
    for fn in (case_a, case_b, case_c, case_d, case_k, case_e):
        try:
            result = fn(executor)
            failures += 0 if result.get("setup_ok") else 1
            emit(result)
        except Exception as exc:  # report and keep the other cases
            failures += 1
            emit({"case": fn.__name__, "error": repr(exc)})
    emit({"case": "summary", "failed_cases": failures, "wall_s": round(time.monotonic() - started, 1)})
    rclpy.shutdown()
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "driver":
        run_driver(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
