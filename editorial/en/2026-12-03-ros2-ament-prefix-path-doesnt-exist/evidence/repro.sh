#!/bin/bash
# Run inside ros:<distro>-ros-base as: bash repro.sh
# Reproduces colcon's "The path '...' in the environment variable AMENT_PREFIX_PATH doesn't exist"
# warning (and its CMAKE_PREFIX_PATH / COLCON_PREFIX_PATH siblings), checks which commands print it,
# and compares fixes. Each "shell" below is a fresh bash -c with only /opt/ros sourced first.
ulimit -c 0
set -u
D=$ROS_DISTRO
echo "=== distro=$D"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-rmw-implementation ros-$D-ament-index-python 2>/dev/null
dpkg-query -W -f='${Package} ${Version}\n' 'python3-colcon-core' 'python3-colcon-ros' 'python3-colcon-cmake' 'python3-colcon-library-path' 2>/dev/null
python3 -c 'import colcon_core;print("colcon_core", colcon_core.__version__)'

mkws() {  # $1 = workspace path; three packages: py_pkg (ament_python), cpp_a and cpp_b (ament_cmake)
  local W=$1; rm -rf $W; mkdir -p $W/src
  mkdir -p $W/src/py_pkg/py_pkg $W/src/py_pkg/resource; cd $W/src/py_pkg
  touch resource/py_pkg py_pkg/__init__.py
  printf 'def main():\n    print("HELLO from py_pkg")\n' > py_pkg/hello.py
  cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>py_pkg</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<export><build_type>ament_python</build_type></export></package>
X
  cat > setup.py <<'X'
from setuptools import setup
setup(name='py_pkg', version='0.0.0', packages=['py_pkg'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/py_pkg']),
                  ('share/py_pkg', ['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': ['hello = py_pkg.hello:main']})
X
  printf '[develop]\nscript_dir=$base/lib/py_pkg\n[install]\ninstall_scripts=$base/lib/py_pkg\n' > setup.cfg
  for p in cpp_a cpp_b; do
    mkdir -p $W/src/$p; cd $W/src/$p
    cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$p</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
    printf 'cmake_minimum_required(VERSION 3.8)\nproject(%s NONE)\nfind_package(ament_cmake REQUIRED)\nament_package()\n' $p > CMakeLists.txt
  done
  cd $W
}

# run "$label" "commands": fresh shell, /opt/ros sourced, then the commands
run() {
  echo; echo "### $1"
  echo "\$ $2"
  local t0=$(date +%s.%N)
  bash -c "source /opt/ros/$D/setup.bash; $2" > /tmp/run.out 2>&1; local rc=$?
  local t1=$(date +%s.%N)
  sed 's/^/    /' /tmp/run.out | grep -v '^    $' | head -40
  echo "    [rc=$rc] [warn_lines=$(grep -c "doesn't exist" /tmp/run.out)] [ament=$(grep -c "AMENT_PREFIX_PATH doesn't exist" /tmp/run.out)] [cmake=$(grep -c "CMAKE_PREFIX_PATH doesn't exist" /tmp/run.out)] [colcon=$(grep -c "COLCON_PREFIX_PATH doesn't exist" /tmp/run.out)] [secs=$(python3 -c "print(round($t1-$t0,2))")]"
}
B="colcon build --event-handlers console_direct- console_cohesion- >/dev/null 2>/tmp/err; cat /tmp/err"
# quieter build: colcon writes the prefix-path warnings to stderr, so keep only stderr

W=/ws
mkws $W
run "C0 baseline: first build in a clean shell" "cd $W; colcon build"
run "C0b env after sourcing" "cd $W; source install/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH; echo CMAKE_PREFIX_PATH=\$CMAKE_PREFIX_PATH; echo COLCON_PREFIX_PATH=\${COLCON_PREFIX_PATH:-unset}"
run "C0c rebuild in a sourced shell, nothing deleted" "cd $W; source install/setup.bash; $B"

# Cause 1: rm -rf build install log in a shell that sourced the overlay, then rebuild
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "C1 rm -rf build install log, rebuild in the same shell" "cd $W; source install/setup.bash; rm -rf build install log; $B"
run "C1-ros2 same shell, ros2 pkg list / ros2 run after deletion and rebuild" "cd $W; source install/setup.bash; rm -rf build install log; colcon build >/dev/null 2>&1; ros2 pkg list 2>&1 | grep -E '^(py_pkg|cpp_a|cpp_b)\$'; ros2 run py_pkg hello"
run "C1-twice rebuild a second time in that shell (no re-source)" "cd $W; source install/setup.bash; rm -rf build install log; colcon build >/dev/null 2>&1; $B"

# Cause 2: package removed from src and its install dir deleted (RSE 113088)
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "C2 remove src/cpp_b and install/cpp_b, rebuild in same shell" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; $B"
run "C2-py same for the ament_python package py_pkg" "cd $W; source install/setup.bash; rm -rf src/py_pkg install/py_pkg build/py_pkg; $B"
run "C2-ros2 ros2 commands in that shell" "cd $W; source install/setup.bash; ros2 pkg list 2>&1 | grep -E '^(py_pkg|cpp_a|cpp_b)\$'; ros2 pkg prefix cpp_a; echo rc=\$?; ros2 pkg prefix cpp_b; echo rc=\$?"

# Cause 3: package removed from src only (install/cpp_b left behind)
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "C3 remove src/cpp_b only, rebuild in same shell" "cd $W; source install/setup.bash; rm -rf src/cpp_b; $B; ls install"
run "C3-ros2 is cpp_b still a package?" "cd $W; source install/setup.bash; ros2 pkg list | grep -E '^(py_pkg|cpp_a|cpp_b)\$'; ros2 pkg prefix cpp_b"

# Cause 4: workspace moved or renamed after sourcing
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "C4 source /ws, mv /ws /ws_moved, build there" "source $W/install/setup.bash; mv $W /ws_moved; cd /ws_moved; $B; mv /ws_moved $W"

# Cause 5: two overlays, the first one deleted
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
mkws /ws2; rm -rf /ws2/src/py_pkg /ws2/src/cpp_a; mv /ws2/src/cpp_b /ws2/src/cpp_c; sed -i 's/cpp_b/cpp_c/g' /ws2/src/cpp_c/package.xml /ws2/src/cpp_c/CMakeLists.txt
run "C5 source /ws, delete /ws, build /ws2" "source $W/install/setup.bash; rm -rf $W; cd /ws2; $B"

# Fixes, all starting from cause 2 (cpp_b deleted)
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "F1 re-source install/setup.bash in the same shell" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; source install/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH; $B"
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "F2 re-source /opt/ros setup.bash, then install/setup.bash" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; source /opt/ros/$D/setup.bash; source install/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH; $B"
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1; rm -rf src/cpp_b install/cpp_b build/cpp_b"
run "F3 new shell: only /opt/ros sourced, then build" "cd $W; $B"
run "F3b new shell, source install/setup.bash, then build" "cd $W; source install/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH; $B"
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "F4 reset the three variables by hand in the same shell" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; export AMENT_PREFIX_PATH=/opt/ros/$D; unset CMAKE_PREFIX_PATH COLCON_PREFIX_PATH; $B"
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "F5 env -i style: build with a clean environment from the polluted shell" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; env -i HOME=\$HOME PATH=/usr/bin:/bin bash -c 'source /opt/ros/$D/setup.bash; cd $W; $B'"
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "F6 colcon --log-level error hides it?" "cd $W; source install/setup.bash; rm -rf src/cpp_b install/cpp_b build/cpp_b; colcon --log-level error build --event-handlers console_direct- console_cohesion- >/dev/null 2>/tmp/err; cat /tmp/err"

# Does a build that warns still work?
mkws $W; bash -c "source /opt/ros/$D/setup.bash; cd $W; colcon build >/dev/null 2>&1"
run "H1 warned build: are packages installed and runnable afterwards (new shell)?" "cd $W; source install/setup.bash; rm -rf build install log; colcon build >/dev/null 2>&1; echo build_rc=\$?; bash -c 'source /opt/ros/$D/setup.bash; source $W/install/setup.bash; ros2 run py_pkg hello; ros2 pkg prefix cpp_a'"

# Scale: warning count vs number of ament_cmake packages (rm -rf install in sourced shell)
for N in 10 30; do
  rm -rf /wsn; mkdir -p /wsn/src
  for i in $(seq 1 $N); do p=c$i; mkdir -p /wsn/src/$p
    printf '<?xml version="1.0"?><package format="3"><name>%s</name><version>0.0.0</version><description>t</description><maintainer email="dev@example.com">a</maintainer><license>MIT</license><buildtool_depend>ament_cmake</buildtool_depend><export><build_type>ament_cmake</build_type></export></package>\n' $p > /wsn/src/$p/package.xml
    printf 'cmake_minimum_required(VERSION 3.8)\nproject(%s NONE)\nfind_package(ament_cmake REQUIRED)\nament_package()\n' $p > /wsn/src/$p/CMakeLists.txt
  done
  bash -c "source /opt/ros/$D/setup.bash; cd /wsn; colcon build --parallel-workers 2 >/dev/null 2>&1"
  run "S$N $N ament_cmake packages, rm -rf install, rebuild in same shell" "cd /wsn; source install/setup.bash; rm -rf build install log; colcon build --parallel-workers 2 --event-handlers console_direct- console_cohesion- >/dev/null 2>/tmp/err; cat /tmp/err"
  run "S$N-clean same rebuild from a clean shell" "cd /wsn; rm -rf build install log; colcon build --parallel-workers 2 --event-handlers console_direct- console_cohesion- >/dev/null 2>/tmp/err; cat /tmp/err"
done
echo "=== done $D"
