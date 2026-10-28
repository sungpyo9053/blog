#!/bin/bash
# Run inside ros:<distro>-ros-base:
#   docker run --rm -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Measures QoS compatibility between an rclpy publisher and subscriber in separate
# processes on topic /x (std_msgs/Int32), plus ros2 topic echo/hz/info behavior.
source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1
echo "=== distro=$ROS_DISTRO rmw=${RMW_IMPLEMENTATION:-default}"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2topic ros-$ROS_DISTRO-fastrtps ros-$ROS_DISTRO-fastdds 2>/dev/null
D=/tmp/q; mkdir -p $D; cd $D

cat > qosarg.py <<'X'
# spec: comma list, e.g. "rel=best_effort,dur=volatile,deadline=1.0,live=automatic,lease=2.0"
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, LivelinessPolicy
from rclpy.duration import Duration
def make(spec):
    q = QoSProfile(depth=10)
    for kv in filter(None, spec.split(',')):
        k, v = kv.split('=')
        if k == 'rel': q.reliability = getattr(ReliabilityPolicy, v.upper())
        if k == 'dur': q.durability = getattr(DurabilityPolicy, v.upper())
        if k == 'live': q.liveliness = getattr(LivelinessPolicy, v.upper())
        if k == 'deadline': q.deadline = Duration(seconds=float(v))
        if k == 'lease': q.liveliness_lease_duration = Duration(seconds=float(v))
    return q
def events():
    try:
        from rclpy.event_handler import SubscriptionEventCallbacks, PublisherEventCallbacks
    except ImportError:
        from rclpy.qos_event import SubscriptionEventCallbacks, PublisherEventCallbacks
    return SubscriptionEventCallbacks, PublisherEventCallbacks
X

cat > pub.py <<'X'
# usage: pub.py SPEC COUNT RATE_HZ [events|sensor]
import sys, time, rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import Int32
import qosarg
rclpy.init(args=sys.argv)
a = remove_ros_args(sys.argv)
spec, count, rate = a[1], int(a[2]), float(a[3])
mode = a[4] if len(a) > 4 else ''
n = Node('qos_pub')
kw = {}
if mode == 'events':
    _, P = qosarg.events()
    kw['event_callbacks'] = P(incompatible_qos=lambda e: print(
        f'PUB EVENT incompatible_qos total_count={e.total_count} total_count_change={e.total_count_change} last_policy_kind={e.last_policy_kind}', flush=True))
if mode == 'sensor':
    from rclpy.qos import qos_profile_sensor_data as q
else:
    q = qosarg.make(spec)
p = n.create_publisher(Int32, '/x', q, **kw)
print(f'PUB qos reliability={q.reliability.name} durability={q.durability.name}', flush=True)
# wait up to 4 s for a matched subscription before sending (an incompatible one never matches)
t0 = time.time()
while time.time() - t0 < 4.0 and p.get_subscription_count() == 0: rclpy.spin_once(n, timeout_sec=0.05)
t_end = time.time() + 0.5
while time.time() < t_end: rclpy.spin_once(n, timeout_sec=0.05)
print(f'PUB matched_subs_before_send={p.get_subscription_count()}', flush=True)
sent = 0
for i in range(count):
    p.publish(Int32(data=i)); sent += 1
    t_end = time.time() + 1.0 / rate
    while time.time() < t_end: rclpy.spin_once(n, timeout_sec=0.01)
t_end = time.time() + 1.0
while time.time() < t_end: rclpy.spin_once(n, timeout_sec=0.05)
print(f'PUB sent={sent} matched_subs={p.get_subscription_count()}', flush=True)
n.destroy_node(); rclpy.shutdown()
X

