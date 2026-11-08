#!/bin/bash
# Reproduces "error while loading shared libraries: libX.so: cannot open shared
# object file" for a ROS 2 ament_cmake node that links a prebuilt (vendor) .so,
# then compares the fixes.
# Run inside ros:<distro>-ros-base, e.g.:
#   docker run --rm --network none -e ROS_DOMAIN_ID=88 -v $PWD:/w ros:humble-ros-base bash /w/repro.sh
# (no set -u: the ROS setup scripts read unset variables)
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export MAKEFLAGS=-j2
R=/work; mkdir -p $R
echo "distro=$ROS_DISTRO cmake=$(cmake --version | head -1) gcc=$(g++ -dumpfullversion) glibc=$(ldd --version | head -1 | awk '{print $NF}')"

# ---- a prebuilt vendor library, laid out like an SDK: real file + soname links ----
V=$R/vendor_sdk; mkdir -p $V/include $V/lib
printf '#pragma once\nint vendor_read();\n' > $V/include/vendor.h
printf '#include "vendor.h"\nint vendor_read() { return 42; }\n' > $V/vendor.cpp
g++ -shared -fPIC -I$V/include -Wl,-soname,libvendor.so.4 -o $V/lib/libvendor.so.4.6.0 $V/vendor.cpp
( cd $V/lib && ln -s libvendor.so.4.6.0 libvendor.so.4 && ln -s libvendor.so.4 libvendor.so )
echo "vendor files:"; ls -l $V/lib | awk 'NR>1{print "  "$1, $9, $10, $11}'
echo "vendor SONAME: $(readelf -d $V/lib/libvendor.so.4.6.0 | grep SONAME | sed 's/.*Library soname: //')"

APP='#include <rclcpp/rclcpp.hpp>
#include "vendor.h"
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("cam");
  RCLCPP_INFO(n->get_logger(), "vendor_read()=%d", vendor_read());
  rclcpp::shutdown();
  return 0;
}'

