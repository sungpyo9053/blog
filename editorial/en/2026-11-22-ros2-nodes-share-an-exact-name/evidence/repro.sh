#!/bin/bash
# Run inside ros:<distro>-ros-base (docker run --rm -e ROS_DOMAIN_ID=77 ...).
# Measures what happens when two ROS 2 nodes share a fully qualified name:
# the CLI warning, ros2 param / get_parameters services, topics, lifecycle,
# actions, common causes (ros2 run x2, launch x2, launch name override,
# composable nodes, same process) and the renaming fixes.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rclcpp-components \
  ros-$ROS_DISTRO-launch-ros 2>/dev/null
N=${N:-20}

W=/ws; mkdir -p $W/src/dupn/src $W/src/dupn/launch; cd $W/src/dupn
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>dupn</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>rclcpp_components</depend>
<depend>rclcpp_lifecycle</depend><depend>std_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(dupn)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_components REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(std_msgs REQUIRED)
add_library(talker_comp SHARED src/talker.cpp)
target_link_libraries(talker_comp rclcpp::rclcpp rclcpp_components::component ${std_msgs_TARGETS})
rclcpp_components_register_nodes(talker_comp "dupn::Talker")
add_executable(cpp_talker src/main.cpp)
target_link_libraries(cpp_talker talker_comp)
add_executable(cpp_twice src/twice.cpp)
target_link_libraries(cpp_twice talker_comp)
add_executable(cpp_lc src/lc.cpp)
target_link_libraries(cpp_lc rclcpp_lifecycle::rclcpp_lifecycle)
install(TARGETS talker_comp ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION bin)
install(TARGETS cpp_talker cpp_twice cpp_lc DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py_node.py py_twice.py py_act.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()
X
cat > src/talker.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_components/register_node_macro.hpp>
#include <std_msgs/msg/string.hpp>
namespace dupn {
class Talker : public rclcpp::Node {
public:
  explicit Talker(const rclcpp::NodeOptions & o) : Node("cpp_talker", o) {
    tag_ = declare_parameter("tag", std::string("unset"));
    declare_parameter("note", std::string("none"));
    cb_ = add_on_set_parameters_callback([this](const std::vector<rclcpp::Parameter> & ps) {
      for (auto & p : ps) printf("SETCB tag=%s %s=%s\n", tag_.c_str(), p.get_name().c_str(), p.value_to_string().c_str());
      fflush(stdout);
      rcl_interfaces::msg::SetParametersResult r; r.successful = true; return r; });
    pub_ = create_publisher<std_msgs::msg::String>("chatter", 10);
    tm_ = create_wall_timer(std::chrono::milliseconds(500), [this]() {
      std_msgs::msg::String m; m.data = tag_; pub_->publish(m); });
    RCLCPP_INFO(get_logger(), "START tag=%s fqn=%s", tag_.c_str(), get_fully_qualified_name());
  }
private:
  std::string tag_;
  rclcpp::Node::OnSetParametersCallbackHandle::SharedPtr cb_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr tm_;
};
}
RCLCPP_COMPONENTS_REGISTER_NODE(dupn::Talker)
X
cat > src/main.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_components/node_factory.hpp>
#include <class_loader/class_loader.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  class_loader::ClassLoader l("libtalker_comp.so");
  auto f = l.createInstance<rclcpp_components::NodeFactory>("rclcpp_components::NodeFactoryTemplate<dupn::Talker>");
  auto w = f->create_node_instance(rclcpp::NodeOptions());
  rclcpp::spin(w.get_node_base_interface());
  rclcpp::shutdown();
}
X
cat > src/twice.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_components/node_factory.hpp>
#include <class_loader/class_loader.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  class_loader::ClassLoader l("libtalker_comp.so");
  auto f = l.createInstance<rclcpp_components::NodeFactory>("rclcpp_components::NodeFactoryTemplate<dupn::Talker>");
  auto a = f->create_node_instance(rclcpp::NodeOptions().parameter_overrides({{"tag", "first"}}));
  printf("CREATED first\n"); fflush(stdout);
  auto b = f->create_node_instance(rclcpp::NodeOptions().parameter_overrides({{"tag", "second"}}));
  printf("CREATED second\n"); fflush(stdout);
  rclcpp::executors::SingleThreadedExecutor e;
  e.add_node(a.get_node_base_interface()); e.add_node(b.get_node_base_interface());
  e.spin();
  rclcpp::shutdown();
}
X
cat > src/lc.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>
using CR = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;
class Lc : public rclcpp_lifecycle::LifecycleNode {
public:
  Lc() : LifecycleNode("dup_lc") { tag_ = declare_parameter("tag", std::string("unset")); }
  CR on_configure(const rclcpp_lifecycle::State &) override { printf("CONFIGURED tag=%s\n", tag_.c_str()); fflush(stdout); return CR::SUCCESS; }
  CR on_activate(const rclcpp_lifecycle::State &) override { printf("ACTIVATED tag=%s\n", tag_.c_str()); fflush(stdout); return CR::SUCCESS; }
  std::string tag_;
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<Lc>();
  rclcpp::spin(n->get_node_base_interface());
  rclcpp::shutdown();
}
X
cat > py_node.py <<'X'
#!/usr/bin/env python3
import sys, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import String
rclpy.init(args=sys.argv)
n = Node('dup_node')
tag = n.declare_parameter('tag', 'unset').value
n.declare_parameter('note', 'none')
seen = set()
def cb(ps):
    for p in ps:
        print(f'SETCB tag={tag} {p.name}={p.value}', flush=True)
    return SetParametersResult(successful=True)
