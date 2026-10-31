#!/bin/bash
# Run inside ros:<distro>-ros-base, e.g.
#   docker run --rm --name tpub-humble --network none --cpus 1.5 --ulimit core=0 \
#     -v $PWD:/w ros:humble-ros-base bash /w/repro.sh > out_humble.txt 2>&1
# Measures YAML argument errors of `ros2 topic pub` / `ros2 service call`,
# the working forms, `ros2 interface proto`, and -1 / -w / -r / -t delivery counts.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=77
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2topic ros-$ROS_DISTRO-ros2service \
  ros-$ROS_DISTRO-ros2interface ros-$ROS_DISTRO-rosidl-runtime-py ros-$ROS_DISTRO-rmw \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp python3-yaml 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"

mkdir -p /tmp/t && cd /tmp/t
cat > sink.py <<'X'
import rclpy, sys
from rclpy.node import Node
from std_msgs.msg import String, Int32, ByteMultiArray, UInt8MultiArray, Float64MultiArray
from geometry_msgs.msg import Twist, PoseStamped, Pose
from sensor_msgs.msg import JointState
rclpy.init()
n = Node('sink')
topics = {'/s': String, '/i': Int32, '/b': ByteMultiArray, '/u8': UInt8MultiArray,
          '/f': Float64MultiArray, '/tw': Twist, '/ps': PoseStamped, '/js': JointState, '/pose': Pose}
for c in ['/cnt%d' % i for i in range(1, 21)]:
    topics[c] = String
subs = []
for t, ty in topics.items():
    subs.append(n.create_subscription(ty, t, (lambda m, t=t: print('RECV', t, m, flush=True)), 10))
rclpy.spin(n)
X
cat > srv.py <<'X'
import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool
rclpy.init()
n = Node('sb_server')
def cb(req, res):
    print('SRV got data=%r' % req.data, flush=True)
    res.success = req.data
    res.message = 'ok'
    return res
s = n.create_service(SetBool, '/sb', cb)
rclpy.spin(n)
X
python3 sink.py > sink.log 2>&1 &
python3 srv.py > srv.log 2>&1 &
sleep 4

echo "=== help: topic pub options"
ros2 topic pub -h 2>&1
echo "=== help: service call options"
ros2 service call -h 2>&1
if ros2 topic pub -h 2>&1 | grep -q -- '--wait-matching-subscriptions'; then W='-w 1'; else W=''; fi
echo "W=[$W]"

SL=0; VL=0
c() {  # c <name> <shell command string>
  echo; echo "--- CASE $1"; echo "CMD: $2"
  local t0=$(date +%s.%N)
  eval "timeout 20 $2" > case.out 2>&1; local rc=$?
  local t1=$(date +%s.%N)
  head -c 3000 case.out
  echo "EXIT=$rc SECONDS=$(python3 -c "print(round($t1-$t0,2))")"
  sleep 0.7
  local n=$(wc -l < sink.log); if [ "$n" -gt "$SL" ]; then sed -n "$((SL+1)),${n}p" sink.log | sed 's/^/SINK: /' | cut -c1-600; SL=$n; fi
  n=$(wc -l < srv.log); if [ "$n" -gt "$VL" ]; then sed -n "$((VL+1)),${n}p" srv.log | sed 's/^/SERVER: /'; VL=$n; fi
}
P="ros2 topic pub -1 $W"

echo "=== 1. String"
c str_ok             "$P /s std_msgs/msg/String '{data: hi}'"
c str_nobrace        "$P /s std_msgs/msg/String 'data: hi'"
c str_nospace        "$P /s std_msgs/msg/String '{data:hi}'"
c str_nospace_nobrace "$P /s std_msgs/msg/String 'data:hi'"
c str_wrongfield     "$P /s std_msgs/msg/String '{dat: hi}'"
c str_colon_unquoted "$P /s std_msgs/msg/String '{data: time: 12:30}'"
c str_sexagesimal    "$P /s std_msgs/msg/String '{data: 12:30}'"
c str_colon_quoted   "$P /s std_msgs/msg/String \"{data: 'time: 12:30'}\""
c str_number         "$P /s std_msgs/msg/String '{data: 42}'"
c str_number_quoted  "$P /s std_msgs/msg/String \"{data: '42'}\""
c str_bool_yes       "$P /s std_msgs/msg/String '{data: yes}'"
c str_bare_scalar    "$P /s std_msgs/msg/String 'hi'"

