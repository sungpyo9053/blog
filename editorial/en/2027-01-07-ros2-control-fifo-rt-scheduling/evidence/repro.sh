#!/bin/bash
# Reproduces the ros2_control warning
#   "Could not enable FIFO RT scheduling policy: with error number <1>(Operation not permitted)"
# in Docker, and tests which docker run flags remove it, using mock_components/GenericSystem.
#
#   host side:       repro.sh host <humble|jazzy|lyrical>   (runs on the runner, one distro at a time)
#   inside container: repro.sh in <case label>              (called by the host side)
#
# Every test container runs with --network none and ROS_DOMAIN_ID=88 (+ localhost-only discovery).

W=/tmp/en-pick39

if [ "${1:-}" = host ]; then
  D=$2; IMG=ros:$D-ros-base; LOC=pk29-$D:inst
  if [ "$D" = humble ]; then LOCALENV="-e ROS_LOCALHOST_ONLY=1"; else LOCALENV="-e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"; fi
  echo "=== host $(hostname) kernel $(uname -r) date $(date -Is)"
  echo "host sched_rt_runtime_us=$(cat /proc/sys/kernel/sched_rt_runtime_us) cgroup=$(stat -fc %T /sys/fs/cgroup) realtime_flag=$(cat /sys/kernel/realtime 2>/dev/null || echo absent)"
  docker image inspect $IMG --format "image $IMG {{index .RepoDigests 0}} created {{.Created}}"
  # phase 1: apt install with network, then commit
  docker rm -f pk29-$D-install >/dev/null 2>&1
  timeout 900 docker run --name pk29-$D-install $IMG bash -c \
    "apt-get update -qq >/dev/null && apt-get install -y -qq ros-$D-controller-manager ros-$D-ros2controlcli ros-$D-joint-state-broadcaster ros-$D-robot-state-publisher >/tmp/apt.log 2>&1; echo apt exit \$?; tail -2 /tmp/apt.log"
  docker commit pk29-$D-install $LOC >/dev/null && docker rm pk29-$D-install >/dev/null
  echo "committed $LOC"
  run(){ local label=$1; shift
    while [ "$(cut -d' ' -f1 /proc/loadavg | cut -d. -f1)" -ge 3 ]; do echo "load $(cut -d' ' -f1 /proc/loadavg), waiting"; sleep 20; done
    echo; echo "##### CASE $label"; echo "docker flags: $*"; echo "load before: $(cut -d' ' -f1-3 /proc/loadavg)"
    timeout 120 docker run --rm --name pk29-$D-c --network none --pids-limit 200 --ulimit core=0 \
      -e ROS_DOMAIN_ID=88 $LOCALENV -e ROS_LOG_DIR=/tmp/roslog -e HOME=/tmp -e CMARGS="${CMARGS:-}" \
      -v $W:/w:ro "$@" $LOC bash /w/repro.sh in "$label" 2>&1
    echo "docker exit $?"
  }
  run "1 default (root, no extra flags)"
  run "2 --cap-add SYS_NICE" --cap-add SYS_NICE
  run "3 --ulimit rtprio=99 (root, no capability)" --ulimit rtprio=99
  run "4 --cap-add SYS_ADMIN" --cap-add SYS_ADMIN
  run "5 --privileged" --privileged
  run "6 non-root --user 1000:1000" --user 1000:1000
  run "7 non-root + --ulimit rtprio=99" --user 1000:1000 --ulimit rtprio=99
  run "8 non-root + --cap-add SYS_NICE" --user 1000:1000 --cap-add SYS_NICE
  run "9 --ulimit rtprio=40, default priority" --ulimit rtprio=40
  CMARGS="-p thread_priority:=40" run "10 --ulimit rtprio=40 + -p thread_priority:=40" --ulimit rtprio=40
  run "11 --cap-add SYS_NICE --ulimit memlock=-1" --cap-add SYS_NICE --ulimit memlock=-1
  CMARGS="-p lock_memory:=false" run "12 --cap-add SYS_NICE + -p lock_memory:=false" --cap-add SYS_NICE
  echo; echo "##### CASE 13 docker --cpu-rt-runtime=950000 (cgroup v2 host)"
  timeout 60 docker run --rm --name pk29-$D-rt --network none --cpu-rt-runtime=950000 --cap-add SYS_NICE $LOC true 2>&1 | cut -c1-300
  echo "docker exit ${PIPESTATUS[0]}"
  docker rm -f pk29-$D-c pk29-$D-rt >/dev/null 2>&1
  exit 0
