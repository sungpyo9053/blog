#!/bin/bash
# Runs inside ros:<distro>-ros-base as: bash /w/repro.sh <distro>
# Host side (runner), one distro at a time:
#   docker run -d --name pk42-$D -e ROS_DOMAIN_ID=88 -v /tmp/en-pick52:/w ros:$D-ros-base sleep infinity
#   docker exec pk42-$D bash -c "apt-get update && apt-get install -y ros-$D-robot-state-publisher ros-$D-xacro liburdfdom-tools"
#   docker exec pk42-$D bash /w/repro.sh $D > out_$D.txt 2>&1
# DDS stays inside the container: ROS_DOMAIN_ID=88 plus localhost-only discovery.
set +e
ulimit -c 0
D=$1
source /opt/ros/$D/setup.bash
export ROS_DOMAIN_ID=88
if [ "$D" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export PYTHONUNBUFFERED=1 RCUTILS_COLORIZED_OUTPUT=0
N=/w/n_$D; mkdir -p $N; cd $N

# ---------- URDF / xacro inputs ----------
cat > valid.urdf <<'U'
<?xml version="1.0"?>
<robot name="bot">
  <link name="base_link"/>
  <link name="laser"/>
  <link name="wheel"/>
  <joint name="laser_joint" type="fixed">
    <parent link="base_link"/><child link="laser"/>
    <origin xyz="0.1 0 0.2" rpy="0 0 0"/>
  </joint>
  <joint name="wheel_joint" type="revolute">
    <parent link="base_link"/><child link="wheel"/>
    <axis xyz="0 0 1"/>
    <limit lower="-3.14" upper="3.14" effort="100" velocity="10"/>
  </joint>
</robot>
U
# links only inside a macro that is never called
cat > macro_not_called.xacro <<'U'
<?xml version="1.0"?>
<robot name="bot" xmlns:xacro="http://www.ros.org/wiki/xacro">
  <xacro:macro name="body">
    <link name="base_link"/>
    <link name="laser"/>
    <joint name="laser_joint" type="fixed">
      <parent link="base_link"/><child link="laser"/>
    </joint>
  </xacro:macro>
</robot>
U
# same idea, macro called, with a property
cat > good.xacro <<'U'
<?xml version="1.0"?>
<robot name="bot" xmlns:xacro="http://www.ros.org/wiki/xacro">
  <xacro:property name="h" value="0.2"/>
  <xacro:macro name="body">
    <link name="base_link"/>
    <link name="laser"/>
    <joint name="laser_joint" type="fixed">
      <parent link="base_link"/><child link="laser"/>
      <origin xyz="0.1 0 ${h}" rpy="0 0 0"/>
    </joint>
  </xacro:macro>
  <xacro:body/>
</robot>
U
# xacro include of a file that does not exist
cat > bad_include.xacro <<'U'
<?xml version="1.0"?>
<robot name="bot" xmlns:xacro="http://www.ros.org/wiki/xacro">
  <xacro:include filename="$(find robot_state_publisher)/urdf/missing.xacro"/>
  <link name="base_link"/>
</robot>
U
LIM='<limit lower="-3.14" upper="3.14" effort="100" velocity="10"/>'
sed 's/<robot name="bot">/<robot>/' valid.urdf > no_name.urdf
# limit written as child elements (robotics.stackexchange 110645)
sed "s#$LIM#<limit><lower>-3.14</lower><upper>3.14</upper><effort>100</effort><velocity>10</velocity></limit>#" valid.urdf > limit_children.urdf
sed '/<limit /d' valid.urdf > revolute_no_limit.urdf
sed "s#$LIM#<limit lower=\"-3.14\" upper=\"3.14\" velocity=\"10\"/>#" valid.urdf > limit_no_effort.urdf
sed "s#$LIM#<limit lower=\"-3.14\" upper=\"3.14\" effort=\"100\"/>#" valid.urdf > limit_no_velocity.urdf
sed '$d' valid.urdf > unclosed.urdf
sed 's#<link name="wheel"/>#<link name="wheel"/>\n  <link name="orphan"/>#' valid.urdf > two_roots.urdf
sed 's#<child link="laser"/>#<child link="lidar"/>#' valid.urdf > missing_child.urdf
sed 's#<link name="laser"/>#<link name="laser"/>\n  <link name="laser"/>#' valid.urdf > dup_link.urdf
sed 's#type="revolute"#type="spinning"#' valid.urdf > bad_joint_type.urdf
printf '' > empty.urdf
# a colon inside an XML comment (robotics.stackexchange 102227) and inside an attribute (package:// mesh)
sed 's#<link name="wheel"/>#<!-- note: wheel radius is 0.05 -->\n  <link name="wheel"/>#' valid.urdf > colon_comment.urdf
sed 's#<link name="laser"/>#<link name="laser"><visual><geometry><mesh filename="package://bot/meshes/laser.stl"/></geometry></visual></link>#' valid.urdf > colon_attr.urdf

echo "### versions"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-robot-state-publisher ros-$D-xacro ros-$D-urdf ros-$D-urdfdom liburdfdom-tools 'liburdfdom-model*' 2>/dev/null | sort -u
python3 --version

# params file from a URDF string (yaml.safe_dump handles quoting)
mkp() { python3 -c "import sys,yaml;yaml.safe_dump({'robot_state_publisher':{'ros__parameters':{'robot_description':open(sys.argv[1]).read()}}},open(sys.argv[2],'w'))" "$1" "$2"; }
mkp_str() { python3 -c "import sys,yaml;yaml.safe_dump({'robot_state_publisher':{'ros__parameters':{'robot_description':sys.argv[1]}}},open(sys.argv[2],'w'))" "$1" "$2"; }

# run for up to 6 s; rc 124/130 = still running after 6 s (it started fine)
run() { local name=$1; shift
  echo; echo "### CASE $name"
  echo "\$ $*" | cut -c1-200
  local t0=$(date +%s%N)
  timeout -s INT -k 3 6 "$@" 2>&1 | sed 's/^\[[^]]*\] \[[0-9.]*\] //' | head -30
  local rc=${PIPESTATUS[0]}; local t1=$(date +%s%N)
  echo "rc=$rc elapsed_ms=$(( (t1-t0)/1000000 ))"
}
RSP="ros2 run robot_state_publisher robot_state_publisher"

echo; echo "### xacro expansions"
xacro macro_not_called.xacro > macro_not_called.urdf; echo "xacro macro_not_called rc=$? links=$(grep -c '<link' macro_not_called.urdf)"
xacro good.xacro > good.urdf; echo "xacro good rc=$? links=$(grep -c '<link' good.urdf)"
xacro bad_include.xacro > bad_include.urdf 2> bad_include.err; echo "xacro bad_include rc=$? bytes=$(wc -c < bad_include.urdf)"; head -5 bad_include.err
xacro nofile.xacro > /dev/null 2> nofile.err; echo "xacro nofile rc=$?"; head -3 nofile.err

for c in valid empty macro_not_called no_name limit_children revolute_no_limit limit_no_effort limit_no_velocity unclosed two_roots missing_child dup_link bad_joint_type good bad_include; do
  mkp $c.urdf $c.yaml
  run "params-file $c" $RSP --ros-args --params-file $c.yaml
done
mkp good.xacro raw_xacro.yaml
run "params-file raw xacro (not expanded)" $RSP --ros-args --params-file raw_xacro.yaml
mkp_str "$N/valid.urdf" path.yaml
run "params-file robot_description = path string" $RSP --ros-args --params-file path.yaml
run "no robot_description at all" $RSP
run "positional urdf file argument" $RSP $N/valid.urdf
run "-p robot_description:=\$(xacro good.xacro)" $RSP --ros-args -p robot_description:="$(xacro good.xacro)"
run "-p robot_description:=\$(cat valid.urdf)" $RSP --ros-args -p robot_description:="$(cat valid.urdf)"
ONE=$(tr -d '\n' < valid.urdf | sed 's/  */ /g')
run "-p robot_description:=<one-line urdf>" $RSP --ros-args -p robot_description:="$ONE"
for c in colon_comment colon_attr; do
  mkp $c.urdf $c.yaml
  run "params-file $c" $RSP --ros-args --params-file $c.yaml
  run "-p robot_description:=\$(cat $c.urdf)" $RSP --ros-args -p robot_description:="$(cat $c.urdf)"
  run "-p robot_description:='\$(cat $c.urdf)' (single quotes inside)" $RSP --ros-args -p "robot_description:='$(cat $c.urdf)'"
done
run "-p robot_description:='<xacro output in single quotes>'" $RSP --ros-args -p "robot_description:='$(xacro good.xacro)'"

echo; echo "### check_urdf"
for c in valid empty macro_not_called no_name limit_children revolute_no_limit limit_no_effort two_roots missing_child; do
  echo "-- check_urdf $c"; timeout 10 check_urdf $c.urdf 2>&1 | head -6; echo "rc=${PIPESTATUS[0]}"
done
echo "-- check_urdf good.xacro (raw)"; timeout 10 check_urdf good.xacro 2>&1 | head -6; echo "rc=${PIPESTATUS[0]}"

# ---------- launch files ----------
mk_launch() { # name, python expression for robot_description or 'ARGS'
cat > l_$1.launch.py <<P
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
def generate_launch_description():
    $2
    return LaunchDescription([Node(package='robot_state_publisher', executable='robot_state_publisher', output='screen', $3)])
P
}
mk_launch command "desc = ParameterValue(Command(['xacro ', '$N/good.xacro']), value_type=str)" "parameters=[{'robot_description': desc}]"
mk_launch read "desc = open('$N/valid.urdf').read()" "parameters=[{'robot_description': desc}]"
mk_launch path "desc = '$N/valid.urdf'" "parameters=[{'robot_description': desc}]"
mk_launch args "pass" "arguments=['$N/valid.urdf']"
mk_launch badinc "desc = ParameterValue(Command(['xacro ', '$N/bad_include.xacro']), value_type=str)" "parameters=[{'robot_description': desc}]"
mk_launch colon "desc = open('$N/colon_comment.urdf').read()" "parameters=[{'robot_description': desc}]"
mk_launch macro "desc = ParameterValue(Command(['xacro ', '$N/macro_not_called.xacro']), value_type=str)" "parameters=[{'robot_description': desc}]"
for l in command read path args badinc macro colon; do
  run "launch $l" ros2 launch $N/l_$l.launch.py
done

# ---------- what a working node publishes ----------
echo; echo "### working node outputs (valid.urdf via params file)"
$RSP --ros-args --params-file valid.yaml > rsp_ok.log 2>&1 &
P=$!; sleep 3
echo "-- /tf_static (transient_local)"
timeout 10 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable /tf_static tf2_msgs/msg/TFMessage 2>&1 | grep -E 'frame_id|x:|z:' | head -8
echo "-- /robot_description first lines"
timeout 10 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable --full-length /robot_description std_msgs/msg/String 2>&1 | head -3 | cut -c1-120
echo "-- /tf messages in 5 s without /joint_states"
timeout 5 ros2 topic echo /tf tf2_msgs/msg/TFMessage 2>&1 | grep -c child_frame_id
for H in "" "header: {stamp: now}, "; do
  echo "-- /tf after one /joint_states message, header='$H'"
  ( sleep 4; timeout 8 ros2 topic pub -w 1 --once /joint_states sensor_msgs/msg/JointState "{${H}name: [wheel_joint], position: [0.5]}" > /dev/null 2>&1 ) &
  B=$!
  timeout 12 ros2 topic echo --once /tf tf2_msgs/msg/TFMessage 2>&1 | grep -E 'child_frame_id|z:|w:' | head -4
  echo "echo rc=${PIPESTATUS[0]}"
  wait $B
done
echo "-- set robot_description at runtime to a URDF with no links"
timeout 15 ros2 param set /robot_state_publisher robot_description "<robot name='x'></robot>" 2>&1 | head -3
sleep 1; echo "-- node alive after bad runtime set: $(kill -0 $P 2>/dev/null && echo yes || echo no)"
echo "-- set it back to valid"
timeout 15 ros2 param set /robot_state_publisher robot_description "$(cat valid.urdf)" 2>&1 | head -3
kill -INT $P 2>/dev/null; timeout 5 tail --pid=$P -f /dev/null; pkill -9 -f lib/robot_state_publisher; ros2 daemon stop > /dev/null 2>&1
echo "-- rsp log"; sed 's/^\[[^]]*\] \[[0-9.]*\] //' rsp_ok.log | head -15
echo "### done"
