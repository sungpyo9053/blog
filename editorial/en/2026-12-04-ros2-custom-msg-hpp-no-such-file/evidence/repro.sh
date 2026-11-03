#!/bin/bash
# Run inside ros:<distro>-ros-base (docker run --ulimit core=0 --pids-limit 64 -e MAKEFLAGS=-j1).
# Reproduces "fatal error: <pkg>/msg/<name>.hpp: No such file or directory" and related
# CMake errors for C++ nodes that use custom interfaces. One package per case, built one at a time.
source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
export MAKEFLAGS=-j1
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rosidl-cmake ros-$ROS_DISTRO-rosidl-default-generators \
  ros-$ROS_DISTRO-rosidl-generator-cpp ros-$ROS_DISTRO-ament-cmake 2>/dev/null
echo "rmw default: ${RMW_IMPLEMENTATION:-unset (distro default)}"
cmake --version | head -1; g++ --version | head -1
W=/ws; mkdir -p $W/src; cd $W/src

# mkpkg NAME MSGFILES INCLUDE_LINE CMAKE_BLOCK [nogroup]
mkpkg() {
  local P=$1 MSGS=$2 INC=$3 LINK=$4 GROUP='<member_of_group>rosidl_interface_packages</member_of_group>'
  [ "$5" = nogroup ] && GROUP=''
  mkdir -p $P/msg $P/src
  for m in $MSGS; do printf 'string name\nint16[] id\nfloat32[] pos\n' > $P/msg/$m; done
  cat > $P/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$P</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>rosidl_default_generators</buildtool_depend>
<depend>rclcpp</depend><exec_depend>rosidl_default_runtime</exec_depend>
$GROUP
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > $P/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($P)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rosidl_default_generators REQUIRED)
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp::rclcpp)
$LINK
install(TARGETS node DESTINATION lib/\${PROJECT_NAME})
ament_export_dependencies(rosidl_default_runtime)
ament_package()
X
  cat > $P/src/node.cpp <<X
#include <rclcpp/rclcpp.hpp>
$INC
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("leg_node");
  auto pub = n->create_publisher<$P::msg::Leg>("leg", 10);
  $P::msg::Leg m; m.name = "front_left"; m.id = {1, 2}; m.pos = {0.5f};
  pub->publish(m);
  RCLCPP_INFO(n->get_logger(), "RESULT published name=%s ids=%zu", m.name.c_str(), m.id.size());
  rclcpp::shutdown();
}
X
}
GEN='rosidl_generate_interfaces(${PROJECT_NAME} MSGLIST)'
NEWLINK='rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} rosidl_typesupport_cpp)
target_link_libraries(node "${cpp_typesupport_target}")'
OLDLINK='rosidl_target_interfaces(node ${PROJECT_NAME} "rosidl_typesupport_cpp")'
sub() { sed -i "s#MSGLIST#$2#" $1/CMakeLists.txt; }

ALL="Leg.msg MotorCmd.msg IMUData.msg Pose2D.msg WheelRPM.msg"
mkpkg c1_ok       "$ALL"    '#include "c1_ok/msg/leg.hpp"'       "$GEN
$NEWLINK"
mkpkg c2_camel    "Leg.msg" '#include "c2_camel/msg/Leg.hpp"'    "$GEN
$NEWLINK"
mkpkg c3_nolink   "Leg.msg" '#include "c3_nolink/msg/leg.hpp"'   "$GEN"
mkpkg c4_oldmacro "Leg.msg" '#include "c4_oldmacro/msg/leg.hpp"' "$GEN
$OLDLINK"
mkpkg c5_order    "Leg.msg" '#include "c5_order/msg/leg.hpp"'    "$NEWLINK
$GEN"
mkpkg c6_nogroup  "Leg.msg" '#include "c6_nogroup/msg/leg.hpp"'  "$GEN
$NEWLINK" nogroup
mkpkg c7_lower    "leg.msg" '#include "c7_lower/msg/leg.hpp"'    "$GEN
$NEWLINK"
mkpkg c8_atd      "Leg.msg" '#include "c8_atd/msg/leg.hpp"'      "$GEN
ament_target_dependencies(node \${PROJECT_NAME})"
mkpkg c9_incdir   "Leg.msg" '#include "c9_incdir/msg/leg.hpp"'   "$GEN
include_directories(\${CMAKE_CURRENT_BINARY_DIR}/rosidl_generator_cpp)"
mkpkg c10_nofind  "Leg.msg" '#include "c10_nofind/msg/leg.hpp"'  "$GEN
$NEWLINK"
sed -i '/find_package(rosidl_default_generators REQUIRED)/d' c10_nofind/CMakeLists.txt
for p in c1_ok c2_camel c3_nolink c4_oldmacro c5_order c6_nogroup c7_lower c8_atd c9_incdir c10_nofind; do
  if [ $p = c1_ok ]; then L=""; for m in $ALL; do L="$L \"msg/$m\""; done; sub $p "$L"
  elif [ $p = c7_lower ]; then sub $p '"msg/leg.msg"'; else sub $p '"msg/Leg.msg"'; fi
