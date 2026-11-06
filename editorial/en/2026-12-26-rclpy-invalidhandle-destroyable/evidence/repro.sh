#!/bin/bash
# rclpy "InvalidHandle: cannot use Destroyable because destruction was requested":
# which destroy_* calls trigger it, how often, what happens to the executor, and which fixes stop it.
#
# Host (runner):    bash repro.sh host <distro>   -> container pk17-<distro> from ros:<distro>-ros-base
# Inside container: bash /work/repro.sh inner     (called by host mode)
# Extra pass:       EXTRA=1 bash repro.sh host <distro>  -> container pk17-<distro>-extra, only the deferred-destroy service case
MODE=${1:-}
if [ "$MODE" = host ]; then
  D=$2
  ulimit -c 0
  docker pull -q ros:$D-ros-base >/dev/null
  NAME=pk17-$D; [ "${EXTRA:-0}" = 1 ] && NAME=pk17-$D-extra
  docker run --name $NAME -e EXTRA=${EXTRA:-0} --ulimit core=0 --cpus 1.5 --memory 1200m --memory-swap 1200m --pids-limit 300 \
    -v "$(dirname "$(readlink -f "$0")")":/work ros:$D-ros-base bash /work/repro.sh inner
  exit $?
fi
[ "$MODE" = inner ] || { echo "usage: repro.sh host <distro> | inner"; exit 2; }
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO $(date '+%F %T %Z')"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "python: $(python3 --version); RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"
python3 -c "import rclpy._rclpy_pybind11 as m; print('InvalidHandle class:', m.InvalidHandle.__module__ + '.' + m.InvalidHandle.__name__)"

W=/tmp/pk; mkdir -p $W && cd $W
cat > talker.py <<'X'
# publishes std_msgs/String on /chatter at about 500 Hz until killed
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init()
n = Node('talker')
p = n.create_publisher(String, 'chatter', 10)
m = String(); m.data = 'x'
n.create_timer(0.002, lambda: p.publish(m))
try:
    rclpy.spin(n)
except BaseException:
    pass
X

cat > race.py <<'X'
import os, sys, threading, time, traceback
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.qos import QoSProfile
from std_msgs.msg import String
from std_srvs.srv import Trigger

case = sys.argv[1]; cycles = int(sys.argv[2]); trial = sys.argv[3]
def load(): return open('/proc/loadavg').read().split()[0]
def last(e): return type(e).__module__ + '.' + type(e).__name__ + ': ' + str(e).splitlines()[0] if str(e) else type(e).__module__ + '.' + type(e).__name__

rclpy.init()
node = Node('racer')
got = [0]
def cb(msg): got[0] += 1
ex = MultiThreadedExecutor(num_threads=2) if 'multi' in case else SingleThreadedExecutor()
SLP = float(os.environ.get('SLP', '0.02'))
KEEP = []
SHARED = MutuallyExclusiveCallbackGroup()
def KW():
    if 'sharedgroup' in case: return {'callback_group': SHARED}  # one group created once, reused
    if 'newgroup' in case:
        g = MutuallyExclusiveCallbackGroup()
        if 'keepref' in case: KEEP.append(g)  # keep every group object alive
        return {'callback_group': g}
    return {}
ex.add_node(node)
state = {'dead': None, 'caught': 0, 'first': None, 'frames': None}

def spin_plain():
    try:
        ex.spin()
    except BaseException as e:
        state['dead'] = last(e)
        tb = traceback.extract_tb(e.__traceback__)
        state['frames'] = ' <- '.join('%s:%s' % (f.name, f.line) for f in tb[-3:][::-1])

def spin_guarded():
    # fix: keep spinning and count the exceptions instead of letting the thread die
    from rclpy._rclpy_pybind11 import InvalidHandle
    while rclpy.ok() and not state.get('stop'):
        try:
            ex.spin_once(timeout_sec=0.1)
        except InvalidHandle as e:
            state['caught'] += 1
            state['first'] = state['first'] or last(e)
        except BaseException as e:
            state['dead'] = last(e); return

