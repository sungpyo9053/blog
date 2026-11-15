#!/bin/bash
# Run inside ros:<distro>-ros-base (no network needed):
#   docker run --rm --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Reproduces tf2 "TF_DENORMALIZED_QUATERNION ... invalid quaternion in the transform"
# and "TF_NAN_INPUT ... nan value in the transform": which inputs trigger them,
# the normalization tolerance, which process prints them, what a lookup returns,
# and which fixes remove them.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros ros-$ROS_DISTRO-tf2-ros-py 2>/dev/null
echo "--- format strings in libtf2.so"
strings /opt/ros/$ROS_DISTRO/lib/libtf2.so | grep -E 'TF_NAN_INPUT|TF_DENORMALIZED' | sort -u
mkdir -p /t && cd /t

# ---------- Part 1: Buffer.set_transform() directly, no DDS ----------
cat > direct.py <<'X'
import math, sys
from tf2_ros import Buffer
from rclpy.time import Time
from geometry_msgs.msg import TransformStamped
nan = float('nan'); inf = float('inf')
def tf(q, t=(0.0, 0.0, 0.0), child='base_link'):
    m = TransformStamped()
    m.header.frame_id = 'odom'; m.child_frame_id = child
    m.header.stamp.sec = 100
    m.transform.translation.x, m.transform.translation.y, m.transform.translation.z = t
    r = m.transform.rotation
    if q is not None:
        r.x, r.y, r.z, r.w = q
    return m
def run(name, q, t=(0.0, 0.0, 0.0)):
    b = Buffer()
    m = tf(q, t)
    r = m.transform.rotation
    n2 = r.x*r.x + r.y*r.y + r.z*r.z + r.w*r.w
    sys.stderr.flush()
    try:
        ret = b.set_transform(m, 'direct_test')
    except Exception as e:
        ret = 'EXC %s %s' % (type(e).__name__, e)
    sys.stderr.flush()
    try:
        lr = b.lookup_transform('odom', 'base_link', Time()).transform.rotation
        res = 'LOOKUP_OK rot=(%.6f %.6f %.6f %.6f)' % (lr.x, lr.y, lr.z, lr.w)
    except Exception as e:
        res = 'LOOKUP_FAIL %s: %s' % (type(e).__name__, str(e).splitlines()[0][:120])
    print('CASE %-28s q=(%s) |q|^2-1=%+.6f set_transform=%s %s' % (name, ' '.join(repr(v) for v in (r.x, r.y, r.z, r.w)), n2 - 1, ret, res), flush=True)
s2 = math.sqrt(0.5)
run('default_rotation_unset', None)
run('identity_0001', (0.0, 0.0, 0.0, 1.0))
run('all_zero_0000', (0.0, 0.0, 0.0, 0.0))
run('yaw_in_z_w0', (0.0, 0.0, 1.57, 0.0))
run('yaw_in_z_w1', (0.0, 0.0, 1.57, 1.0))
run('rpy_deg_mistake_sum', (0.0, 0.0, 0.5, 0.5))
run('hand_4dp_0.7071', (0.0, 0.0, 0.7071, 0.7071))
run('hand_2dp_0.71', (0.0, 0.0, 0.71, 0.71))
run('hand_1dp_0.7', (0.0, 0.0, 0.7, 0.7))
run('negated_identity', (0.0, 0.0, 0.0, -1.0))
for d in (-0.05, -0.0101, -0.0099, -0.005, -0.001, 0.001, 0.005, 0.0099, 0.0101, 0.05):
    run('normsq_dev_%+.4f' % d, (0.0, 0.0, 0.0, math.sqrt(1 + d)))
run('nan_in_quat_w', (0.0, 0.0, 0.0, nan))
run('nan_in_quat_all', (nan, nan, nan, nan))
run('nan_in_translation', (0.0, 0.0, 0.0, 1.0), (nan, 0.0, 0.0))
run('inf_in_translation', (0.0, 0.0, 0.0, 1.0), (inf, 0.0, 0.0))
run('inf_in_quat', (0.0, 0.0, 0.0, inf))
run('nan_trans_and_zero_quat', (0.0, 0.0, 0.0, 0.0), (nan, 0.0, 0.0))
# fixes
def normalize(q):
    n = math.sqrt(sum(v*v for v in q))
    return tuple(v / n for v in q)
