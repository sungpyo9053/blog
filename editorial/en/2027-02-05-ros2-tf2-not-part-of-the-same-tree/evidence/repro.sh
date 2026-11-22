#!/bin/bash
# Run inside ros:<distro>-ros-base (no network needed):
#   docker run --rm --network none --pids-limit 512 --ulimit core=0 -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Reproduces tf2 "Could not find a connection between 'A' and 'B' because they
# are not part of the same tree. Tf has two or more unconnected trees." and
# measures its causes (missing link, base_footprint vs base_link, namespaced /tf,
# a static publisher with parent and child swapped, two parents for one frame),
# how it differs from "does not exist" and extrapolation errors, how long a
# lookup with a timeout takes to fail, and which fixes work.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros \
  ros-$ROS_DISTRO-tf2-ros-py ros-$ROS_DISTRO-tf2-tools 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"
echo "--- error strings in libtf2.so"
strings /opt/ros/$ROS_DISTRO/lib/libtf2.so | grep -E "same tree|unconnected|does not exist|connection between" | sort -u
mkdir -p /t && cd /t

# ---------- Part 1: tf2_ros.Buffer directly, no DDS ----------
cat > direct.py <<'X'
import time
from tf2_ros import Buffer
from rclpy.time import Time
from rclpy.duration import Duration
from geometry_msgs.msg import TransformStamped
def tf(parent, child, sec=100, x=1.0):
    m = TransformStamped()
    m.header.frame_id = parent; m.child_frame_id = child
    m.header.stamp.sec = sec
    m.transform.translation.x = x
    m.transform.rotation.w = 1.0
    return m
def look(b, target, source, t=None):
    try:
        r = b.lookup_transform(target, source, t if t is not None else Time())
        return 'OK x=%s' % r.transform.translation.x
    except Exception as e:
        return 'FAIL %s.%s: %s' % (type(e).__module__, type(e).__name__, ' '.join(str(e).split())[:260])
def build(name, dyn=(), stat=()):
    b = Buffer()
    for p, c, *rest in dyn:
        b.set_transform(tf(p, c, *rest), 'dyn')
    for p, c, *rest in stat:
        b.set_transform_static(tf(p, c, *rest), 'stat')
    print('BUILD %s dyn=%s static=%s' % (name, [(d[0], d[1]) for d in dyn], [(s[0], s[1]) for s in stat]), flush=True)
    print('  YAML', ' '.join(b.all_frames_as_yaml().split()) or '(none)', flush=True)
    return b
