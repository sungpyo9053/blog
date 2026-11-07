#!/bin/bash
# ROS 2 component load failures, measured.
# "Failed to find class with the requested plugin name", "Could not find requested resource in ament index",
# invalid ELF header (STATIC library), undefined symbol, constructor exceptions, wrong container names,
# Python packages, unsourced containers and stale libraries after a rebuild.
# Usage on the runner:  ./repro.sh humble|jazzy|lyrical > out_<distro>.txt 2>&1
# One container per distro, --network none (DDS isolated), ROS_DOMAIN_ID=88, core dumps off.
set -u
D=$1
W=/tmp/en-pick35
mkdir -p $W
ulimit -c 0
sed -n '/^#__INNER__$/,$p' "$0" | tail -n +2 > $W/inner.sh
docker run --rm --name pk25-$D --network none --ulimit core=0 --pids-limit 300 \
  -e ROS_DOMAIN_ID=88 -e D=$D -v $W/inner.sh:/inner.sh:ro \
  ros:$D-ros-base timeout 1500 bash /inner.sh
echo "docker exit: $?"
exit 0
#__INNER__
source /opt/ros/$D/setup.bash
export RCUTILS_COLORIZED_OUTPUT=0 MAKEFLAGS=-j2
echo "### distro=$D"
for p in rclcpp rclcpp_components rclpy ros2cli ros2component launch_ros class_loader rmw rmw_fastrtps_cpp; do
  echo "pkg $p $(ros2 pkg xml $p 2>/dev/null | grep -m1 -o '<version>[^<]*' | cut -c10-)"; done
echo "RMW default: ${RMW_IMPLEMENTATION:-unset}"
echo "### packages with 'component' in the name"; ros2 pkg list | grep -i component
which g++ cmake | sed 's/^/tool: /'

ws=/ws; mkdir -p $ws/src/comp_demo/src $ws/src/comp_static/src $ws/src/py_demo/py_demo $ws/src/py_demo/resource
cd $ws/src/comp_demo
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3"><name>comp_demo</name><version>0.0.1</version><description>d</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>rclcpp_components</depend>
<export><build_type>ament_cmake</build_type></export></package>
EOF
mk() { # $1 class  $2 extra body  $3 macro yes/no
cat > src/$1.cpp <<EOF
#include <rclcpp/rclcpp.hpp>
#include <stdexcept>
#ifndef VER
#define VER "v1"
#endif
extern int never_defined_value;
namespace comp_demo {
class $1 : public rclcpp::Node {
public:
  explicit $1(const rclcpp::NodeOptions & o) : Node("${1,,}", o) {
    $2
    RCLCPP_INFO(get_logger(), "$1 constructed, build %s", VER);
  }
};
}
EOF
[ "$3" = yes ] && echo "#include <rclcpp_components/register_node_macro.hpp>
RCLCPP_COMPONENTS_REGISTER_NODE(comp_demo::$1)" >> src/$1.cpp
}
mk Talker "" yes
mk Unregistered "" yes
mk NoMacro "" no
mk Undef "volatile int x = never_defined_value; (void)x;" yes
mk Thrower "throw std::runtime_error(\"camera not found\");" yes
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(comp_demo)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
if(NOT DEFINED VER)
  set(VER v1)
endif()
foreach(c Talker Unregistered NoMacro Undef Thrower)
  add_library(${c}_lib SHARED src/${c}.cpp)
  target_compile_definitions(${c}_lib PRIVATE VER="${VER}")
  target_link_libraries(${c}_lib rclcpp::rclcpp rclcpp_components::component)
  install(TARGETS ${c}_lib LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)
endforeach()
# registered (Talker also gets a standalone executable)
rclcpp_components_register_node(Talker_lib PLUGIN "comp_demo::Talker" EXECUTABLE talker_exec)
rclcpp_components_register_nodes(NoMacro_lib "comp_demo::NoMacro")
rclcpp_components_register_nodes(Undef_lib "comp_demo::Undef")
rclcpp_components_register_nodes(Thrower_lib "comp_demo::Thrower")
# Unregistered_lib: macro in the .cpp, but no rclcpp_components_register_node(s) call
ament_package()
EOF

