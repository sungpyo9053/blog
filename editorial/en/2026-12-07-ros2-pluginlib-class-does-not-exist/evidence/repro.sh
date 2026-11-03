#!/bin/bash
# Run inside ros:<distro>-ros-base (no extra apt packages).
# Reproduces pluginlib "According to the loaded plugin descriptions the class X with
# base class type Y does not exist" and the related load errors, one plugin package
# per cause, all loaded by the same pluginlib::ClassLoader<pbase::RegularPolygon>.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-pluginlib ros-$ROS_DISTRO-class-loader \
  ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw-implementation \
  ros-$ROS_DISTRO-ament-cmake 2>/dev/null
W=/ws; mkdir -p $W/src; cd $W/src

# ---------- base package: interface header + loader executable ----------
mkdir -p pbase/include/pbase pbase/src
cat > pbase/package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>pbase</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>pluginlib</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > pbase/include/pbase/regular_polygon.hpp <<'X'
#pragma once
namespace pbase {
class RegularPolygon {
public:
  virtual void initialize(double side) = 0;
  virtual double area() = 0;
  virtual ~RegularPolygon() {}
};
}
X
cat > pbase/src/loader.cpp <<'X'
#include <pluginlib/class_loader.hpp>
#include <pbase/regular_polygon.hpp>
#include <chrono>
#include <iostream>
int main(int argc, char ** argv) {
  auto t0 = std::chrono::steady_clock::now();
  pluginlib::ClassLoader<pbase::RegularPolygon> loader("pbase", "pbase::RegularPolygon");
  auto t1 = std::chrono::steady_clock::now();
  std::cout << "LOADER_CTOR_MS " << std::chrono::duration<double, std::milli>(t1 - t0).count() << std::endl;
  std::cout << "DECLARED";
  for (auto & c : loader.getDeclaredClasses()) std::cout << " " << c;
  std::cout << std::endl;
  for (int i = 1; i < argc; ++i) {
    std::string name = argv[i];
    auto s = std::chrono::steady_clock::now();
    try {
      auto p = loader.createSharedInstance(name);
      p->initialize(10.0);
      std::cout << "OK " << name << " area=" << p->area();
    } catch (pluginlib::LibraryLoadException & e) {
      std::cout << "LibraryLoadException " << name << ": " << e.what();
    } catch (pluginlib::CreateClassException & e) {
      std::cout << "CreateClassException " << name << ": " << e.what();
    } catch (pluginlib::InvalidXMLException & e) {
      std::cout << "InvalidXMLException " << name << ": " << e.what();
    } catch (pluginlib::ClassLoaderException & e) {
      std::cout << "ClassLoaderException " << name << ": " << e.what();
    } catch (pluginlib::PluginlibException & e) {
      std::cout << "PluginlibException " << name << ": " << e.what();
    }
    std::cout << " [" << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s).count() << " ms]" << std::endl;
  }
}
X
cat > pbase/src/uncaught.cpp <<'X'
#include <pluginlib/class_loader.hpp>
#include <pbase/regular_polygon.hpp>
int main() {
  pluginlib::ClassLoader<pbase::RegularPolygon> l("pbase", "pbase::RegularPolygon");
  l.createSharedInstance("p_noexport::Square");
}
X
cat > pbase/CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(pbase)
find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)
add_library(pbase INTERFACE)
target_include_directories(pbase INTERFACE $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include> $<INSTALL_INTERFACE:include>)
install(DIRECTORY include/ DESTINATION include)
install(TARGETS pbase EXPORT pbaseTargets)
add_executable(loader src/loader.cpp)
target_link_libraries(loader pbase pluginlib::pluginlib)
add_executable(uncaught src/uncaught.cpp)
target_link_libraries(uncaught pbase pluginlib::pluginlib)
install(TARGETS loader uncaught DESTINATION lib/${PROJECT_NAME})
ament_export_targets(pbaseTargets)
ament_export_dependencies(pluginlib)
ament_package()
X