# mk case libdir extra_cmake : workspace $R/<case>/src/cam_node, vendor copied to <pkg>/thirdparty
mk() {
  local c=$1 libdir=$2 extra=$3 p=$R/$1/src/cam_node
  mkdir -p $p/src $p/thirdparty
  cp -a $V/include $V/lib $p/thirdparty/
  echo "$APP" > $p/src/cam.cpp
  cat > $p/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>cam_node</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend>
  <export><build_type>ament_cmake</build_type></export></package>
X
  cat > $p/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(cam_node CXX)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_library(VENDOR_LIB vendor HINTS $libdir NO_DEFAULT_PATH)
if(NOT VENDOR_LIB)
  message(FATAL_ERROR "libvendor not found")
endif()
$extra
add_executable(cam src/cam.cpp)
target_include_directories(cam PRIVATE \${PROJECT_SOURCE_DIR}/thirdparty/include)
target_link_libraries(cam rclcpp::rclcpp \${VENDOR_LIB})
install(TARGETS cam DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
}

build() { # case
  local ws=$R/$1
  echo; echo "### CASE $1"
  cd $ws
  local t0=$(date +%s.%N)
  timeout 400 colcon build --parallel-workers 1 --event-handlers console_direct+ > $ws/build.log 2>&1
  local rc=$?
  echo "colcon exit=$rc seconds=$(python3 -c "print(round($(date +%s.%N)-$t0,1))")"
  grep -E "CMake Error|error:|Summary:|Failed" $ws/build.log | sed "s#$ws#<ws>#g" | head -6
}

# show the stuff that decides the outcome
inspect() { # case
  local ws=$R/$1
  echo "-- RUNPATH build/:   $(readelf -d $ws/build/cam_node/cam | grep -E 'RUNPATH|RPATH' | sed 's/.*\[\(.*\)\]/\1/' | sed "s#$ws#<ws>#g")"
  echo "-- RUNPATH install/: $(readelf -d $ws/install/cam_node/lib/cam_node/cam | grep -E 'RUNPATH|RPATH' | sed 's/.*\[\(.*\)\]/\1/' | sed "s#$ws#<ws>#g")"
  echo "-- NEEDED vendor:    $(readelf -d $ws/install/cam_node/lib/cam_node/cam | grep NEEDED | grep vendor | sed 's/.*\[\(.*\)\]/\1/')"
  echo "-- install/cam_node/lib:"; ls -l $ws/install/cam_node/lib | awk 'NR>1{print "     "$1, $9, $10, $11}'
}

# run in a fresh shell with the workspace sourced
rr() { # case label cmd...
  local ws=$R/$1 label=$2; shift 2
  ( source $ws/install/setup.bash
    local t0=$(date +%s.%N)
    timeout 30 "$@" > $ws/run.log 2>&1; local rc=$?
    echo "-- $label: exit=$rc seconds=$(python3 -c "print(round($(date +%s.%N)-$t0,2))")"
    sed "s#$ws#<ws>#g; s#\[[0-9.]*\]#[t]#g" $ws/run.log | head -6 | sed 's/^/     /' )
}
# only /opt/ros sourced (like a systemd unit or a copied binary)
rr_nows() { # case label cmd...
  local ws=$R/$1 label=$2; shift 2
  ( local t0=$(date +%s.%N)
    timeout 30 "$@" > $ws/run.log 2>&1; local rc=$?
    echo "-- $label: exit=$rc seconds=$(python3 -c "print(round($(date +%s.%N)-$t0,2))")"
    sed "s#$ws#<ws>#g; s#$R#<work>#g; s#\[[0-9.]*\]#[t]#g" $ws/run.log | head -6 | sed 's/^/     /' )
}

TP='${PROJECT_SOURCE_DIR}/thirdparty/lib'

# ---------- C0: link the vendor .so, install only the executable ----------
mk C0_link_only "$TP" ""
build C0_link_only; inspect C0_link_only
W=$R/C0_link_only
rr C0_link_only "build/ binary run directly" $W/build/cam_node/cam
rr C0_link_only "ros2 run cam_node cam" ros2 run cam_node cam
cat > $R/cam.launch.py <<X
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='cam_node', executable='cam', output='screen')])
X
rr C0_link_only "ros2 launch cam.launch.py" ros2 launch $R/cam.launch.py
( source $W/install/setup.bash
  echo "-- ldd install binary (vendor line):"; ldd $W/install/cam_node/lib/cam_node/cam | grep -E "vendor|not found" | sed "s#$W#<ws>#g; s/ (0x.*)//; s/^/     /"
  echo "-- LD_DEBUG=libs for libvendor (search path shortened to 2 entries):"
  LD_DEBUG=libs $W/install/cam_node/lib/cam_node/cam 2>&1 | grep -A60 "find library=libvendor" \
    | grep -E "find library|search path|search cache|cannot open" | sed "s#$W#<ws>#g; s/^ *[0-9]*: */     /" \
    | sed -E 's#(search path=[^:]*:[^:]*):[^\t]*#\1:...#' | head -6
  echo "-- workspace entries in LD_LIBRARY_PATH after sourcing:"; echo "$LD_LIBRARY_PATH" | tr : '\n' | grep "$W" | sed "s#$W#<ws>#g; s/^/     /"
  echo "-- env hook files: $(ls $W/install/cam_node/share/cam_node/environment/ 2>/dev/null | tr '\n' ' ')" )

# C0 + LD_LIBRARY_PATH workaround
rr C0_link_only "ros2 run with LD_LIBRARY_PATH=<pkg>/thirdparty/lib prepended" env LD_LIBRARY_PATH=$W/src/cam_node/thirdparty/lib:$LD_LIBRARY_PATH ros2 run cam_node cam

