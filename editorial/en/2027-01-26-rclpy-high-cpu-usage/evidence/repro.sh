#!/bin/bash
# Run inside ros:<distro>-ros-base:
#   docker run --rm -e ROS_DOMAIN_ID=88 -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# (-e ONLY_EXTRA=1 runs only the coroutine section; used once for Jazzy, which had run the rest first)
# DDS stays on loopback (ROS_LOCALHOST_ONLY=1 / ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST, domain 88).
# The container needs network only for the optional apt install of rmw_cyclonedds_cpp.
# Measures process CPU (time.process_time over wall time) of one rclpy node per case:
# idle nodes under different spin patterns, empty timers, and a subscriber fed by a
# separate rclpy publisher, under SingleThreadedExecutor, MultiThreadedExecutor and EventsExecutor.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
REPS=${REPS:-3}
echo "=== distro=$ROS_DISTRO nproc=$(nproc) python_cpu_count=$(python3 -c 'import os;print(os.cpu_count())')"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-fastrtps \
  ros-$ROS_DISTRO-fastdds ros-$ROS_DISTRO-rmw-cyclonedds-cpp 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
python3 - <<'X'
import inspect, rclpy
from rclpy.executors import MultiThreadedExecutor
print('spin_once signature:', inspect.signature(rclpy.spin_once))
print('MultiThreadedExecutor signature:', inspect.signature(MultiThreadedExecutor.__init__))
try:
    from rclpy.experimental import EventsExecutor
    print('rclpy.experimental.EventsExecutor: available')
except Exception as e:
    print('rclpy.experimental.EventsExecutor: not available (%s: %s)' % (type(e).__name__, e))
X

waitload() {  # keep the shared 2 vCPU runner under load 3.5
  for i in $(seq 1 12); do
    l=$(cut -d' ' -f1 /proc/loadavg)
    awk "BEGIN{exit !($l < 3.5)}" && return
    echo "LOAD $l, waiting 20 s"; sleep 20
  done
}

one() {  # entity mode
  waitload
  timeout 30 python3 /w/cpu.py "$1" "$2"
}

pubsub() {  # rate mode
  waitload
  WARM=3 TAIL=3 timeout 30 python3 /w/cpu.py "pub:$1" spin &
  P=$!
  sleep 1
  timeout 30 python3 /w/cpu.py sub "$2" | sed "s/ sub / sub@$1Hz /"
  wait $P
}

suite() {
  echo "--- suite RMW=${RMW_IMPLEMENTATION:-default} rep=$1 load=$(cut -d' ' -f1-3 /proc/loadavg)"
  for m in spin once0 once10ms onceNone once0_sleep1ms mte ee; do one idle $m; done
  for hz in 10 100 1000; do one timer:$hz spin; done
  one timer:1000 mte; one timer:1000 ee
  for hz in 10 100 500 1000; do pubsub $hz spin; done
  for hz in 500 1000; do pubsub $hz mte; pubsub $hz ee; done
}

extra() {  # rclpy issue 1405: coroutine awaiting a never-done Future, then spin_once loops
  echo "--- extra coro rep=$1 load=$(cut -d' ' -f1-3 /proc/loadavg)"
  for m in onceNone spin steonce; do one coro $m; done
}

if [ -z "$ONLY_EXTRA" ]; then
  for r in $(seq 1 $REPS); do suite $r; done
fi
for r in $(seq 1 $REPS); do extra $r; done
[ -n "$ONLY_EXTRA" ] && { echo "=== done extra $ROS_DISTRO"; exit 0; }

echo "--- optional: rmw_cyclonedds_cpp"
if [ ! -e /opt/ros/$ROS_DISTRO/lib/librmw_cyclonedds_cpp.so ]; then
  (timeout 300 apt-get update -qq && timeout 300 apt-get install -y -qq ros-$ROS_DISTRO-rmw-cyclonedds-cpp) >/tmp/apt.log 2>&1 \
    && echo "installed $(dpkg-query -W -f='${Package} ${Version}' ros-$ROS_DISTRO-rmw-cyclonedds-cpp)" \
    || { echo "cyclone install failed"; tail -3 /tmp/apt.log; }
fi
if [ -e /opt/ros/$ROS_DISTRO/lib/librmw_cyclonedds_cpp.so ]; then
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  for r in $(seq 1 $REPS); do
    echo "--- cyclone rep=$r load=$(cut -d' ' -f1-3 /proc/loadavg)"
    one idle spin; one idle mte; one timer:1000 spin; one timer:1000 mte
    pubsub 500 spin; pubsub 500 mte; pubsub 1000 spin; pubsub 1000 mte
  done
fi
echo "=== done $ROS_DISTRO"
