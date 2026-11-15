#!/bin/bash
# "Failed loading controller" from the ros2_control spawner: what the controller manager
# logs for each cause, and which fixes work. No Gazebo: mock_components/GenericSystem.
#   repro.sh install  -> apt installs (container on the default bridge network)
#   repro.sh run      -> tests, ROS_DOMAIN_ID=88 + localhost-only discovery
D=$ROS_DISTRO
if [ "${1:-}" = install ]; then
  apt-get update -qq >/dev/null
  apt-get install -y -qq ros-$D-controller-manager ros-$D-ros2controlcli ros-$D-joint-state-broadcaster \
    ros-$D-forward-command-controller ros-$D-robot-state-publisher >/tmp/apt.log 2>&1
  echo "apt exit $?"; tail -2 /tmp/apt.log; exit 0
fi
source /opt/ros/$D/setup.bash
ulimit -c 0
echo "=== distro=$D ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-controller-manager ros-$D-ros2controlcli ros-$D-hardware-interface \
  ros-$D-joint-state-broadcaster ros-$D-forward-command-controller ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli \
  ros-$D-rmw-fastrtps-cpp 2>/dev/null
dpkg -l | grep -c "ros-$D-diff-drive-controller" | sed 's/^/diff_drive_controller installed packages: /'
T=/t; mkdir -p $T
cat > $T/robot.urdf <<'X'
<?xml version="1.0"?>
<robot name="r">
  <link name="base"/><link name="l1"/>
  <joint name="j1" type="revolute"><parent link="base"/><child link="l1"/>
    <limit lower="-1" upper="1" effort="1" velocity="1"/></joint>
  <ros2_control name="sys" type="system">
    <hardware><plugin>mock_components/GenericSystem</plugin></hardware>
    <joint name="j1"><command_interface name="position"/><state_interface name="position"/></joint>
  </ros2_control>
</robot>
X
cat > $T/ctl.yaml <<'X'
/controller_manager:
  ros__parameters:
    update_rate: 50
    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster
    fwd:
      type: forward_command_controller/ForwardCommandController
    typo_ctrl:
      type: joint_state_broadcaster/JointStateBroadcast
    ddc:
      type: diff_drive_controller/DiffDriveController
    fwd_nojoints:
      type: forward_command_controller/ForwardCommandController
    fwd_badjoint:
      type: forward_command_controller/ForwardCommandController
fwd:
  ros__parameters:
    joints: [j1]
    interface_name: position
fwd_nojoints:
  ros__parameters:
    interface_name: position
fwd_badjoint:
  ros__parameters:
    joints: [j9]
    interface_name: position
jsb_owntype:
  ros__parameters:
    type: joint_state_broadcaster/JointStateBroadcaster
X
sed 's#^/controller_manager:#/controller_manger:#' $T/ctl.yaml > $T/ctl_topkey_typo.yaml
sed 's#^/controller_manager:#controller_manager:#' $T/ctl.yaml > $T/ctl_noslash.yaml
printf '/controller_manager:\n  ros__parameters:\n    update_rate: 50\n    jsb_emptypf:\n      type: joint_state_broadcaster/JointStateBroadcaster\n      params_file: ""\n' > $T/ctl_emptypf.yaml
printf '/controller_manager:\n  ros__parameters:\n    update_rate: 50\n    jsb_badpf:\n      type: joint_state_broadcaster/JointStateBroadcaster\n      params_file: "/nonexistent/ctl.yaml"\n' > $T/ctl_badpf.yaml
printf 'jsb_pf:\n  ros__parameters:\n    type: joint_state_broadcaster/JointStateBroadcaster\n' > $T/spawner_pf.yaml
now(){ date +%s.%N; }
el(){ python3 -c "print(f'{$2-$1:.2f}')"; }
CMLOG=$T/cm.log
start(){ # $1 = cm params file or "none"
  ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat $T/robot.urdf)" > $T/rsp.log 2>&1 &
  if [ "$1" = none ]; then
    ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' > $CMLOG 2>&1 &
  else
    ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' --params-file "$1" > $CMLOG 2>&1 &
  fi
  sleep 5; echo "[cm started with ${1##*/}; cm log lines: $(wc -l < $CMLOG)]"; grep -E 'ERROR|FATAL|rror' $CMLOG | cut -c1-300 | head -5; }
stop(){ pkill -INT -f ros2_control_node; pkill -INT -f robot_state_publisher; sleep 2
  pkill -9 -f ros2_control_node; pkill -9 -f robot_state_publisher; pkill -9 -f spawner; sleep 1; }
# run a command; print its output (trimmed), exit code, elapsed; then the NEW manager log lines
run(){ local n0=$(wc -l < $CMLOG); local t0=$(now); timeout ${RT:-60} "$@" > $T/out.log 2>&1; local rc=$?; local t1=$(now)
  grep -v '^\s*$' $T/out.log | cut -c1-300 > $T/o2.log
  if [ $(wc -l < $T/o2.log) -gt 16 ]; then head -10 $T/o2.log; echo "[... $(wc -l < $T/o2.log) lines total ...]"; tail -5 $T/o2.log; else cat $T/o2.log; fi
  echo "EXIT=$rc ELAPSED=$(el $t0 $t1)s"; sleep 0.5
  echo "  [controller manager log, new lines:]"; tail -n +$((n0+1)) $CMLOG | grep -v '^\s*$' | sed 's/^\[[A-Z]*\] \[[0-9.]*\] //' | cut -c1-400 | head -${CML:-14}; }
