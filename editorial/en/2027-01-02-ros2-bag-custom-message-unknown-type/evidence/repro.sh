#!/bin/bash
# Run inside ros:<distro>-ros-base (as measured, one distro after another):
#   docker run --rm --network none -e ROS_DOMAIN_ID=88 --pids-limit 512 --ulimit core=0 --cpus 1.5 \
#     -v $PWD:/e ros:<distro>-ros-base bash /e/repro.sh
# Humble: ros:humble-ros-base has no MCAP storage plugin, so it was measured on an image made with
#   docker run --name pk24-hprep ros:humble-ros-base bash -c "apt-get update && apt-get install -y ros-humble-rosbag2-storage-mcap"
#   docker commit pk24-hprep pk24-humble-mcap:1     (then the docker run above with --network none)
# Measures what ros2 bag record / play / info and rosbag2_py do with a custom message type
# when the shell has, or has not, sourced the workspace that defines it.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1 MAKEFLAGS=-j1
D=$ROS_DISTRO
echo "=== distro=$D rmw=${RMW_IMPLEMENTATION:-default} domain=$ROS_DOMAIN_ID"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rosbag2 \
  ros-$D-rosbag2-storage-default-plugins ros-$D-rosbag2-storage-mcap ros-$D-rosbag2-py ros-$D-rmw-fastrtps-cpp 2>/dev/null
W=/w; mkdir -p $W; cd $W

mkpkg() {  # mkpkg <ws> <pkg> <msg body> [package.xml extra mode]
  local p=$W/$1/src/$2; mkdir -p $p/msg
  printf "$3" > $p/msg/Reading.msg
  local group='<member_of_group>rosidl_interface_packages</member_of_group>'
  local exp='<build_type>ament_cmake</build_type>'
  [ "$4" = nogroup ] && group=''
  [ "$4" = archind ] && exp='<build_type>ament_cmake</build_type><architecture_independent/>'
  cat > $p/package.xml <<X
<?xml version="1.0"?>
<package format="3">
  <name>$2</name><version>0.0.1</version><description>t</description>
  <maintainer email="t@example.com">t</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  $group
  <export>$exp</export>
</package>
X
  cat > $p/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($2)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(\${PROJECT_NAME} "msg/Reading.msg")
ament_package()
X
}
build() {  # build <ws>
  echo "--- BUILD $1"
  local t0=$(date +%s)
  (cd $W/$1 && timeout 600 colcon build --parallel-workers 1 --event-handlers console_direct- > build.log 2>&1); local rc=$?
  echo "build exit=$rc secs=$(( $(date +%s) - t0 ))"
  grep -iE -A2 "error|warn|member_of_group" $W/$1/build.log | grep -v -- "-Werror" | head -12
  tail -3 $W/$1/build.log
}

mkpkg ws1 my_msgs 'int32 seq\nfloat64 value\nstring note\n'
mkpkg ws2 my_msgs 'float64 value\nint32 seq\nstring note\nfloat64 extra\n'   # same name, changed definition
mkpkg ws3 nogroup_msgs 'int32 seq\nfloat64 value\nstring note\n' nogroup
mkpkg ws4 archind_msgs 'int32 seq\nfloat64 value\nstring note\n' archind
for w in ws1 ws2 ws3 ws4; do build $w; done

# pub.py <topic> <type> <hz> <secs> : publishes seq 0.. ; sub.py <topic> <type> <secs> : counts
cat > $W/pub.py <<'X'
import sys, time, rclpy
from rosidl_runtime_py.utilities import get_message
topic, typ, hz, secs = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
rclpy.init(); n = rclpy.create_node('pub_node'); M = get_message(typ)
p = n.create_publisher(M, topic, 10); i = 0; t0 = time.time()
while time.time() - t0 < secs:
    m = M(); m.seq = i; m.value = i * 0.5; m.note = f'n{i}'; p.publish(m); i += 1
    rclpy.spin_once(n, timeout_sec=1.0 / hz)
print(f'PUB sent={i}')
X
cat > $W/sub.py <<'X'
import sys, time, rclpy
from rosidl_runtime_py.utilities import get_message
topic, typ, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
rclpy.init(); n = rclpy.create_node('sub_node'); M = get_message(typ); got = []
n.create_subscription(M, topic, lambda m: got.append(m), 100); t0 = time.time()
while time.time() - t0 < secs: rclpy.spin_once(n, timeout_sec=0.1)
print(f'SUB received={len(got)}')
for m in got[:2]: print('SUB msg', m)
X
cat > $W/readbag.py <<'X'
import sys, rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
uri, sid = sys.argv[1], sys.argv[2]
r = rosbag2_py.SequentialReader()
r.open(rosbag2_py.StorageOptions(uri=uri, storage_id=sid), rosbag2_py.ConverterOptions('cdr', 'cdr'))
types = {t.name: t.type for t in r.get_all_topics_and_types()}
print('READ topics', types)
n = 0
while r.has_next():
    topic, data, ts = r.read_next()
    if n == 0:
        try:
            M = get_message(types[topic]); print('READ first', deserialize_message(data, M))
        except Exception as e:
            print('READ deserialize error:', type(e).__name__, e)
    n += 1
print('READ raw messages', n)
X

S0="source /opt/ros/$D/setup.bash"
S1="$S0; source $W/ws1/install/setup.bash"
S2="$S0; source $W/ws2/install/setup.bash"
S3="$S0; source $W/ws3/install/setup.bash"
S4="$S0; source $W/ws4/install/setup.bash"
TOPICS_FLAG=""; ros2 bag record --help 2>/dev/null | grep -q -- '--topics' && TOPICS_FLAG="--topics"
echo "record topic flag: '${TOPICS_FLAG}'"
echo "storage plugins: $(ros2 bag record --help | tr -d "\n " | grep -o "\-s{[^}]*}")"

