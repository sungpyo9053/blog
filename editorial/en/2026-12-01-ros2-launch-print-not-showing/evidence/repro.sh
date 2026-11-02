#!/bin/bash
# Run inside ros:<distro>-ros-base (as root). Measures when (and whether) print() / std::cout
# output from a node started by ros2 launch reaches the terminal, for different
# output=, emulate_tty, PYTHONUNBUFFERED and flush settings, plus ros2 run in a pty vs a pipe.
# The terminal is emulated with `script` (a pty for ros2 launch); every line that reaches it
# is stamped with CLOCK_MONOTONIC on arrival. Each node line carries its own emit time,
# so delay = arrival - emit.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-rcutils ros-$ROS_DISTRO-rmw \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
python3 --version
python3 - <<'X'
import inspect
from launch.actions import ExecuteProcess
try:
    from launch.actions import ExecuteLocal
    sig = inspect.signature(ExecuteLocal.__init__)
except ImportError:
    sig = inspect.signature(ExecuteProcess.__init__)
for k in ('output', 'emulate_tty'):
    print('DEFAULT', k, '=', repr(sig.parameters[k].default) if k in sig.parameters else 'n/a')
X

W=/ws; mkdir -p $W/src/pk2/src $W/src/pk2/launch; cd $W/src/pk2
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>pk2</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><depend>rclcpp</depend><exec_depend>rclpy</exec_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(pk2)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cpp_printer src/cpp_printer.cpp)
target_link_libraries(cpp_printer rclcpp::rclcpp)
install(TARGETS cpp_printer DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS printer.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
ament_package()
X
cat > printer.py <<'X'
#!/usr/bin/env python3
# mode: normal (5 x print + logger.info, 0.4 s apart, then exit), flush (same with flush=True),
#       spin (timer every 0.2 s, rclpy.spin until SIGINT), abort (5 prints then os.abort()),
#       burst (300 lines of 64 bytes, 5 ms apart)
import os, sys, time
import rclpy
from rclpy.node import Node
from rclpy.utilities import remove_ros_args
mode = (remove_ros_args(sys.argv)[1:] or ['normal'])[0]
rclpy.init(args=sys.argv)
node = Node('printer')
log = node.get_logger()
sys.stderr.write(f'ISATTY stdout={sys.stdout.isatty()} PYTHONUNBUFFERED={os.environ.get("PYTHONUNBUFFERED")}\n')
def tick(k, flush=False):
    print(f'PRINT {k} emit={time.monotonic():.3f}', flush=flush)
    log.info(f'LOG {k} emit={time.monotonic():.3f}')
if mode in ('normal', 'flush', 'abort'):
    for k in range(5):
        tick(k, flush=(mode == 'flush'))
        time.sleep(0.4)
    if mode == 'abort':
        os.abort()
elif mode == 'burst':
    for k in range(300):
        s = f'PRINT {k:03d} emit={time.monotonic():.3f} '
        print(s + 'x' * (63 - len(s)))   # 63 chars + newline = 64 bytes
        time.sleep(0.005)
elif mode == 'spin':
    state = {'k': 0}
    def cb():
        tick(state['k']); state['k'] += 1
    node.create_timer(0.2, cb)
    rclpy.spin(node)          # plain tutorial style, no try/except
node.destroy_node()
rclpy.shutdown()
X
chmod +x printer.py
cat > src/cpp_printer.cpp <<'X'
// mode: nl (std::cout << "...\n"), endl (std::endl), burst (300 x 64-byte lines with \n, 5 ms apart),
//       spin (timer every 0.2 s with \n, rclcpp::spin until SIGINT)
#include <rclcpp/rclcpp.hpp>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <string>
#include <thread>
#include <time.h>
#include <unistd.h>
static double mono() { timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }
int main(int argc, char ** argv) {
  auto args = rclcpp::init_and_remove_ros_arguments(argc, argv);
  std::string mode = args.size() > 1 ? args[1] : "nl";
  auto node = std::make_shared<rclcpp::Node>("printer");
  fprintf(stderr, "ISATTY stdout=%d\n", isatty(1));
  char buf[128];
  if (mode == "nl" || mode == "endl") {
    for (int k = 0; k < 5; ++k) {
      snprintf(buf, sizeof buf, "COUT %d emit=%.3f", k, mono());
      if (mode == "endl") std::cout << buf << std::endl; else std::cout << buf << "\n";
      RCLCPP_INFO(node->get_logger(), "LOG %d emit=%.3f", k, mono());
      std::this_thread::sleep_for(std::chrono::milliseconds(400));
    }
  } else if (mode == "burst") {
    for (int k = 0; k < 300; ++k) {
      int n = snprintf(buf, sizeof buf, "COUT %03d emit=%.3f ", k, mono());
      std::cout << buf << std::string(63 - n, 'x') << "\n";
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
  } else if (mode == "spin") {
    int k = 0;
    auto t = node->create_wall_timer(std::chrono::milliseconds(200), [&]() {
      snprintf(buf, sizeof buf, "COUT %d emit=%.3f", k, mono());
      std::cout << buf << "\n";
      RCLCPP_INFO(node->get_logger(), "LOG %d emit=%.3f", k, mono());
      ++k;
    });
    rclcpp::spin(node);
  }
  rclcpp::shutdown();
  return 0;
}
X
cat > launch/v.launch.py <<'X'
# One Node per run; the launch arguments only pick which Node(...) keywords are passed.
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def make(context):
    g = lambda n: LaunchConfiguration(n).perform(context)
    kw = dict(package='pk2', executable=g('exe'), name='printer', arguments=[g('mode')])
    if g('output') != 'default':
        kw['output'] = g('output')
    if g('tty') == 'true':
        kw['emulate_tty'] = True
    env = {}
    if g('unbuf') == 'true':
        env['PYTHONUNBUFFERED'] = '1'
    if g('rcstdout') == 'true':
        env['RCUTILS_LOGGING_USE_STDOUT'] = '1'
    if env:
        kw['additional_env'] = env
    print('NODE_KWARGS', kw)
    return [Node(**kw)]
def generate_launch_description():
    args = [DeclareLaunchArgument(n, default_value=d) for n, d in
            [('exe', 'printer.py'), ('mode', 'normal'), ('output', 'default'), ('tty', 'false'),
             ('unbuf', 'false'), ('rcstdout', 'false')]]
    return LaunchDescription(args + [OpaqueFunction(function=make)])
X
cat > /ws/stamp.py <<'X'
import sys, time
for line in iter(sys.stdin.buffer.readline, b''):
    sys.stdout.write(f'ARR {time.monotonic():.3f} ' + line.decode(errors='replace').rstrip('\r\n') + '\n')
    sys.stdout.flush()
X
cat > /ws/analyze.py <<'X'
# Summarise one stamped run: lines that reached the terminal and their delay (arrival - emit).
import re, sys
kinds = {}
first = {}
for line in open(sys.argv[1], errors='replace'):
    m = re.match(r'ARR (\d+\.\d+) (.*)', line)
    if not m:
        continue
    arr, text = float(m.group(1)), m.group(2)
    e = re.search(r'\b(PRINT|LOG|COUT) (\d+) emit=(\d+\.\d+)', text)
    if not e:
        continue
    kind, k, emit = e.group(1), int(e.group(2)), float(e.group(3))
    kinds.setdefault(kind, []).append((k, arr - emit, arr))
for kind, v in sorted(kinds.items()):
    d = [x[1] for x in v]
    arrs = sorted(set(round(x[2], 1) for x in v))
    first_k = v[0][0]
    print(f'  {kind}: on_screen={len(v)} delay_min={min(d):.3f}s delay_max={max(d):.3f}s '
          f'first_line_index={first_k} distinct_arrival_times(0.1s)={len(arrs)}')
    if len(v) > 20:
        # batches: group by arrival time within 20 ms, report line index ranges
        batches, cur = [], [v[0]]
        for x in v[1:]:
            if x[2] - cur[-1][2] < 0.02:
                cur.append(x)
            else:
                batches.append(cur); cur = [x]
        batches.append(cur)
        print(f'  {kind}: batches={len(batches)} first_batches=' +
              ', '.join(f'[{b[0][0]}..{b[-1][0]}] n={len(b)} bytes={64*len(b)}' for b in batches[:5]))
if not kinds:
    print('  nothing from the node reached the terminal')
X

cd $W
export MAKEFLAGS=-j1
T0=$(date +%s.%N)
colcon build --parallel-workers 1 --event-handlers console_direct- > /tmp/build.log 2>&1 || { tail -40 /tmp/build.log; exit 1; }
echo "BUILD_SECONDS $(echo "$(date +%s.%N) - $T0" | bc 2>/dev/null || python3 -c "print(round($(date +%s.%N)-$T0,1))")"
source $W/install/setup.bash

logfiles() {   # what the run left in ~/.ros/log
  for f in $(find /root/.ros/log -type f 2>/dev/null | sort); do
    echo "  LOGFILE ${f#/root/.ros/log/} PRINT=$(grep -c 'PRINT' $f) COUT=$(grep -c 'COUT' $f) LOG=$(grep -c 'LOG [0-9]' $f)"
  done
}
run_launch() {  # name, launch args...
  local name=$1; shift
  rm -rf /root/.ros/log
  echo; echo "### $name: ros2 launch pk2 v.launch.py $*"
  local t0=$(python3 -c 'import time;print(time.monotonic())')
  script -qfec "ros2 launch pk2 v.launch.py $*" /dev/null < /dev/null | python3 -u /ws/stamp.py > /tmp/$name.raw
  echo "  wall=$(python3 -c "import time;print(round(time.monotonic()-$t0,2))")s"
  python3 /ws/analyze.py /tmp/$name.raw
  grep -h 'ISATTY' /tmp/$name.raw | sed 's/^ARR [0-9.]* /  /' | head -1
  logfiles
  echo "  --- raw (first 14 lines, arrival time relative to start)"
  python3 - /tmp/$name.raw $t0 <<'X'
import sys
t0 = float(sys.argv[2])
for i, l in enumerate(open(sys.argv[1], errors='replace')):
    if i >= 14: break
    p = l.split(' ', 2)
    print(f'  +{float(p[1]) - t0:6.2f}s {p[2].rstrip()[:150]}')
X
}
run_sigint() {  # name, launch args...  (SIGINT to the launch's process group after 3 s, like Ctrl+C)
  local name=$1; shift
  rm -rf /root/.ros/log
  echo; echo "### $name: ros2 launch pk2 v.launch.py $*  + SIGINT to process group at 3 s"
  script -qfec "ros2 launch pk2 v.launch.py $*" /dev/null < /dev/null | python3 -u /ws/stamp.py > /tmp/$name.raw &
  sleep 3
  local lp=$(pgrep -f 'bin/ros2 launch' | head -1)
  local pg=$(ps -o pgid= -p $lp | tr -d ' ')
  kill -INT -- -$pg
  wait
  python3 /ws/analyze.py /tmp/$name.raw
  grep -h -E 'process has finished|process has died|KeyboardInterrupt|ExternalShutdown|signal_handler|Traceback' /tmp/$name.raw | sed 's/^ARR [0-9.]* /  /' | head -6
  logfiles
}
run_run() {  # name, pty|pipe, ros2 run args...
  local name=$1 how=$2; shift 2
  rm -rf /root/.ros/log
  echo; echo "### $name: ros2 run pk2 $* ($how)"
  if [ $how = pty ]; then
    script -qfec "ros2 run pk2 $*" /dev/null < /dev/null | python3 -u /ws/stamp.py > /tmp/$name.raw
  else
    ros2 run pk2 "$@" 2>&1 | python3 -u /ws/stamp.py > /tmp/$name.raw
  fi
  python3 /ws/analyze.py /tmp/$name.raw
  grep -h 'ISATTY' /tmp/$name.raw | sed 's/^ARR [0-9.]* /  /' | head -1
}

run_launch py_default        exe:=printer.py mode:=normal
run_launch py_screen         exe:=printer.py mode:=normal output:=screen
run_launch py_screen_tty     exe:=printer.py mode:=normal output:=screen tty:=true
run_launch py_screen_unbuf   exe:=printer.py mode:=normal output:=screen unbuf:=true
run_launch py_screen_flush   exe:=printer.py mode:=flush  output:=screen
run_launch py_both           exe:=printer.py mode:=normal output:=both
run_launch py_log            exe:=printer.py mode:=normal output:=log
run_launch py_screen_rcstdout exe:=printer.py mode:=normal output:=screen rcstdout:=true
run_launch py_burst_screen   exe:=printer.py mode:=burst  output:=screen
run_launch py_abort_screen   exe:=printer.py mode:=abort  output:=screen
run_launch py_abort_tty      exe:=printer.py mode:=abort  output:=screen tty:=true
run_sigint py_spin_sigint    exe:=printer.py mode:=spin   output:=screen
run_launch cpp_default       exe:=cpp_printer mode:=nl
run_launch cpp_screen_nl     exe:=cpp_printer mode:=nl    output:=screen
run_launch cpp_screen_endl   exe:=cpp_printer mode:=endl  output:=screen
run_launch cpp_screen_tty    exe:=cpp_printer mode:=nl    output:=screen tty:=true
run_launch cpp_burst_screen  exe:=cpp_printer mode:=burst output:=screen
run_sigint cpp_spin_sigint   exe:=cpp_printer mode:=spin  output:=screen
run_run run_py_pty   pty  printer.py normal
run_run run_py_pipe  pipe printer.py normal
run_run run_cpp_pty  pty  cpp_printer nl
run_run run_cpp_pipe pipe cpp_printer nl
# Python's stdout block size when stdout is a pipe (no ROS involved): 2500 lines of 64 bytes,
# 1 ms apart, piped into the stamper. Batch sizes show how much is held before each write.
cat > /ws/burst.py <<'X'
import sys, time
n = int(sys.argv[1])
for k in range(n):
    s = f'PRINT {k:04d} emit={time.monotonic():.3f} '
    print(s + 'x' * (63 - len(s)))
    time.sleep(0.001)
X
echo; echo "### python_pipe_buffer: python3 burst.py 2500 | stamper"
python3 -c "import io, sys; print('  io.DEFAULT_BUFFER_SIZE =', io.DEFAULT_BUFFER_SIZE, ' python', sys.version.split()[0])"
python3 /ws/burst.py 2500 | python3 -u /ws/stamp.py > /tmp/pybuf.raw
python3 /ws/analyze.py /tmp/pybuf.raw
echo; echo "=== done $ROS_DISTRO"
