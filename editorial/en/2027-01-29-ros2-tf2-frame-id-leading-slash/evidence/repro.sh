#!/bin/bash
# Run inside ros:<distro>-ros-base (no network needed):
#   docker run --rm --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# (on the runner also: --pids-limit 512 --ulimit core=0; a limit of 30 killed DDS threads)
# Reproduces tf2 'Invalid argument "/map" passed to lookupTransform argument
# target_frame in tf2 frame_ids cannot start with a '/'' and the empty-frame
# variant: which calls raise it, what set_transform does with slashed names,
# where slashed frames come from (static_transform_publisher, /tf publishers,
# robot_state_publisher frame_prefix), how long a lookup with a timeout takes
# to fail, and which fixes work.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros \
  ros-$ROS_DISTRO-tf2-ros-py ros-$ROS_DISTRO-robot-state-publisher 2>/dev/null
echo "--- frame-id validation strings in libtf2.so"
strings /opt/ros/$ROS_DISTRO/lib/libtf2.so | grep -E "cannot start with|cannot be empty|TF_NO_FRAME_ID|TF_NO_CHILD_FRAME_ID|TF_SELF_TRANSFORM" | sort -u
mkdir -p /t && cd /t

# ---------- Part 1: tf2_ros.Buffer directly, no DDS ----------
cat > direct.py <<'X'
import sys, time
from tf2_ros import Buffer
from rclpy.time import Time
from rclpy.duration import Duration
from geometry_msgs.msg import TransformStamped
def tf(parent, child, x=1.0):
    m = TransformStamped()
    m.header.frame_id = parent; m.child_frame_id = child
    m.header.stamp.sec = 100
    m.transform.translation.x = x
    m.transform.rotation.w = 1.0
    return m
def first(e):
    return str(e).splitlines()[0][:200] if str(e) else ''
def look(b, target, source):
    try:
        t = b.lookup_transform(target, source, Time())
        return 'OK x=%s frames=(%s -> %s)' % (t.transform.translation.x, t.header.frame_id, t.child_frame_id)
    except Exception as e:
        return 'FAIL %s.%s: %s' % (type(e).__module__, type(e).__name__, first(e))
def setcase(name, parent, child):
    b = Buffer()
    sys.stderr.flush()
    try:
        r = b.set_transform(tf(parent, child), 'direct_test')
    except Exception as e:
        r = 'EXC %s: %s' % (type(e).__name__, first(e))
    sys.stderr.flush()
    frames = b.all_frames_as_string().strip().replace('\n', ' | ')
    print('SET %-22s parent=%r child=%r set_transform=%s' % (name, parent, child, r), flush=True)
    print('    frames: %s' % (frames or '(none)'), flush=True)
    for tgt, src in (('map', 'base_link'), ('/map', 'base_link'), ('map', '/base_link')):
        print('    lookup(%r, %r): %s' % (tgt, src, look(b, tgt, src)), flush=True)
    return b
print('### part1a set_transform with different frame strings', flush=True)
setcase('plain', 'map', 'base_link')
setcase('slash_parent', '/map', 'base_link')
setcase('slash_child', 'map', '/base_link')
setcase('slash_both', '/map', '/base_link')
setcase('double_slash_parent', '//map', 'base_link')
setcase('trailing_slash', 'map/', 'base_link')
setcase('empty_parent', '', 'base_link')
setcase('empty_child', 'map', '')
setcase('same_frame', 'map', 'map')
setcase('space_parent', ' map', 'base_link')

print('### part1b lookups on a plain map->base_link buffer', flush=True)
b = Buffer()
b.set_transform(tf('map', 'base_link'), 'direct_test')
for tgt, src in (('/map', 'base_link'), ('map', '/base_link'), ('/map', '/base_link'), ('', 'base_link'),
                 ('map', ''), ('map/', 'base_link'), ('Map', 'base_link'), ('odom', 'base_link'),
                 ('robot1/map', 'base_link')):
    print('LOOKUP target=%r source=%r -> %s' % (tgt, src, look(b, tgt, src)), flush=True)
print('### part1c can_transform and its debug tuple', flush=True)
for tgt in ('map', '/map', '', 'odom'):
    try:
        r = b.can_transform(tgt, 'base_link', Time())
    except Exception as e:
        r = 'EXC %s: %s' % (type(e).__name__, first(e))
    try:
        d = b.can_transform(tgt, 'base_link', Time(), return_debug_tuple=True)
    except Exception as e:
        d = 'EXC %s: %s' % (type(e).__name__, first(e))
    print('CAN target=%r -> %r debug=%r' % (tgt, r, d), flush=True)
print('### part1d lookup_transform_full and exception class tree', flush=True)
try:
    b.lookup_transform_full('/map', Time(), 'base_link', Time(), 'map')
    print('FULL OK', flush=True)
