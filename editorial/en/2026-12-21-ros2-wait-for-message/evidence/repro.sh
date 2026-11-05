#!/bin/bash
# Run inside ros:<distro>-ros-base (default RMW). Measures rclpy and rclcpp wait_for_message:
# signature per distro, normal/timeout/no-timeout, transient_local and best_effort publishers,
# wrong type, calls inside a callback, calls while the node spins in another thread,
# repeated calls, and ros2 topic echo --once as the CLI alternative.
ulimit -c 0
export PYTHONUNBUFFERED=1
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2topic ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
T=/t; mkdir -p $T; cd $T

cat > pub.py <<'X'
#!/usr/bin/env python3
# pub.py <reliable|best_effort> <volatile|transient_local> <rate_hz, 0=once> <string|int>
import sys, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String, Int32
rel, dur, rate, typ = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
rclpy.init()
n = Node('test_pub')
q = QoSProfile(depth=1,
    reliability=ReliabilityPolicy.RELIABLE if rel == 'reliable' else ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.TRANSIENT_LOCAL if dur == 'transient_local' else DurabilityPolicy.VOLATILE)
T = String if typ == 'string' else Int32
p = n.create_publisher(T, '/chatter', q)
i = [0]
def tick():
    m = T(); i[0] += 1
    m.data = f'hello {i[0]}' if T is String else i[0]
    p.publish(m)
if rate == 0:
    tick()
else:
    n.create_timer(1.0 / rate, tick)
try:
    rclpy.spin(n)
except Exception:
    pass
X

cat > wfm.py <<'X'
#!/usr/bin/env python3
import sys, time, inspect, threading, resource, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.wait_for_message import wait_for_message
from std_msgs.msg import String, Int32
case = sys.argv[1]
rclpy.init()
node = Node('waiter')
def call(**kw):
    t0 = time.monotonic()
    try:
        ok, msg = wait_for_message(kw.pop('typ', String), node, '/chatter', **kw)
    except TypeError as e:
        print(f'RESULT case={case} TypeError: {e}'); return None
    dt = time.monotonic() - t0
    print(f'RESULT case={case} ok={ok} msg={getattr(msg, "data", None)!r} elapsed={dt:.3f}s')
    return ok
if case == 'sig':
    print('SIGNATURE', inspect.signature(wait_for_message))
    print('MODULE', inspect.getsourcefile(wait_for_message))
    print('SOURCE-BEGIN')
    print('\n'.join(l for l in inspect.getsource(wait_for_message).splitlines() if l.strip()))
    print('SOURCE-END')
elif case == 'normal':
    for _ in range(5): call(time_to_wait=5.0)
elif case == 'timeout':
    call(time_to_wait=1.0)
elif case == 'forever':
    print('calling with default time_to_wait'); call()
elif case in ('latched_default', 'default_qos'):
    call(time_to_wait=3.0)
