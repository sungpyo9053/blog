#!/bin/bash
# Run inside ros:<distro>-ros-base, isolated from other DDS traffic:
#   docker run --rm --name pk69-ac-<distro> --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Not kept: two one-case smoke tests on Jazzy and a first full Jazzy pass that I stopped early, because the
# client scheduled the cancel from process start instead of from sending the goal. out_jazzy.txt is the rerun.
# Each case starts ac.py server <mode> in the background, then ac.py client in the same container.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88
# Humble has no ROS_AUTOMATIC_DISCOVERY_RANGE; Jazzy+ warns that ROS_LOCALHOST_ONLY is deprecated
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
echo "=== distro=$ROS_DISTRO nproc=$(nproc) date=$(date -u +%FT%TZ)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rcl-action ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp \
  ros-$ROS_DISTRO-example-interfaces 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
echo "--- rclpy defaults (source of default_cancel_callback / default_goal_callback):"
python3 - <<'P'
import inspect, rclpy.action.server as s
print(inspect.getsource(s.default_cancel_callback)); print(inspect.getsource(s.default_goal_callback))
src = inspect.getsource(s)
for l in src.splitlines():
    if 'assuming aborted' in l or 'not set' in l: print('LINE:', l.strip())
P
waitload() { for i in $(seq 1 12); do l=$(cut -d' ' -f1 /proc/loadavg); awk "BEGIN{exit !($l < 3.5)}" && return; echo "LOAD $l, waiting 20 s"; sleep 20; done; }
run() {  # run <mode> <cancel_at> <second_at> <wait>
  waitload
  echo; echo "### case mode=$1 cancel_at=$2 second_at=$3 load=$(cut -d' ' -f1-3 /proc/loadavg)"
  timeout 40 python3 /w/ac.py server $1 2>&1 & SP=$!
  sleep 1.5
  timeout 40 python3 /w/ac.py client $2 $3 $4 2>&1; echo "client exit=$?"
  kill -INT $SP 2>/dev/null; sleep 1; kill -9 $SP 2>/dev/null; wait $SP 2>/dev/null
}
REPS=${REPS:-2}
for r in $(seq 1 $REPS); do
  echo; echo "######## rep $r"
  run default_cancel 1.0 - 12
  run multi_default_cancel 1.0 - 12
  run accept_nocheck 1.0 - 12
  run accept_check 1.0 - 12
  run multi_default_group 1.0 - 12
  run multi_reentrant 1.0 - 12
  run multi_reentrant_nocheck 1.0 - 12
  run accept_check - 1.0 16
  run multi_reentrant - 1.0 16
  run no_state - - 12
  run canceled_unrequested - - 12
  run succeed_twice - - 12
  run raise - - 12
  run return_none - - 12
done
echo "=== done $ROS_DISTRO $(date -u +%FT%TZ)"
