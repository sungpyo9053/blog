#!/bin/bash
# Run inside ros:<distro>-ros-base as: bash /w/repro.sh
# Measures "parameter ... cannot be set because it was not declared" and related
# behavior for an rclpy node and an rclcpp node named param_node.
# MODE env selects node options: plain | allow (allow_undeclared_parameters)
#   | auto (automatically_declare_parameters_from_overrides) | both
# The node declares: declared_int (int 1), declared_ro (int 1, read_only),
# declared_dyn (int 1, dynamic_typing). It then reports has/get for each name
# and its parameter list. ONESHOT=1 makes it exit after the report.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2param ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-launch-ros 2>/dev/null
W=/ws; mkdir -p $W/src/pnode/src $W/src/pnode/launch; cd $W/src/pnode
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>pnode</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>rcl_interfaces</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(pnode)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cpp_node src/node.cpp)
target_link_libraries(cpp_node rclcpp::rclcpp)
install(TARGETS cpp_node DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py_node.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()
X
cat > src/node.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <cxxabi.h>
#include <algorithm>
#include <cstdlib>
static std::string tname(const std::exception & e) {
  int s; char * d = abi::__cxa_demangle(typeid(e).name(), 0, 0, &s);
  std::string r = d ? d : typeid(e).name(); free(d); return r;
}
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string mode = getenv("MODE") ? getenv("MODE") : "plain";
  rclcpp::NodeOptions o;
  if (mode == "allow" || mode == "both") o.allow_undeclared_parameters(true);
  if (mode == "auto" || mode == "both") o.automatically_declare_parameters_from_overrides(true);
  auto n = std::make_shared<rclcpp::Node>("param_node", o);
  auto L = n->get_logger();
  RCLCPP_INFO(L, "MODE %s", mode.c_str());
  auto decl = [&](const std::string & name, rcl_interfaces::msg::ParameterDescriptor d) {
    try { n->declare_parameter(name, rclcpp::ParameterValue(int64_t(1)), d); RCLCPP_INFO(L, "DECLARE %s ok", name.c_str()); }
    catch (const std::exception & e) { RCLCPP_INFO(L, "DECLARE %s EXC %s: %s", name.c_str(), tname(e).c_str(), e.what()); }
  };
  rcl_interfaces::msg::ParameterDescriptor d0, dro, ddyn;
  dro.read_only = true; ddyn.dynamic_typing = true;
  decl("declared_int", d0); decl("declared_ro", dro); decl("declared_dyn", ddyn);
  for (auto name : {"declared_int", "declared_ro", "declared_dyn", "undeclared_cli", "undeclared_yaml", "undeclared_launch"}) {
    try { auto p = n->get_parameter(name);
      RCLCPP_INFO(L, "GET %s has=%d type=%s value=%s", name, n->has_parameter(name), p.get_type_name().c_str(), p.value_to_string().c_str()); }
    catch (const std::exception & e) { RCLCPP_INFO(L, "GET %s has=%d EXC %s: %s", name, n->has_parameter(name), tname(e).c_str(), e.what()); }
  }
  auto names = n->list_parameters({}, 0).names; std::sort(names.begin(), names.end());
  std::string s; for (auto & x : names) s += x + " ";
  RCLCPP_INFO(L, "LIST %s", s.c_str());
  if (!getenv("ONESHOT")) rclcpp::spin(n);
  rclcpp::shutdown();
}
X
cat > py_node.py <<'X'
#!/usr/bin/env python3
import os, rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor
rclpy.init()
mode = os.environ.get('MODE', 'plain')
kw = {}
if mode in ('allow', 'both'): kw['allow_undeclared_parameters'] = True
if mode in ('auto', 'both'): kw['automatically_declare_parameters_from_overrides'] = True
n = Node('param_node', **kw)
log = n.get_logger()
log.info(f'MODE {mode}')
def decl(name, d):
    try:
        n.declare_parameter(name, 1, d); log.info(f'DECLARE {name} ok')
    except Exception as e:
        log.info(f'DECLARE {name} EXC {type(e).__name__}: {e}')
decl('declared_int', ParameterDescriptor())
decl('declared_ro', ParameterDescriptor(read_only=True))
decl('declared_dyn', ParameterDescriptor(dynamic_typing=True))
for name in ['declared_int', 'declared_ro', 'declared_dyn', 'undeclared_cli', 'undeclared_yaml', 'undeclared_launch']:
    try:
        p = n.get_parameter(name)
        log.info(f'GET {name} has={n.has_parameter(name)} type={p.type_.name} value={p.value!r}')
    except Exception as e:
        log.info(f'GET {name} has={n.has_parameter(name)} EXC {type(e).__name__}: {e}')
