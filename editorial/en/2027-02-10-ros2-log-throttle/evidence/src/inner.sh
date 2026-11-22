#!/bin/bash
# Runs inside ros:<distro>-ros-base. /src mounted read-only.
source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
echo "### distro=$ROS_DISTRO date=$(date -u +%FT%TZ)"
echo "### versions"
dpkg-query -W -f '${Package} ${Version}\n' "ros-$ROS_DISTRO-rclpy" "ros-$ROS_DISTRO-rclcpp" "ros-$ROS_DISTRO-ros2cli" "ros-$ROS_DISTRO-rmw" "ros-$ROS_DISTRO-rcutils" "ros-$ROS_DISTRO-rcl" "ros-$ROS_DISTRO-rmw-implementation" 2>&1
python3 --version; g++ --version | head -1
python3 - <<'PY'
import inspect
from rclpy.impl.rcutils_logger import RcutilsLogger
print('### rclpy RcutilsLogger.log signature:', inspect.signature(RcutilsLogger.log))
try:
    from rclpy.impl import logging_rosout  # noqa
except Exception:
    pass
import rclpy.impl.rcutils_logger as m
print('### supported_filters:', list(getattr(m, 'supported_filters', {}).keys()))
src = inspect.getsource(m)
for line in src.splitlines():
    if 'raise ValueError' in line or 'cannot be changed' in line or 'throttle_time_source_type' in line:
        print('### src:', line.strip())
PY
grep -n "define RCUTILS_LOG_CONDITION_THROTTLE_BEFORE" -A 14 /opt/ros/$ROS_DISTRO/include/rcutils/rcutils/logging_macros.h 2>/dev/null | grep -nE "static|last_logged|duration" | head -8
echo "### python cases"
cp /src/ptest.py /src/clockpub.py /tmp/
pycase() { # $1 case $2 clock mode
  local tag="$1"; [ -n "$2" ] && tag="$1/$2"
  local cp=""
  if [ "$2" = fast ]; then python3 /tmp/clockpub.py 0.1 >/dev/null 2>&1 & cp=$!; sleep 2; fi
  timeout 60 python3 /tmp/ptest.py "$1" > /tmp/o.txt 2>&1; local rc=$?
  [ -n "$cp" ] && { kill $cp; wait $cp 2>/dev/null; }
  echo "== py $tag rc=$rc MARK_lines=$(grep -c MARK /tmp/o.txt) [pt]=$(grep -c '\[pt\]' /tmp/o.txt) [pt2]=$(grep -c '\[pt2\]' /tmp/o.txt) [pt.a]=$(grep -c '\[pt\.a\]' /tmp/o.txt) [pt.b]=$(grep -c '\[pt\.b\]' /tmp/o.txt)"
  grep MARK /tmp/o.txt | head -3 | sed 's/^/   first: /'
  grep MARK /tmp/o.txt | tail -1 | sed 's/^/   last:  /'
  grep -E "RESULT|Error|Traceback|EXC" /tmp/o.txt | head -6 | sed 's/^/   /'
}
for c in base thr1 thr1000 thr0 once skipfirst skipfirst_thr once_thr two_loggers same_logger_two_objects child_loggers sev_change period_change src_kwarg; do pycase $c; done
for c in sim_default sim_nodeclock; do pycase $c none; pycase $c fast; done
echo "### rclpy timing: thr1 MARK timestamps (seconds field)"
timeout 60 python3 /tmp/ptest.py thr1 2>&1 | grep MARK | sed -E 's/^\[INFO\] \[([0-9.]+)\].*i=([0-9]+)/   t=\1 i=\2/'
echo "### C++ build"
mkdir -p /ws/src && cp -r /src/thr_cpp /src/bad_ptr /src/bad_dur /src/bad_chrono /ws/src/ && cd /ws
export MAKEFLAGS=-j1
t0=$(date +%s); timeout 600 colcon build --executor sequential --packages-select thr_cpp > /tmp/b.txt 2>&1; echo "thr_cpp build rc=$? secs=$(( $(date +%s)-t0 ))"; tail -3 /tmp/b.txt
for b in bad_ptr bad_dur bad_chrono; do
  timeout 600 colcon build --executor sequential --packages-select $b > /tmp/b.txt 2>&1; echo "== $b build rc=$?"
  grep -E "error:|note: +candidate|cannot convert|no match" /ws/log/latest_build/$b/stdout_stderr.log | head -6 | cut -c1-400 | sed 's/^/   /'
done
source /ws/install/setup.bash
echo "### C++ cases"
cppcase() {
  local tag="$1"; [ -n "$2" ] && tag="$1/$2"
  local cp=""
  if [ "$2" = fast ]; then python3 /tmp/clockpub.py 0.1 >/dev/null 2>&1 & cp=$!; sleep 2; fi
  timeout 60 ros2 run thr_cpp ctest "$1" > /tmp/o.txt 2>&1; local rc=$?
  [ -n "$cp" ] && { kill $cp; wait $cp 2>/dev/null; }
  echo "== cpp $tag rc=$rc MARK_lines=$(grep -c MARK /tmp/o.txt) [ct]=$(grep -c '\[ct\]' /tmp/o.txt) [ct2]=$(grep -c '\[ct2\]' /tmp/o.txt)"
  grep MARK /tmp/o.txt | head -2 | sed 's/^/   first: /'
  grep MARK /tmp/o.txt | tail -1 | sed 's/^/   last:  /'
  grep -E "RESULT|rror|terminate" /tmp/o.txt | head -4 | sed 's/^/   /'
}
for c in thr1000 thr1 thr_dur_ns skipfirst skipfirst_thr two_instances two_instances_once; do cppcase $c; done
for c in sim_nodeclock sim_steady; do cppcase $c none; cppcase $c fast; done
echo "### done $(date -u +%FT%TZ)"
