#!/bin/bash
# slam_toolbox "Failed to compute odom pose": which TF setups trigger it, which ones
# fail silently instead, and which fixes work. Humble, Jazzy, Lyrical.
#
# Host side (one distro at a time, never in parallel):
#   docker run -d --ulimit core=0 --name pk67-<distro> -v /tmp/en-pick67:/w ros:<distro>-ros-base sleep infinity
#   docker exec pk67-<distro> bash -c 'apt-get update && apt-get install -y --no-install-recommends ros-<distro>-slam-toolbox'
#   docker network disconnect bridge pk67-<distro>          # no network from here on
#   docker exec pk67-<distro> bash /w/repro.sh > out_<distro>.txt 2>&1
#   docker rm -f pk67-<distro>
# Rerun of selected cases only: docker exec -e ONLY="case1 case2" pk67-<distro> bash /w/repro.sh
# Note: run_p_lc ran 15 s in the Humble pass and the first Jazzy pass; it was then raised to 25 s
# (Jazzy needs the configure/activate calls first) and rerun on Jazzy with ONLY=run_p_lc
# (appended to out_jazzy.txt). Lyrical ran with 25 s from the start.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=67
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
D=$ROS_DISTRO
SHARE=/opt/ros/$D/share/slam_toolbox
echo "=== distro=$D date=$(date -u +%FT%TZ)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-slam-toolbox ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-rmw-fastrtps-cpp ros-$D-tf2-ros ros-$D-launch-ros 2>/dev/null
python3 --version
echo "RMW default: ${RMW_IMPLEMENTATION:-unset (Fast DDS)}"
echo "--- launch arguments of online_async_launch.py"
ros2 launch slam_toolbox online_async_launch.py --show-args 2>&1 | grep -E "^    '|default" | head -20
echo "--- frames in the shipped params file"
grep -nE "odom_frame|base_frame|map_frame|scan_topic|map_update_interval|transform_timeout|tf_buffer" $SHARE/config/mapper_params_online_async.yaml

# ---------- helper files ----------
cat > /w/fake_robot.py <<'X'
# Fake robot: LaserScan on /scan (square room), odom->CHILD on TF, CHILD->laser static.
import argparse, math, rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from tf2_msgs.msg import TFMessage
p = argparse.ArgumentParser()
p.add_argument('--odom-child', default='base_footprint')    # 'none' = no odom tf at all
p.add_argument('--laser-parent', default='base_footprint')  # 'none' = no static laser tf
p.add_argument('--extra-static', default='')                # parent:child, e.g. base_link:base_footprint
p.add_argument('--odom-rate', type=float, default=20.0)
p.add_argument('--odom-lag', type=float, default=0.0)       # odom stamp = now - lag
p.add_argument('--scan-offset', type=float, default=0.0)    # scan stamp = now + offset
p.add_argument('--tf-topic', default='/tf')
a = p.parse_args()
rclpy.init()
n = Node('pk67_fake_robot')
pub = n.create_publisher(LaserScan, '/scan', 10)
if a.tf_topic == '/tf':
    br = TransformBroadcaster(n)
    send = br.sendTransform
else:
    tfp = n.create_publisher(TFMessage, a.tf_topic, 100)
    send = lambda t: tfp.publish(TFMessage(transforms=[t]))
sb = StaticTransformBroadcaster(n)
statics = []
def tf(parent, child, x=0.0, z=0.0):
    t = TransformStamped()
    t.header.stamp = n.get_clock().now().to_msg()
    t.header.frame_id = parent
    t.child_frame_id = child
    t.transform.translation.x = x
    t.transform.translation.z = z
    t.transform.rotation.w = 1.0
    return t
if a.laser_parent != 'none':
    statics.append(tf(a.laser_parent, 'laser', 0.1, 0.2))
if a.extra_static:
    pa, ch = a.extra_static.split(':')
    statics.append(tf(pa, ch, 0.0, -0.05))
if statics:
    sb.sendTransform(statics)