n.add_on_set_parameters_callback(cb)
pub = n.create_publisher(String, 'chatter', 10)
n.create_timer(0.5, lambda: pub.publish(String(data=tag)))
def rx(m):
    if m.data not in seen:
        seen.add(m.data); print(f'RECV tag={tag} from={m.data}', flush=True)
n.create_subscription(String, 'chatter', rx, 10)
print(f'START tag={tag} fqn={n.get_fully_qualified_name()} rmw={rclpy.get_rmw_implementation_identifier()}', flush=True)
try:
    rclpy.spin(n)
except Exception:
    pass
X
cat > py_twice.py <<'X'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
rclpy.init()
a = Node('dup_node'); print('CREATED first', flush=True)
b = Node('dup_node'); print('CREATED second', flush=True)
a.get_logger().info('log from first')
b.get_logger().info('log from second')
e = SingleThreadedExecutor(); e.add_node(a); e.add_node(b)
try:
    e.spin()
except Exception:
    pass
X
cat > py_act.py <<'X'
#!/usr/bin/env python3
import sys, rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from tf2_msgs.action import LookupTransform
rclpy.init(args=sys.argv)
n = Node('dup_act')
tag = n.declare_parameter('tag', 'unset').value
def ex(gh):
    print(f'GOAL tag={tag} target={gh.request.target_frame}', flush=True)
    gh.succeed(); r = LookupTransform.Result(); r.transform.header.frame_id = tag; return r
s = ActionServer(n, LookupTransform, 'lookup', ex)
print(f'START tag={tag}', flush=True)
try:
    rclpy.spin(n)
except Exception:
    pass
X
chmod +x *.py
cat > launch/one.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='dupn', executable='py_node.py', name='dup_node', output='screen')])
X
cat > launch/override.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    # cpp_talker's default name is cpp_talker; name= renames it to dup_node
    return LaunchDescription([Node(package='dupn', executable='cpp_talker', name='dup_node',
        parameters=[{'tag': 'launch_cpp'}], output='screen')])
X
cat > launch/comp.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
def generate_launch_description():
    return LaunchDescription([ComposableNodeContainer(name='dup_container', namespace='', package='rclcpp_components',
        executable='component_container', output='screen', composable_node_descriptions=[
        ComposableNode(package='dupn', plugin='dupn::Talker', name='dup_comp', parameters=[{'tag': 'c1'}]),
        ComposableNode(package='dupn', plugin='dupn::Talker', name='dup_comp', parameters=[{'tag': 'c2'}])])])
X
cat > launch/fix_ns.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        Node(package='dupn', executable='py_node.py', name='dup_node', namespace='robot1', parameters=[{'tag': 'r1'}], output='screen'),
        Node(package='dupn', executable='py_node.py', name='dup_node', namespace='robot2', parameters=[{'tag': 'r2'}], output='screen')])
X
cat > launch/fix_push.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace
def generate_launch_description():
    def g(ns, tag):
        return GroupAction([PushRosNamespace(ns),
            Node(package='dupn', executable='py_node.py', name='dup_node', parameters=[{'tag': tag}], output='screen')])
    return LaunchDescription([g('robot1', 'p1'), g('robot2', 'p2')])
X
cd $W && MAKEFLAGS=-j1 colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
source $W/install/setup.bash
L=/logs; mkdir -p $L

