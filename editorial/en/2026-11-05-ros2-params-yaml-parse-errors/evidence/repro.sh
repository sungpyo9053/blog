#!/bin/bash
# Run inside ros:<distro>-ros-base. Reproduces rcl argument / params-file parse errors
# for an rclpy node and an rclcpp node that declare: number (int, default 1),
# timer_period (double, default 0.5), label (string, default "default").
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcl-yaml-param-parser ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp libyaml-0-2 2>/dev/null
W=/ws; mkdir -p $W/src/pnode/src; cd $W/src/pnode
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>pnode</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend>
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
ament_package()
X
cat > src/node.cpp <<'X'
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("number_publisher");
  int64_t a = n->declare_parameter<int64_t>("number", 1);
  auto b = n->declare_parameter("timer_period", 0.5);
  auto c = n->declare_parameter("label", std::string("default"));
  RCLCPP_INFO(n->get_logger(), "RESULT number=%lld timer_period=%g label=%s", (long long)a, b, c.c_str());
  RCLCPP_DEBUG(n->get_logger(), "DEBUG-VISIBLE");
  rclcpp::shutdown();
}
X
cat > py_node.py <<'X'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node('number_publisher')
a = n.declare_parameter('number', 1).value
b = n.declare_parameter('timer_period', 0.5).value
c = n.declare_parameter('label', 'default').value
n.get_logger().info(f'RESULT number={a} timer_period={b} label={c}')
n.get_logger().debug('DEBUG-VISIBLE')
rclpy.shutdown()
X
chmod +x py_node.py
cd $W && colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
source $W/install/setup.bash

Y=/y; mkdir -p $Y
cat > $Y/good.yaml <<'X'
/number_publisher:
  ros__parameters:
    number: 5
    timer_period: 1.5
    label: from_yaml
X
cat > $Y/no_leading_slash.yaml <<'X'
number_publisher:
  ros__parameters:
    number: 5
X
cat > $Y/wildcard.yaml <<'X'
/**:
  ros__parameters:
    number: 5
X
cat > $Y/wrong_node_name.yaml <<'X'
/number_node:
  ros__parameters:
    number: 5
X
cat > $Y/no_ros_parameters.yaml <<'X'
/number_publisher:
  number: 5
X
cat > $Y/flat_no_indent.yaml <<'X'
/number_publisher:
ros__parameters:
number: 5
X
printf '/number_publisher:\n\tros__parameters:\n\t\tnumber: 5\n' > $Y/tabs.yaml
cat > $Y/comments.yaml <<'X'
# full-line comment
/number_publisher:
  ros__parameters:
    # indented comment
    number: 5   # inline comment
    label: "a # inside quotes"
X
cat > $Y/int_for_double.yaml <<'X'
/number_publisher:
  ros__parameters:
    timer_period: 1
X
cat > $Y/string_for_int.yaml <<'X'
/number_publisher:
  ros__parameters:
    number: "5"
X
cat > $Y/hex_string.yaml <<'X'
/number_publisher:
  ros__parameters:
    label: 00 13 a2 00 41
X
cat > $Y/null_value.yaml <<'X'
/number_publisher:
  ros__parameters:
    number:
X
cat > $Y/mixed_list.yaml <<'X'
/number_publisher:
  ros__parameters:
    extra: [1, 2.5]
X
: > $Y/empty.yaml
cat > $Y/namespaced_ok.yaml <<'X'
/robot1/number_publisher:
  ros__parameters:
    number: 5
X
cat > $Y/namespaced_nested.yaml <<'X'
robot1:
  number_publisher:
    ros__parameters:
      number: 5
X

run() { # label, args...
  local label=$1; shift
  for exe in py_node.py cpp_node; do
    echo "----- [$label] $exe $*"
    timeout 20 ros2 run pnode $exe "$@" 2>&1 | grep -v '^\s*$' | sed -e 's/\[[0-9]\{10\}\.[0-9]*\]/[T]/' | head -25
    echo "exit=${PIPESTATUS[0]}"
  done
}
run baseline
run good --ros-args --params-file $Y/good.yaml
run no_leading_slash --ros-args --params-file $Y/no_leading_slash.yaml
run wildcard --ros-args --params-file $Y/wildcard.yaml
run wrong_node_name --ros-args --params-file $Y/wrong_node_name.yaml
run no_ros_parameters --ros-args --params-file $Y/no_ros_parameters.yaml
run flat_no_indent --ros-args --params-file $Y/flat_no_indent.yaml
run tabs --ros-args --params-file $Y/tabs.yaml
run comments --ros-args --params-file $Y/comments.yaml
run int_for_double --ros-args --params-file $Y/int_for_double.yaml
run string_for_int --ros-args --params-file $Y/string_for_int.yaml
run hex_string --ros-args --params-file $Y/hex_string.yaml
run null_value --ros-args --params-file $Y/null_value.yaml
run mixed_list --ros-args --params-file $Y/mixed_list.yaml
run empty --ros-args --params-file $Y/empty.yaml
run missing_file --ros-args --params-file $Y/does_not_exist.yaml
run namespaced_ok --ros-args -r __ns:=/robot1 --params-file $Y/namespaced_ok.yaml
run namespaced_nested --ros-args -r __ns:=/robot1 --params-file $Y/namespaced_nested.yaml
run params_file_without_ros_args --params-file $Y/good.yaml
run typo_param_file --ros-args --param-file $Y/good.yaml
run p_ok --ros-args -p number:=7 -p timer_period:=1.0
run p_space_after_assign --ros-args -p number:=7 -p timer_period:= 1.0
run p_dash_name --ros-args -p -publish_rate:=100.0
run p_int_for_double --ros-args -p timer_period:=1
run p_string_with_space --ros-args -p "label:=hello world"
run p_quoted_number_string --ros-args -p "label:='42'"
run p_no_ros_args -p number:=7
run log_level_global --ros-args --log-level DEBUG
run log_level_per_logger --ros-args --log-level number_publisher:=DEBUG
run log_level_lowercase --ros-args --log-level debug
