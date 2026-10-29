#!/bin/bash
# Run inside ros:<distro>-ros-base with --entrypoint bash (so /opt/ros is NOT sourced at start).
#   docker run --rm --name findpkg-$D --entrypoint bash -v $PWD:/w ros:$D-ros-base /w/repro.sh
# Reproduces "Could not find a package configuration file provided by ..." in an ament_cmake package.
# ROS dependency not in ros-base: diagnostic_updater. System libs: Eigen3 (present), nlohmann_json.
D=$ROS_DISTRO
export DEBIAN_FRONTEND=noninteractive
step() { echo; echo "######## $*"; }
t0() { T0=$(date +%s.%N); }
t1() { python3 -c "import time; print('[elapsed %.1fs]' % (time.time() - $T0))"; }
build() {  # build ws from clean, print CMake error block and result
  cd /ws && rm -rf build install log
  t0; colcon build "$@" --event-handlers console_direct- > /tmp/b.log 2>&1; rc=$?; t1
  grep -A14 -E 'CMake Error' /tmp/b.log | head -32
  [ $rc -ne 0 ] && ! grep -q 'CMake Error' /tmp/b.log && { echo '--- no CMake Error; log tail:'; tail -12 /tmp/b.log; }
  grep -E '^Summary|packages? (finished|failed|aborted)|Failed   <<<|Finished <<<' /tmp/b.log
  echo "BUILD_RC=$rc"
}
pkgxml() {  # $1 = dependency lines
cat > /ws/src/fp/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>fp</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
$1
<export><build_type>ament_cmake</build_type></export></package>
X
}
cml() {  # $1 = find_package lines
cat > /ws/src/fp/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(fp)
find_package(ament_cmake REQUIRED)
$1
ament_package()
X
}
installed() { dpkg-query -W -f='${Package} ${Version}\n' "$@" 2>&1; }
purge() { apt-get purge -y -qq ros-$D-diagnostic-updater nlohmann-json3-dev > /dev/null 2>&1; apt-get autoremove -y -qq > /dev/null 2>&1; installed ros-$D-diagnostic-updater; }
rinstall() {  # rosdep install, show what it does
  cd /ws; t0; rosdep install --from-paths src --ignore-src -y "$@" > /tmp/r.log 2>&1; rc=$?; t1
  grep -vE '^(Get:|Selecting|Preparing|Unpacking|\(Reading|debconf|Processing triggers|Fetched|Reading|Building|Need to get|After this)' /tmp/r.log | grep -v '^ *$' | head -40
  echo "apt 'Setting up' lines: $(grep -c '^Setting up' /tmp/r.log)"; echo "ROSDEP_RC=$rc"
}

step "distro=$D"
installed cmake ros-$D-ament-cmake libeigen3-dev nlohmann-json3-dev ros-$D-diagnostic-updater ros-$D-cv-bridge python3-rosdep python3-colcon-core
rosdep --version; cmake --version | head -1; colcon version-check 2>/dev/null | grep colcon-core
python3 -c "import colcon_core; print('colcon-core', colcon_core.__version__)"
ls -la ~/.ros/rosdep/ 2>&1 | head -5; ls /etc/ros/rosdep/sources.list.d/
echo "apt lists files: $(ls /var/lib/apt/lists | grep -vc -E 'lock|partial|auxfiles')"

mkdir -p /ws/src/fp

step "(g) env NOT sourced"
echo "CMAKE_PREFIX_PATH=[${CMAKE_PREFIX_PATH}]"; echo "AMENT_PREFIX_PATH=[${AMENT_PREFIX_PATH}]"; echo "PATH=[$PATH]"
pkgxml ""; cml ""
step "(g) build with /opt/ros NOT sourced"
build
step "(g2) not sourced, only CMAKE_PREFIX_PATH=/opt/ros/$D"
CMAKE_PREFIX_PATH=/opt/ros/$D build
step "(g3) not sourced, only AMENT_PREFIX_PATH=/opt/ros/$D"
AMENT_PREFIX_PATH=/opt/ros/$D build
step "(g4) not sourced, only PATH=/opt/ros/$D/bin:\$PATH"
PATH=/opt/ros/$D/bin:$PATH build

step "(g) env after source /opt/ros/$D/setup.bash"
source /opt/ros/$D/setup.bash
echo "CMAKE_PREFIX_PATH=[${CMAKE_PREFIX_PATH}]"; echo "AMENT_PREFIX_PATH=[${AMENT_PREFIX_PATH}]"; echo "PATH=[$PATH]"
build

step "(a) find_package(diagnostic_updater REQUIRED), dependency missing from package.xml, not installed"
pkgxml ""; cml "find_package(diagnostic_updater REQUIRED)"
build

step "(c1) rosdep install with the image's rosdep cache as shipped, apt lists empty"
pkgxml "<depend>diagnostic_updater</depend>"
rinstall
installed ros-$D-diagnostic-updater; purge

step "(c2) rosdep install with ~/.ros/rosdep removed (rosdep update never run)"
mv ~/.ros/rosdep /tmp/rosdep.bak
rinstall
mv /tmp/rosdep.bak ~/.ros/rosdep

