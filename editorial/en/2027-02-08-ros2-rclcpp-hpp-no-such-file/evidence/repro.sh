#!/bin/bash
# repro.sh - "rclcpp/rclcpp.hpp: No such file or directory" and
# "ament_target_dependencies() the first argument must be a valid target name".
# Host:      bash repro.sh host <distro>    (runs the container, prints to stdout)
# Container: bash repro.sh inner             (called by host mode)

MODE=${1:-host}

if [ "$MODE" = host ]; then
  D=$2; W=/tmp/en-pick71
  mkdir -p $W; [ "$(readlink -f "$0")" = $W/repro.sh ] || cp "$0" $W/repro.sh
  uptime
  docker run --rm --name pk71-$D --network none --ulimit core=0 \
    -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    -e MAKEFLAGS=-j1 -v $W:/w ros:$D-ros-base timeout 1500 bash /w/repro.sh inner
  exit $?
fi

ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "### distro=$ROS_DISTRO"
echo "### cmake: $(cmake --version | head -1)"
echo "### g++: $(g++ --version | head -1)"
for p in rclcpp rclpy ros2cli rmw ament-cmake ament-cmake-target-dependencies; do
  echo "### pkg ros-$ROS_DISTRO-$p $(dpkg-query -W -f='${Version}' ros-$ROS_DISTRO-$p 2>/dev/null || echo missing)"
done

WS=/root/ws; mkdir -p $WS/src; cd $WS

NODE='#include "rclcpp/rclcpp.hpp"
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("pk71_node");
  RCLCPP_INFO(n->get_logger(), "pk71 node ok");
  rclcpp::shutdown();
  return 0;
}'

mkpkg() { # name body
  local n=$1 b=$2
  mkdir -p src/$n/src src/$n/include/$n
  printf '%s\n' "$NODE" > src/$n/src/node.cpp
  cat > src/$n/package.xml <<X
<?xml version="1.0"?>
<package format="3">
  <name>$n</name><version>0.0.1</version><description>pk71</description>
  <maintainer email="pk71@example.com">a</maintainer><license>Apache-2.0</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
X
  { echo 'cmake_minimum_required(VERSION 3.8)'; echo "project($n)"; printf '%s\n' "$b"; echo 'install(TARGETS node DESTINATION lib/${PROJECT_NAME})'; echo 'ament_package()'; } > src/$n/CMakeLists.txt
}

FP='find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)'

mkpkg c01_atd_ok      "$FP
add_executable(node src/node.cpp)
ament_target_dependencies(node rclcpp)"
mkpkg c02_tll_ok      "$FP
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp::rclcpp)"
mkpkg c03_no_link     "$FP
add_executable(node src/node.cpp)"
mkpkg c04_find_after  "add_executable(node src/node.cpp)
target_link_libraries(node \${rclcpp_LIBRARIES})
$FP"
mkpkg c05_atd_before_add "$FP
ament_target_dependencies(node rclcpp)
add_executable(node src/node.cpp)"
mkpkg c06_atd_typo    "$FP
add_executable(node src/node.cpp)
ament_target_dependencies(Node rclcpp)"
mkpkg c07_no_find_rclcpp "find_package(ament_cmake REQUIRED)
add_executable(node src/node.cpp)
ament_target_dependencies(node rclcpp)"
mkpkg c08_tll_no_find "find_package(ament_cmake REQUIRED)
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp::rclcpp)"
mkpkg c09_include_only "$FP
add_executable(node src/node.cpp)
target_include_directories(node PRIVATE \${rclcpp_INCLUDE_DIRS})"
mkpkg c10_tll_plain_name "$FP
add_executable(node src/node.cpp)
target_link_libraries(node rclcpp)"

mkpkg c13_vars_legacy "$FP
add_executable(node src/node.cpp)
target_include_directories(node PRIVATE \${rclcpp_INCLUDE_DIRS})
target_link_libraries(node \${rclcpp_LIBRARIES})"

# library cases: public header includes rclcpp, executable links only the library
LIBB() { # visibility
  echo "$FP
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)
target_link_libraries(mylib $1 rclcpp::rclcpp)
add_executable(node src/node.cpp)
target_link_libraries(node mylib)"
}
for v in PRIVATE PUBLIC; do
  n=c1$([ $v = PRIVATE ] && echo 1 || echo 2)_lib_$(echo $v | tr A-Z a-z)
  mkpkg $n "$(LIBB $v)"
  printf '#pragma once\n#include "rclcpp/rclcpp.hpp"\nrclcpp::Node::SharedPtr make_node();\n' > src/$n/include/$n/mylib.hpp
  printf '#include "%s/mylib.hpp"\nrclcpp::Node::SharedPtr make_node(){return std::make_shared<rclcpp::Node>("pk71_lib");}\n' $n > src/$n/src/mylib.cpp
  printf '#include "%s/mylib.hpp"\nint main(int c,char**v){rclcpp::init(c,v);auto n=make_node();RCLCPP_INFO(n->get_logger(),"pk71 lib node ok");rclcpp::shutdown();return 0;}\n' $n > src/$n/src/node.cpp
done

for d in src/*/; do
  n=$(basename $d)
  echo; echo "===== CASE $n"
  sed -n '3,$p' src/$n/CMakeLists.txt | grep -v -E '^(install|ament_package)' | sed 's/^/  cmake| /'
  t0=$(date +%s.%N)
  colcon build --packages-select $n --parallel-workers 1 --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON > /tmp/$n.log 2>&1
  rc=$?
  t1=$(date +%s.%N)
  echo "exit=$rc seconds=$(python3 -c "print(round($t1-$t0,1))")"
  grep -E 'fatal error|CMake Error|error:|undefined reference|ament_target_dependencies\(\)|Unknown CMake|not found|was not found|Target "|collect2|Summary|finished|failed' /tmp/$n.log | grep -v '^\s*$' | head -12 | sed 's/^/  log| /'
  grep -n -A3 'CMake Error' /tmp/$n.log | head -12 | sed 's/^/  cmk| /'
  cc=build/$n/compile_commands.json
  if [ -f $cc ]; then
    echo "  compile_commands.json entries=$(grep -c '"file"' $cc) rclcpp_include_flags=$(grep -o -E '(-I|-isystem )[^ ]*rclcpp[^ ]*' $cc | sort -u | wc -l)"
    grep -o -E '(-I|-isystem )[^ ]*rclcpp[^ ]*' $cc | sort -u | head -2 | sed 's/^/  inc| /'
  else echo "  compile_commands.json: none"; fi
  if [ $rc = 0 ]; then
    ( source install/setup.bash; timeout 20 ros2 run $n node 2>&1 | head -3 | sed 's/^/  run| /' )
  fi
done
echo; echo "### done $(date -u +%FT%TZ)"
