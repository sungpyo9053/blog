#!/bin/bash
# Reproduces "Could not contact service /controller_manager/..." from the ros2_control
# spawner and the ros2 control CLI, without Gazebo, using mock_components/GenericSystem.
#   phase 1 (network on):  repro.sh install   -> apt installs, then the container is committed
#   phase 2 (--network none, ROS_DOMAIN_ID=88): repro.sh run

D=$ROS_DISTRO
if [ "${1:-}" = install ]; then
  apt-get update -qq >/dev/null
  apt-get install -y -qq ros-$D-controller-manager ros-$D-ros2controlcli \
    ros-$D-joint-state-broadcaster ros-$D-robot-state-publisher >/tmp/apt.log 2>&1
  echo "apt exit $?"; tail -3 /tmp/apt.log; exit 0
fi
source /opt/ros/$D/setup.bash
ulimit -c 0
echo "=== distro=$D ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-controller-manager ros-$D-ros2controlcli \
  ros-$D-hardware-interface ros-$D-joint-state-broadcaster ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli \
  ros-$D-rmw-fastrtps-cpp ros-$D-robot-state-publisher 2>/dev/null
echo "RMW=${RMW_IMPLEMENTATION:-default}"
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
sed 's#mock_components/GenericSystem#my_hw/DoesNotExist#' $T/robot.urdf > $T/bad_plugin.urdf
# controllers yaml for a controller manager with fully qualified name $1
cy(){ printf '%s:\n  ros__parameters:\n    update_rate: 50\n    joint_state_broadcaster:\n      type: joint_state_broadcaster/JointStateBroadcaster\n    jsb2:\n      type: joint_state_broadcaster/JointStateBroadcaster\n' "$1"; }
cy /controller_manager > $T/ctl.yaml
cy /abc/controller_manager > $T/ctl_abc.yaml
cy /my_cm > $T/ctl_mycm.yaml
printf '/controller_manager:\n  ros__parameters:\n    update_rate: 50\n' > $T/ctl_notype.yaml
printf 'jsb2:\n  ros__parameters:\n    type: joint_state_broadcaster/JointStateBroadcaster\n' > $T/ctl_ctrlkey.yaml
python3 - <<'X'
u=open('/t/robot.urdf').read()
open('/t/rd_param.yaml','w').write('/controller_manager:\n  ros__parameters:\n    robot_description: |\n'+''.join('      '+l+'\n' for l in u.splitlines()))
X
now(){ date +%s.%N; }
el(){ python3 -c "print(f'{$2-$1:.2f}')"; }
PIDS=()
bg(){ "$@" > $T/bg_$((${#PIDS[@]})).log 2>&1 & PIDS+=($!); }
stopall(){ for p in "${PIDS[@]}"; do kill -INT $p 2>/dev/null; done; sleep 2; for p in "${PIDS[@]}"; do kill -9 $p 2>/dev/null; done
  pkill -9 -f ros2_control_node 2>/dev/null; pkill -9 -f robot_state_publisher 2>/dev/null; pkill -9 -f spawner 2>/dev/null; PIDS=(); sleep 1; }
showbg(){ for f in $T/bg_*.log; do echo "--- $(basename $f)"; grep -v '^\s*$' $f | cut -c1-260 | head -${1:-12}; echo "  [errors in this log:]"; grep -E 'ERROR|FATAL|rror' $f | cut -c1-400 | head -4; done; rm -f $T/bg_*.log; }
rsp(){ bg ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat ${1:-$T/robot.urdf})" "${@:2}"; }
# remap the manager's ~/robot_description subscription to robot_description (relative, so it follows a namespace)
cm(){ bg ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' "$@"; }
cm_noremap(){ bg ros2 run controller_manager ros2_control_node --ros-args "$@"; }
ros2 daemon start; sleep 3
# run a command, print its output, exit code and elapsed seconds
run(){ local t0=$(now); timeout ${RT:-60} "$@" > $T/out.log 2>&1; local rc=$?; local t1=$(now)
  grep -v '^\s*$' $T/out.log | grep -v '^  File \|^    ' | cut -c1-260 > $T/o2.log
  if [ $(wc -l < $T/o2.log) -gt 14 ]; then head -9 $T/o2.log; echo "[... $(wc -l < $T/o2.log) lines total ...]"; tail -4 $T/o2.log; else cat $T/o2.log; fi
  echo "EXIT=$rc ELAPSED=$(el $t0 $t1)s"; }
SP="ros2 run controller_manager spawner"
case_(){ echo; echo "##### CASE $1"; }

case_ "1 no controller manager running, spawner default timeout (killed after 35 s)"
RT=35 run $SP joint_state_broadcaster
case_ "1b no controller manager, spawner --controller-manager-timeout 3"
run $SP joint_state_broadcaster --controller-manager-timeout 3
case_ "1c no controller manager, ros2 control load_controller (killed after 35 s)"
RT=35 run ros2 control load_controller joint_state_broadcaster
case_ "1d no controller manager, ros2 control list_controllers"
run ros2 control list_controllers

case_ "2 robot_state_publisher + ros2_control_node + ctl.yaml, NO remap of ~/robot_description"
rsp; cm_noremap --params-file $T/ctl.yaml; sleep 4
run ros2 topic list --no-daemon
run $SP joint_state_broadcaster --controller-manager-timeout 10
stopall; showbg 10
case_ "2b baseline: same with -r ~/robot_description:=robot_description"
rsp; cm --params-file $T/ctl.yaml; sleep 4
run $SP joint_state_broadcaster --controller-manager-timeout 10
run ros2 control list_controllers
stopall; showbg 14

case_ "3 robot_description only as a controller_manager parameter, no robot_state_publisher"
cm --params-file $T/ctl.yaml --params-file $T/rd_param.yaml; sleep 4
run bash -c "ros2 daemon stop >/dev/null; ros2 daemon start >/dev/null; sleep 4; ros2 service list | grep -E 'controller_manager/(list|load)_controllers?$'; echo services_total=\$(ros2 service list | wc -l)"
run $SP joint_state_broadcaster --controller-manager-timeout 10
stopall; showbg 10

case_ "4 ros2_control_node without any robot_description (no rsp, no param)"
cm --params-file $T/ctl.yaml; sleep 4
run ros2 node list --no-daemon
run bash -c "ros2 daemon stop >/dev/null; ros2 daemon start >/dev/null; sleep 4; ros2 service list | grep -E 'controller_manager/(list|load)_controllers?$'; echo services_total=\$(ros2 service list | wc -l)"
run $SP joint_state_broadcaster --controller-manager-timeout 10
stopall; showbg 10

case_ "5 controller manager in namespace /abc, spawner without -c"
rsp $T/robot.urdf -r __ns:=/abc
cm -r __ns:=/abc --params-file $T/ctl_abc.yaml; sleep 4
run ros2 node list --no-daemon
run $SP joint_state_broadcaster --controller-manager-timeout 5
case_ "5b same, spawner with --ros-args -r __ns:=/abc (no -c)"
run $SP joint_state_broadcaster --controller-manager-timeout 5 --ros-args -r __ns:=/abc
case_ "5c same, spawner -c /abc/controller_manager (second controller jsb2)"
run $SP jsb2 -c /abc/controller_manager --controller-manager-timeout 5
case_ "5d same, ros2 control list_controllers -c /abc/controller_manager"
run ros2 control list_controllers -c /abc/controller_manager
stopall; showbg 10

case_ "6 controller manager renamed with -r __node:=my_cm"
rsp; cm -r __node:=my_cm --params-file $T/ctl_mycm.yaml; sleep 4
run $SP joint_state_broadcaster --controller-manager-timeout 5
case_ "6b same, spawner -c my_cm"
run $SP joint_state_broadcaster -c my_cm --controller-manager-timeout 5
stopall; showbg 10

case_ "7 spawner started first, controller manager starts 5 s later (default timeout)"
rsp
( sleep 5; ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' --params-file $T/ctl.yaml > $T/bg_late.log 2>&1 ) & PIDS+=($!)
run $SP joint_state_broadcaster
stopall; showbg 8
case_ "7b controller manager starts 15 s later (default timeout)"
rsp
( sleep 15; ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' --params-file $T/ctl.yaml > $T/bg_late.log 2>&1 ) & PIDS+=($!)
run $SP joint_state_broadcaster
stopall; showbg 8
case_ "7c controller manager starts 15 s later, --controller-manager-timeout 30"
rsp
( sleep 15; ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' --params-file $T/ctl.yaml > $T/bg_late.log 2>&1 ) & PIDS+=($!)
run $SP joint_state_broadcaster --controller-manager-timeout 30
stopall; showbg 8

case_ "8 hardware plugin that does not exist in the URDF"
rsp $T/bad_plugin.urdf; cm --params-file $T/ctl.yaml; sleep 5
run ros2 node list --no-daemon
run bash -c "ros2 daemon stop >/dev/null; ros2 daemon start >/dev/null; sleep 4; ros2 service list | grep -E 'controller_manager/(list|load)_controllers?$'; echo services_total=\$(ros2 service list | wc -l)"
run $SP joint_state_broadcaster --controller-manager-timeout 5
stopall; showbg 14

case_ "9 spawner on another ROS_DOMAIN_ID (89) than the controller manager (88)"
rsp; cm --params-file $T/ctl.yaml; sleep 4
ROS_DOMAIN_ID=89 run $SP joint_state_broadcaster --controller-manager-timeout 5
ROS_DOMAIN_ID=89 ros2 daemon stop >/dev/null 2>&1
case_ "9b same domain (88) again"
run $SP joint_state_broadcaster --controller-manager-timeout 5
stopall; showbg 6

case_ "10 controller type missing from the yaml"
rsp; cm --params-file $T/ctl_notype.yaml; sleep 4
run $SP joint_state_broadcaster --controller-manager-timeout 5
stopall; showbg 8

case_ "11 controllers yaml passed to the spawner with --param-file, not to the manager"
rsp; cm; sleep 4
run $SP joint_state_broadcaster --param-file $T/ctl.yaml --controller-manager-timeout 5
case_ "11b same, plus -t joint_state_broadcaster/JointStateBroadcaster"
run $SP joint_state_broadcaster --param-file $T/ctl.yaml -t joint_state_broadcaster/JointStateBroadcaster --controller-manager-timeout 5
case_ "11c spawner --param-file with a controller-keyed file (joint_state_broadcaster: ros__parameters: type: ...)"
run $SP jsb2 --param-file $T/ctl_ctrlkey.yaml --controller-manager-timeout 5
stopall; showbg 8

case_ "12 use_sim_time:=true with no /clock publisher"
rsp; cm --params-file $T/ctl.yaml -p use_sim_time:=true; sleep 4
run $SP joint_state_broadcaster --controller-manager-timeout 5
run ros2 control list_controllers
stopall; showbg 8

case_ "12b list_controllers service called directly while the manager waits for robot_description"
cm --params-file $T/ctl.yaml; sleep 4
RT=15 run ros2 service call /controller_manager/list_controllers controller_manager_msgs/srv/ListControllers
stopall; showbg 4
case_ "13 where the spawner prints the message"
grep -rn -B3 -A3 'Could not contact service' $(python3 -c 'import controller_manager,os;print(os.path.dirname(controller_manager.__file__))') | cut -c1-200 | head -40
case_ "13b spawner help: options"
timeout 30 ros2 run controller_manager spawner -h 2>&1 | grep -E -- '--controller-manager|-c |--param-file|--service-call-timeout|--switch-timeout|--unload|--inactive|--activate|--controller-ros' | cut -c1-200
ros2 daemon stop >/dev/null 2>&1
echo "=== done $D"
