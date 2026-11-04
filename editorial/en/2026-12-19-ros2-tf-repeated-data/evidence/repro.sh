#!/bin/bash
# Run inside ros:<distro>-ros-base:
#   docker run --rm -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Reproduces tf2 "TF_REPEATED_DATA ignoring data with redundant timestamp" and
# "TF_OLD_DATA ignoring data from the past": which publisher patterns trigger
# them, which process prints them, which value wins, how often they print,
# and which fixes / log settings remove them.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros ros-$ROS_DISTRO-tf2-ros-py ros-$ROS_DISTRO-rmw-implementation 2>/dev/null
echo "--- format strings in libtf2.so"
strings /opt/ros/$ROS_DISTRO/lib/libtf2.so | grep -E 'TF_REPEATED_DATA|TF_OLD_DATA|TF_NAN|Authority|authority' | sort -u
mkdir -p /t && cd /t

cat > pub.py <<'X'
# usage: python3 pub.py MODE N X [CHILD]
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
from rosgraph_msgs.msg import Clock
mode, n, xval = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
child = sys.argv[4] if len(sys.argv) > 4 else 'base_link'
rclpy.init()
node = Node('tfpub_' + mode.replace('-', '_'))
if mode == 'static':
    pub = node.create_publisher(TFMessage, '/tf_static', QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
else:
    pub = node.create_publisher(TFMessage, '/tf', 100)
clk = node.create_publisher(Clock, '/clock', 10)
def msg(ns, x):
    t = TransformStamped()
    t.header.frame_id = 'odom'; t.child_frame_id = child
    t.header.stamp.sec = ns // 10**9; t.header.stamp.nanosec = ns % 10**9
    t.transform.translation.x = x; t.transform.rotation.w = 1.0
    return TFMessage(transforms=[t])
end = time.time() + 10
while pub.get_subscription_count() == 0 and time.time() < end:
    time.sleep(0.05)
time.sleep(1.0)
sent = 0; last = None; fixed = time.time_ns()
for i in range(n):
    now = time.time_ns()
    grid = now // 100_000_000 * 100_000_000   # stamp from a 10 Hz source
    if mode == 'once':
        pub.publish(msg(now, xval)); sent += 1
    elif mode == 'dup':                       # same message published twice
        pub.publish(msg(now, xval)); pub.publish(msg(now, xval)); sent += 2
    elif mode == 'diffval':                   # same stamp, new value
        pub.publish(msg(now, 1.0)); pub.publish(msg(now, 2.0)); sent += 2
    elif mode in ('grid', 'grid-dedupe'):     # 20 Hz loop stamped with a 10 Hz stamp
        if mode == 'grid-dedupe' and grid == last:
            time.sleep(0.05); continue
        pub.publish(msg(grid, xval)); sent += 1; last = grid
    elif mode == 'fixed':                     # constant stamp on /tf
        pub.publish(msg(fixed, xval)); sent += 1
    elif mode.startswith('old'):              # one fresh stamp, then oldN = N s in the past
        age = int(mode[3:])
        pub.publish(msg(now if i == 0 else now - age * 10**9, xval)); sent += 1
    elif mode == 'back':                      # 0.5 s older than the newest, inside the 10 s cache
        pub.publish(msg(now if i % 2 == 0 else now - 500_000_000, xval)); sent += 1
    elif mode == 'static':
        pub.publish(msg(fixed, xval)); sent += 1
    elif mode == 'simloop':                   # /clock from 1000 s, jumps back 20 s halfway (bag --loop, sim restart)
        sim = 1000 * 10**9 + (i if i < n // 2 else i - 400) * 50_000_000
        c = Clock(); c.clock.sec = sim // 10**9; c.clock.nanosec = sim % 10**9
        clk.publish(c); pub.publish(msg(sim, xval)); sent += 1
    time.sleep(0.05)
print(f'PUB mode={mode} x={xval} sent={sent}', flush=True)
time.sleep(0.5)
node.destroy_node(); rclpy.shutdown()
X

cat > listen.py <<'X'
# usage: python3 listen.py SECONDS [ros args]
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
secs = float(sys.argv[1])
rclpy.init(args=sys.argv)
node = Node('tflisten')
import os
from rclpy.duration import Duration
cache = float(os.environ.get('CACHE_S', '0'))
if os.environ.get('BUF_NODE'):
    buf = Buffer(node=node)
else:
    buf = Buffer(cache_time=Duration(seconds=cache)) if cache else Buffer()
TransformListener(buf, node)
end = time.time() + secs
while time.time() < end:
    rclpy.spin_once(node, timeout_sec=0.1)
try:
    t = buf.lookup_transform('odom', 'base_link', Time())
    print(f'LOOKUP_OK x={t.transform.translation.x} stamp={t.header.stamp.sec}.{t.header.stamp.nanosec:09d}', flush=True)
except Exception as e:
    print('LOOKUP_FAIL', type(e).__name__, e, flush=True)
node.destroy_node(); rclpy.shutdown()
X

count() {
  echo "  TF_REPEATED_DATA lines: $(grep -c TF_REPEATED_DATA "$1")  TF_OLD_DATA lines: $(grep -c TF_OLD_DATA "$1")"
  grep -m2 -E 'TF_REPEATED_DATA|TF_OLD_DATA' "$1" | sed 's/^/  first: /'
  grep -m2 -i 'jump' "$1" | sed 's/^/  jump: /'
  grep -E 'LOOKUP|PUB ' "$1" | sed 's/^/  /'
}
# case NAME LISTENER_EXTRA_ARGS -- PUB_ARGS [ ;; PUB_ARGS ]
case_run() {
  local name="$1" largs="$2"; shift 2
  echo "### case $name (listener args: ${largs:-none})"
  timeout 40 python3 listen.py 7 $largs > /t/$name.log 2>&1 &
  local L=$!
  sleep 1.5
  local pids=()
  local k=0
  for p in "$@"; do k=$((k+1)); timeout 30 python3 pub.py $p > /t/$name.pub$k.log 2>&1 & pids+=($!); done
  wait "${pids[@]}"; wait $L
  count /t/$name.log
  cat /t/$name.pub*.log | grep -E 'PUB |TF_' | sed 's/^/  pub: /'
}

echo "=== uptime $(cat /proc/loadavg)"
case_run baseline_once ""            "once 40 1.0"
case_run dup_same_msg_twice ""       "dup 40 1.0"
case_run diffval_same_stamp ""       "diffval 40 0"
case_run grid_20hz_10hz_stamp ""     "grid 40 1.0"
case_run fix_grid_dedupe ""          "grid-dedupe 40 1.0"
case_run two_publishers_grid ""      "grid 40 1.0" "grid 40 2.0"
case_run fixed_stamp_on_tf ""        "fixed 40 1.0"
case_run static_repeated ""          "static 40 1.0"
case_run old_9s ""                   "old9 40 1.0"
case_run old_11s ""                  "old11 40 1.0"
case_run old_20s ""                  "old20 40 1.0"
CACHE_S=30 case_run fix_old_20s_cache_30s ""  "old20 40 1.0"
grep -m2 -A1 TF_OLD_DATA /t/old_20s.log | sed 's/^/  raw: /'
case_run back_0_5s_in_cache ""       "back 40 1.0"
echo "=== uptime $(cat /proc/loadavg)"
case_run suppress_loglevel_error "--ros-args --log-level error"            "dup 40 1.0"
case_run suppress_loglevel_tflisten "--ros-args --log-level tflisten:=error" "dup 40 1.0"
case_run suppress_loglevel_tf2 "--ros-args --log-level tf2:=error"           "dup 40 1.0"
case_run suppress_loglevel_rcutils "--ros-args --log-level rcutils:=error"   "dup 40 1.0"
case_run suppress_loglevel_tf2_buffer "--ros-args --log-level tf2_buffer:=error" "dup 40 1.0"
case_run old_suppress_loglevel_error "--ros-args --log-level error"        "old20 40 1.0"
case_run old_suppress_loglevel_fatal "--ros-args --log-level fatal"        "old20 40 1.0"
echo "### case old_which_stream (listener stdout and stderr split)"
timeout 40 python3 listen.py 7 > /t/so.log 2> /t/se.log &
L=$!; sleep 1.5; timeout 30 python3 pub.py old20 40 1.0 > /dev/null 2>&1; wait $L
echo "  stdout TF_OLD_DATA: $(grep -c TF_OLD_DATA /t/so.log)  stderr TF_OLD_DATA: $(grep -c TF_OLD_DATA /t/se.log)"
echo "  console_bridge 'at line' lines on stderr: $(grep -c 'at line' /t/se.log)"
head -3 /t/se.log | sed 's/^/  stderr raw: /'


case_run simloop_py_buffer "--ros-args -p use_sim_time:=true"        "simloop 40 1.0"
BUF_NODE=1 case_run simloop_py_buffer_node "--ros-args -p use_sim_time:=true" "simloop 40 1.0"
echo "### case simloop_cpp_tf2_echo (use_sim_time)"
( timeout 8 ros2 run tf2_ros tf2_echo odom base_link --ros-args -p use_sim_time:=true > /t/echosim.log 2>&1 & E=$!; sleep 1.5; timeout 30 python3 pub.py simloop 40 1.0 > /t/echosim.pub.log 2>&1; wait $E )
count /t/echosim.log
echo "### case cpp_tf2_echo_listener (old20 publisher)"
( timeout 8 ros2 run tf2_ros tf2_echo odom base_link > /t/echo.log 2>&1 & E=$!; sleep 1.5; timeout 30 python3 pub.py old20 40 1.0 > /t/echo.pub.log 2>&1; wait $E )
count /t/echo.log
grep -m3 -E 'Translation|At time' /t/echo.log | sed 's/^/  /'

echo "### case publisher_side_output (does the publisher print it?)"
timeout 30 python3 pub.py old20 40 1.0 > /t/pubonly.log 2>&1 &
P=$!; timeout 40 python3 listen.py 5 > /dev/null 2>&1; wait $P
count /t/pubonly.log

echo "### case rate (120 old messages over ~6 s, one warning per message?)"
timeout 40 python3 listen.py 10 > /t/rate.log 2>&1 &
L=$!; sleep 1.5; timeout 30 python3 pub.py old20 120 1.0 > /t/rate.pub.log 2>&1; wait $L
count /t/rate.log; cat /t/rate.pub.log
echo "=== uptime $(cat /proc/loadavg)"
echo "=== done"
