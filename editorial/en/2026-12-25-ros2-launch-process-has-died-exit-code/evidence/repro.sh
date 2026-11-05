#!/bin/bash
# "process has died [pid N, exit code X, cmd ...]" in ros2 launch: what each exit code means,
# where the real error text goes, and how gdb, PYTHONFAULTHANDLER, respawn and on_exit=Shutdown behave.
#
# Host (runner):    bash repro.sh host <distro>   -> container pk16-<distro> from ros:<distro>-ros-base
# Inside container: bash /work/repro.sh inner     (called by host mode)
MODE=${1:-}
if [ "$MODE" = host ]; then
  D=$2
  ulimit -c 0
  docker pull -q ros:$D-ros-base >/dev/null
  # --memory caps the OOM case inside this container only
  docker run --name pk16-$D --ulimit core=0 --cpus 1.5 --memory 1200m --memory-swap 1200m --pids-limit 300 \
    -v "$(dirname "$(readlink -f "$0")")":/work ros:$D-ros-base bash /work/repro.sh inner
  exit $?
fi
[ "$MODE" = inner ] || { echo "usage: repro.sh host <distro> | inner"; exit 2; }
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO $(date '+%F %T %Z')"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-ros2run ros-$ROS_DISTRO-rmw-implementation \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "compiler: $(g++ --version | head -1); python: $(python3 --version)"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-unset}"
echo "core pattern: $(cat /proc/sys/kernel/core_pattern); ulimit -c: $(ulimit -c)"

mkdir -p /ws/src/crash_demo/src /ws/src/crash_demo/scripts && cd /ws/src/crash_demo
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>crash_demo</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><exec_depend>rclpy</exec_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(crash_demo)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_library(crash_helper SHARED src/helper.cpp)
add_executable(crasher src/crasher.cpp)
target_link_libraries(crasher rclcpp::rclcpp)
add_executable(needs_lib src/needs_lib.cpp)
target_link_libraries(needs_lib crash_helper)
install(TARGETS crash_helper LIBRARY DESTINATION lib)
install(TARGETS crasher needs_lib DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS scripts/py_crasher.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > src/helper.cpp <<'X'
int helper_value() { return 42; }
X
cat > src/needs_lib.cpp <<'X'
#include <cstdio>
int helper_value();
int main() { std::printf("helper says %d\n", helper_value()); return 0; }
X
cat > src/crasher.cpp <<'X'
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <rclcpp/rclcpp.hpp>
using namespace std::chrono_literals;
__attribute__((noinline)) void write_through_null(int *p) { *p = 1; }
__attribute__((noinline)) void read_sensor() { throw std::runtime_error("sensor driver returned -1"); }
class Crasher : public rclcpp::Node {
 public:
  Crasher() : Node("crasher") {
    mode_ = declare_parameter<std::string>("mode", "segv");
    RCLCPP_INFO(get_logger(), "started, mode=%s, crashing in 1 s", mode_.c_str());
    timer_ = create_wall_timer(1s, [this]() { tick(); });
  }
 private:
  void tick() {
    RCLCPP_INFO(get_logger(), "about to crash (%s)", mode_.c_str());
    if (mode_ == "segv") { int *p = nullptr; write_through_null(p); }
    else if (mode_ == "throw") { read_sensor(); }
    else if (mode_ == "abort") { std::abort(); }
    else if (mode_ == "exit1") { RCLCPP_ERROR(get_logger(), "giving up"); std::exit(1); }
    else if (mode_ == "oom") {
      std::vector<char *> keep;
      for (int i = 0; i < 64; ++i) { char *b = static_cast<char *>(std::malloc(64 << 20)); std::memset(b, 1, 64 << 20); keep.push_back(b); }
      RCLCPP_INFO(get_logger(), "allocated 4 GB without being killed");
    }
  }
  std::string mode_;
  rclcpp::TimerBase::SharedPtr timer_;
};
int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Crasher>());
  rclcpp::shutdown();
  return 0;
}
X
cat > scripts/py_crasher.py <<'X'
#!/usr/bin/env python3
import ctypes, sys
import rclpy
from rclpy.node import Node
class PyCrasher(Node):
    def __init__(self):
        super().__init__('crasher')
        self.mode = self.declare_parameter('mode', 'raise').value
        self.get_logger().info(f'started, mode={self.mode}, crashing in 1 s')
        self.create_timer(1.0, self.tick)
    def tick(self):
        self.get_logger().info(f'about to crash ({self.mode})')
        if self.mode == 'raise':
            raise ValueError('sensor driver returned -1')
        if self.mode == 'segv':
            ctypes.string_at(0)
        if self.mode == 'exit2':
            sys.exit(2)
