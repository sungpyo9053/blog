#!/bin/bash
# Repro: /tf_static after `ros2 bag play` for nodes that start late.
# Run on the host: bash repro.sh [distros...]  -> writes /tmp/en-tfstatic/out_<distro>.txt
# Each distro runs in one container (docker --rm, default bridge network, ROS_DOMAIN_ID=78).
set -u
W=/tmp/en-tfstatic
mkdir -p $W
cd $W

# ---- /tf publisher: base -> sensor at 10 Hz, stamped with now() ----
cat > tfpub.py <<'EOF'
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
rclpy.init()
n = Node('tf_dyn_pub')
p = n.create_publisher(TFMessage, '/tf', 100)
def cb():
    t = TransformStamped()
    t.header.stamp = n.get_clock().now().to_msg()
    t.header.frame_id = 'base'
    t.child_frame_id = 'sensor'
    t.transform.translation.x = 0.5
    t.transform.rotation.w = 1.0
    p.publish(TFMessage(transforms=[t]))
n.create_timer(0.1, cb)
rclpy.spin(n)
EOF

# ---- tf2 listener: Buffer + TransformListener, lookups every 0.5 s ----
cat > lis.py <<'EOF'
import sys, time, rclpy
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener
tag = sys.argv[1]; dur = float(sys.argv[2])
rclpy.init()
n = Node('late_listener')
buf = Buffer(); TransformListener(buf, n)
ok = {'base': 0, 'sensor': 0}; fail = {'base': 0, 'sensor': 0}; first_err = {}
t0 = time.time()
while time.time() - t0 < dur:
    rclpy.spin_once(n, timeout_sec=0.5)
    for child in ('base', 'sensor'):
        try:
            buf.lookup_transform('world', child, Time())
            ok[child] += 1
        except Exception as e:
            fail[child] += 1
            first_err.setdefault(child, type(e).__name__ + ': ' + str(e).splitlines()[0])
for child in ('base', 'sensor'):
    print(f'[{tag}] world->{child}: ok={ok[child]} fail={fail[child]}' + (f' first_error="{first_err[child]}"' if child in first_err else ''))
rclpy.shutdown()
EOF

# ---- /tf_static counter with chosen durability ----
cat > cnt.py <<'EOF'
import sys, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from tf2_msgs.msg import TFMessage
tag = sys.argv[1]; dura = sys.argv[2]; dur = float(sys.argv[3])
rclpy.init()
n = Node('static_counter')
q = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
               durability=DurabilityPolicy.TRANSIENT_LOCAL if dura == 'tl' else DurabilityPolicy.VOLATILE)
c = [0]
n.create_subscription(TFMessage, '/tf_static', lambda m: c.__setitem__(0, c[0] + 1), q)
t0 = time.time()
while time.time() - t0 < dur:
    rclpy.spin_once(n, timeout_sec=0.2)
print(f'[{tag}] /tf_static messages received ({dura}, {dur}s): {c[0]}')
rclpy.shutdown()
EOF

# ---- override files ----
cat > override_tl.yaml <<'EOF'
/tf_static:
  history: keep_last
  depth: 1
  reliability: reliable
  durability: transient_local
EOF
cat > override_volatile.yaml <<'EOF'
/tf_static:
  history: keep_last
  depth: 1
  reliability: reliable
  durability: volatile
EOF

# ---- inner script (runs inside the container) ----
cat > in.sh <<'EOF'
#!/bin/bash
# job control on: otherwise background jobs ignore SIGINT and kill -INT does nothing
set -m
source /opt/ros/$ROS_DISTRO/setup.bash
cd /w
export PYTHONUNBUFFERED=1
echo "### distro: $ROS_DISTRO  RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}  ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
dpkg-query -W -f='${Package} ${Version}\n' "ros-$ROS_DISTRO-rosbag2*" "ros-$ROS_DISTRO-tf2-ros" "ros-$ROS_DISTRO-rmw-fastrtps-cpp" 2>/dev/null | grep -v '^$'

echo; echo "### ros2 bag play --help (qos lines)"
ros2 bag play --help | grep -i -A4 'qos'

echo; echo "### record: static_transform_publisher world->base + /tf base->sensor, 6 s bag"
ros2 run tf2_ros static_transform_publisher --x 1 --y 2 --z 3 --frame-id world --child-frame-id base > /tmp/stp.log 2>&1 &
STP=$!
python3 tfpub.py > /tmp/tfpub.log 2>&1 &
TFP=$!
sleep 2
# Lyrical's record CLI no longer takes positional topics; it needs --topics
T="/tf /tf_static"; [ "$ROS_DISTRO" = lyrical ] && T="--topics /tf /tf_static"
ros2 bag record -o /tmp/bag1 $T > /tmp/rec.log 2>&1 &
REC=$!
sleep 7
kill -INT $REC; wait $REC
kill -INT $STP $TFP; sleep 2; pkill -9 -f static_transform_publisher; kill -9 $STP $TFP 2>/dev/null; wait 2>/dev/null
tail -3 /tmp/rec.log
echo; echo "### ros2 bag info"
ros2 bag info /tmp/bag1
echo; echo "### metadata.yaml /tf_static entry"
grep -n -A3 'name: /tf_static' /tmp/bag1/metadata.yaml
python3 - <<'PY'
import yaml
m = yaml.safe_load(open('/tmp/bag1/metadata.yaml'))['rosbag2_bagfile_information']
for t in m['topics_with_message_count']:
    md = t['topic_metadata']
    q = md.get('offered_qos_profiles')
    print('topic', md['name'], 'count', t['message_count'])
    print('  offered_qos_profiles:', repr(q)[:400])
