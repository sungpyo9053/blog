#!/bin/bash
# Run inside ros:<distro>-ros-base as root. Measures ROS 2 lifecycle (managed) node behavior:
#  - "publisher is not activated" in rclcpp and rclpy, per state and per on_activate style
#  - timers and subscriptions while inactive
#  - ros2 lifecycle set for an invalid transition
#  - launch_ros LifecycleNode: no events, activate-only handler, configure+activate events, autostart
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclcpp-lifecycle ros-$ROS_DISTRO-rclpy \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2lifecycle ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros \
  ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
W=/ws; mkdir -p $W/src/lc/src $W/launch; cd $W/src/lc
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>lc</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<depend>rclcpp</depend><depend>rclcpp_lifecycle</depend><depend>std_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(lc)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(lc_cpp src/lc.cpp)
target_link_libraries(lc_cpp rclcpp::rclcpp rclcpp_lifecycle::rclcpp_lifecycle ${std_msgs_TARGETS})
install(TARGETS lc_cpp DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS lc_py.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
# C++ lifecycle node. LC_MODE: base = call LifecycleNode::on_activate/on_deactivate,
# none = override returns SUCCESS and does nothing, manual = pub_->on_activate()/on_deactivate()
cat > src/lc.cpp <<'X'
#include <cstdlib>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>
#include <std_msgs/msg/int32.hpp>
using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;
class Lc : public rclcpp_lifecycle::LifecycleNode {
public:
  Lc() : LifecycleNode("lc_cpp") { const char * m = std::getenv("LC_MODE"); mode_ = m ? m : "base";
    RCLCPP_INFO(get_logger(), "constructed mode=%s", mode_.c_str()); }
  void report(const char * where) {
    RCLCPP_INFO(get_logger(), "COUNTS at %s: timer_ticks=%d sub_msgs=%d pub_is_activated=%d", where, ticks_, subs_,
      pub_ ? (int)pub_->is_activated() : -1);
    ticks_ = 0; subs_ = 0; }
  CallbackReturn on_configure(const rclcpp_lifecycle::State &) override {
    pub_ = create_publisher<std_msgs::msg::Int32>("chatter", 10);
    timer_ = create_wall_timer(std::chrono::milliseconds(100), [this]() {
      ++ticks_; std_msgs::msg::Int32 m; m.data = ticks_; pub_->publish(m); });
    sub_ = create_subscription<std_msgs::msg::Int32>("in", 10, [this](std_msgs::msg::Int32::ConstSharedPtr) { ++subs_; });
    RCLCPP_INFO(get_logger(), "on_configure"); report("on_configure"); return CallbackReturn::SUCCESS; }
  CallbackReturn on_activate(const rclcpp_lifecycle::State & s) override {
    report("on_activate(entry, counts while inactive)");
    if (mode_ == "base") LifecycleNode::on_activate(s);
    if (mode_ == "manual") pub_->on_activate();
    RCLCPP_INFO(get_logger(), "on_activate done, pub_is_activated=%d", (int)pub_->is_activated());
    return CallbackReturn::SUCCESS; }
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & s) override {
    report("on_deactivate(entry, counts while active)");
    if (mode_ == "base") LifecycleNode::on_deactivate(s);
    if (mode_ == "manual") pub_->on_deactivate();
    return CallbackReturn::SUCCESS; }
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State &) override {
    report("on_cleanup(entry, counts while inactive again)");
    timer_.reset(); sub_.reset(); pub_.reset(); return CallbackReturn::SUCCESS; }
  CallbackReturn on_shutdown(const rclcpp_lifecycle::State &) override {
    RCLCPP_INFO(get_logger(), "on_shutdown"); timer_.reset(); sub_.reset(); pub_.reset(); return CallbackReturn::SUCCESS; }
