#!/bin/bash
# Run inside ros:<distro>-ros-base, isolated from other DDS traffic:
#   docker run --rm --name pk48-ws-<distro> --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# out_jazzy_prelim.txt is a first Jazzy pass made with an earlier ws.py (before the *_spin fix variants);
# the article uses out_jazzy.txt, made with this ws.py, plus the marked move_global_spin rerun at its end.
# Each case runs ws.py for DUR seconds, REPS times, and prints one RESULT line per run.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
REPS=${REPS:-3}
DUR=${DUR:-8}
echo "=== distro=$ROS_DISTRO nproc=$(nproc) date=$(date -u +%FT%TZ)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcl-action ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-example-interfaces 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
# Does this rclpy refuse a second concurrent spin? (look for a guard in the executor source)
P=$(python3 -c 'import rclpy.executors as e; print(e.__file__)')
echo "executors.py: $P"
grep -n "already spinning\|_is_shutdown\|is_spinning\|ExternalShutdown" "$P" | head -20
A=$(python3 -c 'import rclpy.action.client as c; print(c.__file__)')
grep -n "_lock\|is_ready" "$A" | head -20

waitload() {  # keep the shared 2 vCPU runner under load 3.5
  for i in $(seq 1 12); do
    l=$(cut -d' ' -f1 /proc/loadavg)
    awk "BEGIN{exit !($l < 3.5)}" && return
    echo "LOAD $l, waiting 20 s"; sleep 20
  done
}

CASES=${CASES:-"seq same_exec same_exec_st same_exec_spin global spin_once_global move_global move_global_spin move_global_nopad move_spin_once move_two_exec move_two_exec_nopad svc_same_exec two_spinners fix_event fix_event_st fix_event_spin fix_event_st_spin fix_async fix_async_spin fix_own_node"}
for r in $(seq 1 $REPS); do
  for c in $CASES; do
    waitload
    echo "--- case=$c rep=$r load=$(cut -d' ' -f1-3 /proc/loadavg)"
    s=$(date +%s.%N)
    timeout $((DUR + 25)) python3 /w/ws.py $c $DUR 2>&1 | head -c 20000
    rc=${PIPESTATUS[0]}
  echo "exit=$rc wall=$(python3 -c "print(round($(date +%s.%N)-$s,2))")s"
  done
done
echo "=== done $ROS_DISTRO $(date -u +%FT%TZ)"