elif case == 'latched_qos':
    call(time_to_wait=3.0, qos_profile=QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
elif case == 'sensor_qos':
    call(time_to_wait=3.0, qos_profile=qos_profile_sensor_data)
elif case == 'wrong_type':
    call(time_to_wait=3.0, typ=Int32)
elif case == 'in_callback':
    done = []
    def cb():
        if done: return
        done.append(1); call(time_to_wait=3.0)
    node.create_timer(0.2, cb)
    ex = SingleThreadedExecutor(); ex.add_node(node)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5: ex.spin_once(timeout_sec=0.1)
elif case == 'spinning_thread':
    ex = MultiThreadedExecutor(); ex.add_node(node)
    th = threading.Thread(target=ex.spin, daemon=True); th.start()
    time.sleep(1.0)
    res = []
    for _ in range(20):
        t0 = time.monotonic()
        try:
            ok, msg = wait_for_message(String, node, '/chatter', time_to_wait=2.0)
        except Exception as e:
            print('EXC', type(e).__name__, e); ok = 'exc'
        res.append((ok, round(time.monotonic() - t0, 3)))
    print(f'RESULT case={case} ok_count={sum(1 for r in res if r[0] is True)}/20 results={res}')
    print(f'EXECUTOR thread alive after the calls: {th.is_alive()}')
    ex.shutdown(); th.join(timeout=3)
elif case in ('spin_timer_same', 'spin_timer_sep'):
    # node spins in a background executor with a 10 Hz timer; wait_for_message is called
    # on the same node or on a separate helper node that is not in any executor
    ticks = [0]
    node.create_timer(0.1, lambda: ticks.__setitem__(0, ticks[0] + 1))
    ex = SingleThreadedExecutor(); ex.add_node(node)
    th = threading.Thread(target=ex.spin, daemon=True); th.start()
    time.sleep(1.0)
    helper = node if case == 'spin_timer_same' else Node('waiter_helper')
    oks = []
    for _ in range(20):
        t0 = time.monotonic()
        ok, _m = wait_for_message(String, helper, '/chatter', time_to_wait=2.0)
        oks.append((ok, round(time.monotonic() - t0, 3)))
    t_before = ticks[0]; time.sleep(2.0); t_after = ticks[0]
    print(f'RESULT case={case} ok_count={sum(1 for o in oks if o[0])}/20 wfm_results={oks} executor_alive={th.is_alive()} timer_ticks_in_next_2s={t_after - t_before}')
    ex.shutdown(); th.join(timeout=3)
elif case == 'repeat':
    N = int(sys.argv[2]); el = []
    c0 = resource.getrusage(resource.RUSAGE_SELF)
    for k in range(N):
        t0 = time.monotonic()
        ok, _ = wait_for_message(String, node, '/chatter', time_to_wait=2.0)
        el.append(time.monotonic() - t0)
        if k in (0, N // 2 - 1, N - 1):
            r = resource.getrusage(resource.RUSAGE_SELF)
            print(f'REPEAT call={k+1} ok={ok} cpu_user+sys={r.ru_utime + r.ru_stime:.3f}s subs_on_node={len(list(node.subscriptions))}')
    a = el[:N // 2]; b = el[N // 2:]
    print(f'RESULT case={case} N={N} mean_first_half={1000*sum(a)/len(a):.2f}ms mean_second_half={1000*sum(b)/len(b):.2f}ms max={1000*max(el):.2f}ms')
    print(f'SUBS after loop: {len(list(node.subscriptions))}, topic subscriptions in graph: {node.count_subscribers("/chatter")}')
node.destroy_node(); rclpy.try_shutdown()
X
chmod +x pub.py wfm.py

startpub() { python3 pub.py "$@" > /t/pub.log 2>&1 & PUB=$!; sleep 2; }
stoppub() { kill -INT $PUB 2>/dev/null; wait $PUB 2>/dev/null; }
run() { echo "--- $*"; timeout 60 python3 wfm.py "$@" 2>&1 | grep -v '^$'; echo "exit=${PIPESTATUS[0]}"; }

echo "===== PY sig"; run sig
echo "===== PY normal (reliable volatile 10 Hz publisher)"; startpub reliable volatile 10 string; run normal; stoppub
echo "===== PY timeout (no publisher, time_to_wait=1.0)"; run timeout
echo "===== PY forever (no publisher, default time_to_wait, killed by timeout 5)"
echo "--- forever"; timeout 5 python3 wfm.py forever 2>&1; echo "exit=$?"
echo "===== PY latched (transient_local publisher, published once 2 s before the call)"
startpub reliable transient_local 0 string; run latched_default; run latched_qos; stoppub
echo "===== PY best_effort 10 Hz publisher"
startpub best_effort volatile 10 string; run default_qos; run default_qos; run default_qos; run sensor_qos; stoppub
echo "===== PY wrong type (String publisher, wait for Int32)"
startpub reliable volatile 10 string; run wrong_type; stoppub
echo "===== PY inside a timer callback of a spinning node"
startpub reliable volatile 10 string; run in_callback; stoppub
echo "===== PY node spinning in a MultiThreadedExecutor thread"
startpub reliable volatile 10 string; run spinning_thread; stoppub
echo "===== PY spinning node with timer: same node vs separate helper node"
startpub reliable volatile 10 string; for k in 1 2 3; do run spin_timer_same; done; run spin_timer_sep; stoppub
echo "===== PY repeated calls (100 Hz publisher)"
startpub reliable volatile 100 string; run repeat 400; stoppub

echo "===== CLI ros2 topic echo --once"
ros2 topic echo --help 2>&1 | grep -E -- '--once|--timeout|--qos-durability' | sed 's/^ */HELP /'
startpub reliable volatile 10 string
s=$(date +%s.%N); timeout 20 ros2 topic echo --once /chatter std_msgs/msg/String 2>&1 | head -3; echo "exit=${PIPESTATUS[0]} elapsed=$(python3 -c "import sys;print(round(float(sys.argv[1])-float(sys.argv[2]),3))" $(date +%s.%N) $s)"
stoppub
startpub reliable transient_local 0 string
echo "--- echo --once, default QoS, latched publisher"
s=$(date +%s.%N); timeout 8 ros2 topic echo --once /chatter std_msgs/msg/String 2>&1 | head -3; echo "exit=${PIPESTATUS[0]} elapsed=$(python3 -c "import sys;print(round(float(sys.argv[1])-float(sys.argv[2]),3))" $(date +%s.%N) $s)"
echo "--- echo --once --qos-durability transient_local"
s=$(date +%s.%N); timeout 8 ros2 topic echo --once --qos-durability transient_local --qos-reliability reliable /chatter std_msgs/msg/String 2>&1 | head -3; echo "exit=${PIPESTATUS[0]} elapsed=$(python3 -c "import sys;print(round(float(sys.argv[1])-float(sys.argv[2]),3))" $(date +%s.%N) $s)"
stoppub
echo "--- echo --once --timeout 2 (no publisher)"
s=$(date +%s.%N); timeout 8 ros2 topic echo --once --timeout 2 /chatter std_msgs/msg/String 2>&1 | head -3; echo "exit=${PIPESTATUS[0]} elapsed=$(python3 -c "import sys;print(round(float(sys.argv[1])-float(sys.argv[2]),3))" $(date +%s.%N) $s)"

echo "===== CPP header"
H=$(find /opt/ros/$ROS_DISTRO/include -name wait_for_message.hpp | head -1); echo "header=$H"
grep -n -A8 '^bool wait_for_message' $H | grep -v '^\s*$' | head -60
QOSARG=0; grep -q 'rclcpp::QoS' $H && QOSARG=1; echo "header_has_qos=$QOSARG"
mkdir -p /ws/src/wfmcpp/src; cd /ws/src/wfmcpp
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>wfmcpp</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><depend>std_msgs</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(wfmcpp)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(wfm src/wfm.cpp)
target_compile_definitions(wfm PRIVATE HAS_QOS=$QOSARG)
target_link_libraries(wfm rclcpp::rclcpp \${std_msgs_TARGETS})
install(TARGETS wfm DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
cat > src/wfm.cpp <<'X'
#include <chrono>
#include <cstdio>
#include <string>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/wait_for_message.hpp>
#include <std_msgs/msg/string.hpp>
using namespace std::chrono_literals;
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  std::string c = argc > 1 ? argv[1] : "normal";
  auto node = std::make_shared<rclcpp::Node>("waiter_cpp");
  std_msgs::msg::String m;
  auto t0 = std::chrono::steady_clock::now();
  bool ok = false;
  if (c == "qos") {
#if HAS_QOS
    ok = rclcpp::wait_for_message(m, node, "/chatter", 3s, rclcpp::QoS(1).reliable().transient_local());
#else
    printf("RESULT case=qos not compiled: header has no QoS parameter\n"); rclcpp::shutdown(); return 0;
#endif
  } else {
    ok = rclcpp::wait_for_message(m, node, "/chatter", c == "timeout" ? 1s : 3s);
  }
  double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  printf("RESULT case=%s ok=%d msg='%s' elapsed=%.3fs\n", c.c_str(), ok, m.data.c_str(), dt);
  rclcpp::shutdown();
}
X
cd /ws && timeout 600 colcon build --event-handlers console_direct- > /t/build.log 2>&1 && echo "build ok" || { echo "build FAILED"; tail -40 /t/build.log; }
source /ws/install/setup.bash
cd $T
crun() { echo "--- cpp $1"; timeout 30 ros2 run wfmcpp wfm $1 2>&1; echo "exit=$?"; }
startpub reliable volatile 10 string; crun normal; stoppub
crun timeout
startpub reliable transient_local 0 string; crun normal; crun qos; stoppub
echo "=== done"
