#!/bin/bash
# Host side: ./repro.sh host <distro>   (humble | jazzy | lyrical)
# Container side (called by host mode): ./repro.sh all | ./repro.sh echo7
# Reproduces "Could not determine the type for the passed topic" from
# ros2 topic echo / hz / info, one cause at a time.
MODE=$1; D=$2; HERE=$(cd "$(dirname "$0")" && pwd)

if [ "$MODE" = hostextra ]; then   # supplementary run, appended after the main run
  IMG=ros:$D-ros-base
  uptime
  docker run --rm --name tec-$D-extra --ulimit core=0 --pids-limit 60 -v $HERE:/w $IMG bash /w/repro.sh extra
  exit 0
fi
if [ "$MODE" = host ]; then
  IMG=ros:$D-ros-base
  docker pull -q $IMG
  waitload() { while :; do l=$(cut -d' ' -f1 /proc/loadavg); uptime; awk "BEGIN{exit !($l<3.0)}" && break; sleep 20; done; }
  waitload
  # causes 1-6, one container
  docker run --rm --name tec-$D-main --ulimit core=0 --pids-limit 60 -v $HERE:/w $IMG bash /w/repro.sh all
  # cause 7, two containers on one docker bridge network
  docker network create tec-net >/dev/null 2>&1
  case7() { # label "pub env" "echo env" [explicit type]
    waitload
    echo "=== CASE7 $1 | publisher env: $2 | echo env: $3"
    docker run -d --name tec-$D-pub --network tec-net --ulimit core=0 $2 $IMG \
      bash -c 'source /opt/ros/$ROS_DISTRO/setup.bash; exec ros2 topic pub -r 2 /x std_msgs/msg/String "{data: hi}"' >/dev/null
    sleep 5
    docker run --rm --name tec-$D-echo --network tec-net --ulimit core=0 $3 -e TYPE="$4" -v $HERE:/w $IMG bash /w/repro.sh echo7
    docker logs tec-$D-pub 2>&1 | head -5
    docker rm -f tec-$D-pub >/dev/null
  }
  case7 both-default "" ""
  case7 pub-localhost-only "-e ROS_LOCALHOST_ONLY=1" ""
  case7 both-localhost-only "-e ROS_LOCALHOST_ONLY=1" "-e ROS_LOCALHOST_ONLY=1"
  case7 pub-localhost-only-explicit-type "-e ROS_LOCALHOST_ONLY=1" "" std_msgs/msg/String
  case7 pub-range-LOCALHOST "-e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST" ""
  case7 echo-range-LOCALHOST "" "-e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"
  case7 both-range-SUBNET "-e ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET" "-e ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET"
  docker network rm tec-net >/dev/null
  exit 0
fi

# ---------------- inside the container ----------------
source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1
ulimit -c 0

# run LABEL TIMEOUT cmd... : prints output with seconds since start, exit code, elapsed.
# exit=124 means the command was still running when timeout stopped it (SIGINT).
run() {
  local label=$1 to=$2; shift 2
  echo "--- $label"; echo "\$ $*"
  local t0=$(date +%s.%N)
  timeout -s INT -k 3 $to "$@" 2>&1 | python3 -u -c '
import sys,time
t0=float(sys.argv[1]); n=0; first=None
for l in sys.stdin:
    n+=1; t=time.time()-t0
    if first is None and l.startswith(("data:","num:")): first=t
    if n<=6: print("%6.2f %s"%(t,l.rstrip()),flush=True)
if n>6: print("       ... %d more lines"%(n-6))
print("first_data=%s"%("%.2f"%first if first is not None else "none"))' $t0
  local rc=${PIPESTATUS[0]}
  python3 -c "import sys; print('exit=%s elapsed=%.2f'%(sys.argv[1], float(sys.argv[3])-float(sys.argv[2])))" $rc $t0 $(date +%s.%N)
}
# PIDS: track every background publisher, including delayed ones still in their sleep
PIDS=""
pub()  { ( [ -n "$2" ] && sleep $2; exec ros2 topic pub -r 2 ${1:-/x} std_msgs/msg/String "{data: hi}" ) >/dev/null 2>&1 & PIDS="$PIDS $!"; }
stop() { [ -n "$PIDS" ] && kill $PIDS 2>/dev/null; PIDS=""; pkill -f "topic pub"; sleep 1; }
fresh(){ stop; ros2 daemon stop >/dev/null 2>&1; sleep 1; }

if [ "$MODE" = echo7 ]; then
  run "echo /x $TYPE" 12 ros2 topic echo /x $TYPE
  run "echo --no-daemon /x $TYPE" 12 ros2 topic echo --no-daemon /x $TYPE
  exit 0
fi

