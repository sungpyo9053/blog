#!/bin/bash
# "parameter is not initialized" / "Statically typed parameter must be initialized" repro.
# Host side (one distro at a time, ROS_DOMAIN_ID 88, localhost-only discovery, no core dumps):
#   docker run --rm --name pk37-$D --ulimit core=0 --pids-limit 256 --cpus 1.5 \
#     -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1            (Humble)
#     -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST             (Jazzy, Lyrical)
#     -v /tmp/en-pick47:/w ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
# The container uses the default bridge only for apt-get (nav2_map_server).
set +u
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export RCUTILS_COLORIZED_OUTPUT=0 PYTHONUNBUFFERED=1 MAKEFLAGS=-j1
T="timeout 60"
echo "=== distro $ROS_DISTRO  RMW default  domain $ROS_DOMAIN_ID"
echo "=== versions"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2param ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rcl-interfaces 2>&1
echo "=== apt install nav2_map_server"
( apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$ROS_DISTRO-nav2-map-server ros-$ROS_DISTRO-ros2lifecycle ) > /tmp/apt.log 2>&1; echo "apt exit=$?"; tail -n 3 /tmp/apt.log
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-nav2-map-server ros-$ROS_DISTRO-ros2lifecycle 2>&1

mkdir -p /y /ws/src/pk/src
cat > /y/p.py <<'PY'
import sys, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import ParameterDescriptor
mode = sys.argv[1]
rclpy.init(args=sys.argv)
n = Node('pnode')
def show(label, f):
    try:
        print(f'{label}: OK -> {f()!r}')
    except Exception as e:
        print(f'{label}: {type(e).__module__}.{type(e).__name__}: {e}')
if mode == 'typed':
    show('declare_parameter(name, Parameter.Type.STRING)', lambda: n.declare_parameter('name', Parameter.Type.STRING).type_)
elif mode == 'noarg':
    show('declare_parameter(name)', lambda: n.declare_parameter('name').type_)
elif mode == 'none':
    show('declare_parameter(name, None)', lambda: n.declare_parameter('name', None).type_)
elif mode == 'dynamic':
    show('declare_parameter(name, None, dynamic_typing=True)', lambda: n.declare_parameter('name', None, ParameterDescriptor(dynamic_typing=True)).type_)
elif mode == 'default':
    show('declare_parameter(name, "default")', lambda: n.declare_parameter('name', 'default').type_)
elif mode == 'crash':
    n.declare_parameter('name', Parameter.Type.STRING)
    print('value =', n.get_parameter('name').value)
    sys.exit(0)
elif mode == 'spin':
    n.declare_parameter('name', Parameter.Type.STRING)
    n.declare_parameter('rate', 10.0)
    print('spinning', flush=True)
    try:
        rclpy.spin(n)
    except Exception as e:
        print('spin exit', type(e).__name__)
    sys.exit(0)
show('has_parameter', lambda: n.has_parameter('name'))
show('get_parameter(name).value', lambda: n.get_parameter('name').value)
show('get_parameter_or(name, fallback).value', lambda: n.get_parameter_or('name', Parameter('name', value='fallback')).value)
show('get_parameters([name])', lambda: [p.value for p in n.get_parameters(['name'])])
show('_parameters[name].value (internal)', lambda: n._parameters['name'].value)
show('set_parameters(name=hello)', lambda: [r.successful for r in n.set_parameters([Parameter('name', value='hello')])])
show('get_parameter(name).value after set', lambda: n.get_parameter('name').value)
PY

cat > /ws/src/pk/package.xml <<'XML'
<?xml version="1.0"?>
<package format="3">
  <name>pk</name><version>0.0.1</version><description>repro</description>
  <maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