cd $ws/src/comp_static
sed 's/comp_demo/comp_static/' ../comp_demo/package.xml > package.xml
sed -e 's/class Talker/class StaticTalker/' -e 's/Talker(const/StaticTalker(const/' -e 's/"talker"/"static_talker"/' \
    -e 's/comp_demo::Talker/comp_demo::StaticTalker/' ../comp_demo/src/Talker.cpp > src/StaticTalker.cpp
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(comp_static)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
add_library(static_talker STATIC src/StaticTalker.cpp)
set_target_properties(static_talker PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_libraries(static_talker rclcpp::rclcpp rclcpp_components::component)
rclcpp_components_register_nodes(static_talker "comp_demo::StaticTalker")
install(TARGETS static_talker LIBRARY DESTINATION lib ARCHIVE DESTINATION lib)
ament_package()
EOF

cd $ws/src/py_demo
touch resource/py_demo py_demo/__init__.py
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3"><name>py_demo</name><version>0.0.1</version><description>d</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license><exec_depend>rclpy</exec_depend>
<export><build_type>ament_python</build_type></export></package>
EOF
cat > py_demo/node.py <<'EOF'
import rclpy
from rclpy.node import Node
class PyTalker(Node):
    def __init__(self):
        super().__init__('py_talker')
def main():
    rclpy.init(); n = PyTalker(); n.get_logger().info('py_talker up'); n.destroy_node(); rclpy.shutdown()
EOF
cat > setup.py <<'EOF'
from setuptools import setup
setup(name='py_demo', version='0.0.1', packages=['py_demo'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/py_demo']), ('share/py_demo', ['package.xml'])],
      entry_points={'console_scripts': ['py_talker = py_demo.node:main']})
EOF

cd $ws
echo "### build (uptime: $(cat /proc/loadavg))"
t0=$(date +%s.%N)
colcon build --parallel-workers 1 --continue-on-error --event-handlers console_direct- 2>&1 | grep -v '^\s*$' | tail -40
echo "build seconds: $(python3 -c "print(round($(date +%s.%N)-$t0,1))")"
echo "### installed libs"; ls install/comp_demo/lib install/comp_static/lib 2>&1
echo "### rclcpp_components resource files"
for f in install/*/share/ament_index/resource_index/rclcpp_components/*; do echo "-- $f"; cat $f; done
source install/setup.bash

echo "### ros2 component types (filtered)"
ros2 component types 2>&1 | grep -A6 -E '^(comp_demo|comp_static|py_demo)'

start_container() { # $1 node name, $2 setup to source
  ( source $2; exec ros2 run rclcpp_components component_container --ros-args -r __node:=$1 ) > /tmp/c_$1.log 2>&1 &
  echo $! > /tmp/c_$1.pid
  for i in $(seq 1 40); do ros2 service list 2>/dev/null | grep -q "^/$1/_container/load_node$" && break; sleep 0.5; done
  echo "container /$1 ready after ~$((i/2))s; its services: $(ros2 service list 2>/dev/null | grep -c "^/$1/")"
}
load() { # $1 container, $2 pkg, $3 plugin, label
  echo "=== LOAD [$4] ros2 component load /$1 $2 $3"
  local before=$(wc -l < /tmp/c_$1.log)
  local t0=$(date +%s%N)
  timeout 30 ros2 component load /$1 $2 $3 2>&1 | sed 's/^/  cli: /'
  local rc=${PIPESTATUS[0]}
  echo "  exit=$rc  ms=$(( ($(date +%s%N)-t0)/1000000 ))"
  sleep 0.5
  tail -n +$((before+1)) /tmp/c_$1.log | sed 's/^/  container: /'
  kill -0 $(cat /tmp/c_$1.pid) 2>/dev/null && echo "  container still running: yes" || echo "  container still running: NO"
}

start_container C $ws/install/setup.bash
load C comp_demo comp_demo::Talker "good"
load C comp_demo comp_demo::Unregistered "macro in .cpp, no CMake registration"
load C comp_demo comp_demo::NoMacro "CMake registration, no macro"
load C comp_demo Talker "class name without namespace"
load C comp_demo comp_demo::talker "wrong case"
load C comp_demo comp_demo/Talker "slash instead of ::"
load C comp_demo Talker_lib "library target name"
load C comp_demo talker_exec "executable name"
load C comp_dem comp_demo::Talker "package name typo"
load C py_demo py_demo.node:PyTalker "ament_python package"
load C rclpy PyTalker "rclpy as package"
load C comp_static comp_demo::StaticTalker "STATIC library"
load C comp_demo comp_demo::Undef "undefined symbol"
load C comp_demo comp_demo::Thrower "constructor throws"
load C comp_demo comp_demo::Talker "good again (second instance, same name)"
echo "=== ros2 component list after all loads"; timeout 20 ros2 component list 2>&1
echo "=== load into a container that does not exist (timeout 15s)"
t0=$(date +%s%N); timeout 15 ros2 component load /NoSuchContainer comp_demo comp_demo::Talker 2>&1 | head -5; echo "  exit=${PIPESTATUS[0]} ms=$(( ($(date +%s%N)-t0)/1000000 ))"

echo "### unsourced container: started with only /opt/ros/$D/setup.bash in a clean env"
env -i HOME=/root PATH=/usr/bin:/bin ROS_DOMAIN_ID=88 bash -c "source /opt/ros/$D/setup.bash; exec ros2 run rclcpp_components component_container --ros-args -r __node:=Bare" > /tmp/c_Bare.log 2>&1 &
echo $! > /tmp/c_Bare.pid
for i in $(seq 1 40); do ros2 service list 2>/dev/null | grep -q "^/Bare/_container/load_node$" && break; sleep 0.5; done
load Bare comp_demo comp_demo::Talker "container not sourced with the workspace (CLI shell is sourced)"

echo "### standalone executable from rclcpp_components_register_node(... EXECUTABLE)"
timeout 4 ros2 run comp_demo talker_exec 2>&1 | head -3; echo "  exit=${PIPESTATUS[0]} (124 = killed by timeout while spinning)"

echo "### stale library: rebuild Talker as v2 while container C is running"
colcon build --packages-select comp_demo --cmake-args -DVER=v2 --event-handlers console_direct- 2>&1 | tail -2
load C comp_demo comp_demo::Talker "after rebuild, same container"
start_container Fresh $ws/install/setup.bash
load Fresh comp_demo comp_demo::Talker "after rebuild, new container"
echo "### unregistered fixed by adding registration + rebuild, container C still running"
sed -i 's|^# Unregistered_lib.*|rclcpp_components_register_nodes(Unregistered_lib "comp_demo::Unregistered")|' src/comp_demo/CMakeLists.txt
colcon build --packages-select comp_demo --cmake-args -DVER=v2 --event-handlers console_direct- 2>&1 | tail -2
load C comp_demo comp_demo::Unregistered "after adding registration, same container, no re-source"
for n in C Bare Fresh; do kill -INT $(cat /tmp/c_$n.pid) 2>/dev/null; done; sleep 2

echo "### launch: ComposableNodeContainer with one good and one bad node"
cat > /tmp/mixed.launch.py <<'EOF'
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
def generate_launch_description():
    return LaunchDescription([ComposableNodeContainer(
        name='mixed', namespace='', package='rclcpp_components', executable='component_container', output='screen',
        composable_node_descriptions=[
            ComposableNode(package='comp_demo', plugin='comp_demo::Talker', name='good_one'),
            ComposableNode(package='comp_demo', plugin='comp_demo::Talkr', name='typo_one'),
            ComposableNode(package='comp_demo', plugin='comp_demo::Thrower', name='throws_one'),
        ])])
EOF
( timeout -s INT 15 ros2 launch /tmp/mixed.launch.py 2>&1; echo "launch exit=$?" ) > /tmp/l1.log &
LP=$!; sleep 9
echo "--- ros2 component list while launch runs"; timeout 10 ros2 component list 2>&1
wait $LP; sed 's/^/  /' /tmp/l1.log

echo "### launch: LoadComposableNodes into a misspelled container name"
cat > /tmp/wrongtarget.launch.py <<'EOF'
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer, LoadComposableNodes
from launch_ros.descriptions import ComposableNode
def generate_launch_description():
    return LaunchDescription([
        ComposableNodeContainer(name='my_container', namespace='', package='rclcpp_components',
                                executable='component_container', output='screen', composable_node_descriptions=[]),
        LoadComposableNodes(target_container='/my_containr', composable_node_descriptions=[
            ComposableNode(package='comp_demo', plugin='comp_demo::Talker', name='late_one')]),
    ])
EOF
( timeout -s INT 20 ros2 launch /tmp/wrongtarget.launch.py 2>&1; echo "launch exit=$?" ) | sed 's/^/  /'
echo "### done $(cat /proc/loadavg)"