echo "=== 2. Shell quoting"
c sh_double_inner_single "$P /s std_msgs/msg/String \"{data: 'hello world'}\""
c sh_single_inner_double "$P /s std_msgs/msg/String '{data: \"hello world\"}'"
c sh_double_inner_double "$P /s std_msgs/msg/String \"{data: \"a: b\"}\""
c sh_double_dollar   "$P /s std_msgs/msg/String \"{data: price \$5}\""
c sh_single_dollar   "$P /s std_msgs/msg/String '{data: price \$5}'"
c sh_unquoted        "$P /s std_msgs/msg/String {data: hi}"
c sh_unquoted_nospace "$P /s std_msgs/msg/String {data:hi}"

echo "=== 3. Int vs float"
c tw_int_for_float   "$P /tw geometry_msgs/msg/Twist '{linear: {x: 1}}'"
c tw_float           "$P /tw geometry_msgs/msg/Twist '{linear: {x: 0.5}, angular: {z: 1.0}}'"
c tw_str_for_float   "$P /tw geometry_msgs/msg/Twist \"{linear: {x: '1.0'}}\""
c i32_float_for_int  "$P /i std_msgs/msg/Int32 '{data: 1.5}'"
c i32_float_whole    "$P /i std_msgs/msg/Int32 '{data: 1.0}'"
c i32_str_for_int    "$P /i std_msgs/msg/Int32 \"{data: '5'}\""
c i32_ok             "$P /i std_msgs/msg/Int32 '{data: 5}'"
c i32_overflow       "$P /i std_msgs/msg/Int32 '{data: 3000000000}'"

echo "=== 4. Nested messages"
c tw_flat            "$P /tw geometry_msgs/msg/Twist '{x: 1.0}'"
c tw_dotted          "$P /tw geometry_msgs/msg/Twist '{linear.x: 1.0}'"
c tw_scalar_for_msg  "$P /tw geometry_msgs/msg/Twist '{linear: 1.0}'"
c tw_list_for_msg    "$P /tw geometry_msgs/msg/Twist '{linear: [1.0, 0.0, 0.0]}'"
c ps_skip_pose       "$P /ps geometry_msgs/msg/PoseStamped '{position: {x: 1.0}}'"
c ps_ok              "$P /ps geometry_msgs/msg/PoseStamped '{header: {frame_id: map}, pose: {position: {x: 1.0, y: 2.0}, orientation: {w: 1.0}}}'"
c pose_question_form "$P /pose geometry_msgs/msg/Pose '{position:{1,1,1},orientation:{1,1,1,1}}'"
c pose_set_form      "$P /pose geometry_msgs/msg/Pose '{position: {1,1,1}, orientation: {1,1,1,1}}'"
c ps_block_yaml      "$P /ps geometry_msgs/msg/PoseStamped \$'header:\n  frame_id: map\npose:\n  position:\n    x: 3.0'"

echo "=== 5. Arrays"
c js_ok              "$P /js sensor_msgs/msg/JointState '{name: [j1, j2], position: [1.0, 2.0]}'"
c js_int_list        "$P /js sensor_msgs/msg/JointState '{name: [j1, j2], position: [1, 2]}'"
c js_quoted_list     "$P /js sensor_msgs/msg/JointState \"{name: [j1, j2], position: '[1,2]'}\""
c js_nospace_list    "$P /js sensor_msgs/msg/JointState '{name: [j1,j2], position: [1.0,2.0]}'"
c js_scalar_for_list "$P /js sensor_msgs/msg/JointState '{position: 1.0}'"
c f64_ok             "$P /f std_msgs/msg/Float64MultiArray '{data: [0.2, 0.4]}'"
c f64_tabcomplete    "$P /f std_msgs/msg/Float64MultiArray 'layout:  dim: []  data_offset: 0data: [0.2]'"
c f64_block          "$P /f std_msgs/msg/Float64MultiArray \$'layout:\n  dim: []\n  data_offset: 0\ndata: [0.2]'"

