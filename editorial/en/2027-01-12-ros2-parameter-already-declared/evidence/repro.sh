#!/bin/bash
# Run inside ros:<distro>-ros-base with --network none.
# Reproduces "parameter '...' has already been declared" (ParameterAlreadyDeclaredException)
# in rclpy and rclcpp, and compares fixes. One mode per process run.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclcpp-lifecycle ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
W=/ws; mkdir -p $W/src/pdecl/src; cd $W/src/pdecl
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>pdecl</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>rclcpp_lifecycle</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(pdecl)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
add_executable(cpp_node src/node.cpp)
target_link_libraries(cpp_node rclcpp::rclcpp rclcpp_lifecycle::rclcpp_lifecycle)
install(TARGETS cpp_node DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py_node.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > src/node.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>
#include <chrono>
using CB = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;
struct Helper {  // like a plugin or sub-object that declares its own parameter
  Helper(rclcpp::Node & n, const std::string & prefix) {
    bool v = n.declare_parameter(prefix + "enabled", true);
    RCLCPP_INFO(n.get_logger(), "RESULT helper declared %senabled=%d", prefix.c_str(), v);
  }
};
struct LNode : rclcpp_lifecycle::LifecycleNode {
  bool guard;
  LNode(bool g) : rclcpp_lifecycle::LifecycleNode("lc_node"), guard(g) {}
  CB on_configure(const rclcpp_lifecycle::State &) override {
    if (!guard || !has_parameter("rate")) declare_parameter("rate", 10.0);
    RCLCPP_INFO(get_logger(), "RESULT on_configure rate=%g", get_parameter("rate").as_double());
    return CB::SUCCESS;
  }
  CB on_cleanup(const rclcpp_lifecycle::State &) override { return CB::SUCCESS; }
};
int main(int argc, char ** argv) {
  auto args = rclcpp::init_and_remove_ros_arguments(argc, argv);
  std::string m = args.size() > 1 ? args[1] : "";
  rclcpp::NodeOptions opt;
  if (m.rfind("auto", 0) == 0) opt.automatically_declare_parameters_from_overrides(true);
  if (m.rfind("lifecycle", 0) == 0) {
    auto n = std::make_shared<LNode>(m == "lifecycle_guard");
    auto s1 = n->configure(); RCLCPP_INFO(n->get_logger(), "RESULT state after configure 1: %s", s1.label().c_str());
    auto s2 = n->cleanup();   RCLCPP_INFO(n->get_logger(), "RESULT state after cleanup: %s", s2.label().c_str());
    auto s3 = n->configure(); RCLCPP_INFO(n->get_logger(), "RESULT state after configure 2: %s", s3.label().c_str());
    rclcpp::shutdown(); return 0;
  }
  auto n = std::make_shared<rclcpp::Node>("decl_node", opt);
  auto L = n->get_logger();
  if (m == "twice") {
    n->declare_parameter("speed", 1.0);
    n->declare_parameter("speed", 1.0);
  } else if (m == "use_sim_time") {
    n->declare_parameter("use_sim_time", false);
  } else if (m == "auto_with_override" || m == "auto_no_override") {
    auto v = n->declare_parameter("speed", 1.0);
    RCLCPP_INFO(L, "RESULT speed=%g", v);
  } else if (m == "auto_get") {
    double v = n->get_parameter_or("speed", 1.0);
    RCLCPP_INFO(L, "RESULT get_parameter_or speed=%g has=%d", v, n->has_parameter("speed"));
  } else if (m == "helpers_same") {
    Helper a(*n, ""); Helper b(*n, "");
  } else if (m == "helpers_prefixed") {
    Helper a(*n, "left."); Helper b(*n, "right.");
  } else if (m == "guard") {
    for (int i = 0; i < 2; i++) {
      if (!n->has_parameter("speed")) n->declare_parameter("speed", 1.0);
    }
    RCLCPP_INFO(L, "RESULT guard ok speed=%g", n->get_parameter("speed").as_double());
  } else if (m == "catch") {
    n->declare_parameter("speed", 1.0);
    try { n->declare_parameter("speed", 2.0); }
    catch (const rclcpp::exceptions::ParameterAlreadyDeclaredException & e) {
      RCLCPP_INFO(L, "RESULT caught: %s; value kept=%g", e.what(), n->get_parameter("speed").as_double());
    }
  } else if (m == "undeclare_static") {
    n->declare_parameter("speed", 1.0);
    try { n->undeclare_parameter("speed"); RCLCPP_INFO(L, "RESULT undeclare ok"); }
    catch (const std::exception & e) { RCLCPP_INFO(L, "RESULT undeclare failed: %s", e.what()); }
  } else if (m == "undeclare_dynamic") {
    rcl_interfaces::msg::ParameterDescriptor d; d.dynamic_typing = true;
    n->declare_parameter("speed", rclcpp::ParameterValue(1.0), d);
    n->undeclare_parameter("speed");
    auto v = n->declare_parameter("speed", 2.0);
    RCLCPP_INFO(L, "RESULT undeclare+redeclare ok speed=%g", v);
  } else if (m == "timing") {
    auto t0 = std::chrono::steady_clock::now(); int k = 0;
    for (int i = 0; i < 100000; i++) { if (!n->has_parameter("speed")) n->declare_parameter("speed", 1.0); k++; }
    auto t1 = std::chrono::steady_clock::now();
    RCLCPP_INFO(L, "RESULT has_parameter guard x100000: %.1f ms",
      std::chrono::duration<double, std::milli>(t1 - t0).count());
  }
  RCLCPP_INFO(L, "RESULT reached end of mode %s", m.c_str());
  rclcpp::shutdown();
}
X
cat > py_node.py <<'X'
#!/usr/bin/env python3
import sys, time
import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.exceptions import ParameterAlreadyDeclaredException
args = rclpy.utilities.remove_ros_args(sys.argv)
m = args[1] if len(args) > 1 else ''
rclpy.init()
if m.startswith('lifecycle'):
    from rclpy.lifecycle import Node as LNode, TransitionCallbackReturn
    guard = m == 'lifecycle_guard'
    class L(LNode):
        def on_configure(self, state):
            if not guard or not self.has_parameter('rate'):
                self.declare_parameter('rate', 10.0)
            self.get_logger().info(f"RESULT on_configure rate={self.get_parameter('rate').value}")
            return TransitionCallbackReturn.SUCCESS
        def on_cleanup(self, state):
            return TransitionCallbackReturn.SUCCESS
    n = L('lc_node')
    for name, fn in (('configure 1', n.trigger_configure), ('cleanup', n.trigger_cleanup), ('configure 2', n.trigger_configure)):
        r = fn()
        n.get_logger().info(f'RESULT {name} returned {r}, state id={n._state_machine.current_state[0]} label={n._state_machine.current_state[1]}')
    rclpy.shutdown(); sys.exit(0)
n = Node('decl_node', automatically_declare_parameters_from_overrides=m.startswith('auto'))
L = n.get_logger()
if m == 'twice':
    n.declare_parameter('speed', 1.0)
    n.declare_parameter('speed', 1.0)
elif m == 'use_sim_time':
    n.declare_parameter('use_sim_time', False)
elif m in ('auto_with_override', 'auto_no_override'):
    v = n.declare_parameter('speed', 1.0).value
    L.info(f'RESULT speed={v}')
elif m == 'auto_get':
    v = n.get_parameter_or('speed', rclpy.parameter.Parameter('speed', value=1.0)).value
    L.info(f"RESULT get_parameter_or speed={v} has={n.has_parameter('speed')}")
elif m == 'list_dup':
    r = n.declare_parameters('', [('speed', 1.0), ('speed', 2.0)])
    L.info(f"RESULT list_dup returned {[p.value for p in r]} get_parameter={n.get_parameter('speed').value}")
elif m == 'guard':
    for _ in range(2):
        if not n.has_parameter('speed'):
            n.declare_parameter('speed', 1.0)
    L.info(f"RESULT guard ok speed={n.get_parameter('speed').value}")
elif m == 'catch':
    n.declare_parameter('speed', 1.0)
    try:
        n.declare_parameter('speed', 2.0)
    except ParameterAlreadyDeclaredException as e:
        L.info(f"RESULT caught: {type(e).__name__}: {e}; value kept={n.get_parameter('speed').value}")
elif m == 'undeclare_static':
    n.declare_parameter('speed', 1.0)
    try:
        n.undeclare_parameter('speed'); L.info('RESULT undeclare ok')
        v = n.declare_parameter('speed', 2.0).value; L.info(f'RESULT redeclare speed={v}')
    except Exception as e:
        L.info(f'RESULT undeclare failed: {type(e).__name__}: {e}')
elif m == 'undeclare_dynamic':
    n.declare_parameter('speed', 1.0, ParameterDescriptor(dynamic_typing=True))
    n.undeclare_parameter('speed')
    v = n.declare_parameter('speed', 2.0).value
    L.info(f'RESULT undeclare+redeclare ok speed={v}')
elif m == 'timing':
    t0 = time.perf_counter()
    for _ in range(100000):
        if not n.has_parameter('speed'):
            n.declare_parameter('speed', 1.0)
    L.info(f'RESULT has_parameter guard x100000: {(time.perf_counter()-t0)*1000:.1f} ms')
L.info(f'RESULT reached end of mode {m}')
rclpy.shutdown()
X
chmod +x py_node.py
cd $W && timeout 600 colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
echo "build ok"
source $W/install/setup.bash

run() {  # lang mode [ros args...]
  local lang=$1 mode=$2; shift 2
  local exe=cpp_node; [ $lang = py ] && exe=py_node.py
  echo; echo "--- $lang $mode $*"
  timeout 60 ros2 run pdecl $exe $mode "$@" 2>&1 | grep -v '^\s*$' | tail -n 12
  echo "exit=${PIPESTATUS[0]}"
}
for lang in py cpp; do
  run $lang twice
  run $lang use_sim_time
  run $lang use_sim_time --ros-args -p use_sim_time:=true
  run $lang auto_with_override --ros-args -p speed:=3.0
  run $lang auto_no_override
  run $lang auto_get --ros-args -p speed:=3.0
  [ $lang = cpp ] && run $lang helpers_same
  [ $lang = cpp ] && run $lang helpers_prefixed
  run $lang lifecycle
  run $lang lifecycle_guard
  run $lang guard
  run $lang catch
  run $lang undeclare_static
  run $lang undeclare_dynamic
  run $lang timing
done
run py list_dup

echo; echo "--- launch: cpp twice under ros2 launch"
cat > /tmp/l.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='pdecl', executable='cpp_node', arguments=['twice'], output='screen')])
X
timeout 60 ros2 launch /tmp/l.launch.py 2>&1 | grep -E "ERROR|what|terminate|died|exit code" | sed -E 's/pid [0-9]+/pid N/'
echo "=== done"
