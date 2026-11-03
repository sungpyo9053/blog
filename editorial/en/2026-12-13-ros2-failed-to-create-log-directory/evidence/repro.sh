#!/bin/bash
# Run inside ros:<distro>-ros-base as root (docker run --rm ... bash /w/repro.sh).
# Reproduces "Failed to create log directory" / "Failed to get logging directory"
# in rclpy, rclcpp, ros2 launch and the ros2 CLI, then compares the fixes.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcl-logging-spdlog \
  ros-$ROS_DISTRO-rcutils ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-rcl-logging-interface 2>/dev/null
echo "RMW_IMPLEMENTATION env: '${RMW_IMPLEMENTATION}'"
ls /opt/ros/$ROS_DISTRO/lib | grep -i 'rcl_logging' | sed 's/^/logging lib: /'
id

# --- tiny nodes ---
mkdir -p /ws/src/lognode/src && cd /ws/src/lognode
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>lognode</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(lognode)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cpp_node src/node.cpp)
target_link_libraries(cpp_node rclcpp::rclcpp)
install(TARGETS cpp_node DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py_node.py DESTINATION lib/${PROJECT_NAME})
install(FILES one.launch.py DESTINATION share/${PROJECT_NAME})
ament_package()
X
cat > src/node.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("cpp_node");
  RCLCPP_INFO(n->get_logger(), "NODE-OK");
  rclcpp::shutdown();
}
X
cat > py_node.py <<'X'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node('py_node')
n.get_logger().info('NODE-OK')
rclpy.shutdown()
X
chmod +x py_node.py
cat > one.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lognode', executable='py_node.py', output='screen')])
X
cd /ws && colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
chmod -R a+rX /ws
source /ws/install/setup.bash
PY=/ws/install/lognode/lib/lognode/py_node.py
CPP=/ws/install/lognode/lib/lognode/cpp_node

# non-root user 1234 whose HOME is /home/u (owned by root, not writable)
mkdir -p /home/u && chmod 755 /home/u
AS_U="setpriv --reuid=1234 --regid=1234 --clear-groups"

# run <label> <env args...> -- <cmd...>
run() {
  local label=$1; shift
  local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  local t0=$(date +%s%N)
  timeout 60 env "${envs[@]}" "$@" >/tmp/o.txt 2>&1; local rc=$?
  local ms=$(( ($(date +%s%N)-t0)/1000000 ))
  echo "--- [$label] rc=$rc ms=$ms"
  grep -vE '^\s*$' /tmp/o.txt | grep -E 'NODE-OK|rror|what\(\)|terminate|Abort|Traceback|logging|Permission|Exception' | head -8 | cut -c1-400
}
nfiles() { find "$@" -type f 2>/dev/null | wc -l; }

echo; echo "##### A. causes (python node / C++ node)"
for KIND in py cpp; do
  B=$PY; [ $KIND = cpp ] && B=$CPP
  rm -rf /root/.ros
  run "$KIND A1 root, HOME=/root" HOME=/root -- $B
  echo "    files in /root/.ros/log: $(nfiles /root/.ros/log)"
  run "$KIND A2 uid 1234, HOME=/home/u not writable" HOME=/home/u -- $AS_U $B
  run "$KIND A3 uid 1234, HOME unset" -u HOME -- $AS_U $B
  run "$KIND A4 uid 1234, HOME empty" HOME= -- $AS_U $B
  run "$KIND A5 uid 1234, HOME=/nonexistent" HOME=/nonexistent -- $AS_U $B
  # ~/.ros/log exists but owned by root (e.g. made by an earlier root run or a mounted volume)
  rm -rf /home/r && mkdir -p /home/r/.ros/log && chown 1234:1234 /home/r && chmod 755 /home/r/.ros/log
  run "$KIND A6 uid 1234, ~/.ros/log exists, owned by root" HOME=/home/r -- $AS_U $B
  run "$KIND A7 uid 1234, ROS_LOG_DIR=/var/log/ros (not writable)" HOME=/home/u ROS_LOG_DIR=/var/log/ros -- $AS_U $B
  run "$KIND A8 uid 1234, HOME unset, ROS_LOG_DIR=/tmp/ld_$KIND" -u HOME ROS_LOG_DIR=/tmp/ld_$KIND -- $AS_U $B
  echo "    files in /tmp/ld_$KIND: $(nfiles /tmp/ld_$KIND)"
  run "$KIND A9 uid 1234, HOME unset, ROS_HOME=/tmp/rh_$KIND" -u HOME ROS_HOME=/tmp/rh_$KIND -- $AS_U $B
  echo "    dirs with files under /tmp/rh_$KIND: $(find /tmp/rh_$KIND -type f 2>/dev/null | sed 's#/[^/]*$##' | sort -u | tr '\n' ' ')"