cat > sub.py <<'X'
# usage: sub.py SPEC SECONDS [events|override]
import sys, time, rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
from std_msgs.msg import Int32
import qosarg
rclpy.init(args=sys.argv)
a = remove_ros_args(sys.argv)
spec, secs = a[1], float(a[2])
mode = a[3] if len(a) > 3 else ''
n = Node('qos_sub')
got = []
kw = {}
if mode == 'events':
    S, _ = qosarg.events()
    kw['event_callbacks'] = S(incompatible_qos=lambda e: print(
        f'SUB EVENT incompatible_qos total_count={e.total_count} total_count_change={e.total_count_change} last_policy_kind={e.last_policy_kind}', flush=True))
if mode == 'override':
    from rclpy.qos_overriding_options import QoSOverridingOptions
    kw['qos_overriding_options'] = QoSOverridingOptions.with_default_policies()
s = n.create_subscription(Int32, '/x', lambda m: got.append(m.data), qosarg.make(spec), **kw)
print(f'SUB qos reliability={s.qos_profile.reliability.name} durability={s.qos_profile.durability.name}', flush=True)
# matched publisher count, sampled while spinning (Subscription.get_publisher_count is missing on Humble)
cnt = getattr(s, 'get_publisher_count', None)
peak = 0
t_end = time.time() + secs
while time.time() < t_end:
    rclpy.spin_once(n, timeout_sec=0.05)
    if cnt: peak = max(peak, cnt())
print(f'SUB received={len(got)} first={got[:1]} peak_matched_pubs={peak if cnt else "n/a"}', flush=True)
n.destroy_node(); rclpy.shutdown()
X

ros2 daemon start >/dev/null 2>&1

# pair SUBSPEC PUBSPEC [submode] [pubmode] [extra sub args...]
pair() {
  local ss=$1 ps=$2 sm=$3 pm=$4; shift 4
  echo "--- sub[$ss $sm] pub[$ps $pm]"
  python3 sub.py "$ss" 9 $sm "$@" > sub.log 2>&1 &
  local sp=$!
  sleep 1
  python3 pub.py "$ps" 30 20 $pm > pub.log 2>&1
  wait $sp
  sed 's/^/  [sub] /' sub.log; sed 's/^/  [pub] /' pub.log
}

echo; echo "=== 1. reliability matrix (sub starts first, pub sends 30 msgs at 20 Hz)"
for pr in reliable best_effort; do for sr in reliable best_effort; do for rep in 1 2 3; do
  pair "rel=$sr" "rel=$pr" "" ""
done; done; done

echo; echo "=== 2. durability matrix (both reliable)"
for pd in volatile transient_local; do for sd in volatile transient_local; do for rep in 1 2 3; do
  pair "dur=$sd" "dur=$pd" "" ""
done; done; done

echo; echo "=== 3. both reliability and durability wrong (pub best_effort+volatile, sub reliable+transient_local)"
pair "rel=reliable,dur=transient_local" "rel=best_effort,dur=volatile" "" ""

echo; echo "=== 4. deadline"
pair "deadline=0.5" "deadline=1.0" "" ""
pair "deadline=1.0" "deadline=0.5" "" ""
pair "deadline=1.0" "" "" ""

echo; echo "=== 5. liveliness"
pair "live=manual_by_topic" "live=automatic" "" ""
pair "live=automatic" "live=manual_by_topic" "" ""
pair "lease=1.0" "lease=2.0" "" ""
pair "lease=2.0" "lease=1.0" "" ""

echo; echo "=== 6. qos_profile_sensor_data publisher vs default (reliable) subscriber"
pair "rel=reliable" "" "" "sensor"
pair "rel=best_effort" "" "" "sensor"

echo; echo "=== 7. event callbacks (incompatible_qos) on both sides, reliability mismatch"
pair "rel=reliable" "rel=best_effort" "events" "events"
echo "--- event callbacks, durability mismatch"
pair "dur=transient_local" "dur=volatile" "events" "events"
echo "--- event callbacks, deadline mismatch"
pair "deadline=0.5" "deadline=1.0" "events" "events"

