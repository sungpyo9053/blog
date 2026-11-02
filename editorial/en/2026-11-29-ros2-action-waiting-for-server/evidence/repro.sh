#!/bin/bash
# Reproduces "Waiting for an action server to become available..." from ros2 action send_goal
# and rclpy ActionClient goals/results that never arrive, with a small example_interfaces Fibonacci server.
# Main run, one distro at a time, inside ros:<distro>-ros-base:
#   docker run --rm --name act-<distro> --ulimit core=0 --cpus=1.5 -v /tmp/en-action:/w \
#     ros:<distro>-ros-base bash /w/repro.sh main > out_<distro>.txt 2>&1
# Cross-container ROS_DOMAIN_ID check (run from the host, appended to the same file):
#   bash repro.sh host <distro> >> out_<distro>.txt 2>&1
# Note: the first host-part attempt on Humble ran before inst() existed and printed "The passed action
# type is invalid" (fresh containers lack example_interfaces); that block was removed and the part rerun.
ulimit -c 0
MODE=${1:-main}

if [ "$MODE" = host ]; then
  D=$2; IMG=ros:$D-ros-base
  echo; echo "##### X1 two containers on the default bridge network: server ROS_DOMAIN_ID=7, client default (unset)"
  docker run -d --name act-srv-$D --ulimit core=0 --cpus=0.7 -e ROS_DOMAIN_ID=7 -v /tmp/en-action:/w $IMG \
    bash /w/repro.sh xsrv >/dev/null
  for i in $(seq 1 60); do docker logs act-srv-$D 2>&1 | grep -q SERVER_READY && break; sleep 1; done
  docker logs act-srv-$D 2>&1 | grep -o 'SERVER_READY.*'
  docker run --rm --name act-cli-$D --ulimit core=0 --cpus=0.7 -v /tmp/en-action:/w $IMG bash /w/repro.sh xcli 15
  echo; echo "##### X2 same server container, client container with ROS_DOMAIN_ID=7"
  docker run --rm --name act-cli-$D --ulimit core=0 --cpus=0.7 -e ROS_DOMAIN_ID=7 -v /tmp/en-action:/w $IMG bash /w/repro.sh xcli 30
  docker rm -f act-srv-$D >/dev/null
  echo "=== host part done $D"
  exit 0
fi

source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1
sub() { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.2f", a-b}'; }
inst() { (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$ROS_DISTRO-example-interfaces) >/tmp/apt.log 2>&1 || tail -5 /tmp/apt.log; source /opt/ros/$ROS_DISTRO/setup.bash; }
if [ "$MODE" = xsrv ]; then inst; exec python3 /w/srv.py /fibonacci ok; fi
if [ "$MODE" = xcli ]; then
  inst
  echo "client container ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-unset}"
  s=$(date +%s.%N); echo "\$ timeout $2 ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci '{order: 3}'"
  timeout $2 ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci '{order: 3}' 2>&1 | head -12
  echo "rc=${PIPESTATUS[0]} elapsed=$(sub $(date +%s.%N) $s)s"
  echo '$ ros2 action list -t'; timeout 20 ros2 action list -t; echo "rc=$?"
  exit 0
fi
echo "=== distro=$ROS_DISTRO"
date -u +%FT%TZ
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclcpp-action \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2action ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-fastrtps ros-$ROS_DISTRO-fastdds ros-$ROS_DISTRO-example-interfaces \
  ros-$ROS_DISTRO-action-msgs ros-$ROS_DISTRO-action-tutorials-interfaces 2>/dev/null
echo "--- default RMW"
python3 -c "from rclpy.utilities import get_rmw_implementation_identifier as g; print(g())"
echo "--- action types in the image"
ros2 interface list -a 2>&1
echo "##### C-1 send_goal with a type whose package is not installed (example_interfaces is not in ros-base)"
s=$(date +%s.%N); timeout 20 ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 5}" 2>&1 | head; echo "rc=${PIPESTATUS[0]} elapsed=$(sub $(date +%s.%N) $s)s"
echo "--- installing ros-$ROS_DISTRO-example-interfaces"
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$ROS_DISTRO-example-interfaces) >/tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-example-interfaces
source /opt/ros/$ROS_DISTRO/setup.bash
ros2 interface list -a 2>&1

