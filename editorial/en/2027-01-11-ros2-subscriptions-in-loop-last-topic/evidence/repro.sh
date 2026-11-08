#!/bin/bash
# Run inside ros:<distro>-ros-base with --network none, ROS_DOMAIN_ID=88.
# Mount: this folder at /w (read-only), scratch at /ws.
# Host command used (2026-11-08, one distro at a time):
#   docker run --rm --name pk33-<distro> --network none --cpus 1.5 --memory 1500m --pids-limit 200 \
#     --ulimit core=0 -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 (Humble) | -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST (Jazzy, Lyrical) \
#     -v $PWD:/w:ro ros:<distro>-ros-base bash /w/repro.sh > out_<distro>.txt
# Files: loop_subs.py, unsub.py, xproc.py, cppsubs/ (rclcpp package).
set +e
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "### distro $ROS_DISTRO  RMW=${RMW_IMPLEMENTATION:-default}  domain=$ROS_DOMAIN_ID"
echo "### versions"
for p in rclpy rclcpp ros2cli rmw rmw_fastrtps_cpp; do printf '%s ' $p; ros2 pkg xml $p 2>/dev/null | grep -o '<version>[^<]*' | sed 's/<version>//'; done
python3 --version
echo "### rclpy loop variants (3 topics x 20 msgs = 60 sent)"
for v in lambda default_arg kwonly_default partial factory not_stored; do
  echo "--- $v"; timeout 60 python3 /w/loop_subs.py $v 2>&1 | tail -8
done
echo "### rclpy destroy_subscription"
for i in 1 2 3; do echo "--- run $i"; timeout 60 python3 /w/unsub.py 2>&1 | tail -6; done
echo "### cross-process destroy_subscription (pub process watches matched count)"
for i in 1 2 3; do
  echo "--- run $i"
  timeout 30 python3 /w/xproc.py pub > /tmp/pub.txt 2>&1 &
  sleep 3
  timeout 30 python3 /w/xproc.py sub 2>&1 | tee /tmp/sub.txt
  sleep 0.8; echo "ros2 topic info (daemon) ~0.8 s after sub process exit:"; timeout 20 ros2 topic info /xproc_topic 2>&1
  echo "ros2 topic info --no-daemon:"; timeout 20 ros2 topic info /xproc_topic --no-daemon 2>&1
  wait; cat /tmp/pub.txt
done
ros2 daemon stop >/dev/null 2>&1
echo "### rclcpp build"
mkdir -p /ws/src && cp -r /w/cppsubs /ws/src/ && cd /ws
t0=$(date +%s.%N)
MAKEFLAGS=-j1 timeout 900 colcon build --packages-select cppsubs 2>&1 | tail -5
python3 -c "import sys;print('build_s', round(float(sys.argv[1])-float(sys.argv[2]),1))" $(date +%s.%N) $t0
source /ws/install/setup.bash
for v in not_stored stored_loop reset; do
  echo "--- cpp $v"; timeout 60 ros2 run cppsubs subs $v 2>&1 | tail -5
done
for i in 2 3; do echo "--- cpp reset run $i"; timeout 60 ros2 run cppsubs subs reset 2>&1 | tail -3; done