PY
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1

# helper: play with args, start late listener + tf2_echo + echo at +2 s
late() {
  local tag=$1; shift
  echo; echo "### ($tag) ros2 bag play $*  | listener, tf2_echo, topic echo start 2 s after play"
  ros2 bag play /tmp/bag1 "$@" > /tmp/play_$tag.log 2>&1 &
  local P=$!
  sleep 2
  python3 lis.py "$tag" 4 &
  local L=$!
  timeout -s INT -k 2 4 ros2 run tf2_ros tf2_echo world base > /tmp/echo_$tag.log 2>&1 &
  local E=$!
  sleep 1
  echo "[$tag] player QoS on /tf_static:"
  ros2 topic info /tf_static -v 2>&1 | sed -n '/rosbag2_player/,/Liveliness:/p' | grep -E 'Node name|Endpoint|Reliability|History|Durability'
  wait $L $E
  echo "[$tag] tf2_echo output (first 3 lines, line count):"
  head -3 /tmp/echo_$tag.log; echo "  lines=$(wc -l < /tmp/echo_$tag.log) translation_lines=$(grep -c 'Translation' /tmp/echo_$tag.log)"
  wait $P
  echo "[$tag] player log:"; grep -v '^$' /tmp/play_$tag.log | head -5
}

late a_default
late b_override_tl --qos-profile-overrides-path /w/override_tl.yaml
late x_override_volatile --qos-profile-overrides-path /w/override_volatile.yaml

echo; echo "### (e) listener started BEFORE play"
for mode in default volatile; do
  args=(); [ $mode = volatile ] && args=(--qos-profile-overrides-path /w/override_volatile.yaml)
  python3 lis.py "e_before_$mode" 9 &
  L=$!
  sleep 2
  ros2 bag play /tmp/bag1 "${args[@]}" > /tmp/play_e_$mode.log 2>&1
  wait $L
done

echo; echo "### (after-end) listener started 1 s AFTER play finished (default)"
ros2 bag play /tmp/bag1 > /dev/null 2>&1
sleep 1
python3 lis.py after_end 3

echo; echo "### (f) ros2 topic echo /tf_static late join, +2 s after play"
for mode in default override_tl volatile; do
  args=()
  [ $mode = override_tl ] && args=(--qos-profile-overrides-path /w/override_tl.yaml)
  [ $mode = volatile ] && args=(--qos-profile-overrides-path /w/override_volatile.yaml)
  for eargs in "" "--qos-durability transient_local" "--qos-durability transient_local --qos-reliability reliable"; do
    ros2 bag play /tmp/bag1 "${args[@]}" > /dev/null 2>&1 &
    P=$!
    sleep 2
    out=$(timeout -s INT -k 2 3 ros2 topic echo /tf_static $eargs 2>&1)
    echo "[f_$mode] echo $eargs -> child_frame_id lines: $(echo "$out" | grep -c 'child_frame_id: base')  other: $(echo "$out" | grep -v -E '^\s|^---|^transforms|^$' | head -2 | tr '\n' ' ')"
    wait $P
  done
done

echo; echo "### (d) --loop: volatile + transient_local counters from before play, 20 s; late listener at +8 s"
ros2 bag play /tmp/bag1 --loop > /tmp/play_loop.log 2>&1 &
P=$!
python3 cnt.py d_loop_volatile vol 20 &
C1=$!
python3 cnt.py d_loop_tl tl 20 &
C2=$!
sleep 8
python3 lis.py d_loop_late8s 4 &
L=$!
sleep 1
ros2 topic info /tf_static -v 2>&1 | sed -n '/rosbag2_player/,/Liveliness:/p' | grep -E 'Node name|Durability'
wait $C1 $C2 $L
kill -INT $P; sleep 2; kill -9 $P 2>/dev/null; pkill -9 -f 'bag play'; wait $P 2>/dev/null

echo; echo "### (d2) --loop with override_tl, late listener at +8 s"
ros2 bag play /tmp/bag1 --loop --qos-profile-overrides-path /w/override_tl.yaml > /dev/null 2>&1 &
P=$!
sleep 8
python3 lis.py d2_loop_tl_late8s 4
kill -INT $P; sleep 2; kill -9 $P 2>/dev/null; pkill -9 -f 'bag play'; wait $P 2>/dev/null

echo; echo "### (g) --start-offset 2, listener started before play"
for mode in default override_tl; do
  args=(); [ $mode = override_tl ] && args=(--qos-profile-overrides-path /w/override_tl.yaml)
  python3 lis.py "g_offset_$mode" 7 &
  L=$!
  sleep 2
  ros2 bag play /tmp/bag1 --start-offset 2 "${args[@]}" > /tmp/play_g_$mode.log 2>&1
  wait $L
  grep -v '^$' /tmp/play_g_$mode.log | head -3
done
echo "### done"
EOF
chmod +x in.sh

for d in ${@:-humble jazzy lyrical}; do
  img=ros:$d-ros-base
  if docker pull -q $img > /dev/null 2>&1; then
    timeout 1200 docker run --rm --name tfst-$d -e ROS_DOMAIN_ID=78 -v $W:/w $img bash /w/in.sh > $W/out_$d.txt 2>&1
  else
    echo "image $img not available" > $W/out_$d.txt
  fi
done
