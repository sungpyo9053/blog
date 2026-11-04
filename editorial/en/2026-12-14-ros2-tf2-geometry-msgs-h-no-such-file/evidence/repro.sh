#!/bin/bash
# Run inside ros:<distro>-ros-base (docker run --ulimit core=0 --pids-limit 64 -e MAKEFLAGS=-j1).
# Reproduces "fatal error: tf2_geometry_msgs/tf2_geometry_msgs.h(pp): No such file or directory"
# and related build errors. One small ament_cmake package per case, built one at a time.
source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
export MAKEFLAGS=-j1
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-tf2 ros-$ROS_DISTRO-tf2-ros ros-$ROS_DISTRO-tf2-geometry-msgs \
  ros-$ROS_DISTRO-tf2-eigen ros-$ROS_DISTRO-ament-cmake ros-$ROS_DISTRO-cv-bridge 2>&1
cmake --version | head -1; g++ --version | head -1
I=/opt/ros/$ROS_DISTRO/include
echo "=== header survey: where tf2_geometry_msgs headers live"
find $I/tf2_geometry_msgs -maxdepth 3 -type f | sed "s#$I/##" | sort
echo "=== header survey: .h files in tf2 packages that print a warning when included"
for f in $(find $I/tf2 $I/tf2_ros $I/tf2_geometry_msgs $I/tf2_eigen $I/tf2_sensor_msgs -name '*.h' 2>/dev/null | sort); do
  w=$(grep -m1 -E '#warning|#pragma message' $f); [ -n "$w" ] && echo "  ${f#$I/}: $w"
done
HS=$(find $I/tf2 $I/tf2_ros $I/tf2_geometry_msgs $I/tf2_eigen -name '*.h' 2>/dev/null)
echo "  count of .h files under tf2, tf2_ros, tf2_geometry_msgs, tf2_eigen: $(echo "$HS" | grep -c .)"
echo "  count of those with #warning/#pragma message: $( [ -n "$HS" ] && grep -l -E '#warning|#pragma message' $HS | wc -l || echo 0)"
echo "=== exported CMake targets / include dirs"
mkdir -p /tmp/probe; cat > /tmp/probe/CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(probe)
find_package(tf2_geometry_msgs REQUIRED)
message(STATUS "PROBE tf2_geometry_msgs_INCLUDE_DIRS=${tf2_geometry_msgs_INCLUDE_DIRS}")
message(STATUS "PROBE tf2_geometry_msgs_TARGETS=${tf2_geometry_msgs_TARGETS}")
if(TARGET tf2_geometry_msgs::tf2_geometry_msgs)
  message(STATUS "PROBE target tf2_geometry_msgs::tf2_geometry_msgs exists")
endif()
X
(cd /tmp/probe && cmake -S . -B b 2>&1 | grep PROBE | sed "s#/opt/ros/$ROS_DISTRO#/opt/ros/DISTRO#g")
echo "=== python: import tf2_geometry_msgs"
python3 -c "import tf2_geometry_msgs; from tf2_geometry_msgs import do_transform_point; print('import ok', tf2_geometry_msgs.__file__)" 2>&1 | tail -2 | sed "s#/opt/ros/$ROS_DISTRO#/opt/ros/DISTRO#g"

W=/ws; mkdir -p $W/src; cd $W/src
BODY_DT='  geometry_msgs::msg::PointStamped in, out; in.header.frame_id = "laser"; in.point.x = 1.0;
  geometry_msgs::msg::TransformStamped t; t.header.frame_id = "base_link"; t.child_frame_id = "laser";
  t.transform.translation.x = 0.5; t.transform.rotation.w = 1.0;
  tf2::doTransform(in, out, t);'
BODY_BUF='  geometry_msgs::msg::PointStamped in; in.header.frame_id = "laser"; in.point.x = 1.0;
  geometry_msgs::msg::TransformStamped t; t.header.frame_id = "base_link"; t.child_frame_id = "laser";
  t.transform.translation.x = 0.5; t.transform.rotation.w = 1.0;
  tf2_ros::Buffer buf(n->get_clock()); buf.setTransform(t, "test", true);
  auto out = buf.transform(in, "base_link");'