echo; echo "=== 8. QoS overriding: reliable sub in code, reliability overridden by parameter"
pair "rel=reliable" "rel=best_effort" "override" "" --ros-args -p "qos_overrides./x.subscription.reliability:=best_effort"
echo "--- same node, no override parameter"
pair "rel=reliable" "rel=best_effort" "override" ""

# long-running publisher for CLI tests: 20 Hz for 50 s
bg_pub() { python3 pub.py "$1" 1000 20 > bgpub.log 2>&1 & BGP=$!; sleep 2; }
echo_n() { # label, args...
  local l=$1; shift
  echo "--- ros2 topic echo $l /x, 4 s"
  timeout 4 ros2 topic echo "$@" /x std_msgs/msg/Int32 > echo.out 2> echo.err
  echo "  data lines: $(grep -c '^data:' echo.out)"; grep -v 'rclpy.ok' echo.err | sed 's/^/  [stderr] /' | head -5
}
info_during() { # label, command...
  local l=$1; shift
  echo "--- ros2 topic info -v /x while '$l' runs (subscription endpoints only)"
  timeout 7 "$@" > /dev/null 2>&1 & local cp=$!
  sleep 4; ros2 topic info -v /x | awk '/Endpoint type: PUBLISHER/{p=1} /Endpoint type: SUBSCRIPTION/{p=0} /Publisher count|Subscription count/{print; next} !p && /Endpoint type|Reliability|Durability|Depth|Node name/{print "  " $0}'
  wait $cp
}

echo; echo "=== 9. ros2 topic echo / hz help (QoS options)"
ros2 topic echo -h 2>&1 | grep -oE -- '--qos-[a-z-]+( \{[^}]*\})?' | sort -u
echo "--- hz"
ros2 topic hz -h 2>&1 | grep -oE -- '--qos-[a-z-]+( \{[^}]*\})?' | sort -u
ros2 topic hz -h 2>&1 | grep -q -- '--qos' || echo "(no --qos options in ros2 topic hz -h)"

for pspec in "rel=best_effort" "rel=reliable,dur=transient_local"; do
echo; echo "=== 10. CLI against publisher [$pspec]"
bg_pub "$pspec"
echo_n "(defaults)"
echo_n "--qos-reliability reliable" --qos-reliability reliable
echo_n "--qos-profile services_default" --qos-profile services_default
echo_n "--qos-profile sensor_data" --qos-profile sensor_data
info_during "ros2 topic echo /x" ros2 topic echo /x std_msgs/msg/Int32
info_during "ros2 topic echo --qos-profile services_default /x" ros2 topic echo --qos-profile services_default /x std_msgs/msg/Int32
info_during "ros2 topic hz /x" ros2 topic hz /x
echo "--- ros2 topic hz /x (defaults), 5 s"
timeout -s INT 5 ros2 topic hz /x > hz.out 2>&1; sed 's/^/  /' hz.out | head -6
kill $BGP 2>/dev/null; wait $BGP 2>/dev/null
done

echo; echo "=== 10b. ros2 topic echo started BEFORE any publisher exists, then best_effort pub starts"
timeout -k 3 8 ros2 topic echo /x std_msgs/msg/Int32 > echo.out 2> echo.err & EP=$!  # -k 3 added after the Jazzy run hung here; Jazzy echo was killed by hand with kill -9
sleep 2; python3 pub.py "rel=best_effort" 80 20 > pub.log 2>&1
wait $EP
echo "  data lines: $(grep -c '^data:' echo.out)"; grep -v 'rclpy.ok' echo.err | sed 's/^/  [stderr] /' | head -3; sed 's/^/  [pub] /' pub.log

echo; echo "=== 11. ros2 topic info -v /x with best_effort pub and reliable sub (mismatch)"
python3 sub.py "rel=reliable" 8 > sub.log 2>&1 & SP=$!
python3 pub.py "rel=best_effort" 120 20 > pub.log 2>&1 & PP=$!
sleep 3; ros2 topic info -v /x
wait $SP $PP; sed 's/^/  [sub] /' sub.log; sed 's/^/  [pub] /' pub.log
echo "=== done"