step "(c3) /etc/ros/rosdep/sources.list.d missing (rosdep init never run)"
mv /etc/ros/rosdep/sources.list.d/20-default.list /tmp/20.bak
t0; rosdep update 2>&1 | tail -8; t1
mv ~/.ros/rosdep /tmp/rosdep.bak
rinstall
mv /tmp/20.bak /etc/ros/rosdep/sources.list.d/20-default.list
mv /tmp/rosdep.bak ~/.ros/rosdep

step "rosdep update"
t0; rosdep update > /tmp/u.log 2>&1; echo "rc=$?"; tail -3 /tmp/u.log; t1
step "apt-get update"
t0; apt-get update -qq > /dev/null 2>&1; echo "rc=$?"; t1

step "(b0) dependency MISSING from package.xml -> rosdep install"
pkgxml ""
rinstall; installed ros-$D-diagnostic-updater; build

step "(b1) <build_depend>diagnostic_updater</build_depend> only"
pkgxml "<build_depend>diagnostic_updater</build_depend>"
rinstall; installed ros-$D-diagnostic-updater; build; purge

step "(b2) <exec_depend>diagnostic_updater</exec_depend> only"
pkgxml "<exec_depend>diagnostic_updater</exec_depend>"
rinstall; installed ros-$D-diagnostic-updater; build; purge

step "(b3) <exec_depend> only, rosdep install --dependency-types build"
rinstall --dependency-types build; installed ros-$D-diagnostic-updater; purge

step "(b4) <depend>diagnostic_updater</depend>"
pkgxml "<depend>diagnostic_updater</depend>"
rinstall; installed ros-$D-diagnostic-updater; build
step "(b4) second rosdep install (already installed)"
rinstall; purge

step "(d) apt-get install ros-$D-diagnostic-updater by hand, same shell, no re-source"
pkgxml ""
t0; apt-get install -y -qq ros-$D-diagnostic-updater > /tmp/a.log 2>&1; echo "rc=$? setting-up=$(grep -c '^Setting up' /tmp/a.log)"; t1
build
step "(d) same, in a fresh bash that sources /opt/ros"
bash -c "source /opt/ros/$D/setup.bash; cd /ws; rm -rf build install log; colcon build > /tmp/b2.log 2>&1; echo BUILD_RC=\$?"
purge

step "(sys) find_package(nlohmann_json REQUIRED), not installed, not in package.xml"
pkgxml ""; cml "find_package(nlohmann_json REQUIRED)"
installed nlohmann-json3-dev; build
step "(sys) <depend>nlohmann-json-dev</depend> -> rosdep install"
pkgxml "<depend>nlohmann-json-dev</depend>"
rinstall; installed nlohmann-json3-dev; build
step "(sys) wrong rosdep key <depend>nlohmann_json</depend>"
pkgxml "<depend>nlohmann_json</depend>"
rinstall
purge

step "(f) Eigen3 (installed): correct case"
pkgxml "<depend>eigen</depend>"; cml "find_package(Eigen3 REQUIRED)"
build
step "(f) find_package(eigen3 REQUIRED) lowercase"
cml "find_package(eigen3 REQUIRED)"; build
step "(f) find_package(EIGEN3 REQUIRED) uppercase"
cml "find_package(EIGEN3 REQUIRED)"; build
step "(f) find_package(Diagnostic_Updater REQUIRED) with ros-$D-diagnostic-updater installed"
apt-get install -y -qq ros-$D-diagnostic-updater > /dev/null 2>&1
cml "find_package(Diagnostic_Updater REQUIRED)"; build
purge

step "(e) workspace package mylib exists, fp find_package(mylib)"
mkdir -p /ws/src/mylib
cat > /ws/src/mylib/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>mylib</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
printf 'cmake_minimum_required(VERSION 3.8)\nproject(mylib)\nfind_package(ament_cmake REQUIRED)\nexecute_process(COMMAND sleep 5)\nament_package()\n' > /ws/src/mylib/CMakeLists.txt
cml "find_package(mylib REQUIRED)"
step "(e1) <depend>mylib</depend>, colcon build --packages-select fp (mylib never built)"
pkgxml "<depend>mylib</depend>"; build --packages-select fp
step "(e2) <depend>mylib</depend>, colcon build (all)"
build
step "(e3) mylib built, then colcon build --packages-select fp, install/setup.bash NOT sourced"
cd /ws; colcon build --packages-select fp > /tmp/b3.log 2>&1; echo "BUILD_RC=$?"; tail -2 /tmp/b3.log
echo "after colcon build, in this shell: CMAKE_PREFIX_PATH=[${CMAKE_PREFIX_PATH}] AMENT_PREFIX_PATH=[${AMENT_PREFIX_PATH}]"
( source /ws/install/setup.bash
echo "after source install/setup.bash: CMAKE_PREFIX_PATH=[${CMAKE_PREFIX_PATH}] AMENT_PREFIX_PATH=[${AMENT_PREFIX_PATH}]" )
step "(e4) mylib NOT declared in fp package.xml, colcon build (all), parallel"
pkgxml ""; build
step "(e5) mylib NOT declared, colcon build --executor sequential"
build --executor sequential
step "(e6) mylib NOT declared, colcon graph"
cd /ws; colcon graph
step "done"