N = 360
def scan():
    s = LaserScan()
    s.header.stamp = (n.get_clock().now() + Duration(seconds=a.scan_offset)).to_msg()
    s.header.frame_id = 'laser'
    s.angle_min = -math.pi
    s.angle_increment = 2 * math.pi / N
    s.angle_max = s.angle_min + s.angle_increment * (N - 1)
    s.scan_time = 0.1
    s.time_increment = 0.0
    s.range_min = 0.1
    s.range_max = 10.0
    r = []
    for i in range(N):
        th = s.angle_min + i * s.angle_increment
        c, si = abs(math.cos(th)), abs(math.sin(th))
        d = min(2.0 / c if c > 1e-6 else 99, 1.5 / si if si > 1e-6 else 99)
        r.append(float(d))
    s.ranges = r
    pub.publish(s)
def odom():
    t = tf('odom', a.odom_child)
    t.header.stamp = (n.get_clock().now() - Duration(seconds=a.odom_lag)).to_msg()
    send(t)
n.create_timer(0.1, scan)
if a.odom_child != 'none':
    n.create_timer(1.0 / a.odom_rate, odom)
try:
    rclpy.spin(n)
except Exception:
    pass
X

cat > /w/probe.py <<'X'
# Watch /map and /tf for DUR seconds. Prints first /map time, size, count, map->odom seen.
import sys, time, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from nav_msgs.msg import OccupancyGrid
from tf2_msgs.msg import TFMessage
dur = float(sys.argv[1])
rclpy.init()
n = Node('pk67_probe')
t0 = time.monotonic()
st = {'first': None, 'count': 0, 'size': None, 'map_odom': 0, 'map_odom_stamp': None}
def on_map(m):
    st['count'] += 1
    if st['first'] is None:
        st['first'] = round(time.monotonic() - t0, 2)
    st['size'] = f"{m.info.width}x{m.info.height}@{m.info.resolution:.3f}"
def on_tf(m):
    for t in m.transforms:
        if t.header.frame_id == 'map' and t.child_frame_id == 'odom':
            st['map_odom'] += 1
            st['map_odom_stamp'] = t.header.stamp.sec
qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
n.create_subscription(OccupancyGrid, '/map', on_map, qos)
n.create_subscription(TFMessage, '/tf', on_tf, 100)
while time.monotonic() - t0 < dur:
    rclpy.spin_once(n, timeout_sec=0.1)
print(f"PROBE first_map_s={st['first']} maps={st['count']} size={st['size']} map_to_odom_tf={st['map_odom']} last_map_to_odom_stamp_sec={st['map_odom_stamp']} wall_sec={int(time.time())}")
X

# params files derived from the shipped one
cp $SHARE/config/mapper_params_online_async.yaml /w/p_default.yaml
sed 's/^\(\s*base_frame:\).*/\1 base_link/' /w/p_default.yaml > /w/p_base_link.yaml
sed 's/^\(\s*transform_timeout:\).*/\1 1.0/' /w/p_default.yaml > /w/p_timeout1.yaml
sed 's/^\(\s*transform_timeout:.*\)$/\1\n    scan_queue_size: 10/' /w/p_default.yaml > /w/p_queue10.yaml
sed 's/^\(\s*transform_timeout:\).*$/\1 1.0\n    scan_queue_size: 10/' /w/p_default.yaml > /w/p_queue10_timeout1.yaml
grep -n "transform_timeout\|scan_queue_size" /w/p_queue10.yaml /w/p_queue10_timeout1.yaml
grep -n "base_frame" /w/p_base_link.yaml; grep -n "transform_timeout" /w/p_timeout1.yaml