done

echo; echo "##### B. fixes for uid 1234 with HOME=/home/u not writable"
for KIND in py cpp; do
  B=$PY; [ $KIND = cpp ] && B=$CPP
  rm -rf /tmp/ld /tmp/rhb
  run "$KIND B1 ROS_LOG_DIR=/tmp/ld" HOME=/home/u ROS_LOG_DIR=/tmp/ld -- $AS_U $B
  echo "    files in /tmp/ld: $(nfiles /tmp/ld)"
  run "$KIND B2 ROS_HOME=/tmp/rhb" HOME=/home/u ROS_HOME=/tmp/rhb -- $AS_U $B
  echo "    files in /tmp/rhb/log: $(nfiles /tmp/rhb/log)"
  run "$KIND B3 HOME=/tmp/hb_$KIND (writable, created by the node)" HOME=/tmp/hb_$KIND -- $AS_U $B
  echo "    files in /tmp/hb_$KIND/.ros/log: $(nfiles /tmp/hb_$KIND/.ros/log)"
  run "$KIND B4 --ros-args --disable-external-lib-logs" HOME=/home/u -- $AS_U $B --ros-args --disable-external-lib-logs
  run "$KIND B5 ROS_LOG_DIR=~/logs (literal tilde)" HOME=/tmp/hb_$KIND 'ROS_LOG_DIR=~/logs' -- $AS_U $B
  echo "    /tmp/hb_$KIND/logs files: $(nfiles /tmp/hb_$KIND/logs)"
  run "$KIND B6 ROS_LOG_DIR= (empty)" HOME=/tmp/hb_$KIND ROS_LOG_DIR= -- $AS_U $B
  echo "    /tmp/hb_$KIND/.ros/log files now: $(nfiles /tmp/hb_$KIND/.ros/log)"
  run "$KIND B7 ROS_LOG_DIR=/tmp/a/b/c_$KIND (nested, missing)" HOME=/home/u ROS_LOG_DIR=/tmp/a/b/c_$KIND -- $AS_U $B
  echo "    /tmp/a/b/c_$KIND files: $(nfiles /tmp/a/b/c_$KIND)"
  run "$KIND B8 ROS_LOG_DIR=/dev/null" HOME=/home/u ROS_LOG_DIR=/dev/null -- $AS_U $B
done

