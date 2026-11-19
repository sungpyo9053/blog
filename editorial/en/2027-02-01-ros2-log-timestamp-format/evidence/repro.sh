#!/bin/bash
# ROS 2 console log format: {time} vs readable timestamps, RCUTILS_CONSOLE_OUTPUT_FORMAT tokens,
# launch, log files, colors and sim time. Run inside ros:<distro>-ros-base, no network needed:
#   docker run --rm --name pk64-<distro> --network none --pids-limit 60 --cpus 1.5 \
#     -e TZ=UTC -v /tmp/en-pick64:/w ros:<distro>-ros-base bash /w/repro.sh > out_<distro>.txt 2>&1
# An earlier Jazzy pass of this script (ROS_LOCALHOST_ONLY set on every distro, no section K) was discarded;
# out_jazzy.txt, out_humble.txt and out_lyrical.txt all come from this version, run in that order.
ulimit -c 0
export ROS_DOMAIN_ID=88 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
# ROS_LOCALHOST_ONLY only on Humble: Jazzy/Lyrical print a deprecation WARN for it, which would fill every sample line
[ "$ROS_DISTRO" = humble ] && export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
D=$ROS_DISTRO
source /opt/ros/$D/setup.bash
sec() { echo; echo "### $*"; }
# show output with escape characters visible (cat -v), drop blank lines
show() { cat -v | grep -v '^$' | head -n "${1:-8}"; }

echo "=== distro=$D nproc=$(nproc) date=$(date -u +%FT%TZ) TZ=$TZ load=$(cut -d' ' -f1-3 /proc/loadavg)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rcutils ros-$D-rcl ros-$D-rcl-logging-spdlog ros-$D-rclpy \
  ros-$D-rclcpp ros-$D-ros2cli ros-$D-launch ros-$D-launch-ros ros-$D-rmw ros-$D-rmw-fastrtps-cpp ros-$D-tf2-ros 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"

mkdir -p /tmp/t && cd /tmp/t
cat > py_log.py <<'X'
import rclpy
rclpy.init()
n = rclpy.create_node('fmt_py')
n.get_logger().info('hello from rclpy')
n.get_logger().warning('warn from rclpy')
rclpy.shutdown()
X
# C++ logger without compiling: static_transform_publisher logs one INFO line at start
cpp() { timeout -s INT 3 ros2 run tf2_ros static_transform_publisher --x 1 --frame-id a --child-frame-id b 2>&1; }
py() { timeout 20 python3 py_log.py 2>&1; }

sec "A default format (env unset), no tty"
py | show; cpp | show 3
echo "wall clock now: $(date -u +%s.%N) $(date -u '+%F %T')"

sec "B one token per run"
for tok in '{time}' '{time_as_nanoseconds}' '{date_time_with_ms}' '{severity}' '{name}' '{function_name}' \
           '{file_name}' '{line_number}' '{message}' '{datetime}' '{date_time}' '{time:%H:%M:%S}' '{TIME}'; do
  echo "--- FORMAT='[$tok] {message}'"
  RCUTILS_CONSOLE_OUTPUT_FORMAT="[$tok] {message}" py | show 1
  RCUTILS_CONSOLE_OUTPUT_FORMAT="[$tok] {message}" cpp | show 1
done

sec "C full readable formats"
for f in '[{severity}] [{date_time_with_ms}] [{name}]: {message}' \
         '[{severity}] [{time}] [{name}]: {message} ({function_name}() at {file_name}:{line_number})' \
         '' ' ' 'plain text no tokens' '{{time}} {message}' '{message' ; do
  echo "--- FORMAT='$f'"
  RCUTILS_CONSOLE_OUTPUT_FORMAT="$f" py | show 2
  RCUTILS_CONSOLE_OUTPUT_FORMAT="$f" cpp | show 1
done