# ---------- C1: install(FILES) only the libvendor.so name ----------
mk C1_install_so_symlink_only "$TP" ""
echo 'install(FILES ${PROJECT_SOURCE_DIR}/thirdparty/lib/libvendor.so DESTINATION lib)' >> $R/C1_install_so_symlink_only/src/cam_node/CMakeLists.txt
build C1_install_so_symlink_only; inspect C1_install_so_symlink_only
rr C1_install_so_symlink_only "ros2 run cam_node cam" ros2 run cam_node cam

# ---------- C2: install every libvendor.so* file ----------
mk C2_install_all_files "$TP" ""
echo 'file(GLOB VENDOR_FILES ${PROJECT_SOURCE_DIR}/thirdparty/lib/libvendor.so*)
install(FILES ${VENDOR_FILES} DESTINATION lib)' >> $R/C2_install_all_files/src/cam_node/CMakeLists.txt
build C2_install_all_files; inspect C2_install_all_files
W=$R/C2_install_all_files
rr C2_install_all_files "ros2 run cam_node cam" ros2 run cam_node cam
( source $W/install/setup.bash
  echo "-- workspace entries in LD_LIBRARY_PATH after sourcing:"; echo "$LD_LIBRARY_PATH" | tr : '\n' | grep "$W" | sed "s#$W#<ws>#g; s/^/     /"
  echo "-- env hook files: $(ls $W/install/cam_node/share/cam_node/environment/ 2>/dev/null | tr '\n' ' ')"
  echo "-- colcon hook files: $(ls $W/install/cam_node/share/cam_node/hook/ 2>/dev/null | tr '\n' ' ')" )
rr_nows C2_install_all_files "install binary, workspace NOT sourced" $W/install/cam_node/lib/cam_node/cam
rm -rf $W/src/cam_node/thirdparty/lib
rr C2_install_all_files "ros2 run after deleting src/.../thirdparty/lib" ros2 run cam_node cam

# ---------- C3: CMAKE_INSTALL_RPATH_USE_LINK_PATH, nothing installed ----------
mk C3_rpath_use_link_path "$TP" "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)"
build C3_rpath_use_link_path; inspect C3_rpath_use_link_path
W=$R/C3_rpath_use_link_path
rr C3_rpath_use_link_path "ros2 run cam_node cam" ros2 run cam_node cam
mv $W/src/cam_node/thirdparty $W/thirdparty.moved
rr C3_rpath_use_link_path "ros2 run after moving src/.../thirdparty away" ros2 run cam_node cam
mv $W/thirdparty.moved $W/src/cam_node/thirdparty

# ---------- C4: install all files + INSTALL_RPATH $ORIGIN/.. ----------
mk C4_install_plus_origin_rpath "$TP" ""
echo 'file(GLOB VENDOR_FILES ${PROJECT_SOURCE_DIR}/thirdparty/lib/libvendor.so*)
install(FILES ${VENDOR_FILES} DESTINATION lib)
set_target_properties(cam PROPERTIES INSTALL_RPATH "$ORIGIN/..")' >> $R/C4_install_plus_origin_rpath/src/cam_node/CMakeLists.txt
build C4_install_plus_origin_rpath; inspect C4_install_plus_origin_rpath
W=$R/C4_install_plus_origin_rpath
rr C4_install_plus_origin_rpath "ros2 run cam_node cam" ros2 run cam_node cam
rr_nows C4_install_plus_origin_rpath "install binary, workspace NOT sourced" $W/install/cam_node/lib/cam_node/cam
rm -rf $W/src/cam_node/thirdparty/lib
cp -a $W/install $R/install_copy_C4
rr_nows C4_install_plus_origin_rpath "copied install/ tree, src lib deleted, NOT sourced" $R/install_copy_C4/cam_node/lib/cam_node/cam

