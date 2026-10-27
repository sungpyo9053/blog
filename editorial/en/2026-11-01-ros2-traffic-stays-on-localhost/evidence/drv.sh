#!/bin/bash
set -m
D=$1; source /opt/ros/$D/setup.bash
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y tcpdump ros-$D-rmw-cyclonedds-cpp >/dev/null 2>&1
echo "## $D $(dpkg -s ros-$D-rmw-fastrtps-cpp 2>/dev/null | grep ^Version | cut -d' ' -f2) cyclone $(dpkg -s ros-$D-rmw-cyclonedds-cpp 2>/dev/null | grep ^Version | cut -d' ' -f2)"
PAY=$(python3 -c "print('x'*1000)")
run(){ label=$1; shift
  ( env "$@" bash -c "source /opt/ros/$D/setup.bash; ros2 daemon stop >/dev/null 2>&1; timeout 16 ros2 topic pub -r 50 /chatter std_msgs/msg/String \"{data: $PAY}\" >/dev/null 2>/tmp/pub.err" ) &
  sleep 3
  st(){ cat /sys/class/net/$1/statistics/tx_packets /sys/class/net/$1/statistics/tx_bytes | tr '\n' ' '; }
  e0=($(st eth0)); l0=($(st lo))
  hz=$(env "$@" bash -c "source /opt/ros/$D/setup.bash; timeout 10 ros2 topic hz /chatter 2>&1" | grep -m1 -o "average rate: [0-9.]*" | tail -1)
  e1=($(st eth0)); l1=($(st lo))
  tl=$(env "$@" bash -c "source /opt/ros/$D/setup.bash; timeout 8 ros2 topic list 2>&1" | grep -c "^/chatter")
  ep=$((e1[0]-e0[0])); eb=$((e1[1]-e0[1])); lp=$((l1[0]-l0[0])); lb=$((l1[1]-l0[1]))
  warn=$(grep -m1 -o "not multicast-capable[^\"]*" /tmp/pub.err)
  wait
  echo "[$label] sub ${hz:-NO DATA} | eth0 tx $ep pkts $eb B | lo tx $lp pkts $lb B (10s) | topic list sees /chatter: $tl ${warn:+| warn: $warn}"
  ros2 daemon stop >/dev/null 2>&1; sleep 1; }
F=RMW_IMPLEMENTATION=rmw_fastrtps_cpp; C=RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
run fastdds_default $F
run fastdds_LOCALHOST_ONLY $F ROS_LOCALHOST_ONLY=1
run cyclone_default $C
run cyclone_LOCALHOST_ONLY $C ROS_LOCALHOST_ONLY=1
if [ $D != humble ]; then
run fastdds_RANGE_LOCALHOST $F ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
run cyclone_RANGE_LOCALHOST $C ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
fi