private:
  std::string mode_; int ticks_ = 0; int subs_ = 0;
  rclcpp_lifecycle::LifecyclePublisher<std_msgs::msg::Int32>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr sub_;
};
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<Lc>();
  rclcpp::spin(n->get_node_base_interface());
  rclcpp::shutdown();
}
X
# Python lifecycle node. LC_MODE: base = super().on_activate/on_deactivate, none = return SUCCESS only
cat > lc_py.py <<'X'
#!/usr/bin/env python3
import os
import rclpy
from rclpy.lifecycle import Node, TransitionCallbackReturn
from std_msgs.msg import Int32
class Lc(Node):
    def __init__(self):
        super().__init__('lc_py')
        self.mode = os.environ.get('LC_MODE', 'base')
        self.ticks = 0
        self.subs = 0
        self.pub = None
        self.get_logger().info('constructed mode=%s' % self.mode)
    def report(self, where):
        act = -1
        if self.pub is not None:
            v = getattr(self.pub, 'is_activated', getattr(self.pub, '_enabled', -1))
            act = int(v() if callable(v) else v)
        self.get_logger().info('COUNTS at %s: timer_ticks=%d sub_msgs=%d pub_is_activated=%d' % (where, self.ticks, self.subs, act))
        self.ticks = 0
        self.subs = 0
    def tick(self):
        self.ticks += 1
        m = Int32()
        m.data = self.ticks
        self.pub.publish(m)
    def cb(self, m):
        self.subs += 1
    def on_configure(self, state):
        self.pub = self.create_lifecycle_publisher(Int32, 'chatter', 10)
        self.timer = self.create_timer(0.1, self.tick)
        self.sub = self.create_subscription(Int32, 'in', self.cb, 10)
        self.get_logger().info('on_configure')
        self.report('on_configure')
        return TransitionCallbackReturn.SUCCESS
    def on_activate(self, state):
        self.report('on_activate(entry, counts while inactive)')
        if self.mode == 'base':
            super().on_activate(state)
        self.get_logger().info('on_activate done')
        return TransitionCallbackReturn.SUCCESS
    def on_deactivate(self, state):
        self.report('on_deactivate(entry, counts while active)')
        if self.mode == 'base':
            super().on_deactivate(state)
        return TransitionCallbackReturn.SUCCESS
    def on_cleanup(self, state):
        self.report('on_cleanup(entry, counts while inactive again)')
        self.destroy_timer(self.timer)
        self.destroy_subscription(self.sub)
        self.destroy_lifecycle_publisher(self.pub) if hasattr(self, 'destroy_lifecycle_publisher') else self.destroy_publisher(self.pub)
        self.pub = None
        return TransitionCallbackReturn.SUCCESS
    def on_shutdown(self, state):
        self.get_logger().info('on_shutdown')
        return TransitionCallbackReturn.SUCCESS
def main():
    rclpy.init()
    n = Lc()
    try:
        rclpy.spin(n)
    except BaseException as e:
        print('spin ended:', type(e).__name__)
if __name__ == '__main__':
    main()
X
chmod +x lc_py.py
cd $W
T0=$(date +%s.%N)
MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- > /tmp/build.log 2>&1
echo "BUILD exit=$? seconds=$(python3 -c "print(round($(date +%s.%N)-$T0,1))")"; tail -3 /tmp/build.log
source $W/install/setup.bash

echo_count() { # count messages on /chatter for 3 s
  timeout -s INT 4 ros2 topic echo /chatter std_msgs/msg/Int32 2>/dev/null | grep -c '^data:'
}
feed_in() { timeout -s INT 4 ros2 topic pub -r 10 /in std_msgs/msg/Int32 "{data: 1}" > /dev/null 2>&1; }
phase() { # $1 node name, $2 label
  feed_in & local fp=$!
  local c; c=$(echo_count); wait $fp
  echo "PHASE $2: echo_received=$c state=$(timeout 20 ros2 lifecycle get /$1 2>&1 | head -1)"
}
lset() { # node transition
  local out; out=$(timeout 20 ros2 lifecycle set /$1 $2 2>&1); local rc=$?
  echo "SET $2 -> rc=$rc out=$(echo "$out" | tr '\n' '|')"
}
run_node() { # $1 exe, $2 node name, $3 mode
  echo; echo "##### node=$2 exe=$1 LC_MODE=$3"
  ros2 daemon stop > /dev/null 2>&1; ros2 daemon start > /dev/null 2>&1
  # run the installed executable directly so the signal reaches the node process itself
  LC_MODE=$3 $W/install/lc/lib/lc/$1 > /tmp/node_$2_$3.log 2>&1 &
  local np=$!
  sleep 3
  echo "ros2 lifecycle nodes: $(timeout 20 ros2 lifecycle nodes 2>&1 | tr '\n' ' ')"
  phase $2 unconfigured
  lset $2 activate
  echo "available: $(timeout 20 ros2 lifecycle list /$2 2>&1 | tr '\n' '|')"
  lset $2 configure
  phase $2 inactive
  lset $2 activate
  phase $2 active
  lset $2 deactivate
  phase $2 deactivated
  lset $2 cleanup
  lset $2 shutdown
  echo "state after shutdown: $(timeout 20 ros2 lifecycle get /$2 2>&1 | head -1)"
  sleep 1; kill -INT $np 2>/dev/null; sleep 2; kill -9 $np 2>/dev/null; wait $np 2>/dev/null
  pkill -9 -f /install/lc/lib/lc/ 2>/dev/null; echo "leftover lc processes: $(pgrep -fc /install/lc/lib/lc/)"
  echo "--- node log (not-activated lines collapsed)"
  grep -v 'not activated' /tmp/node_$2_$3.log | sed 's/\[[0-9.]*\]//'
  echo "not_activated_lines=$(grep -c 'not activated' /tmp/node_$2_$3.log)"
  echo "first not-activated line: $(grep -m1 'not activated' /tmp/node_$2_$3.log)"
}
ros2 daemon start > /dev/null 2>&1
run_node lc_cpp lc_cpp base
run_node lc_cpp lc_cpp none
run_node lc_cpp lc_cpp manual
run_node lc_py.py lc_py base
run_node lc_py.py lc_py none