# ---------- C5: SDK installed to /usr/local/lib (like make install), no ldconfig ----------
cp -a $V/lib/libvendor.so* /usr/local/lib/
echo; echo "/etc/ld.so.conf.d files listing /usr/local/lib: $(grep -l /usr/local/lib /etc/ld.so.conf.d/* | tr '\n' ' ')"
echo "ldconfig -p | grep -c vendor before ldconfig: $(ldconfig -p | grep -c vendor)"
mk C5_usr_local_no_ldconfig "/usr/local/lib" ""
build C5_usr_local_no_ldconfig; inspect C5_usr_local_no_ldconfig
W=$R/C5_usr_local_no_ldconfig
rr C5_usr_local_no_ldconfig "build/ binary run directly" $W/build/cam_node/cam
rr C5_usr_local_no_ldconfig "ros2 run cam_node cam" ros2 run cam_node cam
ldconfig
echo "-- ran ldconfig; ldconfig -p | grep vendor: $(ldconfig -p | grep vendor | sed 's/ (.*=>/ =>/' | tr '\n' ';' | tr -s ' ')"
rr C5_usr_local_no_ldconfig "ros2 run after ldconfig" ros2 run cam_node cam
rm -f /usr/local/lib/libvendor.so*; ldconfig

# ---------- C8: SDK in /opt/vendor_sdk/lib (outside the project, not known to ld.so) ----------
mkdir -p /opt/vendor_sdk/lib; cp -a $V/lib/libvendor.so* /opt/vendor_sdk/lib/
mk C8a_opt_sdk_link_only "/opt/vendor_sdk/lib" ""
build C8a_opt_sdk_link_only; inspect C8a_opt_sdk_link_only
rr C8a_opt_sdk_link_only "ros2 run cam_node cam" ros2 run cam_node cam
mk C8b_opt_sdk_rpath_use_link_path "/opt/vendor_sdk/lib" "set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)"
build C8b_opt_sdk_rpath_use_link_path; inspect C8b_opt_sdk_rpath_use_link_path
rr C8b_opt_sdk_rpath_use_link_path "ros2 run cam_node cam" ros2 run cam_node cam
rr_nows C8b_opt_sdk_rpath_use_link_path "install binary, workspace NOT sourced" $R/C8b_opt_sdk_rpath_use_link_path/install/cam_node/lib/cam_node/cam
rm -rf /opt/vendor_sdk

# ---------- C6/C7: the package's own library, with and without install(TARGETS own) ----------
own() { # case install_lib(yes/no)
  local p=$R/$1/src/own_pkg
  mkdir -p $p/src $p/include/own_pkg
  printf '#pragma once\nint own_read();\n' > $p/include/own_pkg/own.hpp
  printf '#include "own_pkg/own.hpp"\nint own_read() { return 7; }\n' > $p/src/own.cpp
  echo "$APP" | sed 's#"vendor.h"#"own_pkg/own.hpp"#; s#vendor_read#own_read#g' > $p/src/cam.cpp
  sed 's/cam_node/own_pkg/' $R/C0_link_only/src/cam_node/package.xml > $p/package.xml
  local il=""; [ "$2" = yes ] && il='install(TARGETS own LIBRARY DESTINATION lib)'
  cat > $p/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(own_pkg CXX)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_library(own SHARED src/own.cpp)
target_include_directories(own PUBLIC include)
add_executable(cam src/cam.cpp)
target_link_libraries(cam rclcpp::rclcpp own)
install(TARGETS cam DESTINATION lib/\${PROJECT_NAME})
$il
ament_package()
X
}
for c in C6_own_lib_not_installed:no C7_own_lib_installed:yes; do
  n=${c%%:*}; own $n ${c##*:}; build $n
  echo "-- install/own_pkg/lib: $(ls $R/$n/install/own_pkg/lib | tr '\n' ' ')"
  rr $n "ros2 run own_pkg cam" ros2 run own_pkg cam
done
rr_nows C7_own_lib_installed "C7 install binary, workspace NOT sourced" $R/C7_own_lib_installed/install/own_pkg/lib/own_pkg/cam
echo; echo "DONE $ROS_DISTRO"