echo "=== 6. byte[] / uint8[]"
c byte_ints          "$P /b std_msgs/msg/ByteMultiArray '{data: [3, 4]}'"
c byte_hex           "$P /b std_msgs/msg/ByteMultiArray '{data: [0x03, 0x04]}'"
c byte_binary_items  "$P /b std_msgs/msg/ByteMultiArray '{data: [!!binary Aw==, !!binary BA==]}'"
c byte_binary_whole  "$P /b std_msgs/msg/ByteMultiArray '{data: !!binary AwQ=}'"
c u8_ints            "$P /u8 std_msgs/msg/UInt8MultiArray '{data: [3, 4, 255]}'"
c u8_hex             "$P /u8 std_msgs/msg/UInt8MultiArray '{data: [0x03, 0xff]}'"
c u8_256             "$P /u8 std_msgs/msg/UInt8MultiArray '{data: [256]}'"
c u8_neg             "$P /u8 std_msgs/msg/UInt8MultiArray '{data: [-1]}'"
c u8_binary          "$P /u8 std_msgs/msg/UInt8MultiArray '{data: !!binary AwQ=}'"

echo "=== 7. Header stamp"
c ps_stamp_now       "$P /ps geometry_msgs/msg/PoseStamped '{header: {stamp: now, frame_id: map}}'"
c ps_header_auto     "$P /ps geometry_msgs/msg/PoseStamped '{header: auto}'"
c ps_stamp_explicit  "$P /ps geometry_msgs/msg/PoseStamped '{header: {stamp: {sec: 5, nanosec: 0}, frame_id: map}}'"
c ps_stamp_float     "$P /ps geometry_msgs/msg/PoseStamped '{header: {stamp: 5.5}}'"
c ps_no_header       "$P /ps geometry_msgs/msg/PoseStamped '{pose: {position: {x: 1.0}}}'"
c js_header_auto     "$P /js sensor_msgs/msg/JointState '{header: auto, name: [j1], position: [0.5]}'"

echo "=== 8. Service call (std_srvs/SetBool)"
S="ros2 service call /sb std_srvs/srv/SetBool"
c srv_ok             "$S '{data: true}'"
c srv_True           "$S '{data: True}'"
c srv_yes            "$S '{data: yes}'"
c srv_int            "$S '{data: 1}'"
c srv_string         "$S \"{data: 'true'}\""
c srv_nospace        "$S '{data:true}'"
c srv_wrongfield     "$S '{dta: true}'"
c srv_nobrace        "$S 'data: false'"
c srv_noargs         "$S"
c srv_bare_scalar    "$S 'true'"

echo "=== 9. interface proto"
for T in std_msgs/msg/String geometry_msgs/msg/Twist geometry_msgs/msg/PoseStamped sensor_msgs/msg/JointState std_srvs/srv/SetBool std_msgs/msg/ByteMultiArray; do
  echo "--- PROTO $T"; ros2 interface proto $T; echo "EXIT=$?"
done
echo "--- PROTO --no-quotes"; ros2 interface proto --no-quotes geometry_msgs/msg/Twist; echo "EXIT=$?"
c proto_as_arg       "$P /tw geometry_msgs/msg/Twist \"\$(ros2 interface proto geometry_msgs/msg/Twist)\""
c proto_noquotes_arg "$P /tw geometry_msgs/msg/Twist \"\$(ros2 interface proto --no-quotes geometry_msgs/msg/Twist)\""
c proto_ps_as_arg    "$P /ps geometry_msgs/msg/PoseStamped \"\$(ros2 interface proto --no-quotes geometry_msgs/msg/PoseStamped)\""
c proto_srv_as_arg   "$S \"\$(ros2 interface proto --no-quotes std_srvs/srv/SetBool)\""