done

# Separate interface package + consumer package (the usual recommendation)
mkpkg leg_interfaces "Leg.msg" '' "$GEN"
sub leg_interfaces '"msg/Leg.msg"'
sed -i '/add_executable/d; /target_link_libraries(node rclcpp/d; /install(TARGETS/d' leg_interfaces/CMakeLists.txt
rm -r leg_interfaces/src
mkdir -p leg_user/src
cat > leg_user/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>leg_user</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>leg_interfaces</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > leg_user/CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(leg_user)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(leg_interfaces REQUIRED)
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp::rclcpp ${leg_interfaces_TARGETS})
install(TARGETS node DESTINATION lib/${PROJECT_NAME})
ament_package()
X
sed 's/c1_ok/leg_interfaces/g' c1_ok/src/node.cpp > leg_user/src/node.cpp

cd $W
build() {
  local P=$1; local t0=$(date +%s.%N)
  colcon build --executor sequential --packages-select $P > /tmp/b_$P.log 2>&1; local rc=$?
  local t1=$(date +%s.%N)
  echo "--- case=$P${2:+ ($2)} rc=$rc seconds=$(python3 -c "print(round($t1-$t0,1))")"
  # first error with 4 lines of context, then any deprecation/warning with 2 lines
  grep -m1 -A4 -E "CMake Error|fatal error|error:|Unknown CMake" log/latest_build/$P/stdout_stderr.log 2>/dev/null | sed 's#/ws/##'
  grep -A2 -E "Deprecation|CMake Warning" log/latest_build/$P/stdout_stderr.log 2>/dev/null | sed 's#/ws/##' | head -8
  echo "--- end $P"
}
for p in c1_ok c2_camel c3_nolink c4_oldmacro c5_order c6_nogroup c7_lower c8_atd c9_incdir c10_nofind leg_interfaces leg_user; do
  build $p
done
# second colcon build of the two packages that failed without a CMake error: does a rebuild change anything?
build c3_nolink "second build"
build c9_incdir "second build"
ls build/c3_nolink/rosidl_generator_cpp/c3_nolink/msg/leg.hpp build/c9_incdir/rosidl_generator_cpp/c9_incdir/msg/leg.hpp 2>&1 | sed 's#^#  header present after failed builds: #'
echo "=== c7_lower full rosidl_adapter message"
grep -A1 InvalidResourceName log/latest_build/c7_lower/stdout_stderr.log 2>/dev/null | head -3
grep -h -A1 InvalidResourceName build/c7_lower/CMakeFiles/CMakeOutput.log /tmp/b_c7_lower.log 2>/dev/null | head -3
# Same two broken packages again from a clean build dir, now with make -j2 (2 vCPU runner), built twice
for p in c3_nolink c9_incdir; do rm -r build/$p; done
export MAKEFLAGS=-j2
for p in c3_nolink c9_incdir; do build $p "clean, -j2, build 1"; build $p "-j2, build 2"; done
export MAKEFLAGS=-j1
echo "=== generated C++ message headers for c1_ok (build tree, top-level only)"
ls build/c1_ok/rosidl_generator_cpp/c1_ok/msg/ | grep -v -E '^detail$'
echo "=== installed path(s) of leg.hpp for c1_ok"
find install/c1_ok -name leg.hpp | sed 's#^#  #'
source install/setup.bash
for p in c1_ok c3_nolink c4_oldmacro c9_incdir c10_nofind leg_user; do
  echo "=== run $p"; timeout 20 ros2 run $p node 2>&1 | sed -E 's/\[[0-9]+\.[0-9]+\]//'; echo "exit=${PIPESTATUS[0]}"
done
echo "=== python import of same-package messages (c1_ok)"
python3 -c "from c1_ok.msg import Leg, IMUData; print('PY OK', repr(Leg().name), IMUData.__name__)" 2>&1 | tail -1
echo "=== ros2 interface show c1_ok/msg/IMUData"; timeout 30 ros2 interface show c1_ok/msg/IMUData 2>&1
echo "=== done"
