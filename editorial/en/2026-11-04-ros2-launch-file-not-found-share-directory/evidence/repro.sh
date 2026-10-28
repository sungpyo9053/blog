#!/bin/bash
# Run inside ros:<distro>-ros-base. Reproduces "file '...' was not found in the share directory of package '...'"
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-ros2launch ros-$ROS_DISTRO-launch python3-colcon-core python3-colcon-ros 2>/dev/null
python3 -c "import setuptools;print('setuptools',setuptools.__version__)"
W=/ws; mkdir -p $W/src; cd $W/src

LAUNCH='from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    return LaunchDescription([LogInfo(msg="VERSION-1")])'

mkpy() { # name, data_files extra line, launch file names...
  local n=$1 extra=$2; shift 2
  mkdir -p $n/$n $n/resource $n/launch; touch $n/$n/__init__.py $n/resource/$n
  for f in "$@"; do echo "$LAUNCH" > $n/launch/$f; done
  cat > $n/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$n</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<exec_depend>launch</exec_depend>
<export><build_type>ament_python</build_type></export></package>
X
  printf '[develop]\nscript_dir=$base/lib/%s\n[install]\ninstall_scripts=$base/lib/%s\n' $n $n > $n/setup.cfg
  cat > $n/setup.py <<X
import os
from glob import glob
from setuptools import setup
package_name = '$n'
setup(name=package_name, version='0.0.0', packages=[package_name],
  data_files=[
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    $extra
  ], install_requires=['setuptools'], zip_safe=True)
X
}
mkcm() { # name, cmake extra
  local n=$1 extra=$2
  mkdir -p $n/launch; echo "$LAUNCH" > $n/launch/demo.launch.py
  cat > $n/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$n</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><exec_depend>launch</exec_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  printf 'cmake_minimum_required(VERSION 3.8)\nproject(%s)\nfind_package(ament_cmake REQUIRED)\n%s\nament_package()\n' $n "$extra" > $n/CMakeLists.txt
}

mkpy py_nodata ""                                                      demo.launch.py
mkpy py_globmiss "(os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py'))," demo_launch.py
mkpy py_fixed "(os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*launch.[pxy][yma]*')))," demo.launch.py other_launch.py
mkpy py_flat "(os.path.join('share', package_name), glob('launch/*.launch.py'))," demo.launch.py
mkpy py_dup "(os.path.join('share', package_name), glob('launch/*.launch.py')), (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py'))," demo.launch.py
mkcm cm_noinstall ""
# ament_cmake package that also carries a setup.py with data_files (colcon ignores it)
cp py_fixed/setup.py cm_noinstall/setup.py; sed -i "s/py_fixed/cm_noinstall/" cm_noinstall/setup.py
mkcm cm_fixed 'install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})'

cd $W
colcon build 2>&1 | grep -E "Finished|Failed|Summary|error" ; source install/setup.bash

run() { echo "--- ros2 launch $*"; timeout 20 ros2 launch "$@" 2>&1 | sed -E 's/^\[INFO\] \[[^]]*\] \[launch\.user\]: //' | grep -vE '^\[INFO\] \[launch\]' | head -5; echo "exit=${PIPESTATUS[0]}"; }
run py_nodata demo.launch.py
run py_globmiss demo_launch.py
run py_fixed demo.launch.py
run py_fixed other_launch.py
run py_flat demo.launch.py
run py_dup demo.launch.py
run cm_noinstall demo.launch.py
run cm_fixed demo.launch.py

echo "--- what got installed"
for p in py_nodata py_globmiss py_fixed py_flat py_dup cm_noinstall cm_fixed; do
  echo "$p: $(cd install/$p/share/$p 2>/dev/null && find . -name '*launch*' \( -type f -o -type l \) | sort | tr '\n' ' ')"; done

echo "--- stale copy: edit src after a normal build, no rebuild"
sed -i 's/VERSION-1/VERSION-2/' src/py_fixed/launch/demo.launch.py src/cm_fixed/launch/demo.launch.py
run py_fixed demo.launch.py
run cm_fixed demo.launch.py
echo "--- symlink-install build in fresh build/install dirs, then edit again"
mv build build_copy; mv install install_copy
colcon build --symlink-install --packages-select py_fixed cm_fixed 2>&1 | grep -E "Finished|Summary"
source install/setup.bash
ls -l install/py_fixed/share/py_fixed/launch/demo.launch.py install/cm_fixed/share/cm_fixed/launch/demo.launch.py | awk '{print $1, $9, $10, $11}'
sed -i 's/VERSION-2/VERSION-3/' src/py_fixed/launch/demo.launch.py src/cm_fixed/launch/demo.launch.py
run py_fixed demo.launch.py
run cm_fixed demo.launch.py

echo "--- new launch file added after symlink build, no rebuild"
echo "$LAUNCH" > src/cm_fixed/launch/new.launch.py
echo "$LAUNCH" > src/py_fixed/launch/new.launch.py
run cm_fixed new.launch.py
run py_fixed new.launch.py
echo "--- after colcon build --symlink-install again"
colcon build --symlink-install --packages-select py_fixed cm_fixed 2>&1 | grep -E "Summary"
run cm_fixed new.launch.py
run py_fixed new.launch.py

echo "--- workspace not sourced (fresh shell, only /opt/ros)"
env -i HOME=/root PATH=/usr/bin:/bin bash -c "source /opt/ros/$ROS_DISTRO/setup.bash; timeout 20 ros2 launch py_fixed demo.launch.py 2>&1 | head -3"

echo "--- ros2launch lookup source"
python3 - <<'P'
import inspect, ros2launch.api.api as a
print(inspect.getsource(a.get_share_file_path_from_package))
P
