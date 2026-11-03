#!/bin/bash
# Run inside ros:<distro>-ros-base (no xacro preinstalled). Reproduces the launch errors around
# robot_description built from xacro: missing xacro, FindExecutable in PathJoinSubstitution,
# missing space, bad path, xacro errors, and YAML parsing of the URDF string without ParameterValue.
# Host side (one distro at a time):
#   docker run --rm --name pk2-p11-$D --ulimit core=0 --pids-limit 300 --cpus 1.5 \
#     -v /tmp/en-pick11:/e ros:$D-ros-base bash /e/repro.sh > out_$D.txt 2>&1
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=61
echo "=== distro=$ROS_DISTRO"
pkgs() { dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros \
  ros-$ROS_DISTRO-robot-state-publisher ros-$ROS_DISTRO-xacro python3-yaml 2>/dev/null; }
pkgs; echo "RMW default: ${RMW_IMPLEMENTATION:-unset}"; python3 --version
W=/w; mkdir -p $W; cd $W

# ---- URDF variants (all valid XML) ----
cat > plain.urdf.xacro <<'X'
<?xml version="1.0"?>
<robot name="bot" xmlns:xacro="http://www.ros.org/wiki/xacro">
  <xacro:property name="r" value="0.1"/>
  <link name="base_link"/>
  <link name="wheel"><visual><geometry><cylinder radius="${r}" length="0.05"/></geometry></visual></link>
  <joint name="wheel_joint" type="continuous"><parent link="base_link"/><child link="wheel"/><origin xyz="0 0.2 0" rpy="0 0 0"/></joint>
</robot>
X
sed 's#<link name="base_link"/>#<!-- Note: base frame -->\n  <link name="base_link"/>#' plain.urdf.xacro > colon.urdf.xacro
sed 's|<link name="base_link"/>|<!-- link #1 -->\n  <link name="base_link"/>|' plain.urdf.xacro > hash.urdf.xacro
sed 's#<link name="base_link"/>#<material name="red"><color rgba="1 0 0 1"/></material>\n  <link name="base_link"/>#' plain.urdf.xacro > material.urdf.xacro
sed 's#radius="${r}"#radius="${wheel_radius}"#' plain.urdf.xacro > undefined.urdf.xacro
sed 's#</robot>#</robt>#' plain.urdf.xacro > badxml.urdf.xacro
grep -c '' *.xacro

mk() { # $1=name $2=python expression for the robot_description value, $3=extra imports
cat > $1.launch.py <<X
from launch import LaunchDescription
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
$3
def generate_launch_description():
    return LaunchDescription([Node(package='robot_state_publisher', executable='robot_state_publisher',
        output='screen', parameters=[{'robot_description': $2}])])
X
}

run() { # $1=launch file. If still alive at 8 s: query, then SIGINT; check the node and its parameter, report exit code and time.
  echo; echo "########## CASE $1"; grep -o "robot_description.: .*}" $1 2>/dev/null | head -1; grep -E "param |command" $1 2>/dev/null | head -2
  local t0=$(date +%s.%N)
  timeout -s INT 40 ros2 launch $W/$1 > /tmp/l.log 2>&1 & local p=$!
  local alive=""
  for i in $(seq 1 16); do sleep 0.5; kill -0 $p 2>/dev/null || break; done
  if kill -0 $p 2>/dev/null; then
    alive=yes
    echo "--- launch still running after 8 s; node list:"; timeout 20 ros2 node list --no-daemon 2>&1 | head
    for k in 1 2 3 4 5; do timeout 20 ros2 param get /robot_state_publisher robot_description > /tmp/pg.txt 2>&1; grep -q "Node not found" /tmp/pg.txt || break; echo "(param get try $k: Node not found, retrying)"; sleep 1; done
    echo "--- param get: bytes=$(wc -c < /tmp/pg.txt) lines=$(wc -l < /tmp/pg.txt) (xacro output of the same file has more lines if newlines were folded)"
    head -c 200 /tmp/pg.txt; echo
    kill -INT $p
  fi
  wait $p; local rc=$?; local t1=$(date +%s.%N)
  echo "--- exit=$rc alive_at_8s=${alive:-no} elapsed=$(python3 -c "print(round($t1-$t0,2))")s"
  echo "--- launch output (first 25 lines, long lines cut at 400 chars):"; cut -c1-400 /tmp/l.log | grep -v "^\s*$" | head -25
}

echo; echo "=== which xacro before install: $(which xacro || echo none)"
mk A_cmd_noxacro "Command(['xacro ', '$W/plain.urdf.xacro'])"
mk B_findexec_noxacro "Command([FindExecutable(name='xacro'), ' ', '$W/plain.urdf.xacro'])"
mk C_pathjoin_findexec_noxacro "Command([PathJoinSubstitution([FindExecutable(name='xacro')]), ' ', '$W/plain.urdf.xacro'])"
for c in A_cmd_noxacro B_findexec_noxacro C_pathjoin_findexec_noxacro; do run $c.launch.py; done