except Exception as e:
    print('FULL FAIL %s: %s' % (type(e).__name__, first(e)), flush=True)
    print('MRO', [c.__name__ for c in type(e).__mro__], flush=True)
print('### part1e fix: strip the slash before calling tf2', flush=True)
def clean(f):
    return f.lstrip('/')
for f in ('/map', '//map', 'map', '/robot1/base_link'):
    print('CLEAN %r -> %r : %s' % (f, clean(f), look(b, clean(f), 'base_link')), flush=True)
X
echo "### part1 direct Buffer (stdout+stderr merged)"
timeout 60 python3 direct.py 2>&1

# ---------- Part 2: real /tf and /tf_static traffic ----------
cat > listen.py <<'X'
# usage: python3 listen.py SECONDS target source [target source ...]
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from tf2_ros import Buffer, TransformListener
args = rclpy.utilities.remove_ros_args(sys.argv)
secs = float(args[1]); pairs = list(zip(args[2::2], args[3::2]))
rclpy.init(args=sys.argv)
node = Node('tflisten')
buf = Buffer()
TransformListener(buf, node)
end = time.time() + secs
while time.time() < end:
    rclpy.spin_once(node, timeout_sec=0.1)
print('FRAMES', buf.all_frames_as_string().strip().replace('\n', ' | ') or '(none)', flush=True)
for tgt, src in pairs:
    try:
        t = buf.lookup_transform(tgt, src, Time())
        print(f'LOOKUP {tgt!r}->{src!r} OK x={t.transform.translation.x} hdr=({t.header.frame_id} -> {t.child_frame_id})', flush=True)
    except Exception as e:
        print(f'LOOKUP {tgt!r}->{src!r} FAIL', type(e).__name__, str(e).splitlines()[0][:160], flush=True)
node.destroy_node(); rclpy.shutdown()
X
cat > pub.py <<'X'
# usage: python3 pub.py PARENT CHILD N  (publishes N transforms on /tf at 20 Hz)
import sys, time
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
parent, child, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
rclpy.init()
node = Node('slash_pub')
pub = node.create_publisher(TFMessage, '/tf', 100)
end = time.time() + 10
while pub.get_subscription_count() == 0 and time.time() < end:
    time.sleep(0.05)
time.sleep(0.5)
for i in range(n):
    m = TransformStamped()
    m.header.frame_id = parent; m.child_frame_id = child
    m.header.stamp = node.get_clock().now().to_msg()
    m.transform.translation.x = 2.0
    m.transform.rotation.w = 1.0
    pub.publish(TFMessage(transforms=[m]))
    time.sleep(0.05)
print(f'PUB sent={n} parent={parent!r} child={child!r}', flush=True)
time.sleep(0.5)
node.destroy_node(); rclpy.shutdown()
X
cat > timing.py <<'X'
# lookup_transform with a timeout: does an invalid name fail at once or wait?
import sys, time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from tf2_ros import Buffer, TransformListener
rclpy.init()
node = Node('tftiming')
buf = Buffer()
TransformListener(buf, node, spin_thread=True)
time.sleep(2.0)
for tgt in ('map', '/map', 'nonexistent', ''):
    for i in range(3):
        t0 = time.monotonic()
        try:
            buf.lookup_transform(tgt, 'base_link', Time(), timeout=Duration(seconds=2.0))
            r = 'OK'
        except Exception as e:
            r = '%s: %s' % (type(e).__name__, str(e).splitlines()[0][:110])
        print('TIMING lookup(%r, timeout=2.0) run=%d elapsed=%.3fs -> %s' % (tgt, i, time.monotonic() - t0, r), flush=True)
    t0 = time.monotonic()
    try:
        r = buf.can_transform(tgt, 'base_link', Time(), timeout=Duration(seconds=2.0))
    except Exception as e:
        r = '%s: %s' % (type(e).__name__, str(e).splitlines()[0][:110])
    print('TIMING can_transform(%r, timeout=2.0) elapsed=%.3fs -> %r' % (tgt, time.monotonic() - t0, r), flush=True)
node.destroy_node(); rclpy.shutdown()
X
stp() {
  local name="$1"; shift
  echo "### case stp_$name (static_transform_publisher $*)"
  timeout 7 ros2 run tf2_ros static_transform_publisher "$@" > /t/stp_$name.log 2>&1 &
  local S=$!
  timeout 30 python3 listen.py 3.5 map base_link /map base_link > /t/stpl_$name.log 2>&1
  wait $S
  grep -v '^\s*$' /t/stp_$name.log | head -4 | sed 's/^/  stp: /'
  sed 's/^/  /' /t/stpl_$name.log
}
echo "=== uptime $(cat /proc/loadavg)"
stp new_slash_parent --x 1 --frame-id /map --child-frame-id base_link
stp new_slash_child  --x 1 --frame-id map --child-frame-id /base_link
stp old_slash_parent 1 0 0 0 0 0 /map base_link
stp new_plain        --x 1 --frame-id map --child-frame-id base_link