fi

# ---------------- inside the container ----------------
D=$ROS_DISTRO
source /opt/ros/$D/setup.bash
ulimit -c 0
echo "uid=$(id -u) ulimit_r(rtprio)=$(ulimit -r) ulimit_l(memlock)=$(ulimit -l) CapEff=$(grep CapEff /proc/self/status | awk '{print $2}') realtime_flag=$(cat /sys/kernel/realtime 2>/dev/null || echo absent)"
if [ "${2:-}" = "1 default (root, no extra flags)" ]; then
  dpkg-query -W -f='${Package} ${Version}\n' ros-$D-controller-manager ros-$D-hardware-interface ros-$D-realtime-tools \
    ros-$D-joint-state-broadcaster ros-$D-rclcpp ros-$D-rclpy ros-$D-ros2cli ros-$D-rmw-fastrtps-cpp 2>/dev/null
  echo "RMW=${RMW_IMPLEMENTATION:-default}"
fi
T=/tmp/t; mkdir -p $T /tmp/roslog
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
printf '/controller_manager:\n  ros__parameters:\n    update_rate: 100\n    joint_state_broadcaster:\n      type: joint_state_broadcaster/JointStateBroadcaster\n' > $T/ctl.yaml
ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="$(cat $T/robot.urdf)" > $T/rsp.log 2>&1 &
ros2 run controller_manager ros2_control_node --ros-args -r '~/robot_description:=robot_description' \
  --params-file $T/ctl.yaml $CMARGS > $T/cm.log 2>&1 &
sleep 6
CM=$(pgrep -f 'lib/controller_manager/ros2_control_node' | head -1)
echo "--- controller manager log (first 25 lines)"
grep -v '^\s*$' $T/cm.log | sed -E 's/\[[0-9]+\.[0-9]+\]/[t]/' | cut -c1-330 | head -25
echo "--- threads of ros2_control_node pid=$CM (policy/priority from chrt)"
if [ -n "$CM" ]; then
  for t in /proc/$CM/task/*; do tid=${t##*/}; echo "$(cat $t/comm) $(chrt -p $tid 2>&1 | tr '\n' ' ')"; done \
    | sed -E 's/pid [0-9]+.s //g' | sort | uniq -c | sed 's/^ */  /'
  echo "VmLck: $(grep VmLck /proc/$CM/status | awk '{print $2, $3}')"
else echo "ros2_control_node not running"; fi
echo "--- spawner joint_state_broadcaster"
timeout 30 ros2 run controller_manager spawner joint_state_broadcaster --controller-manager-timeout 15 > $T/sp.log 2>&1; echo "spawner exit $?"
grep -v '^\s*$' $T/sp.log | sed -E 's/\[[0-9]+\.[0-9]+\]/[t]/' | cut -c1-200 | tail -2
timeout 15 ros2 topic echo --once /joint_states sensor_msgs/msg/JointState > $T/js.log 2>&1; echo "joint_states echo exit $? $(grep -c 'name:' $T/js.log) msg"
timeout -s INT 9 ros2 topic hz /joint_states --window 50 > $T/hz.log 2>&1
grep 'average rate' $T/hz.log | tail -1
echo "--- WARN/ERROR lines in controller manager log after spawn"
grep -E 'WARN|ERROR' $T/cm.log | sed -E 's/\[[0-9]+\.[0-9]+\]/[t]/' | cut -c1-330 | sort | uniq -c | head -10
pkill -INT -f ros2_control_node; pkill -INT -f robot_state_publisher; sleep 2
pkill -9 -f ros2_control_node 2>/dev/null; pkill -9 -f robot_state_publisher 2>/dev/null; true
