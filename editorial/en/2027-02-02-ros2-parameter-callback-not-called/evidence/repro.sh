#!/bin/bash
# Run inside ros:<distro>-ros-base, isolated from other DDS traffic:
#   docker run --rm --name pk65-<distro> --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Each case starts the node "pcb" (Python: src/pcb.py, C++: src/pcb_cpp) with -p gain:=2.0
# (gain:=5.0 for reject_init), then runs: ros2 param set gain 3.0, the same set again,
# ros2 param get gain, ros2 param get mode, stops the node with SIGINT and prints its log.
# out_jazzy_prelim.txt is a first Jazzy pass made with an earlier version of this script: it used
# ros2 param --no-daemon and its rc= values are wrong (rc of head, not of ros2). The article uses only its
# 'Node not found' count; every other number comes from out_humble.txt, out_jazzy.txt and out_lyrical.txt.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88
# Humble only knows ROS_LOCALHOST_ONLY; Jazzy and later warn about it, so use the newer variable there.
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RCUTILS_COLORIZED_OUTPUT=0
echo "=== distro=$ROS_DISTRO nproc=$(nproc) date=$(date -u +%FT%TZ)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-ros2param ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcl-interfaces ros-$ROS_DISTRO-rmw \
  ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
grep -h "define RCLCPP_VERSION_STR" /opt/ros/$ROS_DISTRO/include/rclcpp/rclcpp/version.h /opt/ros/$ROS_DISTRO/include/rclcpp/version.h 2>/dev/null
N=$(python3 -c 'import rclpy.node as m; print(m.__file__)')
echo "rclpy node.py has: $(grep -o 'def add_[a-z_]*parameters_callback' $N | tr '\n' ' ')"
grep -n "RCUTILS_WARN_UNUSED\|add_on_set_parameters_callback(" /opt/ros/$ROS_DISTRO/include/rclcpp/rclcpp/node.hpp 2>/dev/null | head -6
# Use the ros2 daemon (the default for ros2 param); a first pass with --no-daemon often
# printed "Node not found" for nodes that were running.
ND=""
ros2 daemon start 2>&1

waitload() {  # keep the shared 2 vCPU runner under load 3.5
  for i in $(seq 1 15); do
    l=$(cut -d' ' -f1 /proc/loadavg)
    awk "BEGIN{exit !($l < 3.5)}" && return
    echo "LOAD $l, waiting 20 s"; sleep 20
  done
}
el() { python3 -c "print(round($(date +%s.%N)-$1,2))"; }

echo "=== build pcb_cpp"
mkdir -p /tmp/ws/src && cp -r /w/src/pcb_cpp /w/src/postcheck /tmp/ws/src/
cd /tmp/ws
waitload
s=$(date +%s.%N)
MAKEFLAGS=-j1 nice colcon build --executor sequential --packages-select pcb_cpp \
  --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1 | grep -iE "warning|error|nodiscard|unused|Finished|Failed" | head -30
echo "pcb_cpp build wall=$(el $s)s"
echo "=== build postcheck (uses add_pre/post_set_parameters_callback)"
waitload
s=$(date +%s.%N)
MAKEFLAGS=-j1 nice colcon build --executor sequential --packages-select postcheck \
  --event-handlers console_direct+ 2>&1 | grep -E "error|Finished|Failed" | head -10
echo "postcheck build wall=$(el $s)s"
source /tmp/ws/install/setup.bash

# One retry when the CLI has not discovered the node yet ("Node not found"); the retry is logged.
cli() {  # cli <label> <ros2 param args...>
  local label=$1; shift
  for t in 1 2; do
    local s=$(date +%s.%N)
    out=$(timeout 15 ros2 param "$@" 2>&1); rc=$?
    echo "${out:0:2000}"
    echo "[ros2 param $label] try=$t rc=$rc wall=$(el $s)s"
    echo "$out" | grep -q "Node not found" || return
    sleep 1
  done
}
pset() { cli "set gain $1" set $ND /pcb gain $1; }
pget() { cli "get $1" get $ND /pcb $1; }

run_case() {
  local lang=$1 c=$2 g=2.0
  [ "$c" = reject_init ] && g=5.0
  waitload
  echo
  echo "--- lang=$lang case=$c gain:=$g load=$(cut -d' ' -f1-3 /proc/loadavg)"
  if [ "$lang" = py ]; then
    python3 /w/src/pcb.py $c --ros-args -p gain:=$g > /tmp/node.log 2>&1 &
  else
    /tmp/ws/install/pcb_cpp/lib/pcb_cpp/pcb $c --ros-args -p gain:=$g > /tmp/node.log 2>&1 &
  fi
  local pid=$! s=$(date +%s.%N)
  for i in $(seq 1 40); do
    grep -q READY /tmp/node.log && break
    kill -0 $pid 2>/dev/null || break
    sleep 0.25
  done
  if kill -0 $pid 2>/dev/null; then
    echo "node up after $(el $s)s"
    sleep 2
    pset 3.0
    pset 3.0
    pget gain
    pget mode
    kill -0 $pid 2>/dev/null && echo "node alive after param calls: yes" || echo "node alive after param calls: no"
    kill -INT $pid 2>/dev/null
    for i in $(seq 1 20); do kill -0 $pid 2>/dev/null || break; sleep 0.25; done
    kill -0 $pid 2>/dev/null && { echo "still running 5 s after SIGINT, SIGKILL"; kill -9 $pid; }
  else
    echo "node exited before ready after $(el $s)s"
  fi
  wait $pid; echo "node exit code=$?"
  echo "node log:"
  head -c 8000 /tmp/node.log
}

CASES_PY=${CASES_PY:-"before after return_none return_bool reject reject_init set_inside declare_inside no_spin two_cbs deferred pre_set post_set post_set_modify"}
CASES_CPP=${CASES_CPP:-"before after discard reject reject_init set_inside declare_inside no_spin two_cbs deferred pre_set post_set post_set_modify"}
for c in $CASES_PY; do run_case py $c; done
for c in $CASES_CPP; do run_case cpp $c; done
echo "=== done $ROS_DISTRO $(date -u +%FT%TZ)"