SP="ros2 run controller_manager spawner"
case_(){ echo; echo "##### CASE $1"; }
ros2 daemon start >/dev/null 2>&1; sleep 2

if [ "${1:-}" = run2 ]; then  # second pass: does passing the same file to the spawner fix it everywhere?
case_ "20 manager startup log with ctl.yaml (full)"
start $T/ctl.yaml; grep -v '^\s*$' $CMLOG | sed 's/^\[[A-Z]*\] \[[0-9.]*\] //' | cut -c1-300
case_ "21 spawner fwd --param-file ctl.yaml"
run $SP fwd --param-file $T/ctl.yaml
case_ "22 spawner fwd_badjoint --param-file ctl.yaml"
CML=20 run $SP fwd_badjoint --param-file $T/ctl.yaml
case_ "23 spawner fwd_nojoints --param-file ctl.yaml"
run $SP fwd_nojoints --param-file $T/ctl.yaml
case_ "24 spawner joint_state_broadcaster --param-file ctl.yaml"
run $SP joint_state_broadcaster --param-file $T/ctl.yaml
case_ "25 list_controllers"
CML=2 run ros2 control list_controllers
stop
case_ "26 manager without params file, spawner fwd --param-file with a controller-keyed file holding type + joints"
printf 'fwd:\n  ros__parameters:\n    type: forward_command_controller/ForwardCommandController\n    joints: [j1]\n    interface_name: position\n' > $T/fwd_only.yaml
start none
run $SP fwd --param-file $T/fwd_only.yaml
stop
ros2 daemon stop >/dev/null 2>&1; echo "=== done run2 $D"; exit 0
fi

start $T/ctl.yaml
case_ "1 baseline: spawner joint_state_broadcaster (type in yaml)"
run $SP joint_state_broadcaster
case_ "1b baseline: spawner fwd (forward_command_controller, joints [j1])"
run $SP fwd
case_ "2 spawner name typo: joint_state_broadcastr (not in yaml)"
run $SP joint_state_broadcastr
case_ "3 type only under the controller's own section (jsb_owntype: ros__parameters: type:)"
run $SP jsb_owntype
case_ "4 type string typo: joint_state_broadcaster/JointStateBroadcast"
CML=30 run $SP typo_ctrl
case_ "5 type from a package that is not installed: diff_drive_controller/DiffDriveController"
CML=6 run $SP ddc
case_ "5b ros2 control load_controller ddc"
CML=4 run ros2 control load_controller ddc
case_ "5c ros2 control list_controller_types"
CML=2 run bash -c "ros2 control list_controller_types | head -30; echo types_total=\$(ros2 control list_controller_types | wc -l)"
case_ "6 forward_command_controller with no joints parameter"
run $SP fwd_nojoints
case_ "7 forward_command_controller with joint j9 that is not in the URDF"
run $SP fwd_badjoint
case_ "8 spawner joint_state_broadcaster again (already loaded and active)"
run $SP joint_state_broadcaster
case_ "8b ros2 control list_controllers"
CML=2 run ros2 control list_controllers
case_ "9 fix: spawner -t with a name not in the yaml (jsb_new -t joint_state_broadcaster/JointStateBroadcaster)"
run $SP jsb_new -t joint_state_broadcaster/JointStateBroadcaster
case_ "9b fix: spawner --param-file with the type in a controller-keyed file (jsb_pf)"
run $SP jsb_pf --param-file $T/spawner_pf.yaml
case_ "9c ros2 control list_controllers after the fixes"
CML=2 run ros2 control list_controllers
stop

case_ "10 manager yaml top key typo (/controller_manger:)"
start $T/ctl_topkey_typo.yaml
run $SP joint_state_broadcaster
stop
case_ "10b manager yaml top key without leading slash (controller_manager:)"
start $T/ctl_noslash.yaml
run $SP joint_state_broadcaster
stop
case_ "11 manager started without any params file"
start none
run $SP joint_state_broadcaster
case_ "11b same manager, spawner --param-file ctl.yaml (the manager-keyed file) "
run $SP joint_state_broadcaster --param-file $T/ctl.yaml
stop
case_ "12 controller params_file set to an empty string"
start $T/ctl_emptypf.yaml
run $SP jsb_emptypf
stop
case_ "12b controller params_file set to a path that does not exist"
start $T/ctl_badpf.yaml
run $SP jsb_badpf
stop
case_ "13 spawner help: options"
timeout 30 ros2 run controller_manager spawner -h 2>&1 | grep -E -- '-t |--controller-type|--param-file|--inactive|--load-only|-c ' | cut -c1-200
case_ "13b where the spawner prints Failed loading controller"
grep -rn -B4 'Failed loading controller' $(python3 -c 'import controller_manager,os;print(os.path.dirname(controller_manager.__file__))') | cut -c1-200 | head -30
ros2 daemon stop >/dev/null 2>&1
echo "=== done $D"