run('fix_normalized_0.7', normalize((0.0, 0.0, 0.7, 0.7)))
run('fix_normalized_yaw_in_z', normalize((0.0, 0.0, 1.57, 1.0)))
yaw = 1.57
run('fix_yaw_to_quat_formula', (0.0, 0.0, math.sin(yaw/2), math.cos(yaw/2)))
try:
    normalize((0.0, 0.0, 0.0, 0.0))
except Exception as e:
    print('NORMALIZE_ZERO', type(e).__name__, e, flush=True)
# stale good value survives bad updates
b = Buffer()
good = tf((0.0, 0.0, 0.0, 1.0), (1.0, 0.0, 0.0)); good.header.stamp.sec = 100
b.set_transform(good, 'direct_test')
bad = tf((0.0, 0.0, 0.0, 0.0), (2.0, 0.0, 0.0)); bad.header.stamp.sec = 101
b.set_transform(bad, 'direct_test')
t = b.lookup_transform('odom', 'base_link', Time())
print('STALE good@100 then zero-quat@101: lookup x=%s stamp=%d' % (t.transform.translation.x, t.header.stamp.sec), flush=True)
try:
    b.lookup_transform('odom', 'base_link', Time(seconds=101))
    print('STALE lookup at 101: OK', flush=True)
except Exception as e:
    print('STALE lookup at 101:', type(e).__name__, str(e).splitlines()[0][:160], flush=True)
X
echo "### part1 direct set_transform (stdout+stderr merged)"
timeout 60 python3 direct.py 2>&1

