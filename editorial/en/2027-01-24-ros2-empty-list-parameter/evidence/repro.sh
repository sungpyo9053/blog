#!/bin/bash
# Empty list / empty array parameters in ROS 2: declare, YAML, -p, ros2 param set/dump/load, launch.
# Host side (one distro at a time, no network, domain 88, no core dumps):
#   docker run --rm --name pk46-$D --network none --ulimit core=0 --pids-limit 256 --cpus 1.5 \
#     -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1                (Humble)
#     -e ROS_DOMAIN_ID=88 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST (Jazzy, Lyrical) \
#     -v /tmp/en-pick56:/w:ro ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
set +u
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export RCUTILS_COLORIZED_OUTPUT=0 PYTHONUNBUFFERED=1 MAKEFLAGS=-j1
T="timeout 30"
echo "=== distro $ROS_DISTRO  domain $ROS_DOMAIN_ID  RMW ${RMW_IMPLEMENTATION:-default}"
echo "=== versions"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcl-yaml-param-parser ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2param ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>&1

mkdir -p /y /ws/src/ep/src /ws/src/ep/py /ws/src/ep/launch
cat > /ws/src/ep/py/pnode.py <<'PY'
#!/usr/bin/env python3
import sys, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import ParameterDescriptor, ParameterType
mode = sys.argv[1]
spin = len(sys.argv) > 2 and sys.argv[2] == 'spin'
rclpy.init(args=sys.argv)
def err(e):
    return f'{type(e).__module__}.{type(e).__name__}: {e}'
def show(label, f):
    try:
        print(f'{label}: OK -> {f()!r}', flush=True)
    except Exception as e:
        print(f'{label}: {err(e)}', flush=True)
try:
    n = Node('pnode')
except Exception as e:
    print(f'Node(): {err(e)}', flush=True); sys.exit(3)
def tv():
    p = n.get_parameter('names'); v = p.value
    return (p.type_.name, list(v) if v is not None and not isinstance(v, str) else v)
def decl():
    if mode == 'list_default':
        n.declare_parameter('names', [])
    elif mode == 'list_desc':
        n.declare_parameter('names', [], ParameterDescriptor(type=ParameterType.PARAMETER_STRING_ARRAY))
    elif mode == 'typed':
        n.declare_parameter('names', Parameter.Type.STRING_ARRAY)
    elif mode == 'nonempty':
        n.declare_parameter('names', ['a', 'b'])
    elif mode == 'sentinel':
        n.declare_parameter('names', [''])
    elif mode == 'dynamic':
        n.declare_parameter('names', [], ParameterDescriptor(dynamic_typing=True))
    elif mode == 'typed_param':
        n.declare_parameter('names', Parameter.Type.STRING_ARRAY)
        n.set_parameters([Parameter('names', Parameter.Type.STRING_ARRAY, [])])
    return tv()
show('declare', decl)
show('get', tv)
if spin:
    print('spinning', flush=True)
    try:
        rclpy.spin(n)
    except Exception as e:
        print('spin exit', type(e).__name__, flush=True)
    sys.exit(0)
def setp(p):
    return [(r.successful, r.reason) for r in n.set_parameters([p])]
show('set value=[x,y]', lambda: setp(Parameter('names', value=['x', 'y'])))
show('set STRING_ARRAY []', lambda: setp(Parameter('names', Parameter.Type.STRING_ARRAY, [])))
show('set value=[]', lambda: setp(Parameter('names', value=[])))
show('get after sets', tv)
PY
chmod +x /ws/src/ep/py/pnode.py

cat > /ws/src/ep/src/c.cpp <<'CPP'
#include <cstdlib>
#include <cxxabi.h>
#include <iostream>
#include <string>
#include <vector>
#include <rclcpp/rclcpp.hpp>
static std::string dm(const std::exception & e) {
  int s; char * p = abi::__cxa_demangle(typeid(e).name(), nullptr, nullptr, &s);
  std::string r = p ? p : typeid(e).name(); std::free(p); return r; }
template<class F> void show(const std::string & l, F f) {
  try { auto r = f(); std::cout << l << ": OK -> " << r << std::endl; }
  catch (const std::exception & e) { std::cout << l << ": " << dm(e) << ": " << e.what() << std::endl; } }
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string mode = std::getenv("MODE") ? std::getenv("MODE") : "";
  bool spin = std::getenv("SPIN") != nullptr;
  rclcpp::Node::SharedPtr n;
  try { n = std::make_shared<rclcpp::Node>("cnode"); }
  catch (const std::exception & e) { std::cout << "Node(): " << dm(e) << ": " << e.what() << std::endl; rclcpp::shutdown(); return 3; }
  auto tv = [&]{ auto p = n->get_parameter("names"); std::string s = p.get_type_name() + " " + p.value_to_string(); if (p.get_type() == rclcpp::PARAMETER_STRING_ARRAY) s += " size=" + std::to_string(p.as_string_array().size()); return s; };
  show("declare", [&]{
    if (mode == "tmpl_empty") n->declare_parameter<std::vector<std::string>>("names", std::vector<std::string>{});
    else if (mode == "tmpl_ab") n->declare_parameter<std::vector<std::string>>("names", {"a", "b"});
    else if (mode == "enum") n->declare_parameter("names", rclcpp::PARAMETER_STRING_ARRAY);
    return tv(); });
  show("get", tv);
  if (spin) { std::cout << "spinning" << std::endl; rclcpp::spin(n); rclcpp::shutdown(); return 0; }
  show("set {} (empty vector<string>)", [&]{ auto r = n->set_parameter(rclcpp::Parameter("names", std::vector<std::string>{})); return std::string(r.successful ? "true " : "false ") + r.reason; });
  show("get after set", tv);
  rclcpp::shutdown();
  return 0;
}
CPP

