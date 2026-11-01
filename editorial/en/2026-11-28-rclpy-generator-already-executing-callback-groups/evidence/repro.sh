#!/bin/bash
# Run inside ros:<distro>-ros-base with cbg.py at /e/cbg.py:
#   docker run --rm --ulimit core=0 --pids-limit 128 -v $PWD:/e ros:humble-ros-base bash /e/repro.sh
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-std-srvs 2>/dev/null
python3 --version; echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"
P=/e/cbg.py
python3 $P server & SRV=$!
sleep 2
run() { echo; echo "--- $*"; timeout 20 python3 $P "$@" 2>&1; echo "exit=$?"; }
echo; echo "##### 1+4: timer callback calls a service (server in another process)"
for ex in ste mte4; do for g in default sep reentrant; do run svc $ex $g call; done; done
run svc ste default call_timeout
run svc mte4 default call_timeout
for ex in ste mte4; do run svc $ex default async_cb; for g in default sep reentrant; do run svc $ex $g await; done; done
echo; echo "##### 2: nested spinning inside a callback"
for v in spin_once_ste spin_once_mte4 spin_once_none_ste spin_once_none_mte4 sufc_same_ste sufc_same_mte4 sufc_global_ste sufc_global_mte4 thread_global thread_spin_once thread_spin_once_none thread_sufc two_spin; do run gen $v; done
echo; echo "##### 3: 10 Hz timer + callback that sleeps 1 s every 2 s"
run slow ste same
for ex in mte1 mte4; do for g in same sep reentrant; do run slow $ex $g; done; done
kill $SRV; wait $SRV 2>/dev/null
echo "=== done"
