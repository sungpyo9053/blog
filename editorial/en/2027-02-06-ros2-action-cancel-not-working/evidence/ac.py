# ac.py server <mode>  |  ac.py client <cancel_at|-> <second_goal_at|-> <wait_s>
# Server: 10 steps of 0.5 s (time.sleep), feedback each step. Uses tf2_msgs/action/LookupTransform,
# the only action type in ros-base; the result's frame_id carries the number of finished steps.
import sys, time, threading, traceback
import rclpy
from rclpy.action import ActionServer, ActionClient, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node
from tf2_msgs.action import LookupTransform as Act

T0 = time.monotonic()
def ts(): return f"{time.monotonic()-T0:6.2f}s"
def log(*a): print(f"[{sys.argv[1]} {ts()}]", *a, flush=True)
STATUS = {0: 'UNKNOWN', 1: 'ACCEPTED', 2: 'EXECUTING', 3: 'CANCELING', 4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}

def server(mode):
    node = Node('fib_server')
    multi = mode.startswith('multi')
    group = ReentrantCallbackGroup() if mode in ('multi_reentrant', 'multi_reentrant_nocheck', 'multi_default_cancel') else None
    check = mode not in ('accept_nocheck', 'multi_reentrant_nocheck')
    def cancel_cb(goal_handle):
        log('cancel_callback called -> ACCEPT')
        return CancelResponse.ACCEPT
    def execute(goal_handle):
        log('execute start, target', goal_handle.request.target_frame, 'thread', threading.current_thread().name)
        fb = Act.Feedback(); steps = 0
        for i in range(10):
            if check and goal_handle.is_cancel_requested:
                log('is_cancel_requested True at step', i)
                if mode != 'cancel_requested_but_succeed':
                    goal_handle.canceled()
                    log('goal_handle.canceled() done')
                    r = Act.Result(); r.transform.header.frame_id = 'steps=%d' % steps; return r
            steps += 1
            goal_handle.publish_feedback(fb)
            time.sleep(0.5)
        r = Act.Result(); r.transform.header.frame_id = 'steps=%d' % steps
        if mode == 'no_state':
            log('returning result without succeed()'); return r
        if mode == 'canceled_unrequested':
            log('calling canceled() without a cancel request')
            try: goal_handle.canceled()
            except Exception as e: log('EXC', type(e).__name__, e)
            return r
        if mode == 'succeed_twice':
            goal_handle.succeed()
            try: goal_handle.succeed()
            except Exception as e: log('EXC', type(e).__name__, e)
            return r
        if mode == 'raise':
            raise RuntimeError('boom in execute')
        if mode == 'return_none':
            goal_handle.succeed(); log('succeed() then return None'); return None
        goal_handle.succeed(); log('succeed() done')
        return r
    kw = {}
    if mode not in ('default_cancel', 'multi_default_cancel'):
        kw['cancel_callback'] = cancel_cb
    if group is not None:
        kw['callback_group'] = group
    ActionServer(node, Act, 'fib', execute, **kw)
    log('server up, mode', mode, 'executor', 'Multi' if multi else 'Single', 'group', 'Reentrant' if group else 'default')
    ex = MultiThreadedExecutor(num_threads=4) if multi else SingleThreadedExecutor()
    ex.add_node(node)
    try:
        ex.spin()
    except (KeyboardInterrupt, Exception) as e:
        log('spin ended', type(e).__name__)

def client(cancel_at, second_at, wait_s):
    node = Node('fib_client')
    ac = ActionClient(node, Act, 'fib')
    if not ac.wait_for_server(timeout_sec=10):
        log('NO SERVER'); return
    log('server found')
    from action_msgs.srv import CancelGoal as CG
    log('CancelGoal return codes:', {k: getattr(CG.Response, k) for k in dir(CG.Response) if k.startswith('ERROR')})
    goals = {}
    def send(tag):
        g = Act.Goal(); g.target_frame = 'map'; g.source_frame = tag
        t = time.monotonic()
        f = ac.send_goal_async(g, feedback_callback=lambda m, tag=tag: goals[tag].setdefault('fb', []).append(1))
        goals[tag] = {'sent': t}
        def on_goal(fut, tag=tag):
            gh = fut.result(); goals[tag]['gh'] = gh
            log(tag, 'goal response accepted=%s after %.2fs' % (gh.accepted, time.monotonic()-goals[tag]['sent']))
            if gh.accepted:
                rf = gh.get_result_async()
                def on_res(rfut, tag=tag):
                    res = rfut.result()
                    log(tag, 'RESULT status=%d %s %s fb_msgs=%d' % (res.status, STATUS.get(res.status), res.result.transform.header.frame_id or '(empty result)', len(goals[tag].get('fb', []))))
                    goals[tag]['done'] = True
                rf.add_done_callback(on_res)
        f.add_done_callback(on_goal)
    send('goal1')
    cancel_sent = False; second_sent = False
    end = time.monotonic() + wait_s
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        el = time.monotonic() - goals['goal1']['sent']  # cancel_at / second_at count from sending goal1
        if cancel_at is not None and not cancel_sent and el >= cancel_at and 'gh' in goals['goal1']:
            cancel_sent = True; tc = time.monotonic()
            log('goal1 cancel_goal_async sent')
            cf = goals['goal1']['gh'].cancel_goal_async()
            cf.add_done_callback(lambda fut: log('goal1 CANCEL response return_code=%d goals_canceling=%d after %.2fs' % (fut.result().return_code, len(fut.result().goals_canceling), time.monotonic()-tc)))
        if second_at is not None and not second_sent and el >= second_at:
            second_sent = True; log('goal2 sent'); send('goal2')
        if all(v.get('done') for v in goals.values()) and (second_at is None or second_sent) and (cancel_at is None or cancel_sent):
            # give a pending cancel response a moment
            t2 = time.monotonic() + 1.0
            while time.monotonic() < t2: rclpy.spin_once(node, timeout_sec=0.05)
            break
    for k, v in goals.items():
        if not v.get('done'): log(k, 'NO RESULT within %ss' % wait_s)
    log('client exit')

rclpy.init()
try:
    if sys.argv[1] == 'server':
        server(sys.argv[2])
    else:
        a = lambda s: None if s == '-' else float(s)
        client(a(sys.argv[2]), a(sys.argv[3]), float(sys.argv[4]))
finally:
    try: rclpy.shutdown()
    except Exception: pass