echo; echo "=== installing xacro"; t0=$(date +%s)
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$ROS_DISTRO-xacro) > /tmp/apt.log 2>&1; echo "apt rc=$? seconds=$(( $(date +%s)-t0 ))"
source /opt/ros/$ROS_DISTRO/setup.bash; echo "which xacro: $(which xacro)"; pkgs | grep xacro
echo "--- xacro CLI directly on each file:"
for f in plain colon hash material undefined badxml; do echo "## xacro $f.urdf.xacro"; timeout 60 xacro $W/$f.urdf.xacro > /tmp/x.out 2>/tmp/x.err; echo "rc=$? stdout_lines=$(wc -l < /tmp/x.out)"; tail -3 /tmp/x.err | cut -c1-300; done
timeout 60 xacro $W/missing.urdf.xacro; echo "missing rc=$?"
echo "--- YAML view of xacro output (what launch_ros does with a raw Command result):"
for f in plain colon hash material; do xacro $W/$f.urdf.xacro > /tmp/$f.urdf; python3 -c "
import yaml,sys
s=open('/tmp/$f.urdf').read()
try:
  v=yaml.safe_load(s); print('$f: yaml ok, type', type(v).__name__, 'len', len(str(v)), 'equal_to_input', v==s, 'first80', repr(str(v)[:80]))
except yaml.YAMLError as e: print('$f: YAMLError', type(e).__name__, str(e).replace(chr(10),' | ')[:200])
"; done
echo "--- xacro output header (plain):"; head -8 /tmp/plain.urdf

mk D_findexec_ok "Command([FindExecutable(name='xacro'), ' ', '$W/plain.urdf.xacro'])"
mk E_pathjoin_findexec_ok "Command([PathJoinSubstitution([FindExecutable(name='xacro')]), ' ', '$W/plain.urdf.xacro'])"
mk F_nospace "Command(['xacro', '$W/plain.urdf.xacro'])"
mk G_badpath "Command(['xacro ', '$W/missing.urdf.xacro'])"
mk H_undefined "Command(['xacro ', '$W/undefined.urdf.xacro'])"
mk I_badxml "Command(['xacro ', '$W/badxml.urdf.xacro'])"
mk J_raw_plain "Command(['xacro ', '$W/plain.urdf.xacro'])"
mk K_raw_colon "Command(['xacro ', '$W/colon.urdf.xacro'])"
mk L_raw_hash "Command(['xacro ', '$W/hash.urdf.xacro'])"
mk M_raw_material "Command(['xacro ', '$W/material.urdf.xacro'])"
mk N_pv_colon "ParameterValue(Command(['xacro ', '$W/colon.urdf.xacro']), value_type=str)"
mk O_pv_hash "ParameterValue(Command(['xacro ', '$W/hash.urdf.xacro']), value_type=str)"
mk P_pv_undefined "ParameterValue(Command(['xacro ', '$W/undefined.urdf.xacro']), value_type=str)"
mk Q_python_xacro "xacro.process_file('$W/colon.urdf.xacro').toxml()" "import xacro"
mk R_open_read "open('/tmp/colon.urdf').read()"
mk S_cat_raw "Command(['cat ', '/tmp/colon.urdf'])"
cat > T_xml_raw.launch.xml <<X
<launch><node pkg="robot_state_publisher" exec="robot_state_publisher" output="screen">
  <param name="robot_description" value="\$(command 'xacro $W/colon.urdf.xacro')"/></node></launch>
X
cat > U_xml_typestr.launch.xml <<X
<launch><node pkg="robot_state_publisher" exec="robot_state_publisher" output="screen">
  <param name="robot_description" value="\$(command 'xacro $W/colon.urdf.xacro')" type="str"/></node></launch>
X
cat > V_xml_plain_raw.launch.xml <<X
<launch><node pkg="robot_state_publisher" exec="robot_state_publisher" output="screen">
  <param name="robot_description" value="\$(command 'xacro $W/plain.urdf.xacro')"/></node></launch>
X
for c in D_findexec_ok E_pathjoin_findexec_ok F_nospace G_badpath H_undefined I_badxml J_raw_plain K_raw_colon L_raw_hash M_raw_material N_pv_colon O_pv_hash P_pv_undefined Q_python_xacro R_open_read S_cat_raw; do run $c.launch.py; done
for c in T_xml_raw U_xml_typestr V_xml_plain_raw; do run $c.launch.xml; done
echo "--- Command source: on_stderr option present?"; python3 -c "import inspect,launch.substitutions.command as c; s=inspect.signature(c.Command.__init__); print(s)"
echo "=== done $ROS_DISTRO"
