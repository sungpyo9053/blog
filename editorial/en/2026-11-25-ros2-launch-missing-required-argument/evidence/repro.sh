#!/bin/bash
# Run inside ros:<distro>-ros-base. ROS 2 launch argument behavior: required args,
# IncludeLaunchDescription launch_arguments forms, scoping/leaks, typos, defaults, booleans.
source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-launch-xml ros-$ROS_DISTRO-launch-yaml ros-$ROS_DISTRO-ros2launch ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset, default>}"
W=/ws; P=$W/src/larg; mkdir -p $P/launch; cd $P
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>larg</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><exec_depend>rclpy</exec_depend><exec_depend>launch_ros</exec_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(larg)
find_package(ament_cmake REQUIRED)
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS pnode.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > pnode.py <<'X'
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
rclpy.init()
n = Node('pnode', automatically_declare_parameters_from_overrides=True)
p = n.get_parameter('flag')
print(f'NODE {n.get_name()} flag={p.value!r} type={p.type_.name}', flush=True)
rclpy.shutdown()
X
chmod +x pnode.py
L=$P/launch
HDR='import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration as LC
from launch.conditions import IfCondition, UnlessCondition
def inc(name, **kw):
    return IncludeLaunchDescription(PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory("larg"), "launch", name)), **kw)
def generate_launch_description():
    return LaunchDescription(['
mk() { { echo "$HDR"; cat; echo '    ])'; } > $L/$1; }

# (1) child with a required argument x
mk child.launch.py <<'X'
        DeclareLaunchArgument('x', description='the x value'),
        LogInfo(msg=['CHILD x=', LC('x')]),
X
mk parent_noargs.launch.py <<'X'
        inc('child.launch.py'),
X
# (2) launch_arguments forms
mk parent_items.launch.py <<'X'
        inc('child.launch.py', launch_arguments={'x': 'from_items'}.items()),
X
mk parent_tuples.launch.py <<'X'
        inc('child.launch.py', launch_arguments=[('x', 'from_tuples')]),
X
mk parent_dict.launch.py <<'X'
        inc('child.launch.py', launch_arguments={'x': 'from_dict'}),
X
mk parent_int.launch.py <<'X'
        inc('child.launch.py', launch_arguments={'x': 5}.items()),
X
mk parent_lc.launch.py <<'X'
        DeclareLaunchArgument('x', default_value='parent_x'),
        inc('child.launch.py', launch_arguments={'x': LC('x')}.items()),
X
mk parent_dict_optional.launch.py <<'X'
        inc('child_y.launch.py', launch_arguments={'y': 'from_dict'}),
X
# (3) scoping / leaks
mk parent_declares_x.launch.py <<'X'
        DeclareLaunchArgument('x', default_value='parent_x'),
        inc('child.launch.py'),
X
mk child_y.launch.py <<'X'
        DeclareLaunchArgument('y', default_value='child_default'),
        DeclareLaunchArgument('z', default_value='child_z'),
        LogInfo(msg=['CHILD y=', LC('y')]),
        LogInfo(msg=['CHILD u=', LC('u', default='u_unset')]),
X
mk leak_plain.launch.py <<'X'
        DeclareLaunchArgument('y', default_value='parent_default'),
        inc('child_y.launch.py'),
        LogInfo(msg=['PARENT_AFTER z=', LC('z', default='z_unset')]),
X
mk leak_scoped.launch.py <<'X'
        DeclareLaunchArgument('y', default_value='parent_default'),
        GroupAction([inc('child_y.launch.py')], scoped=True),
        LogInfo(msg=['PARENT_AFTER z=', LC('z', default='z_unset')]),
X
mk leak_noforward.launch.py <<'X'
        DeclareLaunchArgument('y', default_value='parent_default'),
        GroupAction([inc('child_y.launch.py')], scoped=True, forwarding=False),
        LogInfo(msg=['PARENT_AFTER z=', LC('z', default='z_unset')]),
X
mk leak_noforward_cfg.launch.py <<'X'
        DeclareLaunchArgument('y', default_value='parent_default'),
        GroupAction([inc('child_y.launch.py')], scoped=True, forwarding=False, launch_configurations={'y': 'via_group'}),
        LogInfo(msg=['PARENT_AFTER z=', LC('z', default='z_unset')]),
X
mk leak_required_noforward.launch.py <<'X'
        DeclareLaunchArgument('x', default_value='parent_x'),
        GroupAction([inc('child.launch.py')], scoped=True, forwarding=False),
X
# (4) typo target
mk sim.launch.py <<'X'
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        LogInfo(msg=['SIM use_sim_time=', LC('use_sim_time')]),
X
# (5) defaults
mk defaults.launch.py <<'X'
        LogInfo(msg=['BEFORE_DECLARE w=', LC('w', default='from_lc_default')]),
        DeclareLaunchArgument('w', default_value='from_declare', description='w arg'),
        LogInfo(msg=['AFTER_DECLARE w=', LC('w', default='from_lc_default')]),
        LogInfo(msg=['UNDECLARED v=', LC('v', default='from_lc_only')]),
X
# (6) booleans
{ echo "$HDR" | sed 's/^from launch.conditions/from launch_ros.actions import Node\nfrom launch_ros.parameter_descriptions import ParameterValue\nfrom launch.conditions/'; cat <<'X'
        DeclareLaunchArgument('b', default_value='false'),
        LogInfo(condition=IfCondition(LC('b')), msg='IF=taken'),
        LogInfo(condition=UnlessCondition(LC('b')), msg='UNLESS=taken'),
        Node(package='larg', executable='pnode.py', name='plain', parameters=[{'flag': LC('b')}], output='screen'),
        Node(package='larg', executable='pnode.py', name='as_str', parameters=[{'flag': ParameterValue(LC('b'), value_type=str)}], output='screen'),
    ])
X
} > $L/bool.launch.py
# XML / YAML frontends
cat > $L/child.launch.xml <<'X'
<launch>
  <arg name="x" description="the x value"/>
  <log message="XML x=$(var x)"/>
