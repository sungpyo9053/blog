#!/bin/bash
# Usage on the host: ./repro.sh <distro>   (humble | jazzy | lyrical)
# Runs inside ros:<distro>-ros-base with --network none and DDS kept local.
# Needs exp_py.py and init_twice.cpp next to this script.
set -u
D=$1
HERE=$(cd "$(dirname "$0")" && pwd)
ulimit -c 0
docker run --rm --name pk26-$D --network none --cpus 1 --memory 1g --pids-limit 30 \
  --ulimit core=0 \
  -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  -v "$HERE":/exp:ro ros:$D-ros-base bash -c '
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro $ROS_DISTRO"
python3 --version
dpkg-query -W -f="\${Package} \${Version}\n" ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset, default>}"
echo
echo "##### rclpy"
for c in twice reinit guard try_shutdown ctxmgr context rerun unittest timing timing timing; do
  echo "--- py:$c"; timeout 60 python3 /exp/exp_py.py $c 2>&1 | tail -n 12; echo "exit=${PIPESTATUS[0]}"
done
echo "--- py:uncaught (full stderr)"; timeout 60 python3 /exp/exp_py.py uncaught 2>&1 | tail -n 8; echo "exit=${PIPESTATUS[0]}"
echo
echo "##### rclcpp"
mkdir -p /ws/src/it && cd /ws/src/it && cp /exp/init_twice.cpp .
cat > package.xml <<EOF
<?xml version="1.0"?>
<package format="3"><name>it</name><version>0.0.0</version><description>x</description>
<maintainer email="dev@example.com">x</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
EOF
cat > CMakeLists.txt <<EOF
cmake_minimum_required(VERSION 3.8)
project(it)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(init_twice init_twice.cpp)
target_link_libraries(init_twice rclcpp::rclcpp \${std_msgs_TARGETS})
install(TARGETS init_twice DESTINATION lib/\${PROJECT_NAME})
ament_package()
EOF
cd /ws && MAKEFLAGS=-j1 timeout 600 colcon build --event-handlers console_direct- > /tmp/build.log 2>&1; echo "colcon exit=$?"; grep -m8 -A3 -E "error|Error" /tmp/build.log; tail -n 3 /tmp/build.log
B=/ws/install/it/lib/it/init_twice
for c in twice reinit guard fixture context timing timing timing; do
  echo "--- cpp:$c"; timeout 60 $B $c 2>&1 | tail -n 12; echo "exit=${PIPESTATUS[0]}"
done
echo "--- cpp:uncaught"; timeout 60 $B uncaught 2>&1 | tail -n 6; echo "exit=${PIPESTATUS[0]}"
'
