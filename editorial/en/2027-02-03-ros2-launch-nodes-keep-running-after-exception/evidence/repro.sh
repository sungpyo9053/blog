#!/bin/bash
# What happens to nodes that ros2 launch already started when the launch then fails
# ("Caught exception in launch"), and which fixes clean them up.
# Upstream report: https://github.com/ros2/launch/issues/747 (fix: ros2/launch PR #996, rolling only).
#
# Host side (one distro at a time, never in parallel):
#   docker run --rm --init --network none --name pk66-<distro> -v /tmp/en-pick66:/w \
#     ros:<distro>-ros-base bash /w/repro.sh > out_<distro>.txt 2>&1
# Inside the container everything below runs. /w is the mounted work dir.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=66
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
D=$ROS_DISTRO
echo "=== distro=$D date=$(date -u +%FT%TZ)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-launch ros-$D-launch-ros ros-$D-ros2launch ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-rmw-fastrtps-cpp ros-$D-tf2-ros 2>/dev/null
python3 --version
echo "RMW default: ${RMW_IMPLEMENTATION:-unset (Fast DDS)}"

# ---------- helper files ----------
cat > /w/pynode.py <<'X'
import sys, rclpy
from rclpy.node import Node
from std_msgs.msg import Int32
rclpy.init()
n = Node(sys.argv[1])
p = n.create_publisher(Int32, 'pk66_' + sys.argv[1], 10)
k = [0]
def tick():
    k[0] += 1
    p.publish(Int32(data=k[0]))
n.create_timer(0.1, tick)
try:
    rclpy.spin(n)
except Exception:
    pass
X

cat > /w/alive.py <<'X'
# Count live (non-zombie) test node processes: static_transform_publisher with __node:=pk66*, or pynode.py.
import os, sys, signal
out = []
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        cmd = open(f'/proc/{pid}/cmdline', 'rb').read().split(b'\0')
        stat = open(f'/proc/{pid}/stat').read()
    except OSError:
        continue
    cmd = [c.decode() for c in cmd if c]
    name = None
    for c in cmd:
        if c.startswith('__node:=pk66'):
            name = c.split(':=')[1]
    if any(c.endswith('pynode.py') for c in cmd):
        name = cmd[-1]
    if name is None:
        continue
    f = stat.rsplit(')', 1)[1].split()
    state, ppid, pgid = f[0], f[1], f[2]
    if state == 'Z':
        continue
    out.append((int(pid), name, ppid, pgid))
if len(sys.argv) > 1 and sys.argv[1] == '--kill':
    for pid, *_ in out:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    sys.exit(0)
print(f"{len(out)}[" + ",".join(f"{n}:ppid{pp}:pg{pg}" for _, n, pp, pg in sorted(out, key=lambda x: x[1])) + "]")
X

cat > /w/child_bad.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        Node(package='tf2_ros', executable='static_transform_publisher', name='pk66child',
             arguments=['--frame-id', 'pk66_c_p', '--child-frame-id', 'pk66_c']),
        Node(package='tf2_ros', executable='fake_node', name='pk66bad'),
    ])
X

cat > /w/case.launch.py <<'X'
import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, OpaqueFunction, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def stf(name):
    return Node(package='tf2_ros', executable='static_transform_publisher', name=name,
                arguments=['--frame-id', name + '_p', '--child-frame-id', name])

def py(name):
    return ExecuteProcess(cmd=['python3', '/w/pynode.py', name], name=name)

def bad():
    return Node(package='tf2_ros', executable='fake_node', name='pk66bad')

def boom(context):
    raise RuntimeError('pk66 boom inside OpaqueFunction')

def generate_launch_description():
    c = os.environ.get('CASE', 'ok')
    g = [stf('pk66a'), stf('pk66b')]
    cases = {
        'ok': g,
        'bad_last': g + [bad()],
        'bad_first': [bad()] + g,
        'typo_kwarg': g + [Node(ackage='tf2_ros', executable='static_transform_publisher')] if c == 'typo_kwarg' else [],
        'opaque': g + [OpaqueFunction(function=boom)],
        'missing_lc': g + [Node(package='tf2_ros', executable='static_transform_publisher', name='pk66c',
                                arguments=['--frame-id', LaunchConfiguration('not_declared'), '--child-frame-id', 'x'])],
        'include_bad': g + [IncludeLaunchDescription(PythonLaunchDescriptionSource('/w/child_bad.launch.py'))],
        'include_missing': g + [IncludeLaunchDescription(PythonLaunchDescriptionSource('/w/does_not_exist.launch.py'))],
        'timer_bad': g + [TimerAction(period=2.0, actions=[bad()])],
        'py_ok': [py('pk66pa'), py('pk66pb')],
        'py_bad_last': [py('pk66pa'), py('pk66pb'), bad()],
    }
    return LaunchDescription(cases[c])
X

# Same change as ros2/launch PR #996 (_is_idle also waits for pending asyncio tasks).
cat > /w/patch_launch.py <<'X'
import re, sys, shutil, launch.launch_service as m
f = m.__file__
if sys.argv[1] == 'restore':
    shutil.copy(f + '.orig', f); print('restored', f); sys.exit(0)
