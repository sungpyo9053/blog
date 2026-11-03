#!/bin/bash
# "RMW implementation not installed" repro.
# Host:   bash repro.sh host <distro>    (humble | jazzy | lyrical), writes out_<distro>.txt
# Inside: bash /w/repro.sh inner         (run by the host part)

MODE=${1:-host}

if [ "$MODE" = host ]; then
  D=$2; C=pk2-p10-$D; W=/tmp/en-pick10
  mkdir -p $W; cp "$0" $W/repro.sh
  ulimit -c 0
  echo "### host $(date -Is) $(uptime)"
  docker pull -q ros:$D-ros-base
  docker image inspect ros:$D-ros-base --format 'IMAGE ros:'$D'-ros-base {{index .RepoDigests 0}} created {{.Created}}'
  docker rm -f $C >/dev/null 2>&1
  docker run -d --name $C --ulimit core=0 --cpus 1.5 --memory 2g -v $W:/w ros:$D-ros-base sleep 3600 >/dev/null
  timeout 1500 docker exec $C bash /w/repro.sh inner 2>&1
  echo "### host done $(date -Is) $(uptime)"
  docker rm -f $C >/dev/null
  exit 0
fi

# ---------------- inner ----------------
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
D=$ROS_DISTRO
unset RMW_IMPLEMENTATION
mkdir -p /tmp/p && cd /tmp/p

cat > probe.py <<'EOF'
import sys, time
t0 = time.time()
print('stage: import rclpy', flush=True)
import rclpy
from rclpy.utilities import get_rmw_implementation_identifier
try:
    print('stage: rclpy.init()', flush=True)
    rclpy.init()
    print('stage: create_node', flush=True)
    n = rclpy.create_node('probe')
    print('OK identifier =', get_rmw_implementation_identifier(), flush=True)
    n.destroy_node(); rclpy.shutdown()
except Exception as e:
    print('PYEXC %s.%s: %s' % (type(e).__module__, type(e).__name__, e), flush=True)
    print('elapsed %.3f s' % (time.time() - t0)); sys.exit(3)
print('elapsed %.3f s' % (time.time() - t0))
EOF

cat > talker.py <<'EOF'
import rclpy, time
from std_msgs.msg import String
rclpy.init(); n = rclpy.create_node('talker_py'); p = n.create_publisher(String, 'chatter', 10)
i = 0; end = time.time() + float(__import__('sys').argv[1])
while time.time() < end:
    m = String(); m.data = 'hello %d' % i; p.publish(m); i += 1
    rclpy.spin_once(n, timeout_sec=0.1)
print('talker sent', i, flush=True)
EOF

cat > listener.py <<'EOF'
import rclpy, time, sys
from rclpy.utilities import get_rmw_implementation_identifier
from std_msgs.msg import String
rclpy.init(); n = rclpy.create_node('listener_py'); got = []
n.create_subscription(String, 'chatter', lambda m: got.append(m.data), 10)
end = time.time() + float(sys.argv[1]); first = None
while time.time() < end:
    rclpy.spin_once(n, timeout_sec=0.1)
    if got and first is None: first = time.time()
names = n.get_node_names()
print('listener rmw=%s received=%d nodes_seen=%s' % (get_rmw_implementation_identifier(), len(got), sorted(names)), flush=True)
EOF

run() { # label, then command; prints output, exit code, wall time
  local label=$1; shift
  echo; echo "=== CASE: $label"; echo "\$ $*"
  local t0=$(date +%s.%N)
  timeout 40 "$@" 2>&1 | head -c 4000
  local rc=${PIPESTATUS[0]}
  local t1=$(date +%s.%N)
  echo "--- exit=$rc wall=$(python3 -c "print('%.2f'%($t1-$t0))")s"
}