# mkpkg NAME INCLUDE_LINES CMAKE_BLOCK [BODY]
mkpkg() {
  local P=$1 INC=$2 BLOCK=$3 BODY=${4:-$BODY_DT}
  mkdir -p $P/src
  cat > $P/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$P</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<depend>rclcpp</depend><depend>geometry_msgs</depend><depend>tf2_geometry_msgs</depend><depend>tf2_ros</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > $P/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($P)
add_compile_options(-Wall -Wextra -Wpedantic)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
add_executable(node src/node.cpp)
$BLOCK
install(TARGETS node DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
  cat > $P/src/node.cpp <<X
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/point_stamped.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
$INC
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("tf_node");
$BODY
  RCLCPP_INFO(n->get_logger(), "RESULT x=%.2f frame=%s", out.point.x, out.header.frame_id.c_str());
  rclcpp::shutdown();
}
X
}
HPP='#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>'
DOTH='#include <tf2_geometry_msgs/tf2_geometry_msgs.h>'
FIND='find_package(tf2_geometry_msgs REQUIRED)'
LINK='target_link_libraries(node rclcpp::rclcpp ${geometry_msgs_TARGETS} tf2_geometry_msgs::tf2_geometry_msgs)'
BASELINK='target_link_libraries(node rclcpp::rclcpp ${geometry_msgs_TARGETS})'
BUFINC='#if __has_include(<tf2_ros/buffer.hpp>)
#include <tf2_ros/buffer.hpp>
#else
#include <tf2_ros/buffer.h>
#endif'
mkpkg t01_ok_hpp       "$HPP"  "$FIND
$LINK"
mkpkg t02_dot_h        "$DOTH" "$FIND
$LINK"
mkpkg t03_dot_h_werror "$DOTH" "$FIND
$LINK
target_compile_options(node PRIVATE -Werror)"
mkpkg t04_no_find      "$HPP"  "$BASELINK"
mkpkg t05_find_nolink  "$HPP"  "$FIND
$BASELINK"
mkpkg t06_atd          "$HPP"  "$FIND
ament_target_dependencies(node rclcpp geometry_msgs tf2_geometry_msgs)"
mkpkg t07_incdirs      "$HPP"  "$FIND
$BASELINK
target_include_directories(node PRIVATE \${tf2_geometry_msgs_INCLUDE_DIRS})"
mkpkg t08_opt_include  "$HPP"  "$BASELINK
include_directories(/opt/ros/\$ENV{ROS_DISTRO}/include)"
mkpkg t09_vars_link    "$HPP"  "$FIND
target_link_libraries(node rclcpp::rclcpp \${geometry_msgs_TARGETS} \${tf2_geometry_msgs_TARGETS})"
mkpkg t10_buf_noheader "$BUFINC" "find_package(tf2_ros REQUIRED)
target_link_libraries(node rclcpp::rclcpp \${geometry_msgs_TARGETS} tf2_ros::tf2_ros)" "$BODY_BUF"
mkpkg t11_buf_header   "$BUFINC
$HPP" "find_package(tf2_ros REQUIRED)
$FIND
target_link_libraries(node rclcpp::rclcpp \${geometry_msgs_TARGETS} tf2_ros::tf2_ros tf2_geometry_msgs::tf2_geometry_msgs)" "$BODY_BUF"
mkpkg t12_has_include  "#if __has_include(<tf2_geometry_msgs/tf2_geometry_msgs.hpp>)
$HPP
#else
$DOTH
#endif" "$FIND
$LINK"
mkpkg t13_wrong_name   "#include <tf2_geometry_msgs/tf2_geometry_msgs/tf2_geometry_msgs.hpp>" "$FIND
$LINK"
echo "=== ros2 pkg create --build-type ament_cmake --dependencies rclcpp geometry_msgs tf2_geometry_msgs --node-name node t14_pkg_create"
ros2 pkg create --build-type ament_cmake --license MIT --dependencies rclcpp geometry_msgs tf2_geometry_msgs --node-name node t14_pkg_create > /dev/null 2>&1; echo "pkg create exit=$?"
grep -v -E '^\s*#|^\s*$' t14_pkg_create/CMakeLists.txt | sed 's/^/  /'
cp t01_ok_hpp/src/node.cpp t14_pkg_create/src/node.cpp

cd $W
build() {
  local P=$1; local t0=$(date +%s.%N)
  colcon build --executor sequential --packages-select $P > /tmp/b_$P.log 2>&1; local rc=$?
  local t1=$(date +%s.%N)
  echo "--- case=$P${2:+ ($2)} rc=$rc seconds=$(python3 -c "print(round($t1-$t0,1))")"
  local L=log/latest_build/$P/stdout_stderr.log
  grep -m1 -A3 -E "CMake Error|fatal error|error:|undefined reference" $L 2>/dev/null | sed "s#/ws/##; s#/opt/ros/$ROS_DISTRO#/opt/ros/DISTRO#g" | cut -c1-400
  grep -m2 -A2 -E "warning|Warning|pragma message" $L 2>/dev/null | sed "s#/ws/##; s#/opt/ros/$ROS_DISTRO#/opt/ros/DISTRO#g" | cut -c1-400
  echo "  lines with 'error': $(grep -c -E 'error' $L 2>/dev/null)  lines with 'warning': $(grep -c -E 'warning' $L 2>/dev/null)"
  echo "--- end $P"
}
CASES="t01_ok_hpp t02_dot_h t03_dot_h_werror t04_no_find t05_find_nolink t06_atd t07_incdirs t08_opt_include t09_vars_link t10_buf_noheader t11_buf_header t12_has_include t13_wrong_name t14_pkg_create"
for p in $CASES; do build $p; done
source install/setup.bash
for p in $CASES; do
  [ -x install/$p/lib/$p/node ] || continue
  echo "=== run $p"; timeout 20 ros2 run $p node 2>&1 | sed -E 's/\[[0-9]+\.[0-9]+\]//'; echo "exit=${PIPESTATUS[0]}"
