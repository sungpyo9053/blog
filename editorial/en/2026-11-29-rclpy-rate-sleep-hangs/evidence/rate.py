#!/usr/bin/env python3
"""rclpy Rate / timer / use_sim_time measurements. One scenario per process:
    python3 rate.py <scenario> [args]
Every blocking call is guarded by a watchdog thread that prints and os._exit(3)s."""
import os, sys, time, threading, signal, statistics, subprocess
import inspect
import rclpy, rclpy.timer, rclpy.clock
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.duration import Duration
from rclpy.parameter import Parameter

T0 = time.monotonic()
def el():
    return time.monotonic() - T0
def p(*a):
    print(f"[{el():7.3f}s]", *a, flush=True)

def watchdog(sec, what):
    def run():
        time.sleep(sec)
        p(f"WATCHDOG: {what} still blocked after {sec:.1f} s -> os._exit(3)")
        os._exit(3)
    threading.Thread(target=run, daemon=True).start()

def stats(deltas, nominal):
    ms = sorted(d * 1000 for d in deltas)
    n = len(ms)
    p95 = ms[min(n - 1, int(round(0.95 * (n - 1))))]
    jit = [abs(d - nominal * 1000) for d in ms]
    return (f"n={n} nominal={nominal*1000:.2f}ms median={statistics.median(ms):.3f}ms "
            f"mean={statistics.mean(ms):.3f}ms p95={p95:.3f}ms min={ms[0]:.3f}ms max={ms[-1]:.3f}ms "
            f"abs_jitter_median={statistics.median(jit):.3f}ms abs_jitter_p95={sorted(jit)[min(n-1,int(round(0.95*(n-1))))]:.3f}ms "
            f"total={sum(deltas):.3f}s (ideal {n*nominal:.3f}s)")

def spin_thread(node, kind="ste"):
    ex = MultiThreadedExecutor(num_threads=4) if kind == "mte" else SingleThreadedExecutor()
    ex.add_node(node)
    th = threading.Thread(target=ex.spin, daemon=True)
    th.start()
    return ex, th

def loop(fn, n):
    """call fn() n+1 times, return the n deltas between returns"""
    fn()  # first call aligns to the period
    last = time.perf_counter(); out = []
    for _ in range(n):
        fn()
        now = time.perf_counter(); out.append(now - last); last = now
    return out