cat > /w/srv.py <<'PYEOF'
#!/usr/bin/env python3
# usage: srv.py <action_name> <ok|slow|reject|abort|nospin> [--ros-args ...]
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from example_interfaces.action import Fibonacci
rclpy.init(args=sys.argv)
a = rclpy.utilities.remove_ros_args(sys.argv)
name, mode = a[1], a[2]
n = Node('act_server')
log = n.get_logger()
step = 1.0 if mode == 'slow' else 0.1


def goal_cb(req):
    log.info(f'goal request order={req.order} mode={mode}')
    return GoalResponse.REJECT if mode == 'reject' else GoalResponse.ACCEPT


def cancel_cb(gh):
    log.info('cancel request received, accepting')
    return CancelResponse.ACCEPT


def execute(gh):
    seq = [0, 1]
    r = Fibonacci.Result()
    if mode == 'abort':
        gh.abort()
        log.info('goal aborted')
        r.sequence = seq
        return r
    fb = Fibonacci.Feedback()
    for i in range(1, gh.request.order):
        if gh.is_cancel_requested:
            gh.canceled()
            log.info(f'goal canceled at step {i}')
            r.sequence = seq
            return r
        seq.append(seq[i] + seq[i - 1])
        fb.sequence = seq
        gh.publish_feedback(fb)
        time.sleep(step)
    gh.succeed()
    log.info('goal succeeded')
    r.sequence = seq
    return r


s = ActionServer(n, Fibonacci, name, execute, goal_callback=goal_cb, cancel_callback=cancel_cb,
                 callback_group=ReentrantCallbackGroup())
log.info(f'SERVER_READY name={name} ns={n.get_namespace()} mode={mode} t={time.time():.3f}')
if mode == 'nospin':
    while True:
        time.sleep(1)
ex = MultiThreadedExecutor()
ex.add_node(n)
try:
    ex.spin()
except (KeyboardInterrupt, Exception) as e:
    print(f'server exit: {type(e).__name__}', flush=True)
PYEOF
cat > /w/cli.py <<'PYEOF'
#!/usr/bin/env python3
# usage: cli.py <action_name> <mode> [timeout_s] [order] [--ros-args ...]
# modes: wait nospin full cancel killed cb_async_single cb_block_single cb_sync_single
#        cb_sync_multi_default cb_sync_multi_reentrant cb_sync_multi_separate
import os, sys, time, threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup
from example_interfaces.action import Fibonacci
from action_msgs.msg import GoalStatus
T0 = time.monotonic()
rclpy.init(args=sys.argv)
a = rclpy.utilities.remove_ros_args(sys.argv)
name, mode = a[1], a[2]
to = float(a[3]) if len(a) > 3 else 5.0
order = int(a[4]) if len(a) > 4 else 5
STATUS = {getattr(GoalStatus, k): k[7:] for k in dir(GoalStatus) if k.startswith('STATUS_')}


def el():
    return f'{time.monotonic() - T0:.2f}s'


def P(msg):
    print(f'[{mode} +{el()}] {msg}', flush=True)


def goal_msg():
    g = Fibonacci.Goal()
    g.order = order
    return g