# A: the odometry link odom->base_link is missing
b = build('A_missing_link', dyn=[('map', 'odom')], stat=[('base_link', 'laser')])
for t, s in (('map', 'laser'), ('odom', 'base_link'), ('laser', 'map'), ('map', 'odom'), ('base_link', 'laser')):
    print('  A lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
print('  A can_transform(map, laser) =', b.can_transform('map', 'laser', Time()), flush=True)
print('  A debug tuple =', b.can_transform('map', 'laser', Time(), return_debug_tuple=True), flush=True)
# B: odometry publishes base_footprint, URDF starts at base_link
b = build('B_footprint_vs_link', dyn=[('odom', 'base_footprint')], stat=[('base_link', 'laser')])
for t, s in (('odom', 'laser'), ('odom', 'base_link'), ('odom', 'base_footprint')):
    print('  B lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
b.set_transform_static(tf('base_footprint', 'base_link', x=0.0), 'fix')
print('  B after static base_footprint->base_link: lookup(odom, laser):', look(b, 'odom', 'laser'), flush=True)
# C: neither frame exists vs one exists
b = build('C_exist', dyn=[('map', 'odom')])
for t, s in (('map', 'nowhere'), ('nowhere', 'odom'), ('foo', 'bar')):
    print('  C lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
# D: connected, but one link is old -> extrapolation, not the tree error
b = build('D_old_link', dyn=[('map', 'odom', 100), ('odom', 'base_link', 200)])
print('  D lookup(map, base_link, Time()):', look(b, 'map', 'base_link'), flush=True)
print('  D lookup(map, base_link, t=200):', look(b, 'map', 'base_link', Time(seconds=200)), flush=True)
# E: a link that stopped 30 s ago, while the rest of the tree keeps updating (cache_time=10 s)
b = Buffer()
for sec in range(100, 141):
    b.set_transform(tf('map', 'odom', sec), 'dyn')
for sec in range(100, 111):
    b.set_transform(tf('odom', 'base_link', sec), 'dyn')
print('BUILD E_stale_link map->odom stamps 100..140, odom->base_link stamps 100..110', flush=True)
print('  E lookup(map, base_link, Time()):', look(b, 'map', 'base_link'), flush=True)
print('  E lookup(map, base_link, t=140):', look(b, 'map', 'base_link', Time(seconds=140)), flush=True)
print('  E lookup(odom, base_link, Time()):', look(b, 'odom', 'base_link'), flush=True)
# F: two parents for base_link (odom from wheel odometry, map from a second source)
b = Buffer()
for sec in range(100, 111):
    b.set_transform(tf('map', 'odom', sec), 'dyn')
    b.set_transform(tf('odom', 'base_link', sec, 1.0), 'odometry')
    b.set_transform(tf('map', 'base_link', sec, 5.0), 'second_source')
print('BUILD F_two_parents each stamp: map->odom, odom->base_link x=1, map->base_link x=5', flush=True)
print('  YAML', ' '.join(b.all_frames_as_yaml().split()), flush=True)
for t, s in (('map', 'base_link'), ('odom', 'base_link'), ('map', 'odom')):
    print('  F lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
b2 = Buffer()
for sec in range(100, 111):
    b2.set_transform(tf('map', 'odom', sec), 'dyn')
    b2.set_transform(tf('map', 'base_link', sec, 5.0), 'second_source')
    b2.set_transform(tf('odom', 'base_link', sec, 1.0), 'odometry')
print('BUILD F2_two_parents same, but odom->base_link set last', flush=True)
for t, s in (('map', 'base_link'), ('odom', 'base_link')):
    print('  F2 lookup(%s, %s): %s' % (t, s, look(b2, t, s)), flush=True)
# G: static parent and child swapped: laser->base_link static while odom->base_link is dynamic
b = Buffer()
b.set_transform_static(tf('laser', 'base_link', x=0.3), 'swapped_static')
for sec in range(100, 111):
    b.set_transform(tf('odom', 'base_link', sec), 'odometry')
print('BUILD G_swapped_static laser->base_link static, then odom->base_link dynamic', flush=True)
print('  YAML', ' '.join(b.all_frames_as_yaml().split()), flush=True)
for t, s in (('odom', 'laser'), ('odom', 'base_link'), ('laser', 'base_link')):
    print('  G lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
b = Buffer()
for sec in range(100, 111):
    b.set_transform(tf('odom', 'base_link', sec), 'odometry')
b.set_transform_static(tf('laser', 'base_link', x=0.3), 'swapped_static')
print('BUILD G2_swapped_static odom->base_link dynamic first, then laser->base_link static', flush=True)
print('  YAML', ' '.join(b.all_frames_as_yaml().split()), flush=True)
for t, s in (('odom', 'laser'), ('odom', 'base_link'), ('laser', 'base_link')):
    print('  G2 lookup(%s, %s): %s' % (t, s, look(b, t, s)), flush=True)
# H: exception classes
import tf2_ros
b = build('H_classes', dyn=[('map', 'odom')], stat=[('base_link', 'laser')])
try:
    b.lookup_transform('map', 'laser', Time())
except Exception as e:
    print('  H MRO', [c.__module__ + '.' + c.__name__ for c in type(e).__mro__], flush=True)
    print('  H isinstance LookupException:', isinstance(e, tf2_ros.LookupException), 'ConnectivityException:', isinstance(e, tf2_ros.ConnectivityException), 'TransformException:', isinstance(e, tf2_ros.TransformException), flush=True)
X
echo "### part1 direct Buffer"
timeout 60 python3 direct.py 2>&1

# ---------- Part 2: real /tf and /tf_static traffic ----------
cat > odom.py <<'X'
# usage: python3 odom.py PARENT CHILD SECONDS [X] [ros args]  -- TransformBroadcaster at 20 Hz
import sys, time
import rclpy
from rclpy.node import Node
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
a = rclpy.utilities.remove_ros_args(sys.argv)
parent, child, secs = a[1], a[2], float(a[3])
xval = float(a[4]) if len(a) > 4 else 1.0
rclpy.init(args=sys.argv)
node = Node('fake_odom')
br = TransformBroadcaster(node)
end = time.time() + secs
while time.time() < end:
    m = TransformStamped()
    m.header.frame_id = parent; m.child_frame_id = child
    m.header.stamp = node.get_clock().now().to_msg()
    m.transform.translation.x = xval
    m.transform.rotation.w = 1.0
    br.sendTransform(m)
    time.sleep(0.05)
node.destroy_node(); rclpy.shutdown()
X
cat > listen.py <<'X'
# usage: python3 listen.py SECONDS target source [ros args] -- polls lookup every 0.1 s, counts outcomes
import sys, time, threading, collections
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
a = rclpy.utilities.remove_ros_args(sys.argv)
secs, tgt, src = float(a[1]), a[2], a[3]
rclpy.init(args=sys.argv)
node = Node('tflisten')
buf = Buffer()
tl = TransformListener(buf, node, spin_thread=True)
time.sleep(1.0)
c = collections.Counter(); first = {}
end = time.time() + secs
while time.time() < end:
    try:
        r = buf.lookup_transform(tgt, src, Time())
        k = 'OK x=%.2f' % r.transform.translation.x
    except Exception as e:
        k = '%s: %s' % (type(e).__name__, ' '.join(str(e).split())[:200])
    c[k] += 1
    time.sleep(0.1)
print('  FRAMES', ' '.join(buf.all_frames_as_yaml().split())[:600] or '(none)', flush=True)
for k, v in c.most_common():
    print('  RESULT %s->%s count=%d %s' % (tgt, src, v, k), flush=True)
del tl
node.destroy_node(); rclpy.shutdown()
X
cat > timing.py <<'X'
# how long lookup_transform / can_transform with timeout=2.0 take for each error kind
import time
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from tf2_ros import Buffer, TransformListener
rclpy.init()
node = Node('tftiming')
buf = Buffer()
tl = TransformListener(buf, node, spin_thread=True)
time.sleep(2.0)
for tgt, src in (('map', 'laser'), ('map', 'odom'), ('map', 'nowhere')):
    for i in range(3):
        t0 = time.monotonic()
        try:
            buf.lookup_transform(tgt, src, Time(), timeout=Duration(seconds=2.0))
            r = 'OK'
        except Exception as e:
            r = '%s: %s' % (type(e).__name__, ' '.join(str(e).split())[:150])
        print('  TIMING lookup(%s, %s, timeout=2.0) run=%d elapsed=%.3fs -> %s' % (tgt, src, i, time.monotonic() - t0, r), flush=True)
    t0 = time.monotonic()
    r = buf.can_transform(tgt, src, Time(), timeout=Duration(seconds=2.0))
    print('  TIMING can_transform(%s, %s, timeout=2.0) elapsed=%.3fs -> %r' % (tgt, src, time.monotonic() - t0, r), flush=True)
del tl
node.destroy_node(); rclpy.shutdown()
X
stp() { timeout "$1" ros2 run tf2_ros static_transform_publisher --x "$2" --frame-id "$3" --child-frame-id "$4" "${@:5}" > /dev/null 2>&1 & }
finish() { wait 2>/dev/null; }

echo "=== uptime $(cat /proc/loadavg)"
echo "### case R1 missing odom->base_link (statics map->odom, base_link->laser), lookup map->laser"
stp 9 0 map odom; stp 9 0.3 base_link laser
timeout 20 python3 listen.py 3 map laser; finish
echo "### case R1fix same plus fake_odom odom->base_link"
stp 9 0 map odom; stp 9 0.3 base_link laser
timeout 12 python3 odom.py odom base_link 7 &
timeout 20 python3 listen.py 3 map laser; finish

echo "### case R2 odom publishes base_footprint, URDF side has base_link->laser"
stp 9 0.3 base_link laser
timeout 12 python3 odom.py odom base_footprint 7 &
timeout 20 python3 listen.py 3 odom laser; finish
echo "### case R2fix add static base_footprint->base_link"
stp 9 0.3 base_link laser; stp 9 0 base_footprint base_link
timeout 12 python3 odom.py odom base_footprint 7 &
timeout 20 python3 listen.py 3 odom laser; finish

echo "=== uptime $(cat /proc/loadavg)"
echo "### case R3 namespaced robot: odom->base_link on /robot1/tf, statics on global /tf_static, listener global"
stp 9 0 map odom; stp 9 0.3 base_link laser
timeout 12 python3 odom.py odom base_link 7 --ros-args -r __ns:=/robot1 -r /tf:=tf -r /tf_static:=tf_static &
timeout 20 python3 listen.py 3 map laser; finish
echo "### case R3b listener remaps only /tf:=/robot1/tf"
stp 9 0 map odom; stp 9 0.3 base_link laser
timeout 12 python3 odom.py odom base_link 7 --ros-args -r __ns:=/robot1 -r /tf:=tf -r /tf_static:=tf_static &
timeout 20 python3 listen.py 3 map laser --ros-args -r /tf:=/robot1/tf; finish
echo "### case R3fix all robot publishers and the listener on /robot1/tf and /robot1/tf_static"
stp 9 0 map odom --ros-args -r /tf_static:=/robot1/tf_static; stp 9 0.3 base_link laser --ros-args -r /tf_static:=/robot1/tf_static
timeout 12 python3 odom.py odom base_link 7 --ros-args -r __ns:=/robot1 -r /tf:=tf -r /tf_static:=tf_static &
timeout 20 python3 listen.py 3 map laser --ros-args -r /tf:=/robot1/tf -r /tf_static:=/robot1/tf_static; finish
echo "### case R3cli ros2 topic list during R3"
stp 9 0 map odom
timeout 12 python3 odom.py odom base_link 7 --ros-args -r __ns:=/robot1 -r /tf:=tf -r /tf_static:=tf_static &
sleep 2; timeout 10 ros2 topic list --no-daemon --spin-time 3 > /t/tl.log 2>&1; echo "  topic list exit=$?"; sed 's/^/  topic: /' /t/tl.log; finish

echo "=== uptime $(cat /proc/loadavg)"
echo "### case R4 static publisher with parent and child swapped (laser->base_link) while odom->base_link is dynamic"
stp 9 0.3 laser base_link
timeout 12 python3 odom.py odom base_link 7 &
timeout 20 python3 listen.py 3 odom laser; finish
echo "### case R4b same, lookup odom->base_link"
stp 9 0.3 laser base_link
timeout 12 python3 odom.py odom base_link 7 &
timeout 20 python3 listen.py 3 odom base_link; finish

echo "### case R5 two dynamic parents for base_link (odom->base_link x=1 and map->base_link x=5), map->odom static x=0"
stp 9 0 map odom
timeout 12 python3 odom.py odom base_link 7 1.0 &
timeout 12 python3 odom.py map base_link 7 5.0 --ros-args -r __node:=second_source &
timeout 20 python3 listen.py 4 odom base_link; finish
echo "### case R5b same, lookup map->base_link"
stp 9 0 map odom
timeout 12 python3 odom.py odom base_link 7 1.0 &
timeout 12 python3 odom.py map base_link 7 5.0 --ros-args -r __node:=second_source &
timeout 20 python3 listen.py 4 map base_link; finish

echo "=== uptime $(cat /proc/loadavg)"
echo "### case R6 C++ tf2_echo map laser with the R1 tree"
stp 9 0 map odom; stp 9 0.3 base_link laser
timeout 5 ros2 run tf2_ros tf2_echo map laser > /t/echo1.log 2>&1; finish
echo "  lines=$(wc -l < /t/echo1.log) same_tree_lines=$(grep -c 'same tree' /t/echo1.log) translation_lines=$(grep -c 'Translation' /t/echo1.log)"
grep -m3 -v '^\s*$' /t/echo1.log | sed 's/^/  raw: /'
echo "### case R6b tf2_echo map nowhere"
stp 9 0 map odom
timeout 5 ros2 run tf2_ros tf2_echo map nowhere > /t/echo2.log 2>&1; finish
grep -m2 -v '^\s*$' /t/echo2.log | sed 's/^/  raw: /'
echo "### case R6c tf2_monitor with the R1 tree"
stp 16 0 map odom; stp 16 0.3 base_link laser
timeout 14 ros2 run tf2_ros tf2_monitor > /t/mon.log 2>&1; finish
grep -v '^\s*$' /t/mon.log | head -24 | sed 's/^/  mon: /'
echo "### case R6d view_frames available?"
ros2 pkg prefix tf2_tools 2>&1 | sed 's/^/  /'

echo "=== uptime $(cat /proc/loadavg)"
echo "### case R7 timing (R1 tree: map->odom and base_link->laser static)"
stp 25 0 map odom; stp 25 0.3 base_link laser
timeout 60 python3 timing.py 2>&1; finish
echo "=== done $ROS_DISTRO"