echo; echo "##### C. ros2 launch and ros2 CLI"
run "C1 ros2 launch, HOME=/home/u" HOME=/home/u -- $AS_U ros2 launch lognode one.launch.py
grep -iE 'error|denied|launch' /tmp/o.txt | head -6 | cut -c1-300
rm -rf /tmp/lc
run "C2 ros2 launch, ROS_LOG_DIR=/tmp/lc" HOME=/home/u ROS_LOG_DIR=/tmp/lc -- $AS_U ros2 launch lognode one.launch.py
echo "    /tmp/lc files: $(find /tmp/lc -type f | sed 's#/tmp/lc/##' | sed 's#[0-9_-]\{8,\}#<ts>#g' | sort | tr '\n' ' ')"
run "C3 ros2 launch, HOME unset" -u HOME -- $AS_U ros2 launch lognode one.launch.py
grep -iE 'error|denied' /tmp/o.txt | head -4 | cut -c1-300
run "C4 ros2 run, HOME=/home/u" HOME=/home/u -- $AS_U ros2 run lognode py_node.py
run "C5 ros2 topic list --no-daemon, HOME=/home/u" HOME=/home/u -- $AS_U ros2 topic list --no-daemon
head -3 /tmp/o.txt | cut -c1-200
run "C6 ros2 topic pub --once, HOME=/home/u" HOME=/home/u -- $AS_U ros2 topic pub --once /x std_msgs/msg/String "{data: hi}"
tail -3 /tmp/o.txt | cut -c1-200
run "C7 ros2 run with --disable-external-lib-logs, HOME=/home/u" HOME=/home/u -- $AS_U ros2 run lognode py_node.py --ros-args --disable-external-lib-logs

echo; echo "##### D. log growth and cost (root, fresh dir, 20 runs each)"
rm -rf /tmp/grow /tmp/grow2 /tmp/grow3 /tmp/grow4
t0=$(date +%s%N); for i in $(seq 1 20); do ROS_LOG_DIR=/tmp/grow $PY >/dev/null 2>&1; done
echo "D1 python with file logging: $(( ($(date +%s%N)-t0)/1000000 )) ms, files=$(nfiles /tmp/grow), bytes=$(du -sb /tmp/grow | cut -f1)"
t0=$(date +%s%N); for i in $(seq 1 20); do ROS_LOG_DIR=/tmp/grow2 $PY --ros-args --disable-external-lib-logs >/dev/null 2>&1; done
echo "D2 python --disable-external-lib-logs: $(( ($(date +%s%N)-t0)/1000000 )) ms, files=$(nfiles /tmp/grow2)"
t0=$(date +%s%N); for i in $(seq 1 20); do ROS_LOG_DIR=/tmp/grow3 $CPP >/dev/null 2>&1; done
echo "D3 C++ with file logging: $(( ($(date +%s%N)-t0)/1000000 )) ms, files=$(nfiles /tmp/grow3), bytes=$(du -sb /tmp/grow3 | cut -f1)"
t0=$(date +%s%N); for i in $(seq 1 20); do ROS_LOG_DIR=/tmp/grow4 $CPP --ros-args --disable-external-lib-logs >/dev/null 2>&1; done
echo "D4 C++ --disable-external-lib-logs: $(( ($(date +%s%N)-t0)/1000000 )) ms, files=$(nfiles /tmp/grow4)"
echo "D5 sample file names:"; ls /tmp/grow | head -2; ls /tmp/grow3 | head -2
echo "D6 sample content:"; cat "$(ls -d /tmp/grow/* | head -1)" | head -3

echo; echo "##### E. 10 C++ nodes started at once into a missing nested dir, 5 rounds"
# (container runs with --pids-limit 200; a first try with 20 nodes hit that limit, see out_humble_try1.txt)
for r in 1 2 3 4 5; do
  rm -rf /tmp/race /tmp/race_*; fails=0
  for i in $(seq 1 10); do ( ROS_LOG_DIR=/tmp/race/a/b timeout 60 $CPP >/tmp/race_$i.txt 2>&1; echo $? >/tmp/race_rc_$i ) & done; wait
  for i in $(seq 1 10); do [ "$(cat /tmp/race_rc_$i)" != 0 ] && fails=$((fails+1)); done
  echo "E round $r: nonzero=$fails log_files=$(nfiles /tmp/race) log_dir_errors=$(cat /tmp/race_[0-9]*.txt | grep -c 'log directory')"
  [ $fails -gt 0 ] && grep -h -m1 'what' /tmp/race_[0-9]*.txt | sort | uniq -c | head -3
done
echo "=== done $ROS_DISTRO"
