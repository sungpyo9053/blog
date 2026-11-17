"""rclpy action client spun from two threads at once: does
'Failed to get number of ready entities for action client: wait set index ... out of bounds'
appear, how often, and which patterns avoid it?

usage: python3 ws.py <case> [seconds]
Prints one RESULT line per run plus the first full traceback of each new error type.
"""
import collections
import sys
import threading
import time
import traceback

import rclpy
from rclpy.action import ActionClient, ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Empty

# ros-base has no example_interfaces; tf2_msgs ships an action type, so use that
from tf2_msgs.action import LookupTransform as Fibonacci
from rcl_interfaces.srv import ListParameters

CASE = sys.argv[1]
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0

errors = collections.Counter()
first_err = [None]
seen = set()
lock = threading.Lock()
T0 = time.monotonic()
ok = [0]
stop = threading.Event()


def record(where, e):
    key = '%s: %s' % (type(e).__name__, str(e).splitlines()[0][:160] if str(e) else '')
    with lock:
        errors[key] += 1
        if first_err[0] is None:
            first_err[0] = time.monotonic() - T0
        if key not in seen:
            seen.add(key)
            print('--- first %s in %s at %.3fs' % (key, where, time.monotonic() - T0))
            print(''.join(traceback.format_exception(type(e), e, e.__traceback__))[-2500:])


class Server(Node):
    def __init__(self):
        super().__init__('ws_server')
        self.srv = ActionServer(self, Fibonacci, 'fib', self.cb, callback_group=ReentrantCallbackGroup())

    def cb(self, gh):
        gh.succeed()
        return Fibonacci.Result()


class Client(Node):
    """Action client plus some background traffic so the wait set changes size."""

    def __init__(self, name='ws_client', group=None):
        super().__init__(name)
        self.group = group
        self.ac = ActionClient(self, Fibonacci, 'fib', callback_group=group)
        self.sc = self.create_client(ListParameters, '/ws_server/list_parameters', callback_group=group)
        self.pub = self.create_publisher(Empty, 'ws_tick', 10)
        self.subs = [self.create_subscription(Empty, 'ws_tick', lambda m: None, 10, callback_group=group)
                     for _ in range(3)]
        self.create_timer(0.01, lambda: self.pub.publish(Empty()), callback_group=group)


def goal():
    g = Fibonacci.Goal()
    g.target_frame = 'a'
    g.source_frame = 'b'
    return g


def start_server():
    srv = Server()
    ex = SingleThreadedExecutor()
    ex.add_node(srv)
    th = threading.Thread(target=lambda: ex.spin(), daemon=True)
    th.start()
    return srv, ex


def spinner_loop(ex):
    """Background thread: spin_once in a loop so that errors are counted, not fatal."""
    while not stop.is_set():
        try:
            ex.spin_once(timeout_sec=0.05)
        except Exception as e:  # noqa
            record('spinner', e)


spin_died = [None]


def spinner_spin(ex):
    """Background thread: plain executor.spin(), as most user code does."""
    try:
        ex.spin()
    except Exception as e:  # noqa
        spin_died[0] = time.monotonic() - T0
        record('spinner(spin)', e)


def call_goal_with(spin_fn, cli):
    gf = cli.ac.send_goal_async(goal())
    spin_fn(gf)
    if not gf.done():
        return False
    rf = gf.result().get_result_async()
    spin_fn(rf)
    return rf.done()


