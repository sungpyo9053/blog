#!/bin/bash
# usage inside container: run.sh  -> builds one package per CMake variant, prints result lines
source /opt/ros/$ROS_DISTRO/setup.bash
echo "DISTRO $ROS_DISTRO cmake=$(cmake --version | head -1 | awk '{print $3}') ament_cmake=$(dpkg -s ros-$ROS_DISTRO-ament-cmake 2>/dev/null | awk '/^Version/{print $2}')"
mk() { # name, link-lines
  p=/ws/src/$1; mkdir -p $p/src
  cat > $p/package.xml <<X
<?xml version="1.0"?><package format="3"><name>$1</name><version>0.0.0</version><description>t</description><maintainer email="test@example.com">t</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_msgs</depend><export><build_type>ament_cmake</build_type></export></package>
X
  cat > $p/src/n.cpp <<'X'
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
int main(int argc, char ** argv){ rclcpp::init(argc, argv); auto n = rclcpp::Node::make_shared("n");
  auto pub = n->create_publisher<std_msgs::msg::String>("t", 10); std_msgs::msg::String m; m.data = "ok"; pub->publish(m);
  rclcpp::shutdown(); return 0; }
X
  printf 'cmake_minimum_required(VERSION 3.10)\nproject(%s)\nfind_package(ament_cmake REQUIRED)\nfind_package(rclcpp REQUIRED)\nfind_package(std_msgs REQUIRED)\nadd_executable(n src/n.cpp)\n%b\ninstall(TARGETS n DESTINATION lib/${PROJECT_NAME})\nament_package()\n' "$1" "$2" > $p/CMakeLists.txt
}
mk atd 'ament_target_dependencies(n rclcpp std_msgs)'
mk tll_targets 'target_link_libraries(n PUBLIC rclcpp::rclcpp ${std_msgs_TARGETS})'
mk tll_pkgns 'target_link_libraries(n PUBLIC rclcpp::rclcpp std_msgs::std_msgs)'
mk tll_mixed 'target_link_libraries(n rclcpp::rclcpp)\ntarget_link_libraries(n PUBLIC ${std_msgs_TARGETS})'
mk tll_rclcpp_only 'target_link_libraries(n PUBLIC rclcpp::rclcpp)'
mk atd_findpkg 'find_package(ament_cmake_target_dependencies REQUIRED)\nament_target_dependencies(n rclcpp std_msgs)'
cd /ws
for p in ${ONLY:-atd tll_targets tll_pkgns tll_mixed tll_rclcpp_only atd_findpkg}; do
  rm -rf build/$p install/$p log
  out=$(colcon build --packages-select $p --event-handlers console_direct+ 2>&1); rc=$?
  warn=$(echo "$out" | grep -m1 -A9 "Deprecation Warning at /opt")
  err=$(echo "$out" | grep -m1 -A2 -E "CMake Error|error:|undefined reference")
  run=""; [ $rc -eq 0 ] && { source install/setup.bash; ./install/$p/lib/$p/n >/dev/null 2>&1 && run=run_ok || run=run_fail; }
  echo "RESULT $ROS_DISTRO $p rc=$rc $run"
  [ -n "$warn" ] && echo "  WARN: $(echo $warn | head -c 900)"
  [ -n "$err" ] && echo "  ERR: $(echo $err | head -c 400)"
done