# ---------- Part 2: real /tf and /tf_static traffic ----------
cat > pub.py <<'X'
# usage: python3 pub.py tf|static N tx qx qy qz qw
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
topic, n = sys.argv[1], int(sys.argv[2])
tx, qx, qy, qz, qw = (float(v) for v in sys.argv[3:8])
rclpy.init()
node = Node('bad_tf_pub')
if topic == 'static':
    pub = node.create_publisher(TFMessage, '/tf_static', QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
else:
    pub = node.create_publisher(TFMessage, '/tf', 100)
end = time.time() + 10
while pub.get_subscription_count() == 0 and time.time() < end:
    time.sleep(0.05)
time.sleep(1.0)
for i in range(n):
    m = TransformStamped()
    m.header.frame_id = 'odom'; m.child_frame_id = 'base_link'
    m.header.stamp = node.get_clock().now().to_msg()
    m.transform.translation.x = tx
    m.transform.rotation.x, m.transform.rotation.y, m.transform.rotation.z, m.transform.rotation.w = qx, qy, qz, qw
    pub.publish(TFMessage(transforms=[m]))
    time.sleep(0.05)
print(f'PUB topic={topic} sent={n}', flush=True)
time.sleep(1.5 if topic == 'static' else 0.5)
node.destroy_node(); rclpy.shutdown()
X
cat > listen.py <<'X'
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
secs = float(sys.argv[1])
rclpy.init(args=sys.argv)
node = Node('tflisten')
buf = Buffer()
TransformListener(buf, node)
end = time.time() + secs
while time.time() < end:
    rclpy.spin_once(node, timeout_sec=0.1)
try:
    t = buf.lookup_transform('odom', 'base_link', Time())
    r = t.transform.rotation
    print(f'LOOKUP_OK x={t.transform.translation.x} rot=({r.x:.6f} {r.y:.6f} {r.z:.6f} {r.w:.6f})', flush=True)
except Exception as e:
    print('LOOKUP_FAIL', type(e).__name__, str(e).splitlines()[0][:160], flush=True)
node.destroy_node(); rclpy.shutdown()
X
count() {
  echo "  TF_NAN_INPUT lines: $(grep -c TF_NAN_INPUT "$1")  TF_DENORMALIZED_QUATERNION lines: $(grep -c TF_DENORMALIZED_QUATERNION "$1")"
  grep -m1 -E 'TF_NAN_INPUT|TF_DENORMALIZED' "$1" | sed 's/^/  first: /'
  grep -E 'LOOKUP|PUB |Translation|Could not|Invalid|exist' "$1" | sort | uniq -c | head -4 | sed 's/^/  /'
}
case_py() {
  local name="$1"; shift
  echo "### case $name (python listener, pub args: $*)"
  timeout 40 python3 listen.py 6 > /t/$name.log 2>&1 &
  local L=$!; sleep 1.5
  timeout 30 python3 pub.py "$@" > /t/$name.pub.log 2>&1
  wait $L
  count /t/$name.log
  echo "  publisher log: TF_ lines=$(grep -c TF_ /t/$name.pub.log) $(grep PUB /t/$name.pub.log)"
}
echo "=== uptime $(cat /proc/loadavg)"
case_py tf_identity        tf 40 1.0 0 0 0 1
case_py tf_zero_quat       tf 40 1.0 0 0 0 0
case_py tf_hand_0.7        tf 40 1.0 0 0 0.7 0.7
case_py tf_nan_translation tf 40 nan 0 0 0 1
case_py tf_nan_quat        tf 40 1.0 nan nan nan nan
case_py static_zero_quat   static 1 1.0 0 0 0 0
case_py tf_rate_100_zero   tf 100 1.0 0 0 0 0
echo "### case stderr_vs_stdout (zero quat)"
timeout 40 python3 listen.py 5 > /t/so.log 2> /t/se.log &
L=$!; sleep 1.5; timeout 30 python3 pub.py tf 20 1.0 0 0 0 0 > /dev/null 2>&1; wait $L
echo "  stdout: $(grep -c TF_DENORMALIZED /t/so.log)  stderr: $(grep -c TF_DENORMALIZED /t/se.log)"
echo "### case log_level_error (python listener --ros-args --log-level error)"
timeout 40 python3 listen.py 5 --ros-args --log-level error > /t/ll.log 2>&1 &
L=$!; sleep 1.5; timeout 30 python3 pub.py tf 20 1.0 0 0 0 0 > /dev/null 2>&1; wait $L
count /t/ll.log
echo "=== uptime $(cat /proc/loadavg)"
echo "### case cpp_tf2_echo (zero quat)"
( timeout 7 ros2 run tf2_ros tf2_echo odom base_link > /t/echo.log 2>&1 & E=$!; sleep 1.5; timeout 30 python3 pub.py tf 40 1.0 0 0 0 0 > /dev/null 2>&1; wait $E )
count /t/echo.log
grep -m2 -E 'Warning|Invalid|exist' /t/echo.log | sed 's/^/  raw: /'
echo "### case cpp_tf2_echo (nan translation)"
( timeout 7 ros2 run tf2_ros tf2_echo odom base_link > /t/echo2.log 2>&1 & E=$!; sleep 1.5; timeout 30 python3 pub.py tf 40 nan 0 0 0 1 > /dev/null 2>&1; wait $E )
count /t/echo2.log

echo "### case cpp_tf2_echo (unnormalized 0 0 1.57 1)"
( timeout 7 ros2 run tf2_ros tf2_echo odom base_link > /t/echo3.log 2>&1 & E=$!; sleep 1.5; timeout 30 python3 pub.py tf 40 1.0 0 0 1.57 1 > /dev/null 2>&1; wait $E )
count /t/echo3.log
grep -m1 -A1 'Rotation' /t/echo3.log | sed 's/^/  raw: /'

# ---------- Part 3: static_transform_publisher with unnormalized input ----------
stp() {
  local name="$1"; shift
  echo "### case stp_$name (static_transform_publisher $*)"
  timeout 6 ros2 run tf2_ros static_transform_publisher "$@" > /t/stp_$name.log 2>&1 &
  local S=$!
  timeout 30 python3 listen.py 3.5 > /t/stpl_$name.log 2>&1
  wait $S
  grep -v '^\s*$' /t/stp_$name.log | grep -v -i 'spinning\|^\[INFO\].*Translation\|Rotation:' | head -3 | sed 's/^/  stp: /'
  grep -i -E 'rotation|quaternion' /t/stp_$name.log | head -2 | sed 's/^/  stp: /'
  count /t/stpl_$name.log
}
stp qz1_qw1_new   --x 1 --qz 1 --qw 1 --frame-id odom --child-frame-id base_link
stp zero_quat_new --x 1 --qx 0 --qy 0 --qz 0 --qw 0 --frame-id odom --child-frame-id base_link
stp hand_0.7_new  --x 1 --qz 0.7 --qw 0.7 --frame-id odom --child-frame-id base_link
stp yaw_new       --x 1 --yaw 1.57 --frame-id odom --child-frame-id base_link
stp zero_quat_old 1 0 0 0 0 0 0 odom base_link
stp six_args_old  1 0 0 0 0 0 odom base_link
echo "=== uptime $(cat /proc/loadavg)"
echo "=== done"