summarize() {  # $1 = log file
  local L=$1
  echo "  count 'Failed to compute odom pose': $(grep -c 'Failed to compute odom pose' $L)"
  echo "  count 'Message Filter dropping': $(grep -c 'Message Filter dropping' $L)"
  echo "  count 'Failed to compute laser pose': $(grep -c 'Failed to compute laser pose' $L)"
  grep -m1 'Message Filter dropping' $L | sed -E 's/^.*(Message Filter)/  first drop line: \1/'
  local f=$(grep -m1 -n 'Failed to compute odom pose' $L | cut -d: -f1)
  echo "  first 'Failed to compute odom pose' line no: ${f:-none}"
  echo "  distinct WARN/ERROR lines (numbers stripped, with counts):"
  grep -E 'WARN|ERROR|rror' $L | sed -E 's/\[[0-9]+\.[0-9]+\]//g; s/[0-9]+\.[0-9]+/N/g; s/[0-9]{3,}/N/g' | sort | uniq -c | sort -rn | head -8 | sed 's/^/    /'
  echo "  first INFO lines:"
  grep -E 'INFO' $L | grep -v LifecycleLaunch | head -4 | sed 's/^/    /'
}

cleanup_procs() {
  pkill -INT -f 'ros2 launch slam_toolbox' 2>/dev/null
  pkill -INT -f slam_toolbox_node 2>/dev/null
  pkill -f fake_robot.py 2>/dev/null
  pkill -f probe.py 2>/dev/null
  sleep 2
  pkill -9 -f slam_toolbox 2>/dev/null
  pkill -9 -f fake_robot.py 2>/dev/null
  sleep 1
}

# run_case NAME "robot args" MODE "slam args" [DUR]
#   MODE=launch : ros2 launch slam_toolbox online_async_launch.py <slam args>
#   MODE=run    : ros2 run slam_toolbox async_slam_toolbox_node <slam args>
#   MODE=runlc  : like run, then ros2 lifecycle set configure/activate (Jazzy/Lyrical)
run_case() {
  local NAME=$1 RARGS=$2 MODE=$3 SARGS=$4 DUR=${5:-15}
  if [ -n "$ONLY" ] && [[ " $ONLY " != *" $NAME "* ]]; then return; fi
  echo
  echo "######## CASE $NAME"
  echo "robot: $RARGS"
  echo "slam:  $MODE $SARGS"
  python3 /w/fake_robot.py $RARGS > /w/robot_$NAME.log 2>&1 &
  sleep 2
  local L=/w/slam_$NAME.log
  local T0=$(date +%s.%N)
  if [ $MODE = launch ]; then
    ros2 launch slam_toolbox online_async_launch.py $SARGS > $L 2>&1 &
  else
    ros2 run slam_toolbox async_slam_toolbox_node $SARGS > $L 2>&1 &
  fi
  python3 /w/probe.py $DUR > /w/probe_$NAME.txt 2>&1 &
  local PP=$!
  if [ $MODE = runlc ] && [ $D != humble ]; then
    sleep 3
    echo "  lifecycle before: $(timeout 10 ros2 lifecycle get /slam_toolbox 2>&1)"
    timeout 15 ros2 lifecycle set /slam_toolbox configure 2>&1 | sed 's/^/  configure: /'
    timeout 15 ros2 lifecycle set /slam_toolbox activate 2>&1 | sed 's/^/  activate: /'
  fi
  if [ $MODE = run ] && [ $D != humble ]; then
    sleep 4
    echo "  lifecycle state after 4 s: $(timeout 10 ros2 lifecycle get /slam_toolbox 2>&1)"
  fi
  if [ -n "$EXTRA" ]; then sleep 5; eval "$EXTRA"; fi
  wait $PP
  local T1=$(date +%s.%N)
  echo "  $(cat /w/probe_$NAME.txt | grep PROBE)"
  echo "  wall seconds slam ran: $(python3 -c "print(round($T1-$T0,1))")"
  summarize $L
  cleanup_procs
}