info() {  # info <env> <bag>
  bash -c "$1; timeout 60 ros2 bag info $2" 2>&1 | grep -E 'Storage id|Messages|Topic:|Type:|Count|rror|WARN' | head -6
}
record() {  # record <label> <recorder env> <type> <storage> [extra record args]
  local L=$1 E=$2 T=$3 ST=$4; shift 4
  echo "--- RECORD $L (storage=$ST type=$T)"
  rm -rf $W/bag_$L
  bash -c "$S1; $S3; $S4; python3 $W/pub.py /reading $T 20 7" > $W/pub_$L.txt 2>&1 &
  local pp=$!
  sleep 1
  local t0=$(date +%s.%N)
  bash -c "$E; timeout -s INT 5 ros2 bag record -s $ST -o $W/bag_$L $TOPICS_FLAG /reading $*" > $W/rec_$L.txt 2>&1
  echo "record exit=$? secs=$(python3 -c "print(round($(date +%s.%N)-$t0,2))")"
  wait $pp; cat $W/pub_$L.txt
  echo "unknown-type warnings in recorder output: $(grep -c 'unknown type' $W/rec_$L.txt)"
  grep -vE 'Listening|Subscribed|Pausing|Recording\.\.\.|^$' $W/rec_$L.txt | cut -c1-300 | head -8
  [ -d $W/bag_$L ] && info "$S0" $W/bag_$L || echo "no bag directory"
}
play() {  # play <label> <player env> <subscriber env> <type> <bag> [extra play args]
  local L=$1 E=$2 SE=$3 T=$4 B=$5; shift 5
  echo "--- PLAY $L"
  bash -c "$SE; python3 $W/sub.py /reading $T 9" > $W/sub_$L.txt 2>&1 &
  local sp=$!
  sleep 2
  local t0=$(date +%s.%N)
  bash -c "$E; timeout 60 ros2 bag play $B $*" > $W/play_$L.txt 2>&1
  echo "play exit=$? secs=$(python3 -c "print(round($(date +%s.%N)-$t0,2))")"
  grep -vE '^\s*$|Press SPACE|Playback until|Adding keyboard' $W/play_$L.txt | cut -c1-400 | head -8
  wait $sp; cut -c1-300 $W/sub_$L.txt | head -4
}

echo "##### 1. recording"
record src_db3 "$S1" my_msgs/msg/Reading sqlite3
record unsrc_db3 "$S0" my_msgs/msg/Reading sqlite3
record src_mcap "$S1" my_msgs/msg/Reading mcap
record unsrc_mcap "$S0" my_msgs/msg/Reading mcap
echo "--- RECORD unsrc_all (-a, unsourced)"
rm -rf $W/bag_all
bash -c "$S1; python3 $W/pub.py /reading my_msgs/msg/Reading 20 7" > /dev/null 2>&1 & pp=$!
sleep 1; bash -c "$S0; timeout -s INT 5 ros2 bag record -s sqlite3 -o $W/bag_all -a" > $W/rec_all.txt 2>&1; echo "record exit=$?"
wait $pp
grep -iE 'reading|unknown|warn|error' $W/rec_all.txt | cut -c1-300 | head -6
[ -d $W/bag_all ] && info "$S0" $W/bag_all
record nogroup_src "$S3" nogroup_msgs/msg/Reading sqlite3
record archind_src "$S4" archind_msgs/msg/Reading sqlite3

echo "##### 2. bag info without the workspace"
info "$S0" $W/bag_src_db3
info "$S0" $W/bag_src_mcap

echo "##### 3. playback"
play db3_src_player   "$S1" "$S1" my_msgs/msg/Reading $W/bag_src_db3
play db3_unsrc_player "$S0" "$S1" my_msgs/msg/Reading $W/bag_src_db3
play db3_unsrc_topics "$S0" "$S1" my_msgs/msg/Reading $W/bag_src_db3 --topics /reading
play mcap_src_player  "$S1" "$S1" my_msgs/msg/Reading $W/bag_src_mcap
play mcap_unsrc_player "$S0" "$S1" my_msgs/msg/Reading $W/bag_src_mcap
play ament_only "export AMENT_PREFIX_PATH=$W/ws1/install/my_msgs:\$AMENT_PREFIX_PATH" "$S1" my_msgs/msg/Reading $W/bag_src_db3
play changed_def "$S2" "$S2" my_msgs/msg/Reading $W/bag_src_db3
play changed_def_mcap "$S2" "$S2" my_msgs/msg/Reading $W/bag_src_mcap

echo "##### 4. rosbag2_py reading"
for e in S0 S1 S2; do
  for b in db3:sqlite3 mcap:mcap; do
    echo "--- READ env=$e bag=${b%%:*}"
    bash -c "${!e}; timeout 60 python3 $W/readbag.py $W/bag_src_${b%%:*} ${b##*:}" 2>&1 | cut -c1-300 | tail -4
  done
done

echo "##### 5. what the metadata stores"
python3 -c "
import yaml; m = yaml.safe_load(open('$W/bag_src_db3/metadata.yaml'))['rosbag2_bagfile_information']
print('metadata version', m['version'])
for t in m['topics_with_message_count']:
    print({k: v for k, v in t['topic_metadata'].items() if k != 'offered_qos_profiles'})
"
echo "=== done"