XML
cat > /ws/src/pk/CMakeLists.txt <<'CM'
cmake_minimum_required(VERSION 3.10)
project(pk)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cnode src/c.cpp)
target_link_libraries(cnode rclcpp::rclcpp)
install(TARGETS cnode DESTINATION lib/${PROJECT_NAME})
ament_package()
CM
cat > /ws/src/pk/src/c.cpp <<'CPP'
#include <cstdlib>
#include <cxxabi.h>
#include <iostream>
#include <string>
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
  auto n = std::make_shared<rclcpp::Node>("cnode");
  if (mode == "tmpl") {
    show("declare_parameter<std::string>(name)", [&]{ return n->declare_parameter<std::string>("name"); });
  } else if (mode == "enum") {
    show("declare_parameter(name, PARAMETER_STRING)", [&]{ return rclcpp::to_string(n->declare_parameter("name", rclcpp::PARAMETER_STRING)); });
  } else if (mode == "dynamic") {
    rcl_interfaces::msg::ParameterDescriptor d; d.dynamic_typing = true;
    show("declare_parameter(name, ParameterValue{}, dynamic_typing)", [&]{ return rclcpp::to_string(n->declare_parameter("name", rclcpp::ParameterValue{}, d)); });
  } else if (mode == "default") {
    show("declare_parameter<std::string>(name, \"default\")", [&]{ return n->declare_parameter<std::string>("name", "default"); });
  } else if (mode == "crash") {
    auto v = n->declare_parameter<std::string>("name");
    std::cout << "value = " << v << std::endl;
    rclcpp::shutdown(); return 0;
  }
  show("has_parameter", [&]{ return std::string(n->has_parameter("name") ? "true" : "false"); });
  show("get_parameter(name).get_type_name()", [&]{ return n->get_parameter("name").get_type_name(); });
  show("get_parameter(name).as_string()", [&]{ return n->get_parameter("name").as_string(); });
  show("get_parameter(name, out)", [&]{ std::string o = "unset"; bool ok = n->get_parameter("name", o); return std::string(ok ? "true " : "false ") + o; });
  show("get_parameter_or(name, out, fallback)", [&]{ std::string o; bool ok = n->get_parameter_or<std::string>("name", o, "fallback"); return std::string(ok ? "true " : "false ") + o; });
  rclcpp::shutdown();
  return 0;
}
CPP
echo "=== build"
cd /ws && $T colcon build --event-handlers console_direct- 2>&1 | tail -n 3; grep -iE "error|warning" /ws/log/latest_build/pk/stdout_stderr.log | head -n 20
source /ws/install/setup.bash

cat > /y/good.yaml <<'Y'
/pnode:
  ros__parameters:
    name: hello
/cnode:
  ros__parameters:
    name: hello
Y
cat > /y/wrongkey.yaml <<'Y'
/my_node:
  ros__parameters:
    name: hello