shutil.copy(f, f + '.orig')
s = open(f).read(); n = 0
s, k = re.subn(r'(\n(\s+)self\.__this_task(: [^=]+)? = None\n)', r'\1\2self.__process_one_event_task = None\n', s, count=1); n += k
s, k = re.subn(r'\n(\s+)return number_of_entity_future_pairs == 0 and self\.__context\._event_queue\.empty\(\)\n',
    '\n\\1if self.event_loop is not None:\n'
    '\\1    ignore = {self.__this_task, self.__process_one_event_task}\n'
    '\\1    active = [t for t in asyncio.all_tasks(self.event_loop) if t not in ignore and not t.done()]\n'
    '\\1else:\n\\1    active = []\n'
    '\\1return (number_of_entity_future_pairs == 0 and self.__context._event_queue.empty() and len(active) == 0)\n', s, count=1); n += k
s, k = re.subn(r'\n(\s+)(process_one_event_task = this_loop\.create_task\(self\._process_one_event\(\)\))\n',
    r'\n\1\2\n\1self.__process_one_event_task = process_one_event_task\n', s, count=1); n += k
open(f, 'w').write(s)
print('patched', f, 'hunks', n, 'of 3')
X

# Start a command the way a terminal would: SIGINT at its default action (a background job of a
# non-interactive bash inherits SIGINT as ignored) and in its own session/process group.
cat > /w/spawn.py <<'X'
import os, signal, sys
signal.signal(signal.SIGINT, signal.SIG_DFL)
os.setsid()
os.execvp(sys.argv[1], sys.argv[1:])
X

ms() { date +%s%N | cut -b1-13; }

# run CASE TAG [SIG DELAY]
# SIG: none | INTgrp (Ctrl+C: SIGINT to the whole process group) | INT | TERM | KILL (to the launch pid only)
run() {
  local c=$1 tag=$2 sig=${3:-none} d=${4:-0} first=${5:-0}
  local t0=$(ms) note=""
  CASE=$c python3 /w/spawn.py ros2 launch /w/case.launch.py > /tmp/l.txt 2>&1 &
  local pid=$!
  [ "$first" = 1 ] && { sleep 0.05; echo "--- launch pid $pid $(grep SigIgn /proc/$pid/status 2>/dev/null)"; }
  if [ "$sig" != none ]; then
    sleep $d
    case $sig in INTgrp) kill -INT -- -$pid ;; INT) kill -INT $pid ;; TERM) kill -TERM $pid ;; KILL) kill -KILL $pid ;; esac
  fi
  local i=0
  while kill -0 $pid 2>/dev/null && [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done
  if kill -0 $pid 2>/dev/null; then kill -KILL $pid; note=" launch_still_running_30s_killed"; fi
  wait $pid; local rc=$?
  local dur=$(( $(ms) - t0 ))
  sleep 1; local a1=$(python3 /w/alive.py)
  if [ "$first" = 1 ]; then
    echo "--- log excerpt case=$c tag=$tag sig=$sig"
    grep -E "ERROR|Caught|xception|rror:|process started|process has finished|signal|SIGTERM|SIGINT|SIGKILL" /tmp/l.txt | sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9-]+-[0-9a-f]+/<logdir>/' | head -14
    echo "--- ros2 node list --no-daemon (after launch exited)"
    timeout 20 ros2 node list --no-daemon --spin-time 3 2>&1 | head -8
  fi
  sleep 2; local a2=$(python3 /w/alive.py)
  kill -TERM -- -$pid 2>/dev/null; sleep 1.5
  local a3=$(python3 /w/alive.py)
  python3 /w/alive.py --kill; sleep 0.3
  echo "RUN case=$c tag=$tag sig=$sig delay=$d launch_pid=$pid rc=$rc dur_ms=$dur alive_1s=$a1 alive_later=$a2 after_kill_pgroup=$a3$note"
}

series() { # CASE TAG REPS [SIG DELAY]
  local c=$1 tag=$2 n=$3 sig=${4:-none} d=${5:-0}
  for r in $(seq 1 $n); do run $c $tag $sig $d $([ $r = 1 ] && echo 1 || echo 0); done
}

echo "=== uptime: $(cat /proc/loadavg)"
echo "=== PHASE 1: stock launch, failure after nodes were started"
series bad_last stock 6
series bad_first stock 4
series typo_kwarg stock 3
series opaque stock 6
series missing_lc stock 6
series include_bad stock 6
series include_missing stock 4
series timer_bad stock 4
series py_bad_last stock 6

echo "=== PHASE 2: stock launch, signals to a healthy launch (2 static_transform_publisher nodes)"
for d in 0.1 0.3 1 3; do series ok stock 4 INTgrp $d; done
series py_ok stock 3 INTgrp 0.3
series py_ok stock 3 INTgrp 3
series ok stock 3 INT 3
series ok stock 3 TERM 3
series ok stock 3 KILL 3

echo "=== PHASE 3: ros2 launch --print-description does not run anything"
for c in bad_last missing_lc include_missing; do
  CASE=$c timeout 30 ros2 launch --print-description /w/case.launch.py > /tmp/p.txt 2>&1; echo "PRINT case=$c rc=$? lines=$(wc -l < /tmp/p.txt) alive=$(python3 /w/alive.py)"; grep -E "ERROR|xception" /tmp/p.txt | head -3
done

echo "=== uptime: $(cat /proc/loadavg)"
echo "=== PHASE 4: launch_service.py patched like ros2/launch PR #996"
python3 /w/patch_launch.py apply
series bad_last pr996 6
series bad_first pr996 3
series opaque pr996 6
series missing_lc pr996 6
series include_bad pr996 6
series include_missing pr996 3
series py_bad_last pr996 6
series ok pr996 4 INTgrp 0.1
series ok pr996 4 INTgrp 0.3
python3 /w/patch_launch.py restore
echo "=== done $(date -u +%FT%TZ) load: $(cat /proc/loadavg)"