if mode in ('wait', 'nospin', 'full', 'cancel', 'killed'):
    node = Node('act_client')
    ac = ActionClient(node, Fibonacci, name)
    t = time.monotonic()
    ok = ac.wait_for_server(timeout_sec=to)
    P(f'wait_for_server(timeout_sec={to}) returned {ok} after {time.monotonic() - t:.2f}s')
    if mode == 'wait' or not ok:
        sys.exit(0 if ok else 1)
    print(f'SERVER_SEEN t={time.time():.3f}', flush=True)
    gf = ac.send_goal_async(goal_msg())
    if mode == 'nospin':
        time.sleep(to)
        P(f'no spin: send_goal_async future done={gf.done()} after {to}s of sleep')
        rclpy.spin_until_future_complete(node, gf, timeout_sec=to)
        P(f'after spin_until_future_complete: done={gf.done()} accepted={gf.result().accepted if gf.done() else None}')
        sys.exit(0)
    rclpy.spin_until_future_complete(node, gf, timeout_sec=to)
    if not gf.done():
        P(f'goal response not received within {to}s')
        sys.exit(2)
    gh = gf.result()
    P(f'goal accepted={gh.accepted}')
    if not gh.accepted:
        sys.exit(3)
    print(f'GOAL_ACCEPTED t={time.time():.3f}', flush=True)
    rf = gh.get_result_async()
    if mode == 'cancel':
        rclpy.spin_until_future_complete(node, rf, timeout_sec=1.5)
        cf = gh.cancel_goal_async()
        rclpy.spin_until_future_complete(node, cf, timeout_sec=to)
        if cf.done():
            r = cf.result()
            P(f'cancel response return_code={r.return_code} goals_canceling={len(r.goals_canceling)}')
        else:
            P('cancel response not received')
    if mode == 'killed':
        deadline = time.monotonic() + to
        last = None
        while not rf.done() and time.monotonic() < deadline:
            rclpy.spin_until_future_complete(node, rf, timeout_sec=1.0)
            r = ac.server_is_ready()
            if r != last:
                P(f'server_is_ready()={r} result done={rf.done()}')
                last = r
        P(f'result done={rf.done()} after {to}s budget' if not rf.done() else 'result arrived')
        if not rf.done():
            sys.exit(4)
    rclpy.spin_until_future_complete(node, rf, timeout_sec=to)
    if not rf.done():
        P(f'result not received within {to}s')
        sys.exit(4)
    res = rf.result()
    P(f'result status={STATUS.get(res.status, res.status)} sequence={list(res.result.sequence)}')
    sys.exit(0)

# --- callback modes: executor runs in a daemon thread, main thread is the watchdog
done = threading.Event()
node = Node('act_client_cb')
if mode in ('cb_sync_multi_reentrant',):
    g = ReentrantCallbackGroup()
    cg_client, cg_timer = g, g
elif mode == 'cb_sync_multi_separate':
    cg_client, cg_timer = MutuallyExclusiveCallbackGroup(), MutuallyExclusiveCallbackGroup()
else:
    cg_client = cg_timer = None  # node default group (mutually exclusive)
ac = ActionClient(node, Fibonacci, name, callback_group=cg_client)
if not ac.wait_for_server(timeout_sec=5.0):
    P('server not found')
    sys.exit(1)
fired = [False]


def timer_cb():
    if fired[0]:
        return
    fired[0] = True
    P('timer callback started, sending goal')
    if mode == 'cb_async_single':
        def on_result(f):
            r = f.result()
            P(f'result callback: status={STATUS.get(r.status, r.status)} sequence={list(r.result.sequence)}')
            done.set()

        def on_goal(f):
            gh = f.result()
            P(f'goal response callback: accepted={gh.accepted}')
            gh.get_result_async().add_done_callback(on_result)
        ac.send_goal_async(goal_msg()).add_done_callback(on_goal)
        P('timer callback returned')
        return
    if mode == 'cb_block_single':
        gf = ac.send_goal_async(goal_msg())
        t = time.monotonic()
        while not gf.done() and time.monotonic() - t < 8:
            time.sleep(0.01)
        P(f'busy-wait on send_goal_async future in callback: done={gf.done()} after {time.monotonic() - t:.2f}s')
        if gf.done():
            rf = gf.result().get_result_async()
            t = time.monotonic()
            while not rf.done() and time.monotonic() - t < 8:
                time.sleep(0.01)
            P(f'busy-wait on get_result_async future in callback: done={rf.done()}')
            if rf.done():
                done.set()
        return
    # cb_sync_*: blocking ActionClient.send_goal() (waits for goal response and result)
    r = ac.send_goal(goal_msg())
    P(f'send_goal() returned: status={STATUS.get(r.status, r.status)} sequence={list(r.result.sequence)}')
    done.set()