echo "### inner $(date -Is) distro=$D"
echo "### versions (before)"
for p in rclpy rclcpp rcl ros2cli rmw rmw-implementation rmw-fastrtps-cpp rmw-cyclonedds-cpp cyclonedds rmw-zenoh-cpp; do
  dpkg-query -W -f='${Package} ${Version}\n' ros-$D-$p 2>/dev/null || echo "ros-$D-$p NOT INSTALLED"
done
echo "### rmw libraries in /opt/ros/$D/lib"
ls /opt/ros/$D/lib | grep -E '^librmw_[a-z_]+\.so$'
echo "### ros2 doctor middleware"
timeout 60 ros2 doctor --report 2>/dev/null | grep -A3 -i 'RMW MIDDLEWARE' || echo "(ros2 doctor not available)"
ros2 daemon stop >/dev/null 2>&1

run "baseline python, RMW_IMPLEMENTATION unset" python3 probe.py
run "baseline C++ component_container (4 s), unset" timeout 4 ros2 run rclcpp_components component_container
run "empty RMW_IMPLEMENTATION=''" env RMW_IMPLEMENTATION= python3 probe.py
run "python, rmw_cyclonedds_cpp not installed" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 probe.py
run "C++ component_container, rmw_cyclonedds_cpp not installed" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp timeout 4 ros2 run rclcpp_components component_container
run "typo rmw_cyclone_dds_cpp" env RMW_IMPLEMENTATION=rmw_cyclone_dds_cpp python3 probe.py
run "wrong case RMW_CycloneDDS_cpp" env RMW_IMPLEMENTATION=RMW_CycloneDDS_cpp python3 probe.py
run "rmw_connextdds not installed" env RMW_IMPLEMENTATION=rmw_connextdds python3 probe.py
run "rmw_zenoh_cpp not installed" env RMW_IMPLEMENTATION=rmw_zenoh_cpp python3 probe.py
run "ros2 topic list, cyclone not installed (daemon stopped)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 topic list
run "ros2 topic list --no-daemon, cyclone not installed" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 topic list --no-daemon
ros2 daemon stop >/dev/null 2>&1
run "LD_LIBRARY_PATH removed, default RMW" env -u LD_LIBRARY_PATH python3 probe.py
run "LD_LIBRARY_PATH removed, C++ component_container" env -u LD_LIBRARY_PATH timeout 4 /opt/ros/$D/lib/rclcpp_components/component_container

# build-time check
mkdir -p ws/src/pkgcpp/src
cat > ws/src/pkgcpp/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3"><name>pkgcpp</name><version>0.0.0</version><description>d</description>
<maintainer email="a@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend>
<export><build_type>ament_cmake</build_type></export></package>
EOF
cat > ws/src/pkgcpp/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(pkgcpp)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(probe_cpp src/probe.cpp)
target_link_libraries(probe_cpp rclcpp::rclcpp)
install(TARGETS probe_cpp DESTINATION lib/${PROJECT_NAME})
ament_package()
EOF
cat > ws/src/pkgcpp/src/probe.cpp <<'EOF'
#include <rclcpp/rclcpp.hpp>
#include <rmw/rmw.h>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("probe_cpp");
  std::printf("OK identifier = %s\n", rmw_get_implementation_identifier());
  rclcpp::shutdown();
  return 0;
}
EOF
cd ws
run "colcon build with RMW_IMPLEMENTATION=rmw_cyclonedds_cpp (not installed)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp colcon build --event-handlers console_direct+
rm -rf build install log
run "colcon build, RMW unset" colcon build
run "built C++ probe, unset" bash -c 'source install/setup.bash && ros2 run pkgcpp probe_cpp'
run "built C++ probe, cyclone not installed" bash -c 'source install/setup.bash && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 run pkgcpp probe_cpp'
cd /tmp/p

echo; echo "### install rmw_cyclonedds_cpp"
t0=$(date +%s)
timeout 600 apt-get update -qq >/dev/null 2>&1
timeout 600 env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ros-$D-rmw-cyclonedds-cpp 2>&1 | grep -E 'newly installed|Need to get|After this operation|^  ros-|^Setting up ros-'
echo "install wall=$(( $(date +%s) - t0 ))s"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rmw-cyclonedds-cpp ros-$D-cyclonedds