# ---------- launch tests ----------
cat > $W/launch/l1_plain.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
def generate_launch_description():
    return LaunchDescription([LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', namespace='', output='screen')])
X
cat > $W/launch/l2_no_namespace.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
def generate_launch_description():
    return LaunchDescription([LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', output='screen')])
X
cat > $W/launch/l3_activate_only.launch.py <<'X'
import lifecycle_msgs.msg
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
def generate_launch_description():
    node = LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', namespace='', output='screen')
    activate = RegisterEventHandler(OnStateTransition(target_lifecycle_node=node, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE))]))
    return LaunchDescription([activate, node])
X
cat > $W/launch/l4_configure_activate.launch.py <<'X'
import lifecycle_msgs.msg
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
def generate_launch_description():
    node = LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', namespace='', output='screen')
    configure = EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(node),
        transition_id=lifecycle_msgs.msg.Transition.TRANSITION_CONFIGURE))
    activate = RegisterEventHandler(OnStateTransition(target_lifecycle_node=node, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE))]))
    return LaunchDescription([activate, node, configure])
X
cat > $W/launch/l5_autostart.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
def generate_launch_description():
    return LaunchDescription([LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', namespace='', output='screen', autostart=True)])
X
cat > $W/launch/l6_configure_before_node.launch.py <<'X'
import lifecycle_msgs.msg
from launch import LaunchDescription
from launch.actions import EmitEvent
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
def generate_launch_description():
    node = LifecycleNode(package='lc', executable='lc_cpp', name='lc_cpp', namespace='', output='screen')
    configure = EmitEvent(event=ChangeState(lifecycle_node_matcher=matches_action(node),
        transition_id=lifecycle_msgs.msg.Transition.TRANSITION_CONFIGURE))
    return LaunchDescription([configure, node])
X
for L in l1_plain l2_no_namespace l3_activate_only l4_configure_activate l5_autostart l6_configure_before_node; do
  echo; echo "##### launch $L"
  pkill -9 -f /install/lc/lib/lc/ 2>/dev/null; ros2 daemon stop > /dev/null 2>&1; ros2 daemon start > /dev/null 2>&1
  T0=$(date +%s.%N)
  LC_MODE=base timeout -s INT 12 ros2 launch $W/launch/$L.launch.py > /tmp/launch_$L.log 2>&1 &
  lp=$!
  sleep 7
  echo "state at +7s: $(timeout 20 ros2 lifecycle get /lc_cpp 2>&1 | head -1)"
  wait $lp; echo "launch exit=$?"
  python3 - "$T0" /tmp/launch_$L.log <<'P'
import re, sys
t0 = float(sys.argv[1])
for line in open(sys.argv[2], errors='replace'):
    m = re.search(r'\[(\d{10}\.\d+)\] \[lc_cpp\]: (on_configure|on_activate done)', line)
    if m:
        print('  %s at +%.3f s after ros2 launch started' % (m.group(2), float(m.group(1)) - t0))
P
  grep -v 'not activated' /tmp/launch_$L.log | grep -v 'COUNTS' | sed 's/\[[0-9]\{10\}\.[0-9]*\]//' | head -25
  echo "not_activated_lines=$(grep -c 'not activated' /tmp/launch_$L.log)"
done
ros2 daemon stop > /dev/null 2>&1
echo "=== done $ROS_DISTRO"