node.create_timer(0.5, timer_cb, callback_group=cg_timer)
ex = SingleThreadedExecutor() if 'single' in mode else MultiThreadedExecutor(num_threads=4)
ex.add_node(node)
threading.Thread(target=ex.spin, daemon=True).start()
if done.wait(to):
    P('OK: result received')
    code = 0
else:
    P(f'DEADLOCK/TIMEOUT: no result after {to}s (watchdog)')
    code = 5
sys.stdout.flush()
os._exit(code)
PYEOF
SRV="python3 /w/srv.py"; CLI="python3 /w/cli.py"
F=example_interfaces/action/Fibonacci
SP=""
startsrv() { "$@" >/tmp/srv.log 2>&1 & SP=$!; sleep 3; echo "[server] $(grep -o 'SERVER_READY.*' /tmp/srv.log)"; }
stopsrv() { [ -n "$SP" ] && kill -TERM $SP 2>/dev/null; sleep 1; pkill -9 -f '/w/srv.py'; [ -n "$SP" ] && wait $SP 2>/dev/null; SP=""; }
# goal <name> <type> <bound_s> [args...]
goal() {
  local n=$1 t=$2 b=$3; shift 3
  local s=$(date +%s.%N)
  echo "\$ timeout $b ros2 action send_goal $n $t $*"
  timeout $b ros2 action send_goal $n $t "$@" 2>&1 | head -25
  local rc=${PIPESTATUS[0]}
  echo "rc=$rc elapsed=$(sub $(date +%s.%N) $s)s"
}
show() {
  echo "\$ ros2 action list -t"; timeout 20 ros2 action list -t 2>&1; echo "rc=$?"
  echo "\$ ros2 action info $1 -t"; timeout 20 ros2 action info $1 -t 2>&1; echo "rc=$?"
  if [ -n "$2" ]; then echo "\$ ros2 node info $2 (Action part)"; timeout 20 ros2 node info $2 2>&1 | sed -n '/Action Servers/,$p'; fi
}
case_hdr() { echo; echo "##### $*"; ros2 daemon stop >/dev/null 2>&1; uptime; }

echo "--- ros2 action send_goal -h"
ros2 action send_goal -h 2>&1 | sed -n '/options:/,$p'
HAS_TO=0; ros2 action send_goal -h 2>&1 | grep -q -- '--timeout' && HAS_TO=1
echo "send_goal --timeout option present: $HAS_TO"

case_hdr "C0 baseline: server /fibonacci, correct name and type"
startsrv $SRV /fibonacci ok
show /fibonacci /act_server
goal /fibonacci $F 20 "{order: 5}"
echo "--- with --feedback"
goal /fibonacci $F 20 "{order: 3}" --feedback
stopsrv

case_hdr "C1 no server at all (bounded 60s)"
show /fibonacci
goal /fibonacci $F 60 "{order: 5}"
echo "lines printed in a 10s run:"; timeout 10 ros2 action send_goal /fibonacci $F "{order: 5}" 2>&1 | grep -c "Waiting for an action server"
echo "--- Ctrl-C (SIGINT after 5s)"
timeout --preserve-status -s INT 5 ros2 action send_goal /fibonacci $F "{order: 5}" 2>&1 | tail -6; echo "rc=${PIPESTATUS[0]} (exit code of ros2 itself)"
if [ $HAS_TO = 1 ]; then echo "--- --timeout 3"; goal /fibonacci $F 30 "{order: 5}" --timeout 3; fi
echo "--- rclpy wait_for_server with different timeouts"
for t in 0 0.5 2 5; do $CLI /fibonacci wait $t; done

case_hdr "C2 wrong name: server /fibonacci_as, client /fibonacci"
startsrv $SRV /fibonacci_as ok
show /fibonacci /act_server
goal /fibonacci $F 10 "{order: 5}"
$CLI /fibonacci wait 3
stopsrv