log.info('LIST ' + ' '.join(sorted(n._parameters.keys())))
if not os.environ.get('ONESHOT'):
    try:
        rclpy.spin(n)
    except Exception:
        pass
X
chmod +x py_node.py
for exe in py_node.py cpp_node; do
cat > launch/$exe.launch.py <<X
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='pnode', executable='$exe', name='param_node', output='screen',
        parameters=[{'declared_int': 7, 'undeclared_launch': 3}],
        additional_env={'MODE': 'plain', 'ONESHOT': '1'})])
X
done
cd $W && MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
source $W/install/setup.bash

Y=/y; mkdir -p $Y
cat > $Y/all.yaml <<'X'
/**:
  ros__parameters:
    declared_int: 5
    undeclared_yaml: 2
X
cat > $Y/exact.yaml <<'X'
/param_node:
  ros__parameters:
    declared_int: 5
    undeclared_yaml: 2
X
cat > $Y/wrong_name.yaml <<'X'
/params_node:
  ros__parameters:
    declared_int: 5
    undeclared_yaml: 2
X
cat > $Y/typo_ros_parameters.yaml <<'X'
/param_node:
  ros_parameters:
    declared_int: 5
    undeclared_yaml: 2
X
cat > $Y/typo_ros_parameter.yaml <<'X'
/param_node:
  ros__parameter:
    declared_int: 5
    undeclared_yaml: 2
X
clean() { sed -e 's/\[[0-9]\{10\}\.[0-9]*\]/[T]/' -e 's/\[[a-z_]*-[0-9]*\]/[proc]/' -e 's/pid [0-9]*/pid N/' | grep -v '^\s*$'; }
P() { echo "\$ ros2 param $*"; timeout 20 ros2 param "$@" 2>&1 | clean; echo "exit=${PIPESTATUS[0]}"; }
wait_node() { for i in $(seq 40); do ros2 param list /param_node 2>/dev/null | grep -q use_sim_time && return 0; sleep 0.5; done; echo "NODE NOT UP"; }

ros2 daemon start >/dev/null 2>&1
for exe in py_node.py cpp_node; do
  for mode in plain allow auto both; do
    echo; echo "########## $exe MODE=$mode  (--ros-args -p undeclared_cli:=1 --params-file all.yaml)"
    MODE=$mode ros2 run pnode $exe --ros-args -p undeclared_cli:=1 --params-file $Y/all.yaml > /tmp/node.log 2>&1 &
    NP=$!
    wait_node
    echo "--- node startup log"; clean < /tmp/node.log
    P list /param_node
    P set /param_node not_declared 1
    P set /param_node declared_int hello
    P set /param_node declared_int 2.0
    P set /param_node declared_int 3
    P set /param_node declared_ro 2
    P set /param_node declared_dyn hello
    P get /param_node not_declared
    P get /param_node undeclared_cli
    P get /param_node undeclared_yaml
    P get /param_node declared_dyn
    P list /param_node
    kill -INT $NP; sleep 2; kill -9 $NP 2>/dev/null; wait $NP 2>/dev/null
    pkill -9 -f 'pnode/(py_node|cpp_node)' 2>/dev/null
    echo "--- node log after shutdown (new lines only)"; clean < /tmp/node.log | grep -v -e '^\[T\]\|^\[INFO\]' | grep -v -e 'MODE\|DECLARE\|GET\|LIST' | head -15
  done
  echo; echo "########## $exe YAML key / typo cases (MODE=plain, ONESHOT)"
  for f in all exact wrong_name typo_ros_parameters typo_ros_parameter; do
    echo "----- $f.yaml"; cat $Y/$f.yaml
    MODE=plain ONESHOT=1 timeout 20 ros2 run pnode $exe --ros-args --params-file $Y/$f.yaml 2>&1 | clean | grep -v 'declared_ro\|declared_dyn\|undeclared_cli\|undeclared_launch' | head -20
    echo "exit=${PIPESTATUS[0]}"
  done
  echo; echo "########## $exe -p undeclared only, plain, ONESHOT (any warning?)"
  MODE=plain ONESHOT=1 timeout 20 ros2 run pnode $exe --ros-args -p undeclared_cli:=1 -p declared_int:=9 2>&1 | clean
  echo "exit=${PIPESTATUS[0]}"
  echo; echo "########## $exe launch file parameters=[{'declared_int': 7, 'undeclared_launch': 3}], plain"
  timeout 30 ros2 launch pnode $exe.launch.py 2>&1 | clean | grep -v 'All log files\|Default logging' 
  echo "exit=${PIPESTATUS[0]}"
done
echo "=== done $ROS_DISTRO"