if [ "$MODE" = extra ]; then
  echo "=== EXTRA distro=$ROS_DISTRO"
  echo "##### 8 cold daemon: publisher running 5 s, daemon stopped, echo auto-starts it (x5), then echo again"
  for i in 1 2 3 4 5; do
    fresh; pub /x; sleep 5
    run "8a.$i cold daemon, first echo" 8 ros2 topic echo /x
    run "8b.$i second echo right after (daemon now running)" 8 ros2 topic echo /x
  done
  for i in 1 2 3; do
    fresh; ros2 daemon start >/dev/null; sleep 3; pub /x; sleep 5
    run "8c.$i warm daemon (started 3 s before publisher), publisher running 5 s" 8 ros2 topic echo /x
  done
  for i in 1 2 3; do
    fresh; pub /x; sleep 5
    run "8d.$i cold daemon, ros2 topic info" 8 ros2 topic info /x
  done
  echo "##### 4x custom message unsourced, --no-daemon"
  mkdir -p /ws/src/tec_msgs/msg && cd /ws/src/tec_msgs && echo "int64 num" > msg/Num.msg
  printf '%s\n' '<?xml version="1.0"?>' '<package format="3"><name>tec_msgs</name><version>0.0.0</version><description>t</description>' '<maintainer email="dev@example.com">a</maintainer><license>MIT</license>' '<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>rosidl_default_generators</buildtool_depend>' '<exec_depend>rosidl_default_runtime</exec_depend><member_of_group>rosidl_interface_packages</member_of_group>' '<export><build_type>ament_cmake</build_type></export></package>' > package.xml
  printf '%s\n' 'cmake_minimum_required(VERSION 3.8)' 'project(tec_msgs)' 'find_package(ament_cmake REQUIRED)' 'find_package(rosidl_default_generators REQUIRED)' 'rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg")' 'ament_package()' > CMakeLists.txt
  cd /ws && MAKEFLAGS=-j1 colcon build --parallel-workers 1 >/tmp/build.log 2>&1 && echo "tec_msgs built"; cd /
  fresh; bash -c 'source /ws/install/setup.bash; exec ros2 topic pub -r 2 /c tec_msgs/msg/Num "{num: 1}"' >/dev/null 2>&1 & sleep 5
  run "4x1 unsourced echo --no-daemon /c" 10 ros2 topic echo --no-daemon /c
  run "4x2 unsourced echo /c (daemon auto-started by this call)" 10 ros2 topic echo /c
  run "4x3 unsourced echo /c (daemon already running)" 10 ros2 topic echo /c
  stop; fresh
  echo "=== extra done"; exit 0
fi

echo "=== distro=$ROS_DISTRO"
apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq ros-$ROS_DISTRO-rmw-cyclonedds-cpp >/dev/null 2>&1 && echo "cyclonedds installed" || echo "cyclonedds install FAILED"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2topic "ros-$ROS_DISTRO-rmw-*-cpp" ros-$ROS_DISTRO-fastrtps ros-$ROS_DISTRO-fastdds ros-$ROS_DISTRO-cyclonedds 2>/dev/null
python3 -c 'import rclpy; rclpy.init(); from rclpy.utilities import get_rmw_implementation_identifier as g; print("default rmw:", g())'

echo; echo "##### 1 publisher not running / started later"
fresh; run "1a no publisher, daemon" 10 ros2 topic echo /x
fresh; run "1b no publisher, --no-daemon" 10 ros2 topic echo --no-daemon /x
fresh; run "1c hz, no publisher" 10 ros2 topic hz /x
fresh; run "1d info, no publisher" 10 ros2 topic info /x
fresh; pub /x 3; run "1e publisher starts 3 s later, daemon" 12 ros2 topic echo /x
fresh; pub /x 3; run "1f publisher starts 3 s later, --no-daemon" 12 ros2 topic echo --no-daemon /x
fresh; pub /x 3; run "1g hz, publisher starts 3 s later" 12 ros2 topic hz /x
fresh; pub /x; sleep 0.5; run "1h publisher started 0.5 s before, daemon cold (just stopped)" 10 ros2 topic echo /x
fresh; ros2 daemon start; sleep 2; pub /x; sleep 0.5; run "1i publisher started 0.5 s before, daemon warm" 10 ros2 topic echo /x
fresh; pub /x; sleep 0.5; run "1j publisher started 0.5 s before, --no-daemon" 10 ros2 topic echo --no-daemon /x
fresh; pub /x; sleep 5; run "1k publisher running 5 s (baseline), daemon" 10 ros2 topic echo /x
fresh; pub /x; sleep 5; run "1l info, publisher running 5 s" 10 ros2 topic info /x

echo; echo "##### 2 stale daemon after changing env in the same shell"
fresh; ros2 daemon start; sleep 2; ros2 daemon status
( export ROS_DOMAIN_ID=7; pub /x; sleep 3; ros2 daemon status
  run "2a ROS_DOMAIN_ID changed 0->7 after daemon start" 10 ros2 topic echo /x )
