#!/usr/bin/env python3
# Python throttle/once/skip_first cases. Loop: 100 Hz for DUR seconds.
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.logging import LoggingSeverity

DUR = 5.0
case = sys.argv[1]
rclpy.init()


def run_loop(node, body):
    t0 = time.monotonic()
    i = 0
    while time.monotonic() - t0 < DUR:
        rclpy.spin_once(node, timeout_sec=0)
        body(i)
        i += 1
        time.sleep(0.01)
    return i


def helper(logger, i, tag):
    # one call site shared by every caller
    logger.info(f'{tag} {logger.name} i={i}', throttle_duration_sec=1.0)


def helper_level(logger, i, level):
    logger.log(f'SEV i={i}', level, throttle_duration_sec=1.0)


def helper_period(logger, i, period):
    logger.info(f'PER i={i}', throttle_duration_sec=period)


n = Node('pt', parameter_overrides=[Parameter('use_sim_time', value=case.startswith('sim'))])
lg = n.get_logger()
try:
    if case == 'base':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}'))
    elif case == 'thr1':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=1.0))
    elif case == 'thr1000':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=1000))
    elif case == 'thr0':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=0))
    elif case == 'once':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', once=True))
    elif case == 'skipfirst':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', skip_first=True))
    elif case == 'skipfirst_thr':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', skip_first=True, throttle_duration_sec=1.0))
    elif case == 'once_thr':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', once=True, throttle_duration_sec=1.0))
    elif case == 'two_loggers':
        n2 = Node('pt2')
        def body(i):
            helper(lg, i, 'MARK')
            helper(n2.get_logger(), i, 'MARK')
        calls = run_loop(n, body)
    elif case == 'same_logger_two_objects':
        # rclpy.logging.get_logger('pt') builds a new logger object on every call
        def body(i):
            helper(rclpy.logging.get_logger('pt'), i, 'MARK')
        calls = run_loop(n, body)
    elif case == 'child_loggers':
        a = lg.get_child('a')
        b = lg.get_child('b')
        def body(i):
            helper(a, i, 'MARK')
            helper(b, i, 'MARK')
        calls = run_loop(n, body)
    elif case == 'sev_change':
        calls = run_loop(n, lambda i: helper_level(lg, i, LoggingSeverity.INFO if i % 2 == 0 else LoggingSeverity.WARN))
    elif case == 'period_change':
        calls = run_loop(n, lambda i: helper_period(lg, i, 1.0 if i % 2 == 0 else 2.0))
    elif case == 'src_kwarg':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=1.0, throttle_time_source_type=n.get_clock()))
    elif case == 'sim_default':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=1.0))
    elif case == 'sim_nodeclock':
        calls = run_loop(n, lambda i: lg.info(f'MARK i={i}', throttle_duration_sec=1.0, throttle_time_source_type=n.get_clock()))
    else:
        raise SystemExit('unknown case')
    print(f'RESULT case={case} calls={calls} sim_now_ns={n.get_clock().now().nanoseconds}', flush=True)
except Exception as e:
    print(f'RESULT case={case} EXC {type(e).__module__}.{type(e).__name__}: {e}', flush=True)
n.destroy_node()
rclpy.shutdown()