def main():
    rclpy.init()
    rclpy.spin(PyCrasher())
main()
X
cat > /ws/case.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, OpaqueFunction, RegisterEventHandler, Shutdown
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
ARGS = {'exe': 'crasher', 'mode': 'segv', 'output': 'default', 'prefix': '', 'respawn': 'false',
        'respawn_delay': '1.0', 'shutdown': 'false', 'faulthandler': 'false', 'companion': '6', 'cmd': ''}
def setup(context):
    g = lambda k: LaunchConfiguration(k).perform(context)
    kw = {}
    if g('output') != 'default':
        kw['output'] = g('output')
    if g('prefix'):
        kw['prefix'] = g('prefix')
    if g('respawn') == 'true':
        kw['respawn'] = True
        kw['respawn_delay'] = float(g('respawn_delay'))
    if g('shutdown') == 'true':
        kw['on_exit'] = Shutdown(reason='crasher exited')
    if g('faulthandler') == 'true':
        kw['additional_env'] = {'PYTHONFAULTHANDLER': '1'}
    if g('cmd'):
        main = ExecuteProcess(cmd=g('cmd').split(), name='plain', **kw)
    else:
        main = Node(package='crash_demo', executable=g('exe'), name='crasher', parameters=[{'mode': g('mode')}], **kw)
    companion = ExecuteProcess(cmd=['sleep', g('companion')], name='companion')
    handler = RegisterEventHandler(OnProcessExit(target_action=main,
        on_exit=lambda ev, ctx: LogInfo(msg='HANDLER returncode=%s' % ev.returncode)))
    return [main, companion, handler]
def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in ARGS.items()] + [OpaqueFunction(function=setup)])
X

