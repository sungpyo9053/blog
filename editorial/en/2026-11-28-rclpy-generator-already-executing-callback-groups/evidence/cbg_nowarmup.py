#!/usr/bin/env python3
"""Callback-group / executor experiments. Usage: cbg.py <test> <args...>
Every case prints RESULT lines; the main thread enforces a deadline so a deadlock
is reported as completed < expected instead of hanging."""
import os, sys, time, threading, statistics, traceback
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from std_srvs.srv import Trigger

def make_exec(name):
    if name == 'ste': return SingleThreadedExecutor()
    return MultiThreadedExecutor(num_threads=int(name[3:]))  # mte1, mte4

def stats(xs):
    if not xs: return 'n=0'
    xs = sorted(xs)
    return 'n=%d median=%.2fms max=%.2fms' % (len(xs), statistics.median(xs)*1e3, xs[-1]*1e3)

def finish(code=0):
    sys.stdout.flush(); sys.stderr.flush(); os._exit(code)

# ---------- test svc: timer callback calls a Trigger service in another process ----------
def svc(execname, group, method, n=10, deadline=8.0):
    rclpy.init()
    node = Node('caller')
    if group == 'default':
        tg = cg = None                      # node default group (MutuallyExclusive)
    elif group == 'sep':
        tg = None; cg = MutuallyExclusiveCallbackGroup()
    elif group == 'reentrant':
        tg = cg = ReentrantCallbackGroup()
    cli = node.create_client(Trigger, 'trig', callback_group=cg)
    if not cli.wait_for_service(timeout_sec=10):
        print('RESULT no service'); finish(1)
    lat, done, errs, state = [], threading.Event(), [], {'busy': False}
    def record(t0):
        lat.append(time.monotonic() - t0)
        if len(lat) >= n: done.set()
    if method == 'call':
        def cb():
            t0 = time.monotonic()
            cli.call(Trigger.Request())
            record(t0)
    elif method == 'call_timeout':
        def cb():
            t0 = time.monotonic()
            try:
                r = cli.call(Trigger.Request(), timeout_sec=2.0)
            except Exception as e:
                errs.append(repr(e)); done.set(); return
            if r is None:
                errs.append('returned None after %.2fs' % (time.monotonic() - t0))
                if len(errs) >= 2: done.set()
                return
            record(t0)
    elif method == 'async_cb':
        def cb():
            if state['busy']: return
            state['busy'] = True
            t0 = time.monotonic()
            f = cli.call_async(Trigger.Request())
            def on_done(fut):
                state['busy'] = False; record(t0)
            f.add_done_callback(on_done)
    elif method == 'await':
        async def cb():
            t0 = time.monotonic()
            await cli.call_async(Trigger.Request())
            record(t0)
    node.create_timer(0.2, cb, callback_group=tg)
    ex = make_exec(execname); ex.add_node(node)
    threading.Thread(target=ex.spin, daemon=True).start()
    t_start = time.monotonic()
    ok = done.wait(deadline)
    print('RESULT svc exec=%s group=%s method=%s completed=%d/%d within %.0fs -> %s ; latency %s%s' % (
        execname, group, method, len(lat), n, deadline,
        'OK' if ok and len(lat) >= n else ('DEADLOCK/TIMEOUT' if not errs else 'ERROR'),
        stats(lat), (' ; errors: ' + ' | '.join(errs[:2])) if errs else ''))
    finish()