sec "D time zone of {date_time_with_ms}"
for z in UTC Asia/Seoul America/New_York; do
  echo "--- TZ=$z (zoneinfo present: $( [ -e /usr/share/zoneinfo/$z ] && echo yes || echo no))"
  TZ=$z RCUTILS_CONSOLE_OUTPUT_FORMAT='{date_time_with_ms} {time} {message}' py | show 1
done
echo "date -u: $(date -u '+%F %T')"

sec "E colors (cat -v shows ^[[ escapes)"
for c in unset 0 1; do
  echo "--- RCUTILS_COLORIZED_OUTPUT=$c, stdout is a pipe"
  if [ $c = unset ]; then py | show 2; else RCUTILS_COLORIZED_OUTPUT=$c py | show 2; fi
done
echo "--- under script(1) pseudo-tty, env unset"
script -qec "python3 py_log.py" /dev/null 2>&1 | show 2

sec "F log file under ROS_LOG_DIR"
rm -rf /tmp/rl; export ROS_LOG_DIR=/tmp/rl
RCUTILS_CONSOLE_OUTPUT_FORMAT='[{severity}] [{date_time_with_ms}] [{name}]: {message}' py | show 2
f=$(ls /tmp/rl/*.log | head -1); echo "file: $(basename $f)"; cat -v "$f"
rm -rf /tmp/rl
RCUTILS_CONSOLE_OUTPUT_FORMAT='{message}' cpp | show 1
f=$(ls /tmp/rl/*.log | head -1); echo "file (cpp, console format {message}): $(basename $f)"; cat -v "$f" | head -3
unset ROS_LOG_DIR

sec "G ros2 launch"
mkdir -p /tmp/lf
cat > /tmp/lf/a.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable
from launch_ros.actions import Node
import os
def generate_launch_description():
    acts = []
    if os.environ.get('SETENV_IN_LAUNCH'):
        acts.append(SetEnvironmentVariable('RCUTILS_CONSOLE_OUTPUT_FORMAT', '[{severity}] [{date_time_with_ms}] [{name}]: {message}'))
    node_env = {'RCUTILS_CONSOLE_OUTPUT_FORMAT': 'NODE_ENV {date_time_with_ms} {message}'} if os.environ.get('NODE_ENV') else None
    acts.append(Node(package='tf2_ros', executable='static_transform_publisher', name='stp',
                     arguments=['--x', '1', '--frame-id', 'a', '--child-frame-id', 'b'],
                     output='screen', additional_env=node_env))
    acts.append(ExecuteProcess(cmd=['python3', '/tmp/t/py_log.py'], output='screen'))
    return LaunchDescription(acts)
X
L() { timeout -s INT 6 ros2 launch /tmp/lf/a.launch.py 2>&1 | grep -v '^$' | cat -v | head -12; }
echo "--- env unset"; L
echo "--- env exported in the shell before ros2 launch"
RCUTILS_CONSOLE_OUTPUT_FORMAT='[{severity}] [{date_time_with_ms}] [{name}]: {message}' L
echo "--- SetEnvironmentVariable inside the launch file"
SETENV_IN_LAUNCH=1 L
echo "--- Node(additional_env=...) for the C++ node only"
NODE_ENV=1 L
echo "--- RCUTILS_COLORIZED_OUTPUT=1 in shell"
RCUTILS_COLORIZED_OUTPUT=1 L
echo "--- launch.log file (first lines)"
ls -t ~/.ros/log/*/launch.log 2>/dev/null | head -1 | xargs -r head -4 | cat -v

sec "H use_sim_time: does the log time follow /clock?"
cat > sim.py <<'X'
import rclpy, time
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock
from builtin_interfaces.msg import Time
rclpy.init()
n = rclpy.create_node('sim_n', parameter_overrides=[Parameter('use_sim_time', Parameter.Type.BOOL, True)])
pub = n.create_publisher(Clock, '/clock', 10)
t_end = time.time() + 3
while time.time() < t_end and n.get_clock().now().nanoseconds == 0:
    pub.publish(Clock(clock=Time(sec=100, nanosec=500000000)))
    rclpy.spin_once(n, timeout_sec=0.1)
print('node clock now (ns):', n.get_clock().now().nanoseconds, 'wall:', time.time())
n.get_logger().info('logged under sim time')
rclpy.shutdown()
X
RCUTILS_CONSOLE_OUTPUT_FORMAT='[{time}] [{date_time_with_ms}] {message}' timeout 30 python3 sim.py 2>&1 | show 3

sec "I cost per line: 20000 rclpy info() calls, stderr to /dev/null"
cat > bench.py <<'X'
import rclpy, time, os
rclpy.init()
n = rclpy.create_node('bench')
lg = n.get_logger()
t = time.perf_counter()
for i in range(20000):
    lg.info('msg %d' % i)
dt = time.perf_counter() - t
rclpy.shutdown()
print('%-60r %.1f us/line' % (os.environ.get('RCUTILS_CONSOLE_OUTPUT_FORMAT'), dt / 20000 * 1e6))
X
export ROS_LOG_DIR=/tmp/rlb
for rep in 1 2 3; do
for f in '[{severity}] [{time}] [{name}]: {message}' '[{severity}] [{date_time_with_ms}] [{name}]: {message}' '{message}'; do
  rm -rf /tmp/rlb
  RCUTILS_CONSOLE_OUTPUT_FORMAT="$f" timeout 120 python3 bench.py 2>/dev/null
done; done
unset ROS_LOG_DIR

sec "J converting an existing {time} log to readable time"
RCUTILS_CONSOLE_OUTPUT_FORMAT='[{severity}] [{time}] [{name}]: {message}' py > /tmp/old.log 2>&1
cat /tmp/old.log
echo "--- after the python one-liner"
python3 -c "import re,sys,datetime as d
for l in sys.stdin: sys.stdout.write(re.sub(r'\[(\d{10})\.(\d+)\]', lambda m: '['+d.datetime.fromtimestamp(int(m.group(1)), d.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')+'.'+m.group(2)[:3]+']', l, 1))" < /tmp/old.log
sec "K {date_time_with_ms} vs {time} on the same line, 400 lines spread over the second"
cat > cmp.py <<'X'
import rclpy, time
rclpy.init()
n = rclpy.create_node('cmp')
for i in range(400):
    n.get_logger().info('x')
    time.sleep(0.0037)
rclpy.shutdown()
X
RCUTILS_CONSOLE_OUTPUT_FORMAT='{time} {date_time_with_ms} {message}' timeout 60 python3 cmp.py > /tmp/cmp.txt 2>&1
python3 - <<'X'
import datetime as d
bad = []; tot = 0; lt100 = 0
for l in open('/tmp/cmp.txt'):
    p = l.split()
    if len(p) < 4 or p[-1] != 'x' or not p[0][0].isdigit(): continue
    tot += 1
    sec, frac = p[0].split('.')
    want = d.datetime.fromtimestamp(int(sec), d.timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + '.' + frac[:3]
    got = p[1] + ' ' + p[2]
    if int(frac[:3]) < 100: lt100 += 1
    if got != want: bad.append((p[0], got, want))
print('lines=%d  ms<100=%d  mismatches=%d' % (tot, lt100, len(bad)))
for b in bad[:6]: print('time=%s  date_time_with_ms=%s  expected=%s' % b)
ok = [l for l in open('/tmp/cmp.txt') if l.split() and l.split()[0][0].isdigit()][:2]
print('first lines:'); print(''.join(ok), end='')
X
echo "--- C++ node, 15 starts, same format"
for i in $(seq 15); do RCUTILS_CONSOLE_OUTPUT_FORMAT='{time} {date_time_with_ms} {message}' cpp | grep Spinning; done
echo "=== done $(date -u +%FT%TZ)"