# run a CLI command, show stdout/stderr separately and the exit code
cli() { echo "\$ $*"; timeout 30 "$@" >/tmp/o 2>/tmp/e; rc=$?; sed 's/^/  out| /' /tmp/o; sed 's/^/  err| /' /tmp/e; echo "  rc=$rc"; }
# same, but only print a one-line summary (used in repeat loops)
q() { timeout 30 "$@" >/tmp/o 2>/tmp/e; echo "rc=$? $(tr '\n' ' ' </tmp/o | cut -c1-160) ERR:$(grep -c 'share an exact name' /tmp/e)"; }
bg() { local name=$1; shift; "$@" >$L/$name.log 2>&1 & echo $! >$L/$name.pid; }
stopall() { for f in $L/*.pid; do [ -f "$f" ] && kill -INT $(cat $f) 2>/dev/null; done; sleep 2;
  for f in $L/*.pid; do [ -f "$f" ] && kill -9 $(cat $f) 2>/dev/null; rm -f $f; done
  pkill -9 -f /ws/install 2>/dev/null; pkill -9 -f component_container 2>/dev/null; pkill -9 -f 'ros2 launch' 2>/dev/null; sleep 1; ros2 daemon stop >/dev/null 2>&1; }
showlog() { for f in "$@"; do echo "  [log $f]"; grep -vE '^\s*$' $L/$f.log | head -40 | sed 's/^/    /'; done; }
section() { echo; echo "############ $*"; echo "uptime: $(uptime)"; }

section "0. where the warning text lives"
grep -rn "share an exact name" /opt/ros/$ROS_DISTRO/lib/python3*/site-packages/ 2>/dev/null | sed "s#/opt/ros/$ROS_DISTRO/lib/##"
echo "binary libs containing the text:"; grep -rl "share an exact name" /opt/ros/$ROS_DISTRO/lib/*.so 2>/dev/null || echo "  none"

section "1. single node baseline"
bg a ros2 run dupn py_node.py --ros-args -p tag:=A; sleep 5
cli ros2 node list
stopall

section "2. ros2 run twice, same name (/dup_node), tags A and B"
bg a ros2 run dupn py_node.py --ros-args -p tag:=A
bg b ros2 run dupn py_node.py --ros-args -p tag:=B; sleep 6
cli ros2 node list
cli ros2 node info /dup_node
cli ros2 param list /dup_node
cli ros2 param get /dup_node tag
cli ros2 param dump /dup_node
cli ros2 topic list
cli ros2 service list
cli ros2 topic info /chatter
echo "--- ros2 param get /dup_node tag x$N"
for i in $(seq $N); do q ros2 param get /dup_node tag; done | sort | uniq -c
echo "--- ros2 param set /dup_node note v_i x10"
for i in $(seq 10); do q ros2 param set /dup_node note v$i; done | sort | uniq -c
echo "SETCB lines per node:"; echo "  A: $(grep -c SETCB $L/a.log)  B: $(grep -c SETCB $L/b.log)"
grep -h SETCB $L/a.log $L/b.log | sed 's/^/    /'
echo "--- ros2 service call /dup_node/get_parameters x$N"
for i in $(seq $N); do timeout 30 ros2 service call /dup_node/get_parameters rcl_interfaces/srv/GetParameters "{names: [tag]}" 2>&1 | grep -oE "string_value='[^']*'" | head -1; echo "rc=${PIPESTATUS[0]}"; done | paste -d' ' - - | sort | uniq -c
echo "--- topic echo /chatter for 5s: messages per tag"
timeout 5 ros2 topic echo /chatter std_msgs/msg/String 2>/dev/null | grep data | sort | uniq -c
echo "--- each node's subscription saw:"; grep -h RECV $L/a.log $L/b.log | sed 's/^/    /'
showlog a b
stopall

section "3. same-name nodes: rclcpp lifecycle (/dup_lc) x2"
bg la ros2 run dupn cpp_lc --ros-args -p tag:=LA
bg lb ros2 run dupn cpp_lc --ros-args -p tag:=LB; sleep 5
cli ros2 lifecycle nodes
cli ros2 lifecycle get /dup_lc
cli ros2 lifecycle set /dup_lc configure
echo "--- after one configure: ros2 lifecycle get x10"
for i in $(seq 10); do q ros2 lifecycle get /dup_lc; done | sort | uniq -c
cli ros2 lifecycle set /dup_lc configure
cli ros2 lifecycle set /dup_lc configure
echo "--- after three configure calls: ros2 lifecycle get x10"
for i in $(seq 10); do q ros2 lifecycle get /dup_lc; done | sort | uniq -c
showlog la lb
stopall

section "4. same-name nodes with the same action server (/dup_act, action /lookup) x2"
bg xa ros2 run dupn py_act.py --ros-args -p tag:=XA
bg xb ros2 run dupn py_act.py --ros-args -p tag:=XB; sleep 6
cli ros2 node list
cli ros2 action list
cli ros2 action info /lookup
echo "--- ros2 action send_goal x10"
for i in $(seq 10); do timeout 30 ros2 action send_goal /lookup tf2_msgs/action/LookupTransform "{target_frame: g$i}" >/tmp/o 2>&1; rc=$?; echo "rc=$rc $(grep -oE 'Goal (accepted|was rejected)[^.]*|Goal finished with status: [A-Z]+|frame_id: [a-zA-Z]+' /tmp/o | tr '\n' ' ')"; done | sort | uniq -c
echo "GOAL lines per server: XA $(grep -c GOAL $L/xa.log) XB $(grep -c GOAL $L/xb.log)"
showlog xa xb
stopall

section "5. cause: same launch file started twice"
bg l1 ros2 launch dupn one.launch.py
bg l2 ros2 launch dupn one.launch.py; sleep 8
cli ros2 node list
showlog l1 l2
stopall

section "6. cause: launch name= override renames cpp_talker to dup_node, plus ros2 run py_node (default dup_node)"
bg ov ros2 launch dupn override.launch.py
bg pr ros2 run dupn py_node.py --ros-args -p tag:=run_py; sleep 8
cli ros2 node list
for i in $(seq 10); do q ros2 param get /dup_node tag; done | sort | uniq -c
showlog ov pr
stopall

section "7. cause: two ComposableNodes with the same name in one container"
bg cp ros2 launch dupn comp.launch.py; sleep 10
cli ros2 node list
cli ros2 component list
for i in $(seq 10); do q ros2 param get /dup_comp tag; done | sort | uniq -c
echo "--- ros2 component load a third dup_comp by CLI"
cli ros2 component load /dup_container dupn dupn::Talker -n dup_comp -p tag:=c3
cli ros2 component list
showlog cp
stopall

section "8. cause: same name twice in one process (rclcpp)"
bg tw ros2 run dupn cpp_twice; sleep 6
cli ros2 node list
for i in $(seq 10); do q ros2 param get /cpp_talker tag; done | sort | uniq -c
showlog tw
stopall

section "9. cause: same name twice in one process (rclpy)"
bg pt ros2 run dupn py_twice.py; sleep 6
cli ros2 node list
showlog pt
stopall

section "10. fix: -r __node:=dup_node_b on the second instance"
bg a ros2 run dupn py_node.py --ros-args -p tag:=A
bg b ros2 run dupn py_node.py --ros-args -p tag:=B -r __node:=dup_node_b; sleep 6
cli ros2 node list
echo "--- get /dup_node tag x10"; for i in $(seq 10); do q ros2 param get /dup_node tag; done | sort | uniq -c
echo "--- get /dup_node_b tag x10"; for i in $(seq 10); do q ros2 param get /dup_node_b tag; done | sort | uniq -c
stopall

section "11. fix: -r __ns:=/robot1 on the second instance"
bg a ros2 run dupn py_node.py --ros-args -p tag:=A
bg b ros2 run dupn py_node.py --ros-args -p tag:=B -r __ns:=/robot1; sleep 6
cli ros2 node list
cli ros2 topic list
echo "--- get /dup_node tag x10"; for i in $(seq 10); do q ros2 param get /dup_node tag; done | sort | uniq -c
echo "--- get /robot1/dup_node tag x10"; for i in $(seq 10); do q ros2 param get /robot1/dup_node tag; done | sort | uniq -c
stopall

section "12. fix: launch namespace= (robot1, robot2)"
bg fn ros2 launch dupn fix_ns.launch.py; sleep 8
cli ros2 node list
for i in $(seq 5); do q ros2 param get /robot1/dup_node tag; done | sort | uniq -c
for i in $(seq 5); do q ros2 param get /robot2/dup_node tag; done | sort | uniq -c
stopall

section "13. fix: GroupAction + PushRosNamespace"
bg fp ros2 launch dupn fix_push.launch.py; sleep 8
cli ros2 node list
for i in $(seq 5); do q ros2 param get /robot1/dup_node tag; done | sort | uniq -c
for i in $(seq 5); do q ros2 param get /robot2/dup_node tag; done | sort | uniq -c
stopall

section "14. is there an option that refuses duplicate names?"
D=/opt/ros/$ROS_DISTRO
echo "rclcpp NodeOptions setters:"; grep -oE '^\s+[a-z_]+\(\s*(bool|const|rcl|std|size_t|[A-Za-z:]+)' $D/include/rclcpp/rclcpp/node_options.hpp | awk '{print $1}' | sort -u | tr '\n' ' '; echo
echo "rclpy Node.__init__ keyword args:"; python3 - <<'X'
import inspect, rclpy.node
print(' '.join(inspect.signature(rclpy.node.Node.__init__).parameters))
X
echo "grep unique/duplicate in rcl, rclcpp, rclpy node headers/sources:"
grep -rniE "unique|duplicate" $D/include/rcl/rcl/node.h $D/include/rcl/rcl/node_options.h $D/include/rclcpp/rclcpp/node_options.hpp $D/include/rclcpp/rclcpp/node.hpp $D/lib/python3*/site-packages/rclpy/node.py 2>/dev/null | sed "s#$D/##" | head -20
echo "=== done"