t0 = time.monotonic()
done = 0
err_main = None
if case in ('single_bg_sub', 'multi_bg_sub', 'multi_bg_sub_newgroup', 'multi_bg_sub_sharedgroup', 'multi_bg_sub_newgroup_keepref', 'guarded_multi_bg_sub_newgroup', 'single_bg_timer', 'single_bg_pub', 'single_bg_node', 'multi_bg_node'):
    th = threading.Thread(target=spin_guarded if case.startswith('guarded') else spin_plain, daemon=True); th.start()
    time.sleep(0.3)
    try:
        for i in range(cycles):
            if case == 'single_bg_timer':
                t = node.create_timer(0.001, lambda: None); time.sleep(0.02); node.destroy_timer(t)
            elif case == 'single_bg_pub':
                p = node.create_publisher(String, 'chatter2', 10); time.sleep(0.02); node.destroy_publisher(p)
            elif case.endswith('bg_node'):
                s = node.create_subscription(String, 'chatter', cb, 10); time.sleep(0.5)
                node.destroy_node(); done = 1; time.sleep(0.5); break
            else:
                s = node.create_subscription(String, 'chatter', cb, 10, **KW()); time.sleep(SLP); node.destroy_subscription(s)
            done = i + 1
            if state['dead']: break
    except BaseException as e:
        err_main = last(e)
    time.sleep(0.3)
    alive = th.is_alive(); state['stop'] = True
elif case == 'cb_destroy_service_deferred':
    # fix: the service callback only schedules the destroy; a one-shot timer does it after the response went out
    st = {}
    def later():
        node.destroy_timer(st['t']); node.destroy_service(st['srv']); st['destroyed'] = True
    def srv_cb(req, res):
        st['t'] = node.create_timer(0.0, later); res.success = True; return res
    st['srv'] = node.create_service(Trigger, 'trig', srv_cb)
    th = threading.Thread(target=spin_plain, daemon=True); th.start()
    cn = rclpy.create_node('caller'); cli = cn.create_client(Trigger, 'trig')
    cli.wait_for_service(timeout_sec=5.0)
    f = cli.call_async(Trigger.Request()); rclpy.spin_until_future_complete(cn, f, timeout_sec=3.0)
    time.sleep(1.0)
    print('deferred: response received=%s success=%s service destroyed=%s server still visible to client=%s' % (
        f.done(), f.result().success if f.done() else None, st.get('destroyed'), cli.service_is_ready()))
    done = 1; alive = th.is_alive()
elif case in ('cb_cycle_sub', 'multi_cb_cycle_sub_newgroup', 'cb_self_destroy_sub', 'cb_destroy_timer', 'cb_destroy_service'):
    # all create/destroy work happens inside callbacks of the same SingleThreadedExecutor
    st = {'n': 0, 'sub': None, 'timer': None}
    def tick():
        if st['sub'] is not None: node.destroy_subscription(st['sub'])
        st['sub'] = node.create_subscription(String, 'chatter', cb, 10, **KW()); st['n'] += 1
    def self_cb(msg):
        node.destroy_subscription(st['sub'])
        st['n'] += 1
        st['sub'] = node.create_subscription(String, 'chatter', self_cb, 10)
    if case in ('cb_cycle_sub', 'multi_cb_cycle_sub_newgroup'):
        node.create_timer(0.02, tick)
    elif case == 'cb_self_destroy_sub':
        st['sub'] = node.create_subscription(String, 'chatter', self_cb, 10)
    elif case == 'cb_destroy_timer':
        def oneshot():
            node.destroy_timer(st['timer']); st['n'] += 1
            st['timer'] = node.create_timer(0.005, oneshot)
        st['timer'] = node.create_timer(0.005, oneshot)
    elif case == 'cb_destroy_service':
        def srv_cb(req, res):
            node.destroy_service(st['srv']); st['n'] += 1
            st['srv'] = node.create_service(Trigger, 'trig', srv_cb)
            res.success = True; return res
        st['srv'] = node.create_service(Trigger, 'trig', srv_cb)
        cn = rclpy.create_node('caller'); cli = cn.create_client(Trigger, 'trig')
        def caller():
            cli.wait_for_service(timeout_sec=5.0)
            for _ in range(cycles):
                f = cli.call_async(Trigger.Request())
                rclpy.spin_until_future_complete(cn, f, timeout_sec=2.0)
                if not f.done(): state['timeouts'] = state.get('timeouts', 0) + 1
                if state['dead']: break
        threading.Thread(target=caller, daemon=True).start()
    th = threading.Thread(target=spin_plain, daemon=True); th.start()
    limit = time.monotonic() + 30
    while st['n'] < cycles and time.monotonic() < limit and not state['dead']:
        time.sleep(0.05)
    done = st['n']; alive = th.is_alive()