build() {  # extra cmake args
  cd /ws && rm -rf build install log
  local t0=$(date +%s)
  colcon build ${1:+--cmake-args "$@"} > /tmp/build.log 2>&1; local rc=$?
  echo "colcon build $* rc=$rc in $(( $(date +%s) - t0 )) s"; [ $rc = 0 ] || tail -30 /tmp/build.log
  source /ws/install/setup.bash
}
show() {
  sed -E 's/^/  | /' "$1" | grep -vE 'Default logging verbosity|All log files can be found' | head -${2:-40}
}
run_case() {  # name timeout launch-args...
  local name=$1 to=$2; shift 2
  rm -rf /root/.ros/log
  echo; echo "--- case=$name args=[$*] load=$(cut -d' ' -f1 /proc/loadavg)"
  local t0=$(date +%s%N)
  timeout -s INT $to ros2 launch /ws/case.launch.py "$@" > /tmp/run.log 2>&1; local rc=$?
  local ms=$(( ($(date +%s%N) - t0) / 1000000 ))
  echo "ros2 launch exit=$rc after ${ms} ms (timeout ${to}s; 124 = stopped by the timeout's SIGINT)"
  show /tmp/run.log ${MAXL:-40}
  local d=$(ls -d /root/.ros/log/*/ 2>/dev/null | head -1)
  echo "  log dir files: $(ls $d 2>/dev/null | tr '\n' ' ')"
  for pat in "sensor driver returned" "Traceback" "terminate called" "process has died" "Fatal Python error" "error while loading shared" "HANDLER returncode"; do
    local s=$(grep -c "$pat" /tmp/run.log); local f=$(cat $d/* 2>/dev/null | grep -c "$pat")
    [ "$s$f" != "00" ] && echo "  '$pat': screen=$s, log dir=$f"
  done
}

build
echo "binary has debug info (default build): $(readelf -S /ws/install/crash_demo/lib/crash_demo/crasher | grep -c debug_info) debug_info sections"

echo; echo "##### A. Without launch: the binary directly, and ros2 run"
for m in segv throw abort exit1; do
  /ws/install/crash_demo/lib/crash_demo/crasher --ros-args -p mode:=$m > /tmp/d.log 2>&1; rc=$?
  echo "direct binary mode=$m exit=$rc; last lines:"; tail -2 /tmp/d.log | sed 's/^/  | /'
  timeout 20 ros2 run crash_demo crasher --ros-args -p mode:=$m > /tmp/r.log 2>&1; rc=$?
  echo "ros2 run mode=$m exit=$rc; last 2 lines:"; tail -2 /tmp/r.log | sed 's/^/  | /'
done
echo "bash -c with the segv binary (what an interactive shell prints):"
timeout 20 bash -c '/ws/install/crash_demo/lib/crash_demo/crasher --ros-args -p mode:=segv > /dev/null 2>&1; echo "exit=$?"' 2>&1 | sed 's/^/  | /'
for m in raise segv exit2; do
  timeout 20 ros2 run crash_demo py_crasher.py --ros-args -p mode:=$m > /tmp/r.log 2>&1; rc=$?
  echo "ros2 run py_crasher mode=$m exit=$rc; last 3 lines:"; tail -3 /tmp/r.log | sed 's/^/  | /'
done

echo; echo "##### B. Each crash under ros2 launch (default output, companion process sleep 6)"
run_case cpp_segv 25 exe:=crasher mode:=segv
run_case cpp_throw 25 exe:=crasher mode:=throw
run_case cpp_abort 25 exe:=crasher mode:=abort
run_case cpp_exit1 25 exe:=crasher mode:=exit1
run_case cpp_oom 40 exe:=crasher mode:=oom
run_case py_raise 25 exe:=py_crasher.py mode:=raise
run_case py_segv 25 exe:=py_crasher.py mode:=segv
run_case py_exit2 25 exe:=py_crasher.py mode:=exit2
run_case cpp_throw_screen 25 exe:=crasher mode:=throw output:=screen
run_case lib_ok 25 exe:=needs_lib
mv /ws/install/crash_demo/lib/libcrash_helper.so /tmp/
run_case lib_missing 25 exe:=needs_lib
mv /tmp/libcrash_helper.so /ws/install/crash_demo/lib/
run_case cmd_missing 25 cmd:=no_such_program

echo; echo "##### C. Options"
run_case py_segv_faulthandler 25 exe:=py_crasher.py mode:=segv faulthandler:=true
run_case cpp_segv_shutdown 25 exe:=crasher mode:=segv shutdown:=true companion:=20
MAXL=14 run_case cpp_segv_respawn 9 exe:=crasher mode:=segv respawn:=true respawn_delay:=1.0 companion:=30
echo "  'process started' lines: $(grep -c 'process started' /tmp/run.log); 'process has died' lines: $(grep -c 'process has died' /tmp/run.log)"

echo; echo "##### D. gdb as a prefix"
apt-get update -qq > /dev/null 2>&1; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gdb > /dev/null 2>&1; echo "gdb: $(gdb --version | head -1)"
MAXL=60 run_case cpp_segv_gdb_default_build 60 exe:=crasher mode:=segv output:=screen "prefix:=gdb -batch -ex run -ex bt --args"
MAXL=60 run_case cpp_throw_gdb_default_build 60 exe:=crasher mode:=throw output:=screen "prefix:=gdb -batch -ex run -ex bt --args"
build -DCMAKE_BUILD_TYPE=RelWithDebInfo
echo "binary has debug info (RelWithDebInfo): $(readelf -S /ws/install/crash_demo/lib/crash_demo/crasher | grep -c debug_info) debug_info sections"
MAXL=60 run_case cpp_segv_gdb_relwithdebinfo 60 exe:=crasher mode:=segv output:=screen "prefix:=gdb -batch -ex run -ex bt --args"
echo; echo "=== done $(date '+%F %T %Z')"