echo "=== 9b. --stdin / --yaml-file"
printf "data: 'time: 12:30'\n" > /tmp/t/m.yaml
printf "data: true\n" > /tmp/t/sb.yaml
if ros2 topic pub -h 2>&1 | grep -q -- '--stdin'; then
  c pub_stdin        "$P --stdin /s std_msgs/msg/String < /tmp/t/m.yaml"
  c pub_stdin_pos    "$P /s std_msgs/msg/String --stdin < /tmp/t/m.yaml"
else echo "pub --stdin: option not available"; fi
if ros2 topic pub -h 2>&1 | grep -q -- '--yaml-file'; then
  c pub_yaml_file    "$P /s std_msgs/msg/String --yaml-file /tmp/t/m.yaml"
else echo "pub --yaml-file: option not available"; fi
if ros2 service call -h 2>&1 | grep -q -- '--stdin'; then
  c srv_stdin        "$S --stdin < /tmp/t/sb.yaml"
  c srv_stdin_first  "ros2 service call --stdin /sb std_srvs/srv/SetBool < /tmp/t/sb.yaml"
else echo "service call --stdin: option not available"; fi
echo "=== 10. Delivery counts (subscriber 'sink' already running)"
c nosub_once         "ros2 topic pub -1 /nosub std_msgs/msg/String '{data: x}'"
N=20
for k in $(seq $N); do timeout 20 ros2 topic pub -1 /cnt1 std_msgs/msg/String "{data: once_default_$k}" > /dev/null 2>&1; done
sleep 1; echo "COUNT once_default ($N runs): $(grep -c 'RECV /cnt1' sink.log)"
for k in $(seq $N); do timeout 20 ros2 topic pub -1 -w 1 /cnt2 std_msgs/msg/String "{data: once_w1_$k}" > /dev/null 2>&1; done
sleep 1; echo "COUNT once_w1 ($N runs): $(grep -c 'RECV /cnt2' sink.log)"
for k in $(seq $N); do timeout 20 ros2 topic pub -1 -w 0 /cnt3 std_msgs/msg/String "{data: once_w0_$k}" > /dev/null 2>&1; done
sleep 1; echo "COUNT once_w0 ($N runs): $(grep -c 'RECV /cnt3' sink.log)"
echo "once_w0 indices received: $(grep -o 'once_w0_[0-9]*' sink.log | sed 's/once_w0_//' | tr '\n' ' ')"
c nosub_bad_once     "ros2 topic pub -1 /nosub std_msgs/msg/String '{data:hi}'"
c nosub_bad_w0       "ros2 topic pub -1 -w 0 /nosub std_msgs/msg/String '{data:hi}'"
c nosub_once_w0      "ros2 topic pub -1 -w 0 /nosub std_msgs/msg/String '{data: x}'"
c nosub_times_default "ros2 topic pub -t 3 /nosub std_msgs/msg/String '{data: x}'"
c nosub_rate_default "ros2 topic pub -r 10 /nosub std_msgs/msg/String '{data:hi}'"
T=4
for r in 1 2 3; do
  timeout 20 ros2 topic pub -r 10 -t 20 /cnt$T std_msgs/msg/String "{data: t20_default_r$r}" > /dev/null 2>&1
  sleep 1; echo "COUNT round$r rate10_times20_default: $(grep -c "RECV /cnt$T " sink.log)"; T=$((T+1))
  timeout 20 ros2 topic pub -r 10 -t 20 -w 0 /cnt$T std_msgs/msg/String "{data: t20_w0_r$r}" > /dev/null 2>&1
  sleep 1; echo "COUNT round$r rate10_times20_w0: $(grep -c "RECV /cnt$T " sink.log) first_seq_seen=n/a"; T=$((T+1))
  timeout -s INT 3 ros2 topic pub -r 10 /cnt$T std_msgs/msg/String "{data: r3s_r$r}" > pubr.out 2>&1; rc=$?
  sleep 1; echo "COUNT round$r rate10_for_3s_no_t: received=$(grep -c "RECV /cnt$T " sink.log) printed_publishing=$(grep -c 'publishing #' pubr.out) EXIT=$rc"; T=$((T+1))
done
kill %1 %2 2>/dev/null
echo "=== done"