elif case == 'stopped_multi_bg_sub_newgroup':
    # fix: stop the executor thread, destroy, then start spinning again
    alive = True
    for i in range(cycles):
        s = node.create_subscription(String, 'chatter', cb, 10, **KW())
        stop = threading.Event()
        def run():
            try:
                while not stop.is_set(): ex.spin_once(timeout_sec=0.01)
            except BaseException as e:
                state['dead'] = last(e)
        th = threading.Thread(target=run, daemon=True); th.start()
        time.sleep(SLP)
        stop.set(); th.join()
        node.destroy_subscription(s)
        done = i + 1
        if state['dead']: alive = False; break
elif case == 'use_after_destroy':
    p = node.create_publisher(String, 'chatter2', 10)
    s = node.create_subscription(String, 'chatter', cb, 10)
    print('destroy_publisher returned', node.destroy_publisher(p), '; second call returned', node.destroy_publisher(p))
    try:
        p.publish(String(data='x')); print('publish after destroy_publisher: no exception')
    except BaseException as e:
        print('publish after destroy_publisher:', last(e))
    p2 = node.create_publisher(String, 'chatter3', 10)
    node.destroy_node()
    try:
        p2.publish(String(data='x')); print('publish after destroy_node: no exception')
    except BaseException as e:
        print('publish after destroy_node:', last(e))
    try:
        node.create_subscription(String, 'chatter', cb, 10); print('create_subscription after destroy_node: no exception')
    except BaseException as e:
        print('create_subscription after destroy_node:', last(e))
    rclpy.shutdown(); sys.exit(0)

el = time.monotonic() - t0
print('RESULT case=%s trial=%s cycles_done=%d/%d executor_alive=%s dead=%s caught=%d first_caught=%s main_err=%s timeouts=%s msgs=%d elapsed=%.1fs load=%s' % (
    case, trial, done, cycles, alive, state['dead'], state['caught'], state['first'], err_main, state.get('timeouts', 0), got[0], el, load()))
if state['frames']: print('  frames (innermost first):', state['frames'])
sys.stdout.flush()
import os; os._exit(0)
X

if [ "${EXTRA:-0}" = 1 ]; then
  echo "--- cb_destroy_service_deferred (extra pass)"
  for t in 1 2 3 4 5; do timeout 60 python3 race.py cb_destroy_service_deferred 1 $t 2>&1 | grep -E "RESULT|frames|deferred"; done
  echo "=== end extra $(date '+%F %T %Z') load=$(cat /proc/loadavg)"
  exit 0
