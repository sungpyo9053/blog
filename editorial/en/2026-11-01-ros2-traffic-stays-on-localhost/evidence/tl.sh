#!/bin/bash
set -m
D=$1; source /opt/ros/$D/setup.bash; export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
for cfg in "" "ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST" "ROS_LOCALHOST_ONLY=1"; do
 r=""
 for i in 1 2 3; do
  ros2 daemon stop >/dev/null 2>&1
  ( env $cfg bash -c "source /opt/ros/$D/setup.bash; timeout 20 ros2 topic pub -r 10 /chatter std_msgs/msg/String '{data: x}' >/dev/null 2>&1" ) &
  sleep 3
  a=$(env $cfg bash -c "source /opt/ros/$D/setup.bash; timeout 10 ros2 topic list 2>&1" | grep -c '^/chatter')
  b=$(env $cfg bash -c "source /opt/ros/$D/setup.bash; timeout 10 ros2 topic list --no-daemon 2>&1" | grep -c '^/chatter')
  c=$(env $cfg bash -c "source /opt/ros/$D/setup.bash; sleep 3; timeout 10 ros2 topic list 2>&1" | grep -c '^/chatter')
  r="$r daemon=$a,no-daemon=$b,daemon+3s=$c;"; wait
 done
 echo "[$D fastdds ${cfg:-default}]$r"
done
