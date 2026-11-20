#!/usr/bin/env python3
# rclpy node "pcb" with parameters gain (default 1.0) and mode (default "idle").
# argv[1] = case. Every callback call is logged with the parameters it received.
import sys
import time

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter

case = sys.argv[1]
rclpy.init(args=sys.argv)
n = Node('pcb')
log = n.get_logger().info
calls = {'on_set': 0}
pending = []


def fmt(params):
    return ', '.join(f'{p.name}={p.value}' for p in params)


def on_set(params):
    calls['on_set'] += 1
    log(f'CB#{calls["on_set"]} on_set got: {fmt(params)}')
    res = SetParametersResult(successful=True)
    for p in params:
        if p.name != 'gain':
            continue
        if case in ('reject', 'reject_init') and p.value > 2.5:
            res = SetParametersResult(successful=False, reason='gain must be <= 2.5')
        if case == 'set_inside' and p.value == 3.0:
            log('calling set_parameters(mode) inside on_set')
            r = n.set_parameters([Parameter('mode', Parameter.Type.STRING, 'changed')])
            log(f'inner set_parameters returned successful={r[0].successful} reason={r[0].reason!r}')
        if case == 'declare_inside' and p.value == 3.0:
            log('calling declare_parameter(extra) inside on_set')
            n.declare_parameter('extra', 0)
            log('declare_parameter(extra) returned')
        if case == 'deferred' and p.value == 3.0:
            pending.append('changed_by_timer')
    if case == 'return_none':
        return None
    if case == 'return_bool':
        return True
    return res


def on_set_b(params):
    log(f'CB_B on_set got: {fmt(params)}')
    return SetParametersResult(successful=True)


def register():
    n.add_on_set_parameters_callback(on_set)
    if case == 'two_cbs':
        n.add_on_set_parameters_callback(on_set_b)
    if case in ('pre_set', 'post_set', 'post_set_modify'):
        if not hasattr(n, 'add_post_set_parameters_callback'):
            log('NOT AVAILABLE: this rclpy Node has no add_post_set_parameters_callback / add_pre_set_parameters_callback')
            return
        if case == 'pre_set':
            def pre(params):
                log(f'PRE got: {fmt(params)}')
                if any(p.name == 'gain' and p.value == 3.0 for p in params):
                    params = list(params) + [Parameter('mode', Parameter.Type.STRING, 'auto_from_pre_set')]
                return params
            n.add_pre_set_parameters_callback(pre)

        def post(params):
            log(f'POST got: {fmt(params)}')
            if case == 'post_set_modify' and any(p.name == 'gain' and p.value == 3.0 for p in params):
                log('calling set_parameters(mode) inside post_set')
                r = n.set_parameters([Parameter('mode', Parameter.Type.STRING, 'changed_in_post')])
                log(f'inner set_parameters returned successful={r[0].successful} reason={r[0].reason!r}')
        n.add_post_set_parameters_callback(post)


if case != 'after':
    register()
n.declare_parameter('gain', 1.0)
n.declare_parameter('mode', 'idle')
if case == 'after':
    register()

if case == 'deferred':
    def tick():
        while pending:
            v = pending.pop(0)
            r = n.set_parameters([Parameter('mode', Parameter.Type.STRING, v)])
            log(f'timer set mode={v} successful={r[0].successful}')
    n.create_timer(0.1, tick)

log(f'READY gain={n.get_parameter("gain").value} mode={n.get_parameter("mode").value} on_set_calls={calls["on_set"]}')
try:
    if case == 'no_spin':
        while rclpy.ok():
            time.sleep(0.1)
    else:
        rclpy.spin(n)
except (KeyboardInterrupt, ExternalShutdownException) as e:
    print(f'spin ended with {type(e).__name__}', flush=True)
    pass
print(f'EXIT gain={n.get_parameter("gain").value} mode={n.get_parameter("mode").value} on_set_calls={calls["on_set"]}', flush=True)
