#!/bin/bash
# Second pass: repeat the 10x sim-clock case 3 times, and show colcon stderr for thr_cpp.
source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
echo "### extra distro=$ROS_DISTRO date=$(date -u +%FT%TZ)"
cp /src/ptest.py /src/clockpub.py /tmp/
mkdir -p /ws/src && cp -r /src/thr_cpp /ws/src/ && cd /ws
MAKEFLAGS=-j1 timeout 600 colcon build --packages-select thr_cpp > /tmp/b.txt 2>&1; echo "thr_cpp build rc=$?"
echo "--- thr_cpp stderr (first 6 lines):"; head -6 /ws/log/latest_build/thr_cpp/stderr.log 2>/dev/null | cut -c1-300
source /ws/install/setup.bash
for r in 1 2 3; do
  python3 /tmp/clockpub.py 0.1 >/dev/null 2>&1 & cp=$!; sleep 2
  timeout 60 python3 /tmp/ptest.py sim_nodeclock > /tmp/o.txt 2>&1
  echo "== rep$r py sim_nodeclock/fast MARK_lines=$(grep -c MARK /tmp/o.txt) $(grep RESULT /tmp/o.txt)"
  timeout 60 ros2 run thr_cpp ctest sim_nodeclock > /tmp/o.txt 2>&1
  echo "== rep$r cpp sim_nodeclock/fast MARK_lines=$(grep -c MARK /tmp/o.txt) $(grep RESULT /tmp/o.txt)"
  kill $cp; wait $cp 2>/dev/null
done
echo "### extra done"