# ---------- cases ----------
LA="use_sim_time:=false"
# 1. correct: odom->base_footprint->laser, shipped params
run_case ok_footprint "--odom-child base_footprint --laser-parent base_footprint" launch "$LA"
# 2. robot uses base_link, shipped params (base_frame: base_footprint)
EXTRA='echo "  tf2_echo odom base_footprint:"; timeout 4 ros2 run tf2_ros tf2_echo odom base_footprint 2>&1 | head -3 | sed "s/^/    /"; echo "  param base_frame: $(timeout 10 ros2 param get /slam_toolbox base_frame 2>&1 || (sleep 2; timeout 10 ros2 param get /slam_toolbox base_frame 2>&1))"'
run_case baselink_default "--odom-child base_link --laser-parent base_link" launch "$LA"
EXTRA=''
# 3. same, plus base_frame:=base_link as a LAUNCH argument (not a declared argument)
EXTRA='echo "  param base_frame: $(timeout 10 ros2 param get /slam_toolbox base_frame 2>&1)"'
run_case baselink_launcharg "--odom-child base_link --laser-parent base_link" launch "$LA base_frame:=base_link"
EXTRA=''
# 4. fix A: params file with base_frame: base_link
run_case baselink_paramsfile "--odom-child base_link --laser-parent base_link" launch "$LA slam_params_file:=/w/p_base_link.yaml"
# 5. fix B: static base_link->base_footprint so the default name exists
run_case baselink_extra_static "--odom-child base_link --laser-parent base_link --extra-static base_link:base_footprint" launch "$LA"
# 6. fix C: ros2 run with -p (no lifecycle transitions)
run_case run_p_nolc "--odom-child base_link --laser-parent base_link" run "--ros-args -p base_frame:=base_link -p use_sim_time:=false"
# 7. fix C': ros2 run with -p plus lifecycle configure/activate
run_case run_p_lc "--odom-child base_link --laser-parent base_link" runlc "--ros-args -p base_frame:=base_link -p use_sim_time:=false" 25
# 8. no odom tf at all
run_case no_odom "--odom-child none --laser-parent base_footprint" launch "$LA"
# 9. odom tf only on a namespaced topic
run_case odom_ns_topic "--odom-child base_footprint --laser-parent base_footprint --tf-topic /robot1/tf" launch "$LA"
# 10. no base->laser static transform
run_case no_laser_tf "--odom-child base_footprint --laser-parent none" launch "$LA"
# 11-15. odom stamps lagging behind the scan (shipped transform_timeout is 0.2 s)
for LAG in 0.1 0.15 0.25 0.3 1.0; do
  run_case odom_lag_$LAG "--odom-child base_footprint --laser-parent base_footprint --odom-lag $LAG" launch "$LA"
done
# 16-20. lag fixes: transform_timeout alone, scan_queue_size alone, both
run_case odom_lag_0.6_timeout1 "--odom-child base_footprint --laser-parent base_footprint --odom-lag 0.6" launch "$LA slam_params_file:=/w/p_timeout1.yaml"
run_case odom_lag_0.3_queue10 "--odom-child base_footprint --laser-parent base_footprint --odom-lag 0.3" launch "$LA slam_params_file:=/w/p_queue10.yaml"
run_case odom_lag_0.15_queue10 "--odom-child base_footprint --laser-parent base_footprint --odom-lag 0.15" launch "$LA slam_params_file:=/w/p_queue10.yaml"
run_case odom_lag_0.6_queue10_timeout1 "--odom-child base_footprint --laser-parent base_footprint --odom-lag 0.6" launch "$LA slam_params_file:=/w/p_queue10_timeout1.yaml"
run_case odom_lag_1.0_queue10_timeout1 "--odom-child base_footprint --laser-parent base_footprint --odom-lag 1.0" launch "$LA slam_params_file:=/w/p_queue10_timeout1.yaml"
# 21. URDF-style static base_footprint->base_link while odometry also publishes odom->base_link (two parents)
run_case two_parents "--odom-child base_link --laser-parent base_link --extra-static base_footprint:base_link" launch "$LA"
# 14. scan stamped 1 s in the past (old scan, sensor clock behind)
run_case scan_past_1.0 "--odom-child base_footprint --laser-parent base_footprint --scan-offset -1.0" launch "$LA"
# 15. odom tf at 2 Hz
run_case odom_2hz "--odom-child base_footprint --laser-parent base_footprint --odom-rate 2" launch "$LA"
# 16. launch defaults: use_sim_time true, no /clock
run_case simtime_default "--odom-child base_footprint --laser-parent base_footprint" launch ""
echo
echo "=== done $(date -u +%FT%TZ)"