cat > /ws/src/ep/launch/l.launch.py <<'PY'
import os
from launch import LaunchDescription
from launch_ros.actions import Node
CASES = {
    'dict_empty': [{'names': []}],
    'dict_empty_str': [{'names': ['']}],
    'dict_ab': [{'names': ['a', 'b']}],
    'file_empty': ['/y/empty.yaml'],
}
def generate_launch_description():
    case = os.environ['LCASE']
    who = os.environ['LWHO']
    if who == 'py':
        node = Node(package='ep', executable='pnode.py', name='pnode', arguments=[os.environ.get('PMODE', 'nonempty')], parameters=CASES[case], output='screen')
    else:
        node = Node(package='ep', executable='cnode', name='cnode', parameters=CASES[case], output='screen', additional_env={'MODE': os.environ.get('CMODE', 'tmpl_ab')})
    return LaunchDescription([node])
PY

cat > /ws/src/ep/package.xml <<'XML'
<?xml version="1.0"?>
<package format="3">
  <name>ep</name><version>0.0.1</version><description>repro</description>
  <maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>launch_ros</exec_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
XML
cat > /ws/src/ep/CMakeLists.txt <<'CM'
cmake_minimum_required(VERSION 3.10)
project(ep)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cnode src/c.cpp)
target_link_libraries(cnode rclcpp::rclcpp)
install(TARGETS cnode DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py/pnode.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()
CM
echo "=== build"
B0=$(date +%s.%N)
cd /ws && timeout 600 colcon build --event-handlers console_direct- 2>&1 | tail -n 3
grep -iE "error|warning" /ws/log/latest_build/ep/stdout_stderr.log | head -n 20
echo "build seconds: $(python3 -c "import time;print(round(time.time()-$B0,1))")"
source /ws/install/setup.bash

w() { printf '/**:\n  ros__parameters:\n    names: %s\n' "$2" > /y/$1.yaml; }
w empty '[]'
w empty_sp '[ ]'
w empty_str '[""]'
w ab '[a, b]'
w null_v 'null'

run_py() { # mode label args...
  local m=$1 l=$2; shift 2
  echo "--- py mode=$m input=$l"
  $T python3 /ws/install/ep/lib/ep/pnode.py $m "$@" 2>&1 | grep -v "^\s*$" | sed 's/^/    /' | head -n 30
  echo "    exit=${PIPESTATUS[0]}"
}
run_c() {
  local m=$1 l=$2; shift 2
  echo "--- cpp mode=$m input=$l"
  MODE=$m $T /ws/install/ep/lib/ep/cnode "$@" 2>&1 | grep -v "^\s*$" | sed 's/^/    /' | head -n 30
  echo "    exit=${PIPESTATUS[0]}"
}

echo "=== A. rclpy declare_parameter variants x inputs"
for m in list_default list_desc typed typed_param nonempty sentinel dynamic; do
  run_py $m none
  run_py $m yaml_empty --ros-args --params-file /y/empty.yaml
  run_py $m yaml_empty_space --ros-args --params-file /y/empty_sp.yaml
  run_py $m p_empty --ros-args -p 'names:=[]'
  run_py $m yaml_empty_str --ros-args --params-file /y/empty_str.yaml
  run_py $m yaml_ab --ros-args --params-file /y/ab.yaml
done
run_py nonempty yaml_null --ros-args --params-file /y/null_v.yaml

echo "=== B. rclcpp declare_parameter variants x inputs"
for m in tmpl_empty tmpl_ab enum; do
  run_c $m none
  run_c $m yaml_empty --ros-args --params-file /y/empty.yaml
  run_c $m p_empty --ros-args -p 'names:=[]'
  run_c $m yaml_empty_str --ros-args --params-file /y/empty_str.yaml
  run_c $m yaml_ab --ros-args --params-file /y/ab.yaml
done

cli() { echo "\$ $*"; $T "$@" 2>&1 | sed 's/^/    /' | head -n 20; echo "    exit=${PIPESTATUS[0]}"; }
ros2 daemon start >/dev/null 2>&1
echo "=== C. ros2 param set/get/dump/load against running nodes"
echo "--- C1 python nonempty (STRING_ARRAY [a,b])"
timeout 60 python3 /ws/install/ep/lib/ep/pnode.py nonempty spin > /tmp/c1.log 2>&1 & BG=$!
sleep 4
cli ros2 param get /pnode names
cli ros2 param set /pnode names '[]'
cli ros2 param get /pnode names
cli ros2 param set /pnode names "['c']"
cli ros2 param get /pnode names
cli ros2 param describe /pnode names
kill $BG 2>/dev/null; wait $BG 2>/dev/null; sed 's/^/    log: /' /tmp/c1.log | head -n 10

echo "--- C2 python list_default (declared with [])"
timeout 60 python3 /ws/install/ep/lib/ep/pnode.py list_default spin > /tmp/c2.log 2>&1 & BG=$!
sleep 4
cli ros2 param get /pnode names
cli ros2 param describe /pnode names
cli ros2 param set /pnode names "['c']"
cli ros2 param get /pnode names
kill $BG 2>/dev/null; wait $BG 2>/dev/null; sed 's/^/    log: /' /tmp/c2.log | head -n 10

echo "--- C3 python typed_param (STRING_ARRAY set to []), dump and reload"
timeout 60 python3 /ws/install/ep/lib/ep/pnode.py typed_param spin > /tmp/c3.log 2>&1 & BG=$!
sleep 4
cli ros2 param get /pnode names
ros2 param dump /pnode > /y/dump_py.yaml 2>&1; echo "    dump exit=$?"; sed 's/^/    dump: /' /y/dump_py.yaml | head -n 12
cli ros2 param load /pnode /y/empty.yaml
cli ros2 param load /pnode /y/ab.yaml
cli ros2 param get /pnode names
kill $BG 2>/dev/null; wait $BG 2>/dev/null; sed 's/^/    log: /' /tmp/c3.log | head -n 10
grep -q "names" /y/dump_py.yaml && run_py typed reload_dump_py --ros-args --params-file /y/dump_py.yaml

echo "--- C4 cpp tmpl_ab, set [] and dump"
MODE=tmpl_ab SPIN=1 timeout 60 /ws/install/ep/lib/ep/cnode > /tmp/c4.log 2>&1 & BG=$!
sleep 4
cli ros2 param set /cnode names '[]'
cli ros2 param get /cnode names
kill $BG 2>/dev/null; wait $BG 2>/dev/null; sed 's/^/    log: /' /tmp/c4.log | head -n 10

echo "--- C5 cpp tmpl_empty, dump and reload"
MODE=tmpl_empty SPIN=1 timeout 60 /ws/install/ep/lib/ep/cnode > /tmp/c5.log 2>&1 & BG=$!
sleep 4
cli ros2 param get /cnode names
cli ros2 param describe /cnode names
ros2 param dump /cnode > /y/dump_c.yaml 2>&1; echo "    dump exit=$?"; sed 's/^/    dump: /' /y/dump_c.yaml | head -n 12
cli ros2 param load /cnode /y/empty.yaml
cli ros2 param get /cnode names
kill $BG 2>/dev/null; wait $BG 2>/dev/null; sed 's/^/    log: /' /tmp/c5.log | head -n 10
grep -q "names" /y/dump_c.yaml && run_c tmpl_empty reload_dump_c --ros-args --params-file /y/dump_c.yaml

echo "=== D. launch Node(parameters=...)"
for who in py cpp; do
  for c in dict_empty dict_empty_str dict_ab file_empty; do
    echo "--- launch who=$who case=$c"
    LWHO=$who LCASE=$c $T ros2 launch ep l.launch.py 2>&1 | grep -vE "^\s*$|INFO\] \[launch\]: (All log files|Default logging)" | sed 's/^/    /' | head -n 25
    echo "    exit=${PIPESTATUS[0]}"
  done
done
echo "--- launch who=py case=dict_empty PMODE=typed"
LWHO=py LCASE=dict_empty PMODE=typed $T ros2 launch ep l.launch.py 2>&1 | grep -vE "^\s*$|All log files|Default logging" | sed 's/^/    /' | head -n 25
echo "    exit=${PIPESTATUS[0]}"
echo "--- launch who=cpp case=dict_empty CMODE=tmpl_empty"
LWHO=cpp LCASE=dict_empty CMODE=tmpl_empty $T ros2 launch ep l.launch.py 2>&1 | grep -vE "^\s*$|All log files|Default logging" | sed 's/^/    /' | head -n 25
echo "    exit=${PIPESTATUS[0]}"
echo "--- launch_ros temp params file for dict_empty (debug)"
LWHO=py LCASE=dict_empty $T ros2 launch ep l.launch.py --debug 2>&1 | grep -iE "param|yaml|names" | head -n 10 | sed 's/^/    /'
ros2 daemon stop >/dev/null 2>&1
echo "=== done"