done
echo "=== tf2_geometry_msgs include paths given to the compiler (flags.make)"
for p in t01_ok_hpp t05_find_nolink t08_opt_include; do echo "  $p: $(grep -h CXX_INCLUDES build/$p/CMakeFiles/node.dir/flags.make 2>/dev/null | tr ' ' '\n' | grep -E 'tf2_geometry_msgs|/opt/ros/[a-z]+/include$' | sed "s#/opt/ros/$ROS_DISTRO#/opt/ros/DISTRO#g" | sort -u | tr '\n' ' ')"; done

echo "=== cv_bridge: before install"
cvpkg() { # NAME INCLUDE CMAKE_BLOCK
  local P=$1; mkdir -p src/$P/src
  cat > src/$P/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$P</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>cv_bridge</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > src/$P/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($P)
add_compile_options(-Wall -Wextra -Wpedantic)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(node src/node.cpp)
$3
install(TARGETS node DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
  cat > src/$P/src/node.cpp <<X
#include <rclcpp/rclcpp.hpp>
$2
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("cv_node");
  cv::Mat img(4, 6, CV_8UC3, cv::Scalar(0, 0, 255));
  auto msg = cv_bridge::CvImage(std_msgs::msg::Header(), "bgr8", img).toImageMsg();
  RCLCPP_INFO(n->get_logger(), "RESULT %ux%u %s", msg->width, msg->height, msg->encoding.c_str());
  rclcpp::shutdown();
}
X
}
CVLINK='find_package(cv_bridge REQUIRED)
target_link_libraries(node rclcpp::rclcpp cv_bridge::cv_bridge)'
cvpkg c1_cv_missing '#include <cv_bridge/cv_bridge.hpp>' "$CVLINK"
cvpkg c2_cv_nofind  '#include <cv_bridge/cv_bridge.hpp>' 'target_link_libraries(node rclcpp::rclcpp)'
build c1_cv_missing "cv_bridge not installed"
build c2_cv_nofind "cv_bridge not installed, no find_package"
echo "=== apt install ros-$ROS_DISTRO-cv-bridge"
t0=$(date +%s)
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends ros-$ROS_DISTRO-cv-bridge) > /tmp/apt.log 2>&1; echo "apt exit=$? seconds=$(( $(date +%s) - t0 ))"
grep -E "newly installed|After this operation" /tmp/apt.log | head -3
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-cv-bridge libopencv-core-dev 2>&1
echo "  cv_bridge headers: $(find $I/cv_bridge -type f -name 'cv_bridge.h*' | sed "s#$I/##" | sort | tr '\n' ' ')"
for f in $(find $I/cv_bridge -name '*.h'); do w=$(grep -m1 -E '#warning|#pragma message' $f); [ -n "$w" ] && echo "  ${f#$I/}: $w"; done
cvpkg c3_cv_dot_h '#include <cv_bridge/cv_bridge.h>' "$CVLINK"
cvpkg c4_cv_hpp   '#include <cv_bridge/cv_bridge.hpp>' "$CVLINK"
cvpkg c5_cv_nolink '#include <cv_bridge/cv_bridge.hpp>' 'find_package(cv_bridge REQUIRED)
target_link_libraries(node rclcpp::rclcpp)'
# c1 failed at CMake configure; build it again now that cv_bridge is installed (fresh build dir)
mv build/c1_cv_missing /tmp/c1_build_before_install
for p in c1_cv_missing c3_cv_dot_h c4_cv_hpp c5_cv_nolink; do build $p; done
source install/setup.bash
for p in c1_cv_missing c3_cv_dot_h c4_cv_hpp; do
  [ -x install/$p/lib/$p/node ] || continue
  echo "=== run $p"; timeout 20 ros2 run $p node 2>&1 | sed -E 's/\[[0-9]+\.[0-9]+\]//'; echo "exit=${PIPESTATUS[0]}"
done
echo "=== done"
