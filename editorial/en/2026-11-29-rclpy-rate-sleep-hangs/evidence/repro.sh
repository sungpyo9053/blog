#!/bin/bash
# Run inside ros:<distro>-ros-base with rate.py at /e/rate.py:
#   docker run --rm --name rte-<distro> --ulimit core=0 --pids-limit 64 --cpus 1.5 -v $PWD:/e ros:<distro>-ros-base bash /e/repro.sh
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rosgraph-msgs 2>/dev/null
python3 --version; echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"; nproc
P=/e/rate.py
run() { echo; echo "--- $*"; timeout -s KILL 40 python3 $P "$@" 2>&1; echo "exit=$?"; }
echo; echo "##### 0: API info"; run info
echo; echo "##### 1: rate.sleep with no executor spinning"
run nospin 10; run nospin 100; run nospin_spinonce 10
echo; echo "##### 2: period and jitter, 200 iterations"
for hz in 10 100; do run rate_ste $hz 200; run rate_mte $hz 200; run timer $hz 200; run timesleep $hz 200; run sleep_for $hz 200; run sleep_until $hz 200; done
echo; echo "##### 1b: rate.sleep inside a callback"
run incb_ste; run incb_mte; run incb_mte_reentrant
echo; echo "##### 3: use_sim_time=true, no /clock, then /clock"
run simtime rate; run simtime timer; run simtime sleep_for
echo; echo "##### 4: destroy / shutdown while blocked in rate.sleep (0.2 Hz)"
for s in nospin spin; do for w in rate node shutdown; do run destroy $w $s; done; done
echo; echo "##### 4b: SIGINT while main thread is blocked in rate.sleep"
run sigint nospin; run sigint spin
echo; echo "##### 4c: SIGINT with a daemon spin thread, repeated 10 times"
for i in $(seq 1 10); do run sigint spin; done
echo "=== done"