def main():
    rclpy.init()
    srv, sex = start_server()
    mode_exec = SingleThreadedExecutor if '_st' in CASE else MultiThreadedExecutor
    group = ReentrantCallbackGroup() if CASE.startswith('fix_async') else None
    print('diag: case=%s executor=%s' % (CASE, 'SingleThreadedExecutor' if '_st' in CASE else 'MultiThreadedExecutor'))
    cli = Client(group=group)
    ex = mode_exec()
    ex.add_node(cli)
    if not cli.ac.wait_for_server(timeout_sec=5.0):
        print('server not found')
    threads = []

    def bg(fn):
        t = threading.Thread(target=fn, args=(ex,), daemon=True)
        t.start()
        threads.append(t)

    def run_for(body):
        global T0
        T0 = time.monotonic()
        while time.monotonic() - T0 < DUR:
            try:
                if body():
                    ok[0] += 1
            except Exception as e:  # noqa
                record('main', e)
        stop.set()

    if CASE == 'seq':  # one thread only, no background spinner
        run_for(lambda: call_goal_with(lambda f: ex.spin_until_future_complete(f, timeout_sec=2.0), cli))
    elif CASE in ('same_exec', 'same_exec_st'):  # spinner thread + main thread on the same executor
        bg(spinner_loop)
        run_for(lambda: call_goal_with(lambda f: ex.spin_until_future_complete(f, timeout_sec=2.0), cli))
    elif CASE == 'same_exec_spin':  # spinner thread uses executor.spin()
        bg(spinner_spin)
        run_for(lambda: call_goal_with(lambda f: ex.spin_until_future_complete(f, timeout_sec=2.0), cli))
    elif CASE == 'global':  # spinner thread + rclpy.spin_until_future_complete(node, ...) in main, node never re-added
        bg(spinner_loop)
        d = [0]

        def body():
            r = call_goal_with(lambda f: rclpy.spin_until_future_complete(cli, f, timeout_sec=2.0), cli)
            if not d[0]:
                d[0] = 1
                print('diag: after first rclpy.spin_until_future_complete: cli in A=%s cli.executor=%s' % (
                    cli in ex.get_nodes(), cli.executor))
            return r
        run_for(body)
    elif CASE == 'spin_once_global':  # pymoveit2 #93 pattern: rclpy.spin_once(node) while an executor spins it
        bg(spinner_loop)
        run_for(lambda: call_goal_with(lambda f: [rclpy.spin_once(cli, timeout_sec=0.05) for _ in range(40) if not f.done()], cli))
    elif CASE.startswith('move_'):
        # The node is moved between executor A (spun by a background thread) and a second
        # executor B on every goal. B holds an extra node with many subscriptions unless *_nopad.
        # *_spin: the background thread uses plain executor.spin() instead of the counting loop.
        bg(spinner_spin if CASE.endswith('_spin') else spinner_loop)
        pad = Node('ws_pad')
        if '_nopad' not in CASE:
            pad.subs = [pad.create_subscription(Empty, 'ws_tick', lambda m: None, 10) for _ in range(30)]
        if CASE.startswith('move_global') or CASE.startswith('move_spin_once'):
            B = rclpy.get_global_executor()
        else:
            B = SingleThreadedExecutor()
        B.add_node(pad)
        diag = [False]

        def back_to_A():
            ex.add_node(cli)
            if not diag[0]:
                diag[0] = True
                print('diag: after ex.add_node: cli in A=%s cli in B=%s cli.executor is A=%s' % (
                    cli in ex.get_nodes(), cli in B.get_nodes(), cli.executor is ex))

        if CASE.startswith('move_global'):
            def body():
                r = call_goal_with(lambda f: rclpy.spin_until_future_complete(cli, f, timeout_sec=2.0), cli)
                back_to_A()
                return r
        elif CASE.startswith('move_spin_once'):
            def body():
                r = call_goal_with(lambda f: [rclpy.spin_once(cli, timeout_sec=0.05) for _ in range(40) if not f.done()], cli)
                back_to_A()
                return r
        else:  # move_two_exec: B also spun by its own thread; main only moves the node and waits on Events
            bg2 = threading.Thread(target=spinner_loop, args=(B,), daemon=True)
            bg2.start()
            threads.append(bg2)
            flip = [0]

            def body():
                flip[0] += 1
                (B if flip[0] % 2 else ex).add_node(cli)
                ev = threading.Event()
                gf = cli.ac.send_goal_async(goal())
                gf.add_done_callback(lambda f: ev.set())
                if not ev.wait(2.0):
                    return False
                ev2 = threading.Event()
                rf = gf.result().get_result_async()
                rf.add_done_callback(lambda f: ev2.set())
                return ev2.wait(2.0)
        run_for(body)
    elif CASE == 'svc_same_exec':  # same pattern, service client instead of action client
        bg(spinner_loop)

        def body():
            f = cli.sc.call_async(ListParameters.Request())
            ex.spin_until_future_complete(f, timeout_sec=2.0)
            return f.done()
        run_for(body)
    elif CASE == 'two_spinners':  # two background threads both spin_once the same executor, no goals sent from them
        bg(spinner_loop)
        bg(spinner_loop)

        def body():
            ev = threading.Event()
            gf = cli.ac.send_goal_async(goal())
            gf.add_done_callback(lambda f: ev.set())
            if not ev.wait(2.0):
                return False
            ev2 = threading.Event()
            rf = gf.result().get_result_async()
            rf.add_done_callback(lambda f: ev2.set())
            return ev2.wait(2.0)
        run_for(body)
    elif CASE in ('fix_event', 'fix_event_st', 'fix_event_spin', 'fix_event_st_spin'):
        # one spinner; main waits on threading.Event, never spins
        bg(spinner_spin if CASE.endswith('_spin') else spinner_loop)

        def body():
            ev = threading.Event()
            gf = cli.ac.send_goal_async(goal())
            gf.add_done_callback(lambda f: ev.set())
            if not ev.wait(2.0):
                return False
            ev2 = threading.Event()
            rf = gf.result().get_result_async()
            rf.add_done_callback(lambda f: ev2.set())
            return ev2.wait(2.0)
        run_for(body)
    elif CASE in ('fix_async', 'fix_async_spin'):  # coroutine callbacks awaiting futures, one executor, one spinner
        done = [0]

        async def task():
            while not stop.is_set():
                try:
                    gh = await cli.ac.send_goal_async(goal())
                    await gh.get_result_async()
                    done[0] += 1
                except Exception as e:  # noqa
                    record('coroutine', e)
        bg(spinner_spin if CASE.endswith('_spin') else spinner_loop)
        ex.create_task(task)
        T = time.monotonic()
        globals()['T0'] = T
        time.sleep(DUR)
        stop.set()
        ok[0] = done[0]
    elif CASE == 'fix_own_node':  # worker thread owns a second node + executor; main executor spins the first
        bg(spinner_loop)
        cli2 = Client('ws_client2')
        ex2 = SingleThreadedExecutor()
        ex2.add_node(cli2)
        cli2.ac.wait_for_server(timeout_sec=5.0)
        run_for(lambda: call_goal_with(lambda f: ex2.spin_until_future_complete(f, timeout_sec=2.0), cli2))
    else:
        raise SystemExit('unknown case')

    for t in threads:
        t.join(timeout=2.0)
    n = sum(errors.values())
    print('RESULT case=%s exec=%s dur=%.1f ok_goals=%d errors=%d first_err_s=%s spin_thread_died_s=%s types=%s' % (
        CASE, mode_exec.__name__, DUR, ok[0], n,
        'none' if first_err[0] is None else '%.3f' % first_err[0],
        'n/a' if not CASE.endswith('_spin') else ('no' if spin_died[0] is None else '%.3f' % spin_died[0]),
        dict(errors)))
    sys.stdout.flush()
    import os
    os._exit(0)  # skip teardown, it can hang after these races


if __name__ == '__main__':
    main()