# ---------- plugin package generator ----------
# mkplug NAME [knobs as env vars]
#   XML_NAME     lookup name in plugins.xml   (default NAME::Square)
#   XML_TYPE     type attribute               (default NAME::Square)
#   XML_BASE     base_class_type              (default pbase::RegularPolygon)
#   XML_PATH     library path                 (default NAME)
#   EXPORT_LINE  CMake export call            (default pluginlib_export_plugin_description_file(pbase plugins.xml))
#   MACRO        PLUGINLIB_EXPORT_CLASS line  (default export NAME::Square)
#   INSTALL      install(TARGETS) line        (default installs the library)
#   PKG_EXPORT   extra <export> content in package.xml
#   UNDEF        1 = declare a virtual function but never define it
mkplug() {
  local N=$1
  mkdir -p $N/src
  local XN=${XML_NAME-$N::Square} XT=${XML_TYPE-$N::Square} XB=${XML_BASE-pbase::RegularPolygon} XP=${XML_PATH-$N}
  local EL=${EXPORT_LINE-pluginlib_export_plugin_description_file(pbase plugins.xml)}
  local MC=${MACRO-PLUGINLIB_EXPORT_CLASS($N::Square, pbase::RegularPolygon)}
  local IN=${INSTALL-install(TARGETS $N LIBRARY DESTINATION lib ARCHIVE DESTINATION lib RUNTIME DESTINATION bin)}
  cat > $N/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$N</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>pbase</depend><depend>pluginlib</depend>
<export><build_type>ament_cmake</build_type>${PKG_EXPORT}</export></package>
X
  local EXTRA_DECL="" EXTRA_CALL=""
  if [ "$UNDEF" = 1 ]; then EXTRA_DECL="virtual double perimeter();"; fi
  cat > $N/src/square.cpp <<X
#include <pbase/regular_polygon.hpp>
#include <pluginlib/class_list_macros.hpp>
namespace $N {
class Square : public pbase::RegularPolygon {
public:
  void initialize(double s) override { side_ = s; }
  double area() override { return side_ * side_; }
  $EXTRA_DECL
private:
  double side_ = 0;
};
}
$MC
X
  cat > $N/plugins.xml <<X
<library path="$XP">
  <class name="$XN" type="$XT" base_class_type="$XB">
    <description>square</description>
  </class>
</library>
X
  cat > $N/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($N)
find_package(ament_cmake REQUIRED)
find_package(pbase REQUIRED)
find_package(pluginlib REQUIRED)
add_library($N SHARED src/square.cpp)
target_link_libraries($N pbase::pbase pluginlib::pluginlib)
$EL
$IN
ament_package()
X
}

mkplug p_good
EXPORT_LINE="# (no pluginlib_export_plugin_description_file)" mkplug p_noexport
EXPORT_LINE="pluginlib_export_plugin_description_file(p_ownpkg plugins.xml)" mkplug p_ownpkg
EXPORT_LINE="# (ROS 1 style export only)" PKG_EXPORT='<pbase plugin="${prefix}/plugins.xml"/>' mkplug p_ros1export
XML_NAME=p_typo::Sqaure XML_TYPE=p_typo::Sqaure mkplug p_typo
XML_NAME=p_named/Square mkplug p_named
XML_BASE=pbase::Polygon mkplug p_wrongbase
XML_TYPE=p_mismatch::Triangle MACRO='PLUGINLIB_EXPORT_CLASS(p_mismatch::Square, pbase::RegularPolygon)' XML_NAME=p_mismatch::Triangle mkplug p_mismatch
MACRO="// (no PLUGINLIB_EXPORT_CLASS)" mkplug p_nomacro
XML_PATH=p_badpath_wrong mkplug p_badpath
XML_PATH=lib/libp_ros1path mkplug p_ros1path
XML_PATH=libp_libprefix mkplug p_libprefix
INSTALL="# (library not installed)" mkplug p_noinstall
UNDEF=1 mkplug p_undef
# fix variants for the broken ones above
mkplug p_undef_fixed  # same as p_good, kept for symmetry
sed -i 's/virtual double perimeter();/virtual double perimeter() { return 4 * side_; }/' p_undef_fixed/src/square.cpp

