#!/bin/bash
# Publishing a final "stop" message when a ROS 2 node is stopped with Ctrl+C / SIGTERM.
# Host:      bash repro.sh host humble|jazzy|lyrical   (runs the container, prints to stdout)
# Container: bash repro.sh inner                       (called by the host part)
# (no set -u: ROS setup.bash uses unset variables)
MODE=${1:-host}

if [ "$MODE" = host ]; then
  D=$2
  IMG=ros:$D-ros-base
  docker pull -q "$IMG" >/dev/null
  docker run --rm --name pk8-$D --ulimit core=0 --pids-limit 120 --cpus 1.5 \
    -v "$(cd "$(dirname "$0")" && pwd)/repro.sh:/repro.sh:ro" "$IMG" \
    bash -c "ulimit -c 0; bash /repro.sh inner"
  exit $?
fi

# ---------------- inside the container ----------------
source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1
# job control: background jobs keep the default SIGINT disposition, as a process
# started from an interactive terminal does (otherwise bash sets SIGINT to ignored)
set -m
mkdir -p /w/src/stopcpp/src && cd /w

cat > /w/listener.py <<'EOF'
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init()
n = Node('listener')
n.create_subscription(String, 'cmd', lambda m: print('GOT', m.data, flush=True) if m.data.startswith('STOP') else None, 100)
try:
    rclpy.spin(n)
except BaseException:
    pass
EOF

cat > /w/talker.py <<'EOF'
import signal, sys, time
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from std_msgs.msg import String
mode = sys.argv[1]
nohandler = mode.startswith('nohandler')
if nohandler:
    from rclpy.signals import SignalHandlerOptions
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
else:
    rclpy.init()
if mode == 'nohandler_termhandler':
    def on_term(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_term)
node = Node('talker')
pub = node.create_publisher(String, 'cmd', 10)
period = 0.001 if mode == 'timer_race' else 0.1
def tick():
    pub.publish(String(data='tick'))
node.create_timer(period, tick)

def send_stop(where):
    try:
        pub.publish(String(data='STOP'))
        print('PUBLISH_OK', where, flush=True)
    except Exception as e:
        print('PUBLISH_EXC', where, type(e).__name__, str(e), flush=True)

if mode == 'on_shutdown':
    node.context.on_shutdown(lambda: send_stop('on_shutdown'))

print('READY', flush=True)
try:
    rclpy.spin(node)
    print('SPIN_RETURNED', flush=True)
except KeyboardInterrupt:
    print('CAUGHT KeyboardInterrupt ok=%s' % rclpy.ok(), flush=True)
    if mode in ('except_publish', 'nohandler', 'nohandler_acked', 'nohandler_termhandler', 'nohandler_sigterm'):
        send_stop('except')
    if mode == 'except_publish':
        node.get_logger().info('stopping')
    if mode == 'nohandler_acked':
        t0 = time.monotonic()
        r = pub.wait_for_all_acked(Duration(seconds=1))
        print('ACKED', r, '%.4f' % (time.monotonic() - t0), flush=True)
except Exception as e:
    print('SPIN_EXC', type(e).__name__, str(e)[:200], flush=True)
finally:
    node.destroy_node()
    rclpy.try_shutdown()
    print('EXITING', flush=True)
EOF

cat > /w/src/stopcpp/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(stopcpp)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
add_executable(talker src/talker.cpp)
target_link_libraries(talker rclcpp::rclcpp ${std_msgs_TARGETS})
install(TARGETS talker DESTINATION lib/${PROJECT_NAME})
ament_package()
EOF
cat > /w/src/stopcpp/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>stopcpp</name>
  <version>0.0.0</version>
  <description>stop message on shutdown test</description>
  <maintainer email="test@example.com">test</maintainer>
  <license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><depend>std_msgs</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
cat > /w/src/stopcpp/src/talker.cpp <<'EOF'
#include <atomic>
#include <csignal>
#include <cstdio>
#include <string>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
using namespace std::chrono_literals;
static std::atomic<bool> g_stop{false};
static void on_sig(int) { g_stop = true; }