echo "### case py_pub_slash (python /tf publisher with '/odom' -> '/base_link')"
timeout 40 python3 listen.py 7 odom base_link /odom base_link > /t/pp.log 2>&1 &
L=$!; sleep 1.0
timeout 30 python3 pub.py /odom /base_link 40 > /t/pp.pub.log 2>&1
wait $L
sed 's/^/  /' /t/pp.log; sed 's/^/  pub: /' /t/pp.pub.log

echo "=== uptime $(cat /proc/loadavg)"
echo "### case cpp_tf2_echo_slash_target (tf2_echo /map base_link, publisher uses 'map')"
( timeout 6 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id map --child-frame-id base_link > /dev/null 2>&1 &
  timeout 5 ros2 run tf2_ros tf2_echo /map base_link > /t/echo1.log 2>&1; wait )
echo "  lines=$(wc -l < /t/echo1.log) invalid_arg_lines=$(grep -c 'cannot start with' /t/echo1.log) translation_lines=$(grep -c 'Translation' /t/echo1.log)"
grep -m2 -v '^\s*$' /t/echo1.log | sed 's/^/  raw: /'
echo "### case cpp_tf2_echo_plain_target (tf2_echo map base_link, publisher uses '/map')"
( timeout 6 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id /map --child-frame-id base_link > /dev/null 2>&1 &
  timeout 5 ros2 run tf2_ros tf2_echo map base_link > /t/echo2.log 2>&1; wait )
echo "  lines=$(wc -l < /t/echo2.log) invalid_arg_lines=$(grep -c 'cannot start with' /t/echo2.log) translation_lines=$(grep -c 'Translation' /t/echo2.log)"
grep -m3 -E 'Translation|Invalid|exist|cannot' /t/echo2.log | sed 's/^/  raw: /'
echo "### case cpp_tf2_echo_empty_target (tf2_echo '' base_link)"
( timeout 6 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id map --child-frame-id base_link > /dev/null 2>&1 &
  timeout 5 ros2 run tf2_ros tf2_echo '' base_link > /t/echo3.log 2>&1; wait )
echo "  lines=$(wc -l < /t/echo3.log)"
grep -m2 -v '^\s*$' /t/echo3.log | sed 's/^/  raw: /'

echo "### case wire_frame_id (what is actually on /tf_static when the publisher is given '/map')"
timeout 15 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id /map --child-frame-id /base_link > /dev/null 2>&1 &
S=$!; sleep 1.5
timeout 12 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable /tf_static tf2_msgs/msg/TFMessage 2>&1 | grep -E 'frame_id|rror' | sed 's/^/  echo: /'
kill $S 2>/dev/null; wait $S 2>/dev/null

echo "### case timing (static map->base_link running)"
timeout 30 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id map --child-frame-id base_link > /dev/null 2>&1 &
S=$!
timeout 60 python3 timing.py 2>&1 | sed 's/^/  /'
kill $S 2>/dev/null; wait $S 2>/dev/null

# ---------- Part 3: robot_state_publisher frame_prefix ----------
cat > r.urdf <<'X'
<robot name="r"><link name="base_link"/><link name="laser"/>
<joint name="j" type="fixed"><parent link="base_link"/><child link="laser"/><origin xyz="0.3 0 0.2"/></joint></robot>
X
rsp() {
  local name="$1" prefix="$2"; shift 2
  echo "### case rsp_$name (frame_prefix=$prefix)"
  local pp=(); [ -n "$prefix" ] && pp=(-p frame_prefix:="$prefix")
  timeout 16 ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat r.urdf)" "${pp[@]}" > /t/rsp_$name.log 2>&1 &
  local R=$!; sleep 1.0
  timeout 30 python3 listen.py 5 "$@" > /t/rspl_$name.log 2>&1
  timeout 8 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable /tf_static tf2_msgs/msg/TFMessage 2>&1 | grep -E 'frame_id|rror' | sed 's/^/  echo: /'
  wait $R
  grep -m2 -i -E 'error|warn|prefix' /t/rsp_$name.log | sed 's/^/  rsp: /'
  sed 's/^/  /' /t/rspl_$name.log
}
rsp ok_prefix   robot1/   robot1/base_link robot1/laser /robot1/base_link robot1/laser
rsp slash_prefix /robot1/ robot1/base_link robot1/laser /robot1/base_link robot1/laser
rsp no_prefix   ""        base_link laser
echo "=== uptime $(cat /proc/loadavg)"
echo "=== done"