fresh; ros2 daemon start; sleep 2
( export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; pub /x; sleep 3
  run "2b RMW changed to cyclonedds after daemon (fastrtps) start" 10 ros2 topic echo /x
  run "2b ros2 topic list via old daemon" 6 ros2 topic list
  ros2 daemon stop; sleep 1
  run "2c same, after ros2 daemon stop" 10 ros2 topic echo /x )
fresh; ros2 daemon start; sleep 2
( export ROS_LOCALHOST_ONLY=1; pub /x; sleep 3
  run "2d ROS_LOCALHOST_ONLY=1 set after daemon start" 10 ros2 topic echo /x
  ros2 daemon stop; sleep 1
  run "2e same shell, after ros2 daemon stop" 10 ros2 topic echo /x
  run "2f same shell, --no-daemon" 10 ros2 topic echo --no-daemon /x
  stop )

echo; echo "##### 3 different ROS_DOMAIN_ID"
fresh; ROS_DOMAIN_ID=1 bash -c 'source /opt/ros/$ROS_DISTRO/setup.bash; exec ros2 topic pub -r 2 /x std_msgs/msg/String "{data: hi}"' >/dev/null 2>&1 & sleep 4
ROS_DOMAIN_ID=2 run "3a pub domain 1, echo domain 2" 10 ros2 topic echo /x
ROS_DOMAIN_ID=2 run "3b pub domain 1, echo domain 2, explicit type" 10 ros2 topic echo /x std_msgs/msg/String
ROS_DOMAIN_ID=1 run "3c echo domain 1 (control)" 10 ros2 topic echo /x
kill $! 2>/dev/null; pkill -f "topic pub"; ROS_DOMAIN_ID=1 ros2 daemon stop >/dev/null 2>&1; ROS_DOMAIN_ID=2 ros2 daemon stop >/dev/null 2>&1

echo; echo "##### 4 custom message package not sourced in the echo shell"
mkdir -p /ws/src/tec_msgs/msg && cd /ws/src/tec_msgs
echo "int64 num" > msg/Num.msg
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>tec_msgs</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>rosidl_default_generators</buildtool_depend>
<exec_depend>rosidl_default_runtime</exec_depend><member_of_group>rosidl_interface_packages</member_of_group>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(tec_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg")
ament_package()
X
cd /ws && MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- >/tmp/build.log 2>&1 && echo "tec_msgs built" || { tail -30 /tmp/build.log; }
cd /
fresh; bash -c 'source /ws/install/setup.bash; exec ros2 topic pub -r 2 /c tec_msgs/msg/Num "{num: 1}"' >/dev/null 2>&1 & sleep 5
run "4a unsourced echo /c" 10 ros2 topic echo /c
run "4b unsourced echo /c tec_msgs/msg/Num" 10 ros2 topic echo /c tec_msgs/msg/Num
run "4c unsourced hz /c" 10 ros2 topic hz /c
run "4d unsourced info /c" 10 ros2 topic info /c
run "4e unsourced topic list -t" 6 ros2 topic list -t
run "4f sourced echo /c (control)" 10 bash -c 'source /ws/install/setup.bash; exec ros2 topic echo /c'
stop

echo; echo "##### 5 different RMW between publisher and echo (--no-daemon)"
fresh; RMW_IMPLEMENTATION=rmw_fastrtps_cpp pub /x; sleep 4
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp run "5a pub fastrtps, echo cyclonedds" 10 ros2 topic echo --no-daemon /x
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp run "5a2 repeat" 10 ros2 topic echo --no-daemon /x
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp run "5a3 cyclonedds topic list --spin-time 5" 10 ros2 topic list --no-daemon --spin-time 5
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp run "5a4 pub fastrtps, echo cyclonedds, explicit type" 10 ros2 topic echo --no-daemon /x std_msgs/msg/String
stop
fresh; RMW_IMPLEMENTATION=rmw_cyclonedds_cpp pub /x; sleep 4
RMW_IMPLEMENTATION=rmw_fastrtps_cpp run "5b pub cyclonedds, echo fastrtps" 10 ros2 topic echo --no-daemon /x
stop
fresh; RMW_IMPLEMENTATION=rmw_cyclonedds_cpp pub /x; sleep 4
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp run "5c both cyclonedds (control)" 10 ros2 topic echo --no-daemon /x
stop

echo; echo "##### 6 explicit type, publisher appears later"
fresh; pub /x 3; run "6a echo /x std_msgs/msg/String, pub 3 s later, daemon" 12 ros2 topic echo /x std_msgs/msg/String
fresh; pub /x 3; run "6b same, --no-daemon" 12 ros2 topic echo --no-daemon /x std_msgs/msg/String
fresh; run "6c explicit type, no publisher ever" 8 ros2 topic echo /x std_msgs/msg/String
fresh
echo "=== done"