Y
cat > /y/empty_string.yaml <<'Y'
/**:
  ros__parameters:
    name: ""
Y
cat > /y/tilde.yaml <<'Y'
/**:
  ros__parameters:
    name: ~
Y
cat > /y/null.yaml <<'Y'
/**:
  ros__parameters:
    name: null
Y
cat > /y/ns.yaml <<'Y'
/pnode:
  ros__parameters:
    name: hello
/cnode:
  ros__parameters:
    name: hello
Y

py() { echo; echo "--- rclpy: $*"; $T python3 /y/p.py "$@" 2>&1 | grep -v '^\s*$' | tail -n 25; echo "exit=${PIPESTATUS[0]}"; }
cc() { local m=$1; shift; echo; echo "--- rclcpp MODE=$m: $*"; MODE=$m $T ros2 run pk cnode "$@" 2>&1 | tail -n 25; echo "exit=${PIPESTATUS[0]}"; }

echo; echo "=== rclpy declare variants (no override)"
for m in typed noarg none dynamic default; do py $m; done
echo; echo "=== rclpy typed with overrides"
py typed --ros-args -p name:=hello
py typed --ros-args -p name:=5
py typed --ros-args -p "name:=''"
py typed --ros-args --params-file /y/good.yaml
py typed --ros-args --params-file /y/wrongkey.yaml
py typed --ros-args --params-file /y/empty_string.yaml
py typed --ros-args --params-file /y/tilde.yaml
py typed --ros-args --params-file /y/null.yaml
py typed --ros-args -r __ns:=/robot1 --params-file /y/ns.yaml
py typed --ros-args -r __node:=renamed --params-file /y/good.yaml
py typed --params-file /y/good.yaml
echo; echo "=== rclpy uncaught"
py crash

echo; echo "=== rclcpp declare variants (no override)"
for m in tmpl enum dynamic default; do cc $m; done
echo; echo "=== rclcpp typed with overrides"
cc tmpl --ros-args -p name:=hello
cc enum --ros-args -p name:=hello
cc tmpl --ros-args -p name:=5
cc tmpl --ros-args --params-file /y/good.yaml
cc tmpl --ros-args --params-file /y/wrongkey.yaml
cc tmpl --ros-args --params-file /y/empty_string.yaml
cc tmpl --ros-args --params-file /y/tilde.yaml
cc enum --ros-args --params-file /y/tilde.yaml
cc dynamic --ros-args --params-file /y/tilde.yaml
cc tmpl --ros-args -r __ns:=/robot1 --params-file /y/ns.yaml
echo; echo "=== rclcpp uncaught"
cc crash

echo; echo "=== ros2 param CLI against a running rclpy node with an unset STRING parameter"
python3 /y/p.py spin > /tmp/spin.log 2>&1 &
SP=$!
sleep 6
for c in "param list /pnode" "param list /pnode" "param get /pnode name" "param describe /pnode name" "param dump /pnode" "param set /pnode name hello" "param get /pnode name"; do
  echo "\$ ros2 $c"; $T ros2 $c 2>&1 | tail -n 15; echo "exit=${PIPESTATUS[0]}"
done
kill -TERM $SP; sleep 2; kill -KILL $SP 2>/dev/null; wait $SP 2>/dev/null; echo "spin node log:"; cat /tmp/spin.log | tail -n 5

echo; echo "=== nav2_map_server"
if ros2 pkg prefix nav2_map_server >/dev/null 2>&1; then
  python3 - <<'PY'
w, h = 20, 20
open('/y/map.pgm', 'wb').write(b'P5\n%d %d\n255\n' % (w, h) + bytes([254]) * (w * h))
open('/y/map.yaml', 'w').write('image: map.pgm\nresolution: 0.05\norigin: [0.0, 0.0, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.196\n')
PY
  printf '/map_server:\n  ros__parameters:\n    yaml_filename: /y/map.yaml\n' > /y/ms.yaml
  ms() { local N=$1; shift; echo; echo "--- map_server (node $N): $*"; $T ros2 run nav2_map_server map_server "$@" > /tmp/ms.log 2>&1 & local P=$!; sleep 4
    echo "\$ ros2 lifecycle set $N configure"; $T ros2 lifecycle set $N configure 2>&1 | tail -n 3
    echo "\$ ros2 lifecycle get $N"; $T ros2 lifecycle get $N 2>&1 | tail -n 2
    echo "\$ ros2 param get $N yaml_filename"; $T ros2 param get $N yaml_filename 2>&1 | tail -n 2
    kill -TERM $P; sleep 2; pkill -KILL -f map_server 2>/dev/null; wait $P 2>/dev/null; echo "map_server log:"; grep -v '^\s*$' /tmp/ms.log | tail -n 14; }
  ms /map_server
  ms /map_server --ros-args -p yaml_filename:=/y/map.yaml
  ms /map_server --ros-args --params-file /y/ms.yaml
  ms /map_server --ros-args -p "yaml_filename:=''"
  ms /robot1/map_server --ros-args -r __ns:=/robot1 --params-file /y/ms.yaml
else
  echo "nav2_map_server not installed (see apt exit above)"
fi
echo; echo "=== done"
