#!/bin/bash
# Runs inside ros:<distro>-ros-base as: bash /w/repro.sh <distro>
# Container: rmw_cyclonedds_cpp installed first, then network disconnected, ROS_DOMAIN_ID=88.
set +e
ulimit -c 0
DISTRO=$1
source /opt/ros/$DISTRO/setup.bash
export ROS_DOMAIN_ID=88
if [ "$DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export PYTHONUNBUFFERED=1
N=/w/n; mkdir -p $N; cd $N

cat > healthy.py <<'P'
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node('healthy'); n.declare_parameter('speed', 0.5)
rclpy.spin(n)
P
# teleop_twist_keyboard pattern: a loop that never spins
cat > nospin.py <<'P'
import time, rclpy
from rclpy.node import Node
rclpy.init()
n = Node('nospin'); n.declare_parameter('speed', 0.5)
pub = n.create_publisher(__import__('std_msgs.msg', fromlist=['Int32']).Int32, 'cnt', 10)
while True:
    time.sleep(0.1)
P
cat > nospin_fixed.py <<'P'
import time, threading, rclpy
from rclpy.node import Node
rclpy.init()
n = Node('nospin_fixed'); n.declare_parameter('speed', 0.5)
threading.Thread(target=rclpy.spin, args=(n,), daemon=True).start()
while True:
    time.sleep(0.1)
P
# a timer callback that blocks for 8 s, single-threaded executor
cat > blocked.py <<'P'
import time, rclpy
from rclpy.node import Node
rclpy.init()
n = Node('blocked'); n.declare_parameter('speed', 0.5)
n.create_timer(0.5, lambda: time.sleep(8.0))
rclpy.spin(n)
P
cat > blocked_fixed.py <<'P'
import time, rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
rclpy.init()
n = Node('blocked_fixed'); n.declare_parameter('speed', 0.5)
n.create_timer(0.5, lambda: time.sleep(8.0), callback_group=MutuallyExclusiveCallbackGroup())
ex = MultiThreadedExecutor(); ex.add_node(n); ex.spin()
P
# second node created inside the program but never added to an executor
cat > subnode.py <<'P'
import rclpy
from rclpy.node import Node
rclpy.init()
outer = Node('outer'); inner = Node('inner'); inner.declare_parameter('speed', 0.5)
rclpy.spin(outer)
P
cat > subnode_fixed.py <<'P'
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
rclpy.init()
outer = Node('outer_f'); inner = Node('inner_f'); inner.declare_parameter('speed', 0.5)
ex = SingleThreadedExecutor(); ex.add_node(outer); ex.add_node(inner); ex.spin()
P
cat > noservices.py <<'P'
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node('noservices', start_parameter_services=False); n.declare_parameter('speed', 0.5)
rclpy.spin(n)
P

t() { # timed command; SIGTERM after 30 s
  local s=$EPOCHREALTIME
  echo "\$ $*"
  timeout -k 5 30 "$@" 2>&1 | head -20
  local rc=${PIPESTATUS[0]}
  echo "[exit=$rc elapsed=$(awk -v a=$s -v b=$EPOCHREALTIME 'BEGIN{printf "%.2f", b-a}')s]"
}
stop() { # stop node processes, then restart the daemon so the next case starts clean
  for p in "$@"; do kill -TERM $p 2>/dev/null; done; sleep 1
  for p in "$@"; do kill -9 $p 2>/dev/null; wait $p 2>/dev/null; done
  ros2 daemon stop >/dev/null 2>&1; sleep 1; ros2 daemon start >/dev/null 2>&1; sleep 2
}
# press Ctrl+C on a command after N seconds, like a user at a terminal
cat > /w/n/ctrlc.py <<'P'
import signal, subprocess, sys, time
n = float(sys.argv[1]); t0 = time.time()
p = subprocess.Popen(sys.argv[2:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                     preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
try:
    out, _ = p.communicate(timeout=n)
    print(out, end=''); print(f'[finished by itself, exit={p.returncode} elapsed={time.time()-t0:.2f}s]')
except subprocess.TimeoutExpired:
    p.send_signal(signal.SIGINT)
    try:
        out, _ = p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill(); out, _ = p.communicate()
    print(out, end=''); print(f'[Ctrl+C sent at {n:.0f}s, exit={p.returncode} elapsed={time.time()-t0:.2f}s]')
P
c() { echo "\$ $* (Ctrl+C after 10 s)"; python3 /w/n/ctrlc.py 10 "$@" 2>&1 | head -20; }
run_case() { # name file
  echo; echo "########## CASE $1 ($2)"
  python3 $N/$2 > /tmp/$1.log 2>&1 &
  local pid=$!
  sleep 4
  t ros2 node list
  t ros2 param list /$1
  t ros2 param get /$1 speed
  ros2 service list | grep "^/$1/" | tr '\n' ' '; echo
  stop $pid
  echo "node log:"; head -5 /tmp/$1.log
}

if [ "$2" = extra ]; then
  # follow-up: both sides on rmw_cyclonedds_cpp, no fastrtps anywhere
  echo "===== EXTRA cyclonedds-only check on $DISTRO $(date -u +%FT%TZ)"
  ros2 daemon stop >/dev/null 2>&1
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ros2 daemon start; sleep 2
  python3 $N/healthy.py > /tmp/cy2.log 2>&1 & p1=$!; sleep 5
  t ros2 node list
  t ros2 param list /healthy
  t ros2 param list --no-daemon /healthy
  t ros2 service call /healthy/list_parameters rcl_interfaces/srv/ListParameters "{}"
  timeout 10 ros2 topic pub -r 5 /x std_msgs/msg/Int32 "{data: 7}" > /dev/null 2>&1 & 
  t timeout 8 ros2 topic echo --once /x
  stop $p1; echo "node log:"; head -5 /tmp/cy2.log
  echo "-- same with ROS_AUTOMATIC_DISCOVERY_RANGE unset (default SUBNET)"
  unset ROS_AUTOMATIC_DISCOVERY_RANGE; ros2 daemon stop >/dev/null 2>&1; ros2 daemon start; sleep 2
  python3 $N/healthy.py > /tmp/cy3.log 2>&1 & p1=$!; sleep 5
  t ros2 param list /healthy
  t ros2 param get /healthy speed
  stop $p1; ros2 daemon stop >/dev/null 2>&1
  echo "===== EXTRA done"; exit 0
fi
echo "===== distro $DISTRO  $(date -u +%FT%TZ)"
python3 -c 'from rclpy.utilities import get_rmw_implementation_identifier as g; import rclpy; rclpy.init(); print("default rmw:", g())'
echo "--- ros2 param list --help (timeout lines)"; ros2 param list --help | grep -i -A1 timeout
echo "--- ros2 param get --help (timeout lines)"; ros2 param get --help | grep -i -A1 timeout
P2=$(python3 -c 'import ros2param,os;print(os.path.dirname(ros2param.__file__))')
echo "--- timeouts and error string in ros2param source ($P2)"
grep -rn "timeout\|Exception while calling" $P2 --include=*.py | grep -v "^.*#" | head -30

ros2 daemon stop >/dev/null 2>&1; ros2 daemon start; sleep 2
echo "--- list.py call path"; grep -n "call_list_parameters\|wait_for\|spin_until\|future\|Exception while\|timeout" $P2/verb/list.py
echo "--- api call_list_parameters / call_get_parameters"; grep -n -A14 "^def call_list_parameters\|^def call_get_parameters" $P2/api/__init__.py | head -60
run_case healthy healthy.py
run_case nospin nospin.py
echo; echo "########## CASE nospin, Ctrl+C"
python3 $N/nospin.py > /dev/null 2>&1 & pid=$!; sleep 4
c ros2 param list /nospin
c ros2 param get /nospin speed
c ros2 param list
stop $pid
run_case nospin_fixed nospin_fixed.py
run_case blocked blocked.py
run_case blocked_fixed blocked_fixed.py
echo; echo "########## CASE subnode"
python3 $N/subnode.py > /tmp/sub.log 2>&1 & pid=$!; sleep 4
t ros2 node list; t ros2 param list /inner; t ros2 param list /outer; t ros2 param get /inner speed
stop $pid
echo; echo "########## CASE subnode_fixed"
python3 $N/subnode_fixed.py > /tmp/subf.log 2>&1 & pid=$!; sleep 4
t ros2 param list /inner_f; t ros2 param get /inner_f speed
stop $pid
run_case noservices noservices.py

echo; echo "########## CASE param list with no node name, nospin + healthy running"
python3 $N/healthy.py > /dev/null 2>&1 & p1=$!; python3 $N/nospin.py > /dev/null 2>&1 & p2=$!; sleep 4
t ros2 param list
stop $p1 $p2

echo; echo "########## CASE killed node, daemon still running"
python3 $N/healthy.py > /dev/null 2>&1 & p1=$!; sleep 4
t ros2 node list
kill -9 $p1; wait $p1 2>/dev/null; sleep 1
t ros2 node list
t ros2 param list /healthy
t ros2 param list --no-daemon /healthy

echo; echo "########## CASE rmw mismatch: node on cyclonedds, CLI on default"
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 2
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 $N/healthy.py > /tmp/cy.log 2>&1 & p1=$!; sleep 5
t ros2 node list
t ros2 param list /healthy
t ros2 param get /healthy speed
c ros2 param list /healthy
ros2 daemon stop >/dev/null 2>&1; RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 daemon start >/dev/null 2>&1; sleep 3
echo "-- CLI with RMW_IMPLEMENTATION=rmw_cyclonedds_cpp (daemon restarted with it)"
t env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 param list /healthy
t env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 param get /healthy speed
stop $p1; head -5 /tmp/cy.log
ros2 daemon stop >/dev/null 2>&1
echo "===== done $(date -u +%FT%TZ)"