</launch>
X
cat > $L/child.launch.yaml <<'X'
launch:
- arg:
    name: x
    description: the x value
- log:
    message: "YAML x=$(var x)"
X
cat > $L/parent.launch.xml <<'X'
<launch>
  <include file="$(find-pkg-share larg)/launch/child.launch.py"/>
</launch>
X
cat > $L/parent_arg.launch.xml <<'X'
<launch>
  <include file="$(find-pkg-share larg)/launch/child.launch.py">
    <arg name="x" value="from_xml"/>
  </include>
</launch>
X
cd $W && colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { cat /tmp/build.log; exit 1; }
source $W/install/setup.bash

run() { local t="$1"; shift; echo; echo "### $t"; echo "\$ $*"; timeout 60 "$@" 2>&1 | grep -v 'All log files can be found' | sed -E 's/\[[0-9]+\.[0-9]+\] //'; echo "EXIT=${PIPESTATUS[0]}"; }

echo; echo "===== (1) required argument"
run 1a ros2 launch larg child.launch.py
run 1b ros2 launch larg child.launch.py x:=cli
run 1c ros2 launch larg parent_noargs.launch.py
run 1d ros2 launch larg parent_noargs.launch.py x:=cli
run 1e ros2 launch larg parent_declares_x.launch.py
run 1f ros2 launch larg child.launch.xml
run 1g ros2 launch larg child.launch.yaml
run 1h ros2 launch larg parent.launch.xml
run 1i ros2 launch larg parent_arg.launch.xml
echo; echo "===== (2) launch_arguments forms"
run 2a ros2 launch larg parent_items.launch.py
run 2b ros2 launch larg parent_tuples.launch.py
run 2c ros2 launch larg parent_dict.launch.py
run 2d ros2 launch larg parent_int.launch.py
run 2e ros2 launch larg parent_lc.launch.py x:=cli
echo; echo "===== (3) scoping"
run 3a ros2 launch larg leak_plain.launch.py
run 3b ros2 launch larg leak_plain.launch.py y:=cli_y u:=cli_u
run 3c ros2 launch larg leak_scoped.launch.py
run 3d ros2 launch larg leak_scoped.launch.py y:=cli_y u:=cli_u
run 3e ros2 launch larg leak_noforward.launch.py
run 3f ros2 launch larg leak_noforward.launch.py y:=cli_y u:=cli_u
run 3g ros2 launch larg leak_noforward_cfg.launch.py
run 3h ros2 launch larg leak_required_noforward.launch.py
echo; echo "===== (4) misspelled argument"
run 4a ros2 launch larg sim.launch.py use_sim_tme:=true
run 4b ros2 launch larg sim.launch.py use_sim_time:=true
run 4c ros2 launch larg child.launch.py X:=1
echo; echo "===== (5) defaults and --show-args"
run 5a ros2 launch larg defaults.launch.py
run 5b ros2 launch larg defaults.launch.py w:=cli
run 5c ros2 launch larg defaults.launch.py --show-args
run 5d ros2 launch larg child.launch.py --show-args
run 5e ros2 launch larg parent_noargs.launch.py --show-args
run 5f ros2 launch larg leak_plain.launch.py --show-args
run 5g ros2 launch larg child.launch.xml --show-args
echo; echo "===== (6) booleans"
for v in true True TRUE 1 0 false False yes on; do run "6 b=$v" ros2 launch larg bool.launch.py b:=$v; done
echo; echo "===== (7) follow-ups"
run 7a ros2 launch larg parent_dict_optional.launch.py
run 7b ros2 launch larg parent_items.launch.py x:=cli
run 7c ros2 launch -d larg parent_dict.launch.py
echo "=== done"