case_hdr "C3 namespace: server in /robot1 with relative name 'fibonacci', client /fibonacci"
startsrv $SRV fibonacci ok --ros-args -r __ns:=/robot1
show /fibonacci /robot1/act_server
goal /fibonacci $F 10 "{order: 5}"
goal /robot1/fibonacci $F 20 "{order: 5}"
echo "--- rclpy client in /robot1, relative name 'fibonacci'"
$CLI fibonacci wait 3 --ros-args -r __ns:=/robot1
echo "--- rclpy client in /robot1, absolute name '/fibonacci'"
$CLI /fibonacci wait 3 --ros-args -r __ns:=/robot1
stopsrv
case_hdr "C3b remap: server run with -r fibonacci:=fib2"
startsrv $SRV fibonacci ok --ros-args -r fibonacci:=fib2
timeout 20 ros2 action list -t
goal /fibonacci $F 10 "{order: 5}"
stopsrv

case_hdr "C4 wrong type: server Fibonacci on /fibonacci, client sends another existing action type"
startsrv $SRV /fibonacci ok
show /fibonacci
goal /fibonacci tf2_msgs/action/LookupTransform 15 "{target_frame: a, source_frame: b}"
echo "--- misspelled type"
goal /fibonacci example_interfaces/action/Fibonaci 15 "{order: 5}"
echo "--- type written without /action/"
goal /fibonacci example_interfaces/Fibonacci 15 "{order: 5}"
echo "--- bad goal YAML (field that does not exist)"
goal /fibonacci $F 15 "{orders: 5}"
stopsrv

case_hdr "C5 different ROS_DOMAIN_ID in the same container: server 7, client default"
startsrv env ROS_DOMAIN_ID=7 $SRV /fibonacci ok
show /fibonacci
goal /fibonacci $F 10 "{order: 5}"
echo "--- client ROS_DOMAIN_ID=7"
export ROS_DOMAIN_ID=7; ros2 daemon stop >/dev/null 2>&1; goal /fibonacci $F 20 "{order: 5}"; ros2 daemon stop >/dev/null 2>&1; unset ROS_DOMAIN_ID
stopsrv

case_hdr "C6 server created but its node never spins"
startsrv $SRV /fibonacci nospin
show /fibonacci /act_server
goal /fibonacci $F 15 "{order: 5}"
$CLI /fibonacci wait 3
$CLI /fibonacci full 5
stopsrv

case_hdr "C7 server rejects the goal"
startsrv $SRV /fibonacci reject
goal /fibonacci $F 15 "{order: 5}"
$CLI /fibonacci full 5
stopsrv

case_hdr "C7b server aborts the goal"
startsrv $SRV /fibonacci abort
goal /fibonacci $F 15 "{order: 5}"
$CLI /fibonacci full 5
stopsrv

case_hdr "C8 goal canceled"
startsrv $SRV /fibonacci slow
echo "--- CLI, SIGINT 3s into a 10-step goal"
s=$(date +%s.%N)
timeout --preserve-status -s INT 3 ros2 action send_goal /fibonacci $F "{order: 10}" 2>&1 | tail -8; echo "rc=${PIPESTATUS[0]} elapsed=$(sub $(date +%s.%N) $s)s"
sleep 1; echo "[server log tail]"; tail -4 /tmp/srv.log
echo "--- rclpy cancel_goal_async after 1.5s"
$CLI /fibonacci cancel 5 10
stopsrv

case_hdr "C9 server killed (SIGKILL) mid-goal"
startsrv $SRV /fibonacci slow
echo "--- CLI, server killed 3s into a 30-step goal, CLI bounded at 40s"
( sleep 3; pkill -9 -f '/w/srv.py' ) &
goal /fibonacci $F 40 "{order: 30}"
wait; SP=""
if [ $HAS_TO = 1 ]; then
  startsrv $SRV /fibonacci slow
  echo "--- same with --timeout 5"
  ( sleep 3; pkill -9 -f '/w/srv.py' ) &
  goal /fibonacci $F 40 "{order: 30}" --timeout 5
  wait; SP=""
