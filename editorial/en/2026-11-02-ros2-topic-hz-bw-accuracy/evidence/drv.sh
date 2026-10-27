#!/bin/bash
set -m
D=$1; source /opt/ros/$D/setup.bash
echo "## $D nproc $(nproc) $(python3 -c 'import importlib.metadata as m;print("ros2topic", m.version("ros2topic"))' 2>/dev/null)"
cp -r /hz/pkg /tmp/ws_src; mkdir -p /tmp/ws/src; mv /tmp/ws_src /tmp/ws/src/hzbench; cd /tmp/ws
colcon build --event-handlers console_direct- >/tmp/build.log 2>&1 || { tail -20 /tmp/build.log; exit 1; }
source install/setup.bash
for hz in 400 1000 2000 5000 10000; do
  ./install/hzbench/lib/hzbench/pub $hz >/dev/null 2>&1 & p=$!
  sleep 2
  c=$(./install/hzbench/lib/hzbench/count 10)
  h=$(timeout 14 ros2 topic hz /joint_states 2>&1 | grep "average rate" | tail -1)
  b=$(timeout 14 ros2 topic bw /joint_states 2>&1 | grep -E "B/s from" | tail -1)
  h2=$(timeout 14 ros2 topic hz /joint_states -w 2000 2>&1 | grep "average rate" | tail -1)
  kill $p; wait $p 2>/dev/null; sleep 1; echo "    pubs left: $(pgrep -c -f lib/hzbench/pub)"
  echo "[$D target ${hz} Hz] $c"
  echo "    topic hz:          $h"
  echo "    topic hz -w 2000:  $h2"
  echo "    topic bw:          $b"
done