def main():
    sc = sys.argv[1]; args = sys.argv[2:]
    rclpy.init()

    if sc == "info":
        p("rclpy file", rclpy.__file__)
        p("Clock.sleep_for exists:", hasattr(rclpy.clock.Clock, "sleep_for"),
          "| Clock.sleep_until exists:", hasattr(rclpy.clock.Clock, "sleep_until"))
        p("Node.create_rate signature:", inspect.signature(Node.create_rate))
        src = inspect.getsource(rclpy.timer.Rate)
        print("----- rclpy.timer.Rate source -----"); print(src); print("----- end -----")
        src = inspect.getsource(Node.create_rate)
        print("----- Node.create_rate source -----"); print(src); print("----- end -----")

    elif sc == "nospin":  # (1) rate.sleep with nothing spinning
        hz = float(args[0])
        node = Node("nospin")
        rate = node.create_rate(hz)
        watchdog(5.0, f"rate.sleep() at {hz} Hz with no executor")
        for i in range(3):
            t = time.monotonic(); p(f"calling rate.sleep() #{i+1}")
            rate.sleep()
            p(f"rate.sleep() #{i+1} returned after {time.monotonic()-t:.4f} s")

    elif sc == "nospin_spinonce":  # rclpy.spin_once between sleeps in the same thread
        hz = float(args[0])
        node = Node("nospin1"); rate = node.create_rate(hz)
        watchdog(5.0, "rate.sleep() after spin_once")
        rclpy.spin_once(node, timeout_sec=0.5)
        t = time.monotonic(); p("spin_once(timeout_sec=0.5) done, calling rate.sleep()")
        rate.sleep(); p(f"returned after {time.monotonic()-t:.4f} s")

    elif sc in ("rate_ste", "rate_mte"):  # (2) rate.sleep with executor in a background thread
        hz = float(args[0]); n = int(args[1])
        node = Node("ratespin"); spin_thread(node, "mte" if sc == "rate_mte" else "ste")
        rate = node.create_rate(hz)
        watchdog(n / hz * 3 + 5, "rate loop")
        p(sc, hz, "Hz:", stats(loop(rate.sleep, n), 1 / hz))

    elif sc == "timesleep":
        hz = float(args[0]); n = int(args[1])
        p("time.sleep(1/hz)", hz, "Hz:", stats(loop(lambda: time.sleep(1 / hz), n), 1 / hz))

    elif sc in ("sleep_for", "sleep_until"):
        hz = float(args[0]); n = int(args[1])
        if not hasattr(rclpy.clock.Clock, sc):
            p(f"Clock.{sc}: Not available in this rclpy"); return
        node = Node("sleepfor"); clk = node.get_clock(); per = Duration(seconds=1 / hz)
        watchdog(n / hz * 3 + 5, sc)
        if sc == "sleep_for":
            p("get_clock().sleep_for(period), no executor,", hz, "Hz:", stats(loop(lambda: clk.sleep_for(per), n), 1 / hz))
        else:
            nxt = [clk.now()]
            def f():
                nxt[0] = nxt[0] + per; clk.sleep_until(nxt[0])
            p("get_clock().sleep_until(next deadline), no executor,", hz, "Hz:", stats(loop(f, n), 1 / hz))

    elif sc == "timer":  # create_timer callback, spin in main thread
        hz = float(args[0]); n = int(args[1])
        node = Node("timer"); ts = []
        done = threading.Event()
        def cb():
            ts.append(time.perf_counter())
            if len(ts) > n: done.set()
        node.create_timer(1 / hz, cb)
        watchdog(n / hz * 3 + 5, "timer")
        ex = SingleThreadedExecutor(); ex.add_node(node)
        while not done.is_set():
            ex.spin_once(timeout_sec=0.1)
        d = [b - a for a, b in zip(ts, ts[1:])][:n]
        p("create_timer callback", hz, "Hz:", stats(d, 1 / hz))

    elif sc in ("incb_ste", "incb_mte", "incb_mte_reentrant"):  # rate.sleep inside a callback
        node = Node("incb"); rate = node.create_rate(10)
        grp = ReentrantCallbackGroup() if sc == "incb_mte_reentrant" else None
        res = []
        def cb():
            if res: return
            res.append(0); t = time.monotonic(); p("in timer callback, calling rate.sleep() (10 Hz)")
            for i in range(3):
                rate.sleep()
            p(f"3 x rate.sleep() inside callback returned after {time.monotonic()-t:.4f} s"); res.append(1)
        node.create_timer(0.1, cb, callback_group=grp)
        watchdog(5.0, f"rate.sleep() inside a callback ({sc})")
        ex = SingleThreadedExecutor() if sc == "incb_ste" else MultiThreadedExecutor(num_threads=4)
        ex.add_node(node)
        while len(res) < 2:
            ex.spin_once(timeout_sec=0.1)
        p("done")

    elif sc == "simtime":  # (3) use_sim_time=true, no /clock, then a /clock publisher
        mode = args[0]  # rate | timer | sleep_for
        node = Node("simnode", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        p("use_sim_time =", node.get_parameter("use_sim_time").value, "| clock type:", node.get_clock().clock_type,
          "| now() =", node.get_clock().now().nanoseconds, "ns")
        spin_thread(node)
        ev = []; lock = threading.Lock()
        if mode == "timer":
            node.create_timer(0.1, lambda: ev.append((time.monotonic(), node.get_clock().now().nanoseconds)))
            fn = None
        elif mode == "rate":
            rate = node.create_rate(10); fn = rate.sleep
        else:
            if not hasattr(rclpy.clock.Clock, "sleep_for"):
                p("Clock.sleep_for: Not available in this rclpy"); return
            fn = lambda: node.get_clock().sleep_for(Duration(seconds=0.1))
        def sleeper():
            while True:
                fn(); ev.append((time.monotonic(), node.get_clock().now().nanoseconds))
        if fn: threading.Thread(target=sleeper, daemon=True).start()
        time.sleep(3.0)
        p(f"phase A (no /clock, 3.0 s wall): {len(ev)} {mode} wakeups, now() = {node.get_clock().now().nanoseconds} ns")
        here = os.path.abspath(__file__)
        cp = subprocess.Popen([sys.executable, here, "clockpub"]); tstart = time.monotonic()
        p("started /clock publisher process (sim time starts at 1000 s, 1x speed, 100 Hz)")
        n0 = len(ev); time.sleep(5.0)
        new = ev[n0:]
        if new:
            p(f"phase B: first {mode} wakeup {new[0][0]-tstart:.3f} s after publisher start, sim now={new[0][1]/1e9:.3f} s; "
              f"{len(new)} wakeups in 5.0 s wall")
            d = [b[0] - a[0] for a, b in zip(new, new[1:])]
            if len(d) > 5: p("phase B wall intervals between wakeups:", stats(d[1:], 0.1))
        else:
            p("phase B: no wakeups in 5.0 s after starting /clock")
        cp.send_signal(signal.SIGINT); cp.wait(timeout=5); tkill = time.monotonic()
        n1 = len(ev); time.sleep(3.0)
        p(f"phase C (/clock publisher stopped, 3.0 s wall): {len(ev)-n1} wakeups, now() = {node.get_clock().now().nanoseconds/1e9:.3f} s")
        os._exit(0)

    elif sc == "clockpub":
        from rosgraph_msgs.msg import Clock
        node = Node("clockpub"); pub = node.create_publisher(Clock, "/clock", 10)
        start = time.monotonic()
        try:
            while rclpy.ok():
                s = 1000.0 + (time.monotonic() - start)
                m = Clock(); m.clock.sec = int(s); m.clock.nanosec = int((s % 1) * 1e9)
                pub.publish(m); time.sleep(0.01)
        except (KeyboardInterrupt, Exception):
            pass

    elif sc == "destroy":  # (4) destroy/shutdown while another thread is in rate.sleep
        what, spin = args[0], args[1]  # rate|node|shutdown , spin|nospin
        node = Node("destroy")
        if spin == "spin": spin_thread(node)
        rate = node.create_rate(0.2)  # 5 s period
        out = {}
        def sleeper():
            t = time.monotonic()
            try:
                rate.sleep(); rate.sleep()
                out["r"] = f"returned normally after {time.monotonic()-t:.3f} s"
            except BaseException as e:
                out["r"] = f"raised {type(e).__module__}.{type(e).__name__}: {e!r} after {time.monotonic()-t:.3f} s"
            p("sleeper:", out["r"])
        th = threading.Thread(target=sleeper, daemon=True); th.start()
        time.sleep(1.0)
        p(f"main: calling {what} while sleeper is in rate.sleep() (0.2 Hz, {spin})")
        try:
            if what == "rate": rate.destroy()
            elif what == "node": node.destroy_node()
            else: rclpy.shutdown()
            p(f"main: {what} call returned")
        except BaseException as e:
            p(f"main: {what} raised {type(e).__name__}: {e!r}")
        th.join(timeout=12.0)
        if th.is_alive(): p("sleeper STILL blocked 12.0 s after the call")
        os._exit(0)

    elif sc == "sigint_child":  # main thread blocked in rate.sleep; parent sends SIGINT
        spin = args[0]
        node = Node("sigint")
        if spin == "spin": spin_thread(node)
        rate = node.create_rate(0.1 if spin == "spin" else 10)  # spin: 10 s period, so a return means interrupted
        p("child: entering rate.sleep() in the main thread", spin)
        try:
            rate.sleep(); rate.sleep()
            p("child: rate.sleep() returned normally")
        except BaseException as e:
            p(f"child: caught {type(e).__module__}.{type(e).__name__}: {e!r}"); raise

    elif sc == "sigint":
        spin = args[0]
        c = subprocess.Popen([sys.executable, os.path.abspath(__file__), "sigint_child", spin])
        time.sleep(2.0); t = time.monotonic(); c.send_signal(signal.SIGINT); p("parent: SIGINT sent")
        try:
            rc = c.wait(timeout=10.0); p(f"parent: child exited rc={rc} {time.monotonic()-t:.3f} s after SIGINT")
        except subprocess.TimeoutExpired:
            p("parent: child still running 10.0 s after SIGINT, sending SIGKILL"); c.kill(); c.wait()
        os._exit(0)
    else:
        p("unknown scenario", sc)

    try:
        rclpy.shutdown()
    except Exception:
        pass
    sys.stdout.flush()
    os._exit(0)

if __name__ == "__main__":
    main()