fi
startsrv $SRV /fibonacci slow
echo "--- rclpy client, server killed 3s after start of goal"
( sleep 3; pkill -9 -f '/w/srv.py' ) &
$CLI /fibonacci killed 25 30
wait; SP=""
echo "--- ros2 action list right after the kill"
timeout 20 ros2 action list -t; ros2 daemon stop >/dev/null 2>&1; timeout 20 ros2 action list -t; echo "(second list after daemon stop)"
case_hdr "C9b server stopped cleanly (SIGTERM) mid-goal"
startsrv $SRV /fibonacci slow
( sleep 3; kill -TERM $SP ) &
$CLI /fibonacci killed 25 30
wait; stopsrv

case_hdr "C10 rclpy: send_goal_async without spinning"
startsrv $SRV /fibonacci ok
$CLI /fibonacci nospin 5
echo "--- with spin_until_future_complete (the fix)"
$CLI /fibonacci full 5
stopsrv

case_hdr "C11 rclpy: goal and result inside callbacks"
startsrv $SRV /fibonacci ok
for m in cb_async_single cb_block_single cb_sync_single cb_sync_multi_default cb_sync_multi_reentrant cb_sync_multi_separate; do
  echo "--- $m"; timeout 30 $CLI /fibonacci $m 10; echo "rc=$?"
done
stopsrv

case_hdr "C12 discovery: server and client started at the same moment (5 runs each)"
for i in 1 2 3 4 5; do
  ros2 daemon stop >/dev/null 2>&1
  T0=$(date +%s.%N)
  $SRV /fibonacci ok >/tmp/srv.log 2>&1 & SP=$!
  timeout 30 ros2 action send_goal /fibonacci $F "{order: 3}" 2>&1 | while IFS= read -r l; do echo "$(date +%s.%N) $l"; done >/tmp/cli.ts
  TA=$(grep -m1 'Goal accepted' /tmp/cli.ts | cut -d' ' -f1); TW=$(grep -c 'Waiting for an action server' /tmp/cli.ts)
  TR=$(grep -o 'SERVER_READY.* t=[0-9.]*' /tmp/srv.log | grep -o 't=[0-9.]*$' | cut -d= -f2)
  echo "cli run$i: start -> Goal accepted $( [ -n "$TA" ] && sub $TA $T0 || echo none)s ; server ready at $( [ -n "$TR" ] && sub $TR $T0 || echo none)s ; waiting lines=$TW"
  stopsrv
done
for i in 1 2 3 4 5; do
  T0=$(date +%s.%N)
  $SRV /fibonacci ok >/tmp/srv.log 2>&1 & SP=$!
  $CLI /fibonacci full 10 >/tmp/c.out 2>&1
  TA=$(grep -o 'GOAL_ACCEPTED t=[0-9.]*' /tmp/c.out | cut -d= -f2); TS=$(grep -o 'SERVER_SEEN t=[0-9.]*' /tmp/c.out | cut -d= -f2)
  echo "rclpy run$i: start -> server seen $( [ -n "$TS" ] && sub $TS $T0 || echo none)s -> goal accepted $( [ -n "$TA" ] && sub $TA $T0 || echo none)s"
  stopsrv
done
echo "--- against a server already running for 3s (3 runs)"
startsrv $SRV /fibonacci ok
for i in 1 2 3; do
  T0=$(date +%s.%N)
  timeout 30 ros2 action send_goal /fibonacci $F "{order: 3}" 2>&1 | while IFS= read -r l; do echo "$(date +%s.%N) $l"; done >/tmp/cli.ts
  TA=$(grep -m1 'Goal accepted' /tmp/cli.ts | cut -d' ' -f1); TE=$(tail -1 /tmp/cli.ts | cut -d' ' -f1)
  echo "cli run$i: start -> Goal accepted $( [ -n "$TA" ] && sub $TA $T0 || echo none)s ; total $(sub $TE $T0)s ; waiting lines=$(grep -c 'Waiting for an action server' /tmp/cli.ts)"
done
stopsrv
uptime
echo "=== done $ROS_DISTRO"
