#!/bin/bash
# Run inside ros:<distro>-ros-base as: bash repro.sh
# Reproduces "error: unrecognized arguments: --ros-args ..." from argparse in a ROS 2
# Python node, compares three parsing modes (strict / known / remove) and the rclcpp
# equivalents (rclcpp::init vs rclcpp::init_and_remove_ros_arguments).
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-rcl 2>/dev/null
python3 --version
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"
W=/ws; mkdir -p $W/src/argp/src $W/src/argp/launch; cd $W/src/argp
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>argp</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><exec_depend>rclpy</exec_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(argp)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cppnode src/cppnode.cpp)
target_link_libraries(cppnode rclcpp::rclcpp)
install(TARGETS cppnode DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS argnode.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()
X
cat > argnode.py <<'X'
#!/usr/bin/env python3
import argparse, os, sys
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
mode = os.environ.get('MODE', 'strict')
print('ARGV', sys.argv[1:], flush=True)
p = argparse.ArgumentParser()
p.add_argument('--speed', type=float, default=1.0)
if os.environ.get('RFLAG'):
    p.add_argument('-r', '--repeat', default='none')
if mode == 'strict':
    a = p.parse_args()
elif mode == 'known':
    a, extra = p.parse_known_args()
    print('EXTRA', extra, flush=True)
elif mode == 'remove':
    rest = remove_ros_args(args=sys.argv)
    print('REMOVED', rest[1:], flush=True)
    a = p.parse_args(rest[1:])
rclpy.init(args=sys.argv)
n = Node('argnode')
rate = n.declare_parameter('rate', 1).value
extra = f' repeat={a.repeat}' if hasattr(a, 'repeat') else ''
print(f'RESULT mode={mode} speed={a.speed} node={n.get_fully_qualified_name()} rate={rate}{extra}', flush=True)
n.destroy_node()
rclpy.shutdown()
X
chmod +x argnode.py
cat > src/cppnode.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
int main(int argc, char ** argv) {
  std::vector<std::string> rest;
  const char * m = std::getenv("CPPMODE");
  if (m && std::string(m) == "remove") {
    rest = rclcpp::init_and_remove_ros_arguments(argc, argv);
  } else {
    rclcpp::init(argc, argv);
    for (int i = 0; i < argc; ++i) rest.push_back(argv[i]);
  }
  printf("ARGS_SEEN %zu:", rest.size() - 1);
  for (size_t i = 1; i < rest.size(); ++i) printf(" [%s]", rest[i].c_str());
  printf("\n");
  auto n = std::make_shared<rclcpp::Node>("cppnode");
  long rate = n->declare_parameter<int64_t>("rate", 1);
  printf("RESULT cpp node=%s rate=%ld\n", n->get_fully_qualified_name(), rate);
  fflush(stdout);
  rclcpp::shutdown();
}
X
cat > launch/plain.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='argp', executable='argnode.py', output='screen',
                                   arguments=['--speed', '2.0'])])
X
cat > launch/named.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='argp', executable='argnode.py', output='screen',
                                   name='renamed', parameters=[{'rate': 5}],
                                   arguments=['--speed', '2.0'])])
X
cat > launch/rosargs.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='argp', executable='argnode.py', output='screen',
                                   ros_arguments=['-p', 'rate:=7'],
                                   arguments=['--speed', '2.0'])])
X
cat > launch/cpp.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='argp', executable='cppnode', output='screen',
                                   name='cpp_renamed', parameters=[{'rate': 5}],
                                   arguments=['--speed', '2.0'])])
X
cd $W && MAKEFLAGS=-j2 colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
echo "build ok"
source $W/install/setup.bash

run() {  # run <label> <env...> -- <cmd...>
  local label=$1; shift
  echo; echo "### $label"
  local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  echo "\$ ${envs[*]} $*"
  local t0=$(date +%s%N)
  env "${envs[@]}" timeout 40 "$@" 2>&1 | grep -v '^\[INFO\] \[launch\]: All log files' 
  local rc=${PIPESTATUS[0]}
  local t1=$(date +%s%N)
  echo "EXIT=$rc ELAPSED_MS=$(( (t1-t0)/1000000 ))"
}

echo; echo "===== A. ros2 run, strict argparse (parse_args)"
run A1 MODE=strict -- ros2 run argp argnode.py --speed 2.0
run A2 MODE=strict -- ros2 run argp argnode.py --speed 2.0 --ros-args -p rate:=5
run A3 MODE=strict -- ros2 run argp argnode.py --ros-args -r __node:=renamed
run A4 MODE=strict -- ros2 run argp argnode.py --speed 2.0 --ros-args --log-level warn
echo; echo "===== B. ros2 launch, strict argparse"
run B1 MODE=strict -- ros2 launch argp plain.launch.py
run B2 MODE=strict -- ros2 launch argp named.launch.py
run B3 MODE=strict -- ros2 launch argp rosargs.launch.py
echo; echo "===== C. parse_known_args"
run C1 MODE=known -- ros2 run argp argnode.py --speed 2.0 --ros-args -p rate:=5
run C2 MODE=known -- ros2 launch argp named.launch.py
run C3 MODE=known -- ros2 run argp argnode.py --sped 2.0 --ros-args -p rate:=5
run C4 MODE=known RFLAG=1 -- ros2 run argp argnode.py --speed 2.0 --ros-args -r __node:=renamed
echo; echo "===== D. remove_ros_args"
run D1 MODE=remove -- ros2 run argp argnode.py --speed 2.0 --ros-args -p rate:=5
run D2 MODE=remove -- ros2 launch argp named.launch.py
run D3 MODE=remove -- ros2 run argp argnode.py --sped 2.0 --ros-args -p rate:=5
run D4 MODE=remove RFLAG=1 -- ros2 run argp argnode.py --speed 2.0 --ros-args -r __node:=renamed
run D5 MODE=remove -- ros2 run argp argnode.py --ros-args -p rate:=5 -- --speed 2.0
run D6 MODE=remove -- ros2 run argp argnode.py --ros-args -p rate:=5 --speed 2.0
run D7 MODE=strict -- ros2 run argp argnode.py --ros-args -p rate:=5 --speed 2.0
run D8 MODE=remove -- ros2 run argp argnode.py --speed 2.0 --ros-args -r __node:=a --ros-args -p rate:=6
echo; echo "===== E. rclcpp"
run E1 CPPMODE=plain -- ros2 run argp cppnode --speed 2.0 --ros-args -p rate:=5
run E2 CPPMODE=remove -- ros2 run argp cppnode --speed 2.0 --ros-args -p rate:=5
run E3 CPPMODE=remove -- ros2 launch argp cpp.launch.py
run E4 CPPMODE=remove -- ros2 run argp cppnode --ros-args -p rate:=5 --speed 2.0
echo; echo "===== F. rclpy.init with sys.argv vs a cleaned list (strict parser, ROS args still applied?)"
cat > /tmp/f.py <<'X'
import sys, rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
argv = ['prog', '--speed', '2.0', '--ros-args', '-p', 'rate:=5']
rclpy.init(args=remove_ros_args(args=argv))
n = Node('argnode'); print('init(cleaned) rate =', n.declare_parameter('rate', 1).value); n.destroy_node(); rclpy.shutdown()
rclpy.init(args=argv)
n = Node('argnode'); print('init(full) rate =', n.declare_parameter('rate', 1).value); n.destroy_node(); rclpy.shutdown()
X
run F1 -- python3 /tmp/f.py
echo; echo "=== done"
