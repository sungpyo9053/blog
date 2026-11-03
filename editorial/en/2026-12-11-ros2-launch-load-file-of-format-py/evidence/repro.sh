#!/bin/bash
# Run inside ros:<distro>-ros-base. Reproduces "Caught exception when trying to load
# file of format [py]" from ros2 launch with one broken launch file per cause.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-launch-xml ros-$ROS_DISTRO-launch-yaml ros-$ROS_DISTRO-ros2launch ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-ament-index-python 2>/dev/null
python3 --version
L=/l; mkdir -p $L; cd /tmp
cat > $L/c01_ok.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    return LaunchDescription([LogInfo(msg='LAUNCH-OK')])
X
cat > $L/c02_syntax.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    return LaunchDescription([LogInfo(msg='LAUNCH-OK')]
X
cat > $L/c03_nameerror.launch.py <<'X'
from launch import LaunchDescription
def generate_launch_description():
    return LaunchDescription([launch_ros.actions.Node(package='demo', executable='talker')])
X
cat > $L/c04_nofunc.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_descriptions():
    return LaunchDescription([LogInfo(msg='LAUNCH-OK')])
X
cat > $L/c05_pkg_notfound.launch.py <<'X'
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    p = os.path.join(get_package_share_directory('gazebo_ros'), 'launch')
    return LaunchDescription([LogInfo(msg=p)])
X
cat > $L/helper.py <<'X'
MSG = 'HELPER-IMPORTED'
X
cat > $L/c06_helper.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
from helper import MSG
def generate_launch_description():
    return LaunchDescription([LogInfo(msg=MSG)])
X
cat > $L/c06b_helper_fixed.launch.py <<'X'
import os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from launch import LaunchDescription
from launch.actions import LogInfo
from helper import MSG
def generate_launch_description():
    return LaunchDescription([LogInfo(msg=MSG)])
X
cat > $L/c07_returns_none.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    ld = LaunchDescription([LogInfo(msg='LAUNCH-OK')])
X
cat > $L/c08_returns_list.launch.py <<'X'
from launch.actions import LogInfo
def generate_launch_description():
    return [LogInfo(msg='LAUNCH-OK')]
X
cat > $L/c09_bad_kwarg.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='demo', executable='talker', node_name='x')])
X
cat > $L/c10_missing_module.launch.py <<'X'
from launch import LaunchDescription
from nav2_common.launch import RewrittenYaml
def generate_launch_description():
    return LaunchDescription([])
X
cat > $L/c11_import_typo.launch.py <<'X'
from ament_index_python.packages import get_packages_share_directory
from launch import LaunchDescription
def generate_launch_description():
    return LaunchDescription([])
X
cat > $L/c12_runtime_opaque.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import OpaqueFunction
def boom(context):
    raise RuntimeError('raised inside OpaqueFunction')
def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=boom)])
X
cp $L/c01_ok.launch.py $L/c13_python_as.launch
cp $L/c01_ok.launch.py $L/c14_python_as.launch.xml
cat > $L/c15_bad.launch.xml <<'X'
<launch>
  <node pkg="demo" exec="talker" nmae="x"/>
</launch>
X
cat > $L/c16_bad.launch.yaml <<'X'
launch:
- node:
    pkg: demo
    exec: talker
  - bad
X
cat > $L/c17_indent.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import LogInfo
def generate_launch_description():
    msg = 'LAUNCH-OK'
      return LaunchDescription([LogInfo(msg=msg)])
X

run() { # label, args...
  local lab=$1; shift
  echo "----- [$lab] ros2 launch $*"
  local t0=$(date +%s%N)
  timeout 60 ros2 launch "$@" > /tmp/o.txt 2>&1; local rc=$?
  local t1=$(date +%s%N)
  sed -e 's/^/  | /' /tmp/o.txt | head -40
  echo "  exit=$rc elapsed_ms=$(( (t1-t0)/1000000 ))"
}
for f in c01_ok c02_syntax c03_nameerror c04_nofunc c05_pkg_notfound c06_helper c06b_helper_fixed c07_returns_none c08_returns_list c09_bad_kwarg c10_missing_module c11_import_typo c12_runtime_opaque c17_indent; do
  run $f $L/$f.launch.py
done
run c13 $L/c13_python_as.launch
run c14 $L/c14_python_as.launch.xml
run c15 $L/c15_bad.launch.xml
run c16 $L/c16_bad.launch.yaml
run missing_file $L/nope.launch.py
echo "===== debug traceback (-d), last 12 lines"
for f in c03_nameerror c05_pkg_notfound c06_helper; do
  echo "----- [-d $f]"; timeout 60 ros2 launch -d $L/$f.launch.py 2>&1 | grep -v '^\[DEBUG\]' | tail -12 | sed 's/^/  | /'
done
echo "===== -d line count and whether 'Traceback' appears"
for f in c03_nameerror c05_pkg_notfound; do
  n=$(timeout 60 ros2 launch -d $L/$f.launch.py 2>&1 | wc -l); tb=$(timeout 60 ros2 launch -d $L/$f.launch.py 2>&1 | grep -c Traceback); echo "  $f lines=$n traceback_count=$tb"
done
echo "===== --show-args (-s) and --print (-p) on broken files"
for f in c03_nameerror c07_returns_none; do
  echo "----- [-s $f]"; timeout 60 ros2 launch -s $L/$f.launch.py 2>&1 | head -5 | sed 's/^/  | /'; echo "  exit=${PIPESTATUS[0]}"
  echo "----- [-p $f]"; timeout 60 ros2 launch -p $L/$f.launch.py 2>&1 | head -5 | sed 's/^/  | /'; echo "  exit=${PIPESTATUS[0]}"
done
echo "===== pre-checks outside ros2 launch"
for f in c01_ok c02_syntax c03_nameerror c04_nofunc c05_pkg_notfound c06_helper c07_returns_none c10_missing_module c17_indent; do
  timeout 60 python3 -m py_compile $L/$f.launch.py >/dev/null 2>&1; pc=$?
  timeout 60 python3 -c "
import runpy,sys
m=runpy.run_path(sys.argv[1])
ld=m['generate_launch_description']()
from launch import LaunchDescription
assert isinstance(ld, LaunchDescription), type(ld)
" $L/$f.launch.py > /tmp/r.txt 2>&1; rp=$?
  echo "  $f py_compile_exit=$pc runpy_call_exit=$rp last=$(tail -1 /tmp/r.txt)"
done
echo "===== ok launch timing x5"
for i in 1 2 3 4 5; do t0=$(date +%s%N); timeout 60 ros2 launch $L/c01_ok.launch.py >/dev/null 2>&1; t1=$(date +%s%N); echo "  ok run$i elapsed_ms=$(( (t1-t0)/1000000 ))"; done
echo "=== done"