fi
# rclcpp counterpart: reset() a subscription shared_ptr from another thread while spinning
mkdir -p ws/src/cpp_race/src && cd ws/src/cpp_race
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>cpp_race</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(cpp_race)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(race_cpp src/race.cpp)
target_link_libraries(race_cpp rclcpp::rclcpp ${std_msgs_TARGETS})
install(TARGETS race_cpp DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > src/race.cpp <<'X'
#include <chrono>
#include <cstdio>
#include <thread>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
int main(int argc, char ** argv) {
  int cycles = argc > 1 ? std::atoi(argv[1]) : 200;
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("racer_cpp");
  rclcpp::executors::SingleThreadedExecutor ex;
  ex.add_node(node);
  std::thread th([&] { ex.spin(); });
  long msgs = 0; int done = 0;
  for (int i = 0; i < cycles; ++i) {
    auto s = node->create_subscription<std_msgs::msg::String>("chatter", 10,
      [&](std_msgs::msg::String::ConstSharedPtr) { ++msgs; });
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    s.reset();
    done = i + 1;
  }
  ex.cancel(); th.join();
  std::printf("RESULT case=cpp_bg_reset cycles_done=%d/%d msgs=%ld\n", done, cycles, msgs);
  rclcpp::shutdown();
  return 0;
}
X
cd $W/ws
echo "load before colcon: $(cat /proc/loadavg)"
B0=$(date +%s.%N)
MAKEFLAGS=-j1 colcon build --event-handlers console_direct- 2>&1 | tail -3
echo "colcon build seconds: $(echo "$(date +%s.%N) - $B0" | bc 2>/dev/null || python3 -c "print(round($(date +%s.%N)-$B0,1))")"
cd $W

python3 talker.py >/dev/null 2>&1 &
TALK=$!
sleep 2
CYC=200
for c in single_bg_sub multi_bg_sub multi_bg_sub_newgroup multi_bg_sub_sharedgroup multi_bg_sub_newgroup_keepref single_bg_timer single_bg_pub; do
  echo "--- $c ($CYC create/destroy cycles from the main thread, executor spinning in a second thread)"
  for t in 1 2 3 4 5; do timeout 60 python3 race.py $c $CYC $t 2>&1 | grep -E "RESULT|frames" ; done
done
echo "--- single_bg_sub fast (1000 cycles, 1 ms between create and destroy)"
for t in 1 2 3 4 5; do SLP=0.001 timeout 60 python3 race.py single_bg_sub 1000 $t 2>&1 | grep -E "RESULT|frames"; done
echo "--- multi_bg_sub (default group) fast (1000 cycles, 1 ms)"
for t in 1 2 3 4 5; do SLP=0.001 timeout 60 python3 race.py multi_bg_sub 1000 $t 2>&1 | grep -E "RESULT|frames"; done
for c in single_bg_node multi_bg_node; do
  echo "--- $c (destroy_node from main thread while spinning)"
  for t in 1 2 3 4 5; do timeout 60 python3 race.py $c 1 $t 2>&1 | grep -E "RESULT|frames"; done
done
for c in guarded_multi_bg_sub_newgroup stopped_multi_bg_sub_newgroup cb_cycle_sub multi_cb_cycle_sub_newgroup cb_self_destroy_sub cb_destroy_timer cb_destroy_service; do
  echo "--- $c"
  for t in 1 2 3 4 5; do timeout 60 python3 race.py $c $CYC $t 2>&1 | grep -E "RESULT|frames|Error|error" | head -4; done
done
echo "--- use_after_destroy"
timeout 60 python3 race.py use_after_destroy 1 1 2>&1 | tail -6
echo "--- 400 cycles single executor, then interpreter exit while ex.spin() still runs in a daemon thread (stderr unfiltered)"
timeout 60 python3 - <<'X' 2>&1 | head -40
import sys, threading, time
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
rclpy.init(); n = Node('racer_tb'); ex = SingleThreadedExecutor(); ex.add_node(n)
th = threading.Thread(target=ex.spin, daemon=True); th.start(); time.sleep(0.3)
for i in range(400):
    s = n.create_subscription(String, 'chatter', lambda m: None, 10); time.sleep(0.02); n.destroy_subscription(s)
    if not th.is_alive(): print('executor thread died after cycle', i + 1); break
else:
    print('no failure in 400 cycles')
X
echo "--- rclcpp: reset() subscriptions from main thread while spinning"
source $W/ws/install/setup.bash
for t in 1 2 3 4 5; do timeout 60 ros2 run cpp_race race_cpp 200; echo "  exit=$? load=$(cut -d' ' -f1 /proc/loadavg)"; done 2>&1 | grep -vE "^\[INFO"
kill $TALK 2>/dev/null; wait $TALK 2>/dev/null
echo "=== end $(date '+%F %T %Z') load=$(cat /proc/loadavg)"