cd $W
uptime
T0=$(date +%s)
MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- >/tmp/build.log 2>&1
echo "BUILD_EXIT $? seconds=$(( $(date +%s) - T0 ))"
grep -iE "warning|error" /tmp/build.log | grep -v "^--" | head -20
uptime

echo "=== ament index entries for pbase plugins"
ls $W/install/*/share/ament_index/resource_index/pbase__pluginlib__plugin/ 2>/dev/null | sed 's#.*/##' | sort | tr '\n' ' '; echo
ls -d $W/install/*/share/ament_index/resource_index/*__pluginlib__plugin 2>/dev/null | sed 's#.*/resource_index/##' | sort | uniq -c
echo "=== installed libs"; ls $W/install/*/lib/*.so | sed 's#.*/##' | tr '\n' ' '; echo

L="ros2 run pbase loader"
run() { echo "--- $1"; shift; timeout 60 "$@" 2>&1 | sed 's/^/  /'; echo "  exit=${PIPESTATUS[0]}"; }

echo "=== A. not sourced (only /opt/ros) -> loader itself"
( source /opt/ros/$ROS_DISTRO/setup.bash; run "unsourced ros2 run" $L p_good::Square )
( source /opt/ros/$ROS_DISTRO/setup.bash; run "unsourced direct binary" $W/install/pbase/lib/pbase/loader p_good::Square )

source $W/install/setup.bash
echo "=== B. sourced workspace"
run "good"            $L p_good::Square
run "good x3 timing"  $L p_good::Square p_good::Square p_good::Square
run "noexport"        $L p_noexport::Square
run "ownpkg"          $L p_ownpkg::Square
run "ros1export"      $L p_ros1export::Square
run "typo (asked correct name)" $L p_typo::Square
run "typo (asked xml name)"     $L p_typo::Sqaure
run "named by name"   $L p_named/Square
run "named by type"   $L p_named::Square
run "wrongbase"       $L p_wrongbase::Square
run "mismatch"        $L p_mismatch::Triangle
run "nomacro"         $L p_nomacro::Square
run "badpath"         $L p_badpath::Square
run "ros1path lib/libX" $L p_ros1path::Square
run "libprefix libX"  $L p_libprefix::Square
run "noinstall"       $L p_noinstall::Square
run "undef"           $L p_undef::Square
run "undef_fixed"     $L p_undef_fixed::Square
run "never existed"   $L nope::Square

echo "=== C. uncaught exception (what users see from nodes that do not catch)"
run "uncaught" ros2 run pbase uncaught

echo "=== D. package added after sourcing (stale environment)"
cd $W/src && mkplug p_late && cd $W
MAKEFLAGS=-j1 colcon build --packages-select p_late --event-handlers console_direct- >/tmp/build2.log 2>&1; echo "late build exit $?"
run "late, old env"   $L p_late::Square
source $W/install/setup.bash
run "late, re-sourced" $L p_late::Square

echo "=== E. fix check: p_noexport rebuilt with the export call"
sed -i 's|# (no pluginlib_export_plugin_description_file)|pluginlib_export_plugin_description_file(pbase plugins.xml)|' src/p_noexport/CMakeLists.txt
MAKEFLAGS=-j1 colcon build --packages-select p_noexport --event-handlers console_direct- >/tmp/build3.log 2>&1; echo "rebuild exit $?"
run "noexport fixed, same shell" $L p_noexport::Square
echo "=== F. ros2 pkg prefix / AMENT_PREFIX_PATH check"
ros2 pkg prefix p_good; ros2 pkg prefix p_noinstall
echo "=== done $ROS_DISTRO"