run "python, cyclone installed, same shell (not re-sourced)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 probe.py
run "C++ component_container, cyclone installed" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp timeout 4 ros2 run rclcpp_components component_container
run "built C++ probe (built before install), cyclone installed" bash -c 'source ws/install/setup.bash && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 run pkgcpp probe_cpp'
cd ws; rm -rf build install log
run "colcon build with RMW_IMPLEMENTATION=rmw_cyclonedds_cpp (installed)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp colcon build
cd /tmp/p

DDSC=$(find /opt/ros/$D -name 'libddsc.so.0*' | head -1); echo "libddsc at: $DDSC"
if [ -n "$DDSC" ]; then
  mv "$DDSC" "$DDSC.moved"
  run "cyclone installed but libddsc.so.0 missing" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 probe.py
  mv "$DDSC.moved" "$DDSC"
fi

echo; echo "### mixed RMW on one host, same domain"
ros2 daemon stop >/dev/null 2>&1
( RMW_IMPLEMENTATION=rmw_fastrtps_cpp python3 talker.py 10 > t1.log 2>&1 & )
sleep 1
run "talker fastrtps -> listener cyclonedds" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 listener.py 8
sleep 2; cat t1.log
( RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 talker.py 10 > t2.log 2>&1 & )
sleep 1
run "talker cyclonedds -> listener fastrtps" env RMW_IMPLEMENTATION=rmw_fastrtps_cpp python3 listener.py 8
sleep 2; cat t2.log

echo; echo "### daemon started under fastrtps, CLI under cyclone"
ros2 daemon stop >/dev/null 2>&1
env RMW_IMPLEMENTATION=rmw_fastrtps_cpp ros2 daemon start
( RMW_IMPLEMENTATION=rmw_cyclonedds_cpp python3 talker.py 12 > t3.log 2>&1 & )
sleep 3
run "ros2 node list (cyclone shell, fastrtps daemon)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 node list
run "ros2 node list --no-daemon (cyclone shell)" env RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 node list --no-daemon
run "ros2 daemon status" ros2 daemon status
ps -eo pid,args | grep -E '_ros2_daemon|ros2-daemon' | grep -v grep
sleep 8; ros2 daemon stop

echo; echo "### zenoh"
if timeout 300 env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ros-$D-rmw-zenoh-cpp > z.log 2>&1; then
  dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rmw-zenoh-cpp
  run "zenoh installed, shell NOT re-sourced" env RMW_IMPLEMENTATION=rmw_zenoh_cpp timeout 15 python3 probe.py
  RS="source /opt/ros/$D/setup.bash &&"
  run "zenoh, re-sourced, no router (timeout 15 s)" bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp timeout 15 python3 probe.py"
  ( bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp timeout 25 ros2 run rmw_zenoh_cpp rmw_zenohd" > zd.log 2>&1 & )
  sleep 3
  run "zenoh probe, re-sourced, router running" bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp python3 probe.py"
  ( RMW_IMPLEMENTATION=rmw_fastrtps_cpp python3 talker.py 10 > t4.log 2>&1 & )
  sleep 1
  run "talker fastrtps -> listener zenoh (router running)" bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp python3 listener.py 6"
  ( bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp python3 talker.py 8" > t5.log 2>&1 & )
  sleep 1
  run "talker zenoh -> listener zenoh (router running)" bash -c "$RS RMW_IMPLEMENTATION=rmw_zenoh_cpp python3 listener.py 5"
  sleep 4; echo "t4:"; cat t4.log; echo "t5:"; cat t5.log; echo "zenohd log head:"; head -5 zd.log
else
  echo "ros-$D-rmw-zenoh-cpp install failed:"; tail -3 z.log
fi
pkill -f talker.py; pkill -f rmw_zenohd
echo "### inner done $(date -Is)"