# ---------- test gen: nested spinning ----------
# variants: <what>_<exec>; what in spin_once (ex.spin_once in callback),
# sufc_same (ex.spin_until_future_complete in callback), sufc_global
# (rclpy.spin_until_future_complete(node, f) in callback); exec in ste|mte4.
# Special: thread_global = rclpy.spin(node) in a thread + rclpy.spin_until_future_complete in main.
def gen(variant):
    rclpy.init()
    node = Node('nested')
    cli = node.create_client(Trigger, 'trig')
    cli.wait_for_service(timeout_sec=10)
    ticks, out = [], {}
    if variant == 'thread_global':
        node.create_timer(0.2, lambda: ticks.append(time.monotonic()))
        def spin():
            try: rclpy.spin(node)
            except Exception as e:
                out['spin'] = 'rclpy.spin() raised %s: %s' % (type(e).__name__, e); traceback.print_exc()
        threading.Thread(target=spin, daemon=True).start()
        time.sleep(0.5)
        for i in range(5):
            f = cli.call_async(Trigger.Request()); t0 = time.monotonic()
            try:
                rclpy.spin_until_future_complete(node, f, timeout_sec=3.0)
                out['r'] = 'call %d returned after %.3fs, done=%s' % (i, time.monotonic()-t0, f.done())
            except Exception as e:
                out['r'] = 'call %d raised %s: %s' % (i, type(e).__name__, e); traceback.print_exc(); break
            if 'spin' in out: break
        time.sleep(1.0)
    else:
        what, exn = variant.rsplit('_', 1)
        ex = make_exec(exn)
        def cb():
            ticks.append(time.monotonic())
            if len(ticks) > 1: return
            t0 = time.monotonic()
            try:
                if what == 'spin_once':
                    ex.spin_once(timeout_sec=1.0); out['r'] = 'spin_once returned after %.3fs' % (time.monotonic()-t0)
                else:
                    f = cli.call_async(Trigger.Request())
                    if what == 'sufc_global':
                        rclpy.spin_until_future_complete(node, f, timeout_sec=3.0)
                    else:
                        ex.spin_until_future_complete(f, timeout_sec=3.0)
                    out['r'] = 'returned after %.3fs, future.done()=%s' % (time.monotonic()-t0, f.done())
            except Exception as e:
                out['r'] = 'raised %s: %s' % (type(e).__name__, e)
                traceback.print_exc()
        node.create_timer(0.2, cb)
        def spin():
            try:
                ex.add_node(node); ex.spin()
            except Exception as e:
                out['spin'] = 'ex.spin() raised %s: %s' % (type(e).__name__, e)
                traceback.print_exc()
        threading.Thread(target=spin, daemon=True).start()
        time.sleep(4.0)
    print('RESULT gen variant=%s inner=%s ; outer=%s ; timer fired %d times (expected ~20 in 4 s)' % (
        variant, out.get('r', 'never returned'), out.get('spin', 'still spinning'), len(ticks)))
    finish()

# ---------- test slow: 10 Hz timer next to a 1 s sleeping callback ----------
def slow(execname, group, window=10.0):
    rclpy.init()
    node = Node('slow')
    if group == 'same':
        g1 = g2 = None
    elif group == 'sep':
        g1 = MutuallyExclusiveCallbackGroup(); g2 = MutuallyExclusiveCallbackGroup()
    elif group == 'reentrant':
        g1 = g2 = ReentrantCallbackGroup()
    fast = []
    node.create_timer(0.1, lambda: fast.append(time.monotonic()), callback_group=g1)
    node.create_timer(2.0, lambda: time.sleep(1.0), callback_group=g2)
    ex = make_exec(execname); ex.add_node(node)
    threading.Thread(target=ex.spin, daemon=True).start()
    time.sleep(0.5); t0 = time.monotonic(); time.sleep(window); t1 = time.monotonic()
    w = [t for t in fast if t0 <= t <= t1]
    gaps = [b - a for a, b in zip(w, w[1:])]
    print('RESULT slow exec=%s group=%s fast_ticks=%d in %.1fs -> %.2f Hz (target 10) ; max gap %.0fms' % (
        execname, group, len(w), t1 - t0, len(w) / (t1 - t0), max(gaps) * 1e3 if gaps else -1))
    finish()

def server():
    rclpy.init()
    node = Node('trig_server')
    def h(req, res):
        res.success = True; return res
    node.create_service(Trigger, 'trig', h)
    rclpy.spin(node)

if __name__ == '__main__':
    t = sys.argv[1]
    {'svc': svc, 'gen': gen, 'slow': slow, 'server': server}[t](*sys.argv[2:])