int main(int argc, char ** argv) {
  std::string mode = argv[1];
  bool nohandler = mode == "nohandler";
  if (nohandler) {
    rclcpp::init(argc, argv, rclcpp::InitOptions(), rclcpp::SignalHandlerOptions::None);
    std::signal(SIGINT, on_sig);
    std::signal(SIGTERM, on_sig);
  } else {
    rclcpp::init(argc, argv);
  }
  auto node = std::make_shared<rclcpp::Node>("talker");
  auto pub = node->create_publisher<std_msgs::msg::String>("cmd", 10);
  auto timer = node->create_wall_timer(100ms, [pub]() { std_msgs::msg::String m; m.data = "tick"; pub->publish(m); });
  auto send_stop = [pub](const char * where) {
    std_msgs::msg::String m; m.data = "STOP";
    try { pub->publish(m); std::printf("PUBLISH_RETURNED %s\n", where); }
    catch (const std::exception & e) { std::printf("PUBLISH_EXC %s %s\n", where, e.what()); }
    std::fflush(stdout);
  };
  if (mode == "on_shutdown") {
    rclcpp::on_shutdown([&]() { send_stop("on_shutdown"); });
  }
  if (mode == "pre_shutdown") {
    rclcpp::contexts::get_global_default_context()->add_pre_shutdown_callback([&]() { send_stop("pre_shutdown"); });
  }
  std::printf("READY\n"); std::fflush(stdout);
  if (nohandler) {
    rclcpp::executors::SingleThreadedExecutor exec;
    exec.add_node(node);
    while (!g_stop) exec.spin_once(100ms);
  } else {
    rclcpp::spin(node);
  }
  std::printf("SPIN_RETURNED ok=%d\n", (int)rclcpp::ok()); std::fflush(stdout);
  if (mode == "after_spin" || nohandler) {
    send_stop("after_spin");
    RCLCPP_INFO(node->get_logger(), "stopping");
  }
  if (nohandler) {
    auto t0 = std::chrono::steady_clock::now();
    bool r = pub->wait_for_all_acked(1000ms);
    std::printf("ACKED %d %.4f\n", (int)r, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
  }
  timer.reset();
  rclcpp::shutdown();
  std::printf("EXITING\n"); std::fflush(stdout);
  return 0;
}
EOF

echo "=== distro $ROS_DISTRO"
for p in rclpy rclcpp ros2cli rmw rmw_fastrtps_cpp rcl; do
  v=$(grep -o '<version>[^<]*' /opt/ros/$ROS_DISTRO/share/$p/package.xml 2>/dev/null | head -1 | cut -c10-)
  echo "VERSION $p $v"
done
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"

echo "=== colcon build stopcpp"
colcon build --packages-select stopcpp 2>&1 | tail -40
source /w/install/setup.bash
[ -n "${BUILD_ONLY:-}" ] && { ls /w/install/stopcpp/lib/stopcpp; exit 0; }

# run_one <label> <signal> <cmd...> : start listener, start talker, signal it after 2.5 s
run_one() {
  local label=$1 sig=$2; shift 2
  python3 /w/listener.py > /w/l.out 2>&1 &
  local lpid=$!
  sleep 1.5
  "$@" > /w/t.out 2>&1 &
  local tpid=$!
  sleep 2.5
  local t0=$(date +%s.%N)
  kill -$sig $tpid
  local i=0
  while kill -0 $tpid 2>/dev/null && [ $i -lt 120 ]; do sleep 0.1; i=$((i+1)); done
  if kill -0 $tpid 2>/dev/null; then kill -9 $tpid; echo "[$label] TIMEOUT killed"; fi
  wait $tpid; local rc=$?
  local t1=$(date +%s.%N)
  sleep 1
  kill -INT $lpid; wait $lpid 2>/dev/null
  local got=$(grep -c '^GOT STOP' /w/l.out)
  echo "[$label] exit=$rc exit_after_signal_s=$(awk -v a=$t0 -v b=$t1 'BEGIN{printf "%.2f", b-a}') listener_got_stop=$got"
  sed "s/^/[$label]   /" /w/t.out | grep -v '^\s*$' | head -40
}

N=${N:-10}
for mode in except_publish on_shutdown nohandler nohandler_acked nohandler_termhandler; do
  echo "=== py $mode SIGINT x$N"
  for r in $(seq 1 $N); do run_one "py:$mode:INT:$r" INT python3 /w/talker.py $mode; done
done
echo "=== py nohandler SIGTERM x3"
for r in 1 2 3; do run_one "py:nohandler_sigterm:TERM:$r" TERM python3 /w/talker.py nohandler_sigterm; done
echo "=== py nohandler_termhandler SIGTERM x$N"
for r in $(seq 1 $N); do run_one "py:nohandler_termhandler:TERM:$r" TERM python3 /w/talker.py nohandler_termhandler; done
echo "=== py except_publish SIGTERM x3"
for r in 1 2 3; do run_one "py:except_publish:TERM:$r" TERM python3 /w/talker.py except_publish; done
echo "=== py timer_race SIGINT x20 (1 kHz timer publishing)"
for r in $(seq 1 20); do run_one "py:timer_race:INT:$r" INT python3 /w/talker.py timer_race; done

for mode in after_spin on_shutdown pre_shutdown nohandler; do
  echo "=== cpp $mode SIGINT x$N"
  for r in $(seq 1 $N); do run_one "cpp:$mode:INT:$r" INT /w/install/stopcpp/lib/stopcpp/talker $mode; done
done
echo "=== cpp nohandler SIGTERM x3"
for r in 1 2 3; do run_one "cpp:nohandler:TERM:$r" TERM /w/install/stopcpp/lib/stopcpp/talker nohandler; done
echo "=== done"
