#!/bin/bash
# Run inside ros:<distro>-ros-base (one distro at a time):
#   docker run --rm --name wsvc-<distro> --ulimit core=0 --cpus=1.5 -v /tmp/en-wsvc:/w \
#     ros:<distro>-ros-base bash /w/repro.sh > out_<distro>.txt 2>&1
# Reproduces "waiting for service to become available..." and wait_for_service timeouts
# with a minimal rclpy and rclcpp std_srvs service server and client.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
date -u +%FT%TZ
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-ros2service ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp \
  ros-$ROS_DISTRO-fastrtps ros-$ROS_DISTRO-fastdds ros-$ROS_DISTRO-std-srvs 2>/dev/null
echo "--- default RMW"
python3 -c "from rclpy.utilities import get_rmw_implementation_identifier as g; print(g())"
if [ ! -e /opt/ros/$ROS_DISTRO/lib/librmw_cyclonedds_cpp.so ]; then
  echo "--- installing rmw_cyclonedds_cpp (not in image)"
  (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$ROS_DISTRO-rmw-cyclonedds-cpp) >/tmp/apt.log 2>&1 || tail -5 /tmp/apt.log
fi
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rmw-cyclonedds-cpp ros-$ROS_DISTRO-cyclonedds 2>/dev/null

W=/ws; mkdir -p $W/src/wsvc/src; cd $W/src/wsvc
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>wsvc</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_srvs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(wsvc)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_srvs REQUIRED)
add_executable(cpp_server src/server.cpp)
target_link_libraries(cpp_server rclcpp::rclcpp ${std_srvs_TARGETS})
add_executable(cpp_client src/client.cpp)
target_link_libraries(cpp_client rclcpp::rclcpp ${std_srvs_TARGETS})
install(TARGETS cpp_server cpp_client DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS py_server.py py_client.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > src/server.cpp <<'X'
// usage: cpp_server <service_name> <spin 1|0> [--ros-args ...]
#include <chrono>
#include <thread>
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
using namespace std::chrono_literals;
int main(int argc, char ** argv) {
  auto args = rclcpp::init_and_remove_ros_arguments(argc, argv);
  std::string name = args.size() > 1 ? args[1] : "trigger";
  bool spin = args.size() > 2 ? args[2] == "1" : true;
  auto n = std::make_shared<rclcpp::Node>("wsvc_server_cpp");
  auto s = n->create_service<std_srvs::srv::Trigger>(name,
    [](const std::shared_ptr<std_srvs::srv::Trigger::Request>, std::shared_ptr<std_srvs::srv::Trigger::Response> r) {
      r->success = true; r->message = "ok from cpp"; });
  double t = std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
  RCLCPP_INFO(n->get_logger(), "SERVER_READY %s t=%.3f", s->get_service_name(), t);
  if (spin) rclcpp::spin(n); else while (rclcpp::ok()) std::this_thread::sleep_for(1s);
  rclcpp::shutdown();
}
X
cat > src/client.cpp <<'X'
// usage: cpp_client <service_name> <timeout_s>
#include <chrono>
#include <rclcpp/rclcpp.hpp>
#include <std_srvs/srv/trigger.hpp>
int main(int argc, char ** argv) {
  auto args = rclcpp::init_and_remove_ros_arguments(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("wsvc_client_cpp");
  auto c = n->create_client<std_srvs::srv::Trigger>(args[1]);
  double to = std::stod(args[2]);
  auto t0 = std::chrono::steady_clock::now();
  bool ok = c->wait_for_service(std::chrono::duration<double>(to));
  double el = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  RCLCPP_INFO(n->get_logger(), "cpp wait_for_service(%s, %.1fs) returned %s after %.2fs", c->get_service_name(), to, ok ? "true" : "false", el);
  if (ok) {
    auto f = c->async_send_request(std::make_shared<std_srvs::srv::Trigger::Request>());
    auto rc = rclcpp::spin_until_future_complete(n, f, std::chrono::seconds(5));
    if (rc == rclcpp::FutureReturnCode::SUCCESS) RCLCPP_INFO(n->get_logger(), "response: %s", f.get()->message.c_str());
    else RCLCPP_ERROR(n->get_logger(), "no response within 5s");
  }
  rclcpp::shutdown();
  return ok ? 0 : 1;
}
X
cat > py_server.py <<'X'
#!/usr/bin/env python3
# usage: py_server.py <service_name> <Trigger|SetBool> <spin 1|0> [--ros-args ...]
import sys, time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger, SetBool
rclpy.init(args=sys.argv)
a = rclpy.utilities.remove_ros_args(sys.argv)
name, typ, spin = a[1], a[2], a[3]
n = Node('wsvc_server')
T = Trigger if typ == 'Trigger' else SetBool
def cb(req, resp):
    resp.success = True
    resp.message = 'ok from py'
    return resp
s = n.create_service(T, name, cb)
n.get_logger().info(f'SERVER_READY {s.srv_name} type={typ} spin={spin} t={time.time():.3f}')
if spin == '1':
    rclpy.spin(n)
else:
    while True:
        time.sleep(1)
X
cat > py_client.py <<'X'
#!/usr/bin/env python3
# usage: py_client.py <service_name> <mode once|robust|discover> [timeout_s]
import sys, time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
rclpy.init(args=sys.argv)
a = rclpy.utilities.remove_ros_args(sys.argv)
name, mode = a[1], a[2]
to = float(a[3]) if len(a) > 3 else 3.0
node = Node('wsvc_client')
cli = node.create_client(Trigger, name)
log = node.get_logger()
if mode == 'once':
    t0 = time.monotonic()
    ok = cli.wait_for_service(timeout_sec=to)
    log.info(f'py wait_for_service({cli.srv_name}, timeout_sec={to}) returned {ok} after {time.monotonic()-t0:.2f}s')
    sys.exit(0 if ok else 1)
if mode == 'discover':
    while not cli.wait_for_service(timeout_sec=0.005):
        pass
    print(f'SEEN t={time.time():.3f}', flush=True)
    sys.exit(0)
# robust: bounded wait with a log line per attempt, then a bounded call
for i in range(int(to)):
    if cli.wait_for_service(timeout_sec=1.0):
        break
    log.warn(f'{cli.srv_name} not available after {i+1}s, still waiting (check ros2 service list -t)')
else:
    log.error(f'gave up on {cli.srv_name} after {int(to)}s')
    sys.exit(2)
fut = cli.call_async(Trigger.Request())
rclpy.spin_until_future_complete(node, fut, timeout_sec=5.0)
if not fut.done():
    log.error(f'{cli.srv_name} is available but sent no response within 5s')
    sys.exit(3)
log.info(f'response: success={fut.result().success} message={fut.result().message}')
X
chmod +x py_server.py py_client.py
cd $W && MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- >/tmp/build.log 2>&1 || { tail -40 /tmp/build.log; exit 1; }
source $W/install/setup.bash
echo "build ok"

SP=""
startsrv() { "$@" >/tmp/srv.log 2>&1 & SP=$!; sleep 3; echo "[server] $(grep -o 'SERVER_READY.*' /tmp/srv.log)"; }
stopsrv() { pkill -TERM -f 'lib/wsvc/(py|cpp)_server'; [ -n "$SP" ] && kill -TERM $SP 2>/dev/null; sleep 1; pkill -9 -f 'lib/wsvc/(py|cpp)_server'; [ -n "$SP" ] && { kill -9 $SP 2>/dev/null; wait $SP 2>/dev/null; }; SP=""; }
sub() { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.2f", a-b}'; }
# call <name> <type> <bound_s> [args...]: runs ros2 service call bounded by timeout, prints rc and elapsed
call() {
  local n=$1 t=$2 b=$3; shift 3
  local s=$(date +%s.%N)
  echo "\$ timeout $b ros2 service call $n $t $*"
  timeout $b ros2 service call $n $t "$@" 2>&1 | head -20
  local rc=${PIPESTATUS[0]}
  echo "rc=$rc elapsed=$(sub $(date +%s.%N) $s)s"
}
show() {
  echo "\$ ros2 service list -t"; timeout 20 ros2 service list -t 2>&1 | grep -v parameter; echo "rc=${PIPESTATUS[0]} (parameter services hidden)"
  echo "\$ ros2 service type $1"; timeout 20 ros2 service type $1 2>&1; echo "rc=$?"
  echo "\$ ros2 node list"; timeout 20 ros2 node list 2>&1
  if [ -n "$2" ]; then echo "\$ ros2 node info $2 (Service Servers part)"; timeout 20 ros2 node info $2 2>&1 | sed -n '/Service Servers/,/Service Clients/p' | grep -v parameter; fi
}
case_hdr() { echo; echo "##### $*"; ros2 daemon stop >/dev/null 2>&1; uptime; }

echo "--- ros2 service call -h (options)"
ros2 service call -h 2>&1 | sed -n '/options:/,$p'

case_hdr "C0 baseline: py server /trigger spinning"
startsrv ros2 run wsvc py_server.py trigger Trigger 1
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 20
ros2 run wsvc py_client.py /trigger once 3
ros2 run wsvc cpp_client /trigger 3
stopsrv

case_hdr "C0b baseline: cpp server /trigger spinning"
startsrv ros2 run wsvc cpp_server trigger 1
call /trigger std_srvs/srv/Trigger 20
stopsrv

case_hdr "C1 no server at all: CLI output, does it time out on its own (bounded 30s)"
call /trigger std_srvs/srv/Trigger 30
echo "lines printed in a 10s run:"; timeout 10 ros2 service call /trigger std_srvs/srv/Trigger 2>&1 | grep -c "waiting for service"
echo "--- Ctrl-C (SIGINT after 5s)"
timeout -s INT 5 ros2 service call /trigger std_srvs/srv/Trigger 2>&1 | tail -5; echo "rc=${PIPESTATUS[0]}"
if ros2 service call -h 2>&1 | grep -q -- '--timeout'; then echo "--- --timeout option exists"; call /trigger std_srvs/srv/Trigger 30 --timeout 3; fi
ros2 run wsvc py_client.py /trigger once 3
ros2 run wsvc cpp_client /trigger 3
ros2 run wsvc py_client.py /trigger robust 4; echo "rc=$?"

case_hdr "C2 wrong name: server /add_trigger, client /trigger"
startsrv ros2 run wsvc py_server.py add_trigger Trigger 1
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 8
stopsrv

case_hdr "C3 namespace: server in /robot1 with relative name 'trigger', client calls /trigger"
startsrv ros2 run wsvc py_server.py trigger Trigger 1 --ros-args -r __ns:=/robot1
show /trigger /robot1/wsvc_server
call /trigger std_srvs/srv/Trigger 8
call /robot1/trigger std_srvs/srv/Trigger 15
echo "--- py client in /robot1 using relative name 'trigger'"
ros2 run wsvc py_client.py trigger once 3 --ros-args -r __ns:=/robot1
echo "--- py client in /robot1 using absolute name '/trigger'"
ros2 run wsvc py_client.py /trigger once 3 --ros-args -r __ns:=/robot1
stopsrv
case_hdr "C3b namespace: server in /robot1 with absolute name '/trigger'"
startsrv ros2 run wsvc py_server.py /trigger Trigger 1 --ros-args -r __ns:=/robot1
call /trigger std_srvs/srv/Trigger 15
stopsrv

case_hdr "C4 remapped server name: server run with -r trigger:=trigger_v2"
startsrv ros2 run wsvc py_server.py trigger Trigger 1 --ros-args -r trigger:=trigger_v2
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 8
stopsrv
startsrv ros2 run wsvc cpp_server trigger 1 --ros-args -r trigger:=trigger_v2
echo "(cpp server)"; ros2 service list | grep trigger
stopsrv

case_hdr "C5 server created but never spins (py)"
startsrv ros2 run wsvc py_server.py trigger Trigger 0
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 10
ros2 run wsvc py_client.py /trigger once 3
ros2 run wsvc py_client.py /trigger robust 4; echo "rc=$?"
ros2 run wsvc cpp_client /trigger 3
stopsrv
case_hdr "C5b server created but never spins (cpp)"
startsrv ros2 run wsvc cpp_server trigger 0
call /trigger std_srvs/srv/Trigger 10
stopsrv

case_hdr "C6 different ROS_DOMAIN_ID: server domain 7, client default"
startsrv env ROS_DOMAIN_ID=7 ros2 run wsvc py_server.py trigger Trigger 1
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 8
ros2 run wsvc py_client.py /trigger once 3
echo "--- client with ROS_DOMAIN_ID=7"
ROS_DOMAIN_ID=7 ros2 daemon stop >/dev/null 2>&1
export ROS_DOMAIN_ID=7; show /trigger; call /trigger std_srvs/srv/Trigger 15; unset ROS_DOMAIN_ID
ROS_DOMAIN_ID=7 ros2 daemon stop >/dev/null 2>&1
stopsrv

DEF_RMW=$(python3 -c "from rclpy.utilities import get_rmw_implementation_identifier as g; print(g())")
if [ "$DEF_RMW" = rmw_cyclonedds_cpp ]; then OTHER=rmw_fastrtps_cpp; else OTHER=rmw_cyclonedds_cpp; fi
case_hdr "C7 different RMW: server $OTHER, client default $DEF_RMW"
startsrv env RMW_IMPLEMENTATION=$OTHER ros2 run wsvc py_server.py trigger Trigger 1
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 15
ros2 run wsvc py_client.py /trigger once 5
ros2 run wsvc cpp_client /trigger 5
stopsrv
case_hdr "C7b different RMW reversed: server default $DEF_RMW, client $OTHER"
startsrv ros2 run wsvc py_server.py trigger Trigger 1
export RMW_IMPLEMENTATION=$OTHER; ros2 daemon stop >/dev/null 2>&1
show /trigger
call /trigger std_srvs/srv/Trigger 15
ros2 daemon stop >/dev/null 2>&1; unset RMW_IMPLEMENTATION
stopsrv
case_hdr "C7c both on $OTHER"
startsrv env RMW_IMPLEMENTATION=$OTHER ros2 run wsvc py_server.py trigger Trigger 1
export RMW_IMPLEMENTATION=$OTHER; ros2 daemon stop >/dev/null 2>&1
call /trigger std_srvs/srv/Trigger 15
ros2 daemon stop >/dev/null 2>&1; unset RMW_IMPLEMENTATION
stopsrv

case_hdr "C8 type mismatch: server SetBool on /trigger, CLI gives Trigger"
startsrv ros2 run wsvc py_server.py trigger SetBool 1
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 10
ros2 run wsvc py_client.py /trigger once 3
ros2 run wsvc cpp_client /trigger 3
echo "--- correct type"
call /trigger std_srvs/srv/SetBool 15 "{data: true}"
echo "--- type name that does not exist"
call /trigger std_srvs/srv/Trigge 15
stopsrv

case_hdr "C9 server already exited (clean SIGTERM)"
startsrv ros2 run wsvc py_server.py trigger Trigger 1
echo "daemon view while running:"; ros2 service list | grep trigger
stopsrv; sleep 1
echo "t+2s daemon view:"; ros2 service list | grep trigger || echo "(none)"
echo "t+2s --no-daemon view:"; ros2 service list --no-daemon | grep trigger || echo "(none)"
show /trigger /wsvc_server
call /trigger std_srvs/srv/Trigger 8

case_hdr "C9b server killed with SIGKILL (crash)"
ros2 run wsvc py_server.py trigger Trigger 1 >/tmp/srv.log 2>&1 & SP=$!; sleep 3
ros2 service list | grep trigger
# kill the python process itself (ros2 run spawns it as a child)
pkill -9 -f "lib/wsvc/py_server.py"; kill -9 $SP 2>/dev/null; wait $SP 2>/dev/null; SP=""
K=$(date +%s)
for d in 1 5 15 30; do
  while [ $(( $(date +%s) - K )) -lt $d ]; do sleep 0.2; done
  echo "t+${d}s daemon: $(ros2 service list | grep trigger || echo none)  no-daemon: $(ros2 service list --no-daemon | grep trigger || echo none)"
done
call /trigger std_srvs/srv/Trigger 8
echo "--- after ros2 daemon stop"
ros2 daemon stop; ros2 service list | grep trigger || echo "(none)"

case_hdr "C10 does ros2 daemon stop change the wrong-name / domain cases?"
startsrv env ROS_DOMAIN_ID=7 ros2 run wsvc py_server.py trigger Trigger 1
ros2 daemon stop; call /trigger std_srvs/srv/Trigger 8
stopsrv
startsrv ros2 run wsvc py_server.py add_trigger Trigger 1
ros2 daemon stop; call /trigger std_srvs/srv/Trigger 8
stopsrv

case_hdr "C11 call issued before the server starts (server starts 4s later)"
( sleep 4; ros2 run wsvc py_server.py trigger Trigger 1 >/tmp/srv.log 2>&1 ) & BGP=$!
call /trigger std_srvs/srv/Trigger 20
pkill -TERM -f "lib/wsvc/py_server.py"; wait $BGP 2>/dev/null

case_hdr "C12 discovery delay: server process start -> client wait_for_service True (5 runs each)"
for kind in py cpp; do
  for i in 1 2 3 4 5; do
    ros2 run wsvc py_client.py /trigger discover >/tmp/cli.out 2>&1 & CP=$!
    sleep 3
    T0=$(date +%s.%N)
    if [ $kind = py ]; then ros2 run wsvc py_server.py trigger Trigger 1 >/tmp/srv.log 2>&1 & SP=$!
    else ros2 run wsvc cpp_server trigger 1 >/tmp/srv.log 2>&1 & SP=$!; fi
    wait $CP
    TS=$(grep -o 'SEEN t=[0-9.]*' /tmp/cli.out | cut -d= -f2)
    TR=$(grep -o 'SERVER_READY.* t=[0-9.]*' /tmp/srv.log | grep -o 't=[0-9.]*$' | cut -d= -f2)
    echo "$kind run$i: process start -> seen $(sub $TS $T0)s ; service created -> seen $(sub $TS $TR)s"
    stopsrv
  done
done
echo "--- full ros2 service call wall time against an already running py server (3 runs)"
startsrv ros2 run wsvc py_server.py trigger Trigger 1
for i in 1 2 3; do s=$(date +%s.%N); timeout 20 ros2 service call /trigger std_srvs/srv/Trigger >/tmp/c.out 2>&1; echo "run$i rc=$? $(sub $(date +%s.%N) $s)s waiting_lines=$(grep -c waiting /tmp/c.out)"; done
stopsrv
uptime
echo "=== done $ROS_DISTRO"
