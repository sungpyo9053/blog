#!/bin/bash
# image_transport republish (compressed <-> raw) repro, one distro per container.
# Host side (runner, one distro at a time, no core dumps, DDS isolated):
#   docker run --rm --name pk38-$D --ulimit core=0 --pids-limit 256 --cpus 1.5 -e ROS_DOMAIN_ID=88 \
#     -e ROS_LOCALHOST_ONLY=1 (Humble) | -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST (Jazzy, Lyrical) \
#     -v /tmp/en-pick48:/w ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
# The default bridge network is used only by apt-get.
set +u
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export RCUTILS_COLORIZED_OUTPUT=0 PYTHONUNBUFFERED=1
D=$ROS_DISTRO
echo "=== distro $D domain $ROS_DOMAIN_ID localhost_only=${ROS_LOCALHOST_ONLY:-} range=${ROS_AUTOMATIC_DISCOVERY_RANGE:-}"
apt-get update -qq > /tmp/apt.log 2>&1
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$D-image-transport >> /tmp/apt.log 2>&1; echo "apt image_transport exit=$?"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw-fastrtps-cpp ros-$D-image-transport ros-$D-compressed-image-transport 2>&1

mkdir -p /y
cat > /y/pub.py <<'PY'
# 640x480 rgb8 test pattern at 10 Hz on /camera/image_raw (rclpy, raw only)
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
rclpy.init()
n = Node('fake_camera')
p = n.create_publisher(Image, '/camera/image_raw', 10)
W, H = 640, 480
row = bytes((x * 255 // W) for x in range(W) for _ in range(3))
base = bytearray(row * H)
k = [0]
def tick():
    m = Image(); m.header.stamp = n.get_clock().now().to_msg(); m.header.frame_id = 'cam'
    m.width, m.height, m.encoding, m.step = W, H, 'rgb8', W * 3
    b = bytearray(base); i = (k[0] * 997) % (len(b) - 300); b[i:i+300] = bytes(300); k[0] += 1
    m.data = bytes(b); p.publish(m)
n.create_timer(0.1, tick)
try:
    rclpy.spin(n)
except BaseException:
    pass
PY
cat > /y/probe.py <<'PY'
# probe.py TOPIC raw|compressed SECONDS -> message count and first message summary
import sys, time, rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
topic, kind, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
rclpy.init()
n = Node('probe')
got = []
n.create_subscription(Image if kind == 'raw' else CompressedImage, topic, lambda m: got.append(m), 10)
t0 = time.time()
while time.time() - t0 < secs:
    rclpy.spin_once(n, timeout_sec=0.1)
if not got:
    print(f'PROBE {topic} ({kind}): 0 messages in {secs:.0f} s')
else:
    m = got[0]
    if kind == 'raw':
        s = f'{m.width}x{m.height} {m.encoding} bytes={len(m.data)}'
    else:
        s = f'format="{m.format}" bytes={len(m.data)}'
    print(f'PROBE {topic} ({kind}): {len(got)} messages in {secs:.0f} s, first: {s}')
PY

setsid python3 /y/pub.py > /tmp/pub.log 2>&1 &
PUB=$!
sleep 3
python3 /y/probe.py /camera/image_raw raw 3

# Every command runs in its own process group (setsid) so the republish child of
# "ros2 run" / "ros2 launch" is stopped too: SIGINT first, SIGKILL 2 s later.
stop_grp() { kill -INT -- -$1 2>/dev/null; sleep 2; kill -9 -- -$1 2>/dev/null; wait $1 2>/dev/null; }
# run_case NAME CMD... : start CMD, probe /image (raw) for 5 s, list topics, SIGINT after ~12 s, show output
run_case() {
  local name=$1; shift
  echo; echo "### CASE $name"; echo "\$ $*"
  setsid "$@" > /tmp/case.log 2>&1 &
  local pg=$!
  sleep 5
  python3 /y/probe.py /image raw 5
  echo "topics: $(timeout 10 ros2 topic list --no-daemon 2>/dev/null | grep -vE '^/(rosout|parameter_events|camera/image_raw)$' | tr '\n' ' ')"
  local alive=no; kill -0 $pg 2>/dev/null && alive=yes
  echo "still running after probe: $alive"
  stop_grp $pg
  echo "--- output (first 8 lines)"; head -n 8 /tmp/case.log | cut -c1-400
  echo "--- last lines:"; tail -n 3 /tmp/case.log | cut -c1-300
  sleep 2
}
# start_src NAME CMD... : start a raw->compressed republisher; SRC_OK=1 if /cam/compressed gets messages
start_src() {
  local name=$1; shift
  echo; echo "### SOURCE $name"; echo "\$ $*"
  setsid "$@" > /tmp/src.log 2>&1 &
  SRC=$!
  sleep 5
  echo "topics: $(timeout 10 ros2 topic list --no-daemon 2>/dev/null | grep -vE '^/(rosout|parameter_events)$' | tr '\n' ' ')"
  local r; r=$(python3 /y/probe.py /cam/compressed compressed 4); echo "$r"
  python3 /y/probe.py /out/compressed compressed 3
  python3 /y/probe.py /cam raw 3
  SRC_OK=0; echo "$r" | grep -q ': 0 messages' || SRC_OK=1
  echo "still running: $(kill -0 $SRC 2>/dev/null && echo yes || echo no)"
  echo "--- source output (first 5 lines)"; head -n 5 /tmp/src.log | cut -c1-400
}
stop_src() { stop_grp $SRC; sleep 2; }

echo; echo "=== list_transports, compressed plugin NOT installed"
timeout 20 ros2 run image_transport list_transports 2>&1 | head -n 30
echo; echo "=== PHASE A: only image_transport installed"
run_case A1-raw-in-positional ros2 run image_transport republish raw in:=/camera/image_raw raw out:=/image
run_case A2-compressed-in-no-plugin-positional ros2 run image_transport republish compressed in/compressed:=/cam/compressed raw out:=/image
run_case A3-compressed-in-no-plugin-params ros2 run image_transport republish --ros-args -p in_transport:=compressed -p out_transport:=raw -r in/compressed:=/cam/compressed -r out:=/image
start_src A-src-raw-to-all-positional ros2 run image_transport republish raw in:=/camera/image_raw out:=/cam
stop_src

echo; echo "=== install compressed_image_transport"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$D-compressed-image-transport >> /tmp/apt.log 2>&1; echo "apt compressed exit=$?"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-compressed-image-transport 2>&1
timeout 20 ros2 run image_transport list_transports 2>&1 | head -n 30

echo; echo "=== PHASE B: sources (raw -> compressed)"
start_src B1-src-positional-all ros2 run image_transport republish raw in:=/camera/image_raw out:=/cam
stop_src
start_src B2-src-params-no-out-transport ros2 run image_transport republish --ros-args -p in_transport:=raw -r in:=/camera/image_raw -r out:=/cam
stop_src
start_src B3-src-positional-raw-compressed ros2 run image_transport republish raw compressed --ros-args -r in:=/camera/image_raw -r out:=/cam
stop_src
start_src B4-src-positional-plus-out-compressed-remap ros2 run image_transport republish raw compressed --ros-args -r in:=/camera/image_raw -r out:=/cam -r out/compressed:=/cam/compressed
stop_src
start_src B5-src-params-out-compressed ros2 run image_transport republish --ros-args -p in_transport:=raw -p out_transport:=compressed -r in:=/camera/image_raw -r out:=/cam
if [ "$SRC_OK" != 1 ]; then stop_src; start_src B6-src-positional-plus-remap-kept ros2 run image_transport republish raw compressed --ros-args -r in:=/camera/image_raw -r out:=/cam -r out/compressed:=/cam/compressed; fi
echo "compressed source for phase C: SRC_OK=$SRC_OK"

echo; echo "=== PHASE C: compressed -> raw on /image, source publishing /cam/compressed"
run_case C1-positional-in-compressed-remap ros2 run image_transport republish compressed in/compressed:=/cam/compressed raw out:=/image
run_case C2-positional-in-base ros2 run image_transport republish compressed in:=/cam raw out:=/image
run_case C3-positional-in-full-compressed-topic ros2 run image_transport republish compressed in:=/cam/compressed raw out:=/image
run_case C4-positional-transports-ros-args-remaps ros2 run image_transport republish compressed raw --ros-args -r in/compressed:=/cam/compressed -r out:=/image
run_case C5-params-in-compressed-remap ros2 run image_transport republish --ros-args -p in_transport:=compressed -p out_transport:=raw -r in/compressed:=/cam/compressed -r out:=/image
run_case C6-params-in-base ros2 run image_transport republish --ros-args -p in_transport:=compressed -p out_transport:=raw -r in:=/cam -r out:=/image
run_case C7-remaps-only-no-transports ros2 run image_transport republish --ros-args -r in/compressed:=/cam/compressed -r out:=/image
run_case C8-params-out-raw-unset ros2 run image_transport republish --ros-args -p in_transport:=compressed -r in/compressed:=/cam/compressed -r out:=/image
run_case C9-unknown-ros-arg ros2 run image_transport republish --ros-args -r in/compressed:=/cam/compressed out/raw:=/image

echo; echo "=== PHASE D: launch files"
cat > /y/launch_args.py <<'PY'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='image_transport', executable='republish', name='decompress',
        arguments=['compressed', 'raw'],
        remappings=[('in/compressed', '/cam/compressed'), ('out', '/image')])])
PY
cat > /y/launch_params.py <<'PY'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='image_transport', executable='republish', name='decompress',
        parameters=[{'in_transport': 'compressed', 'out_transport': 'raw'}],
        remappings=[('in/compressed', '/cam/compressed'), ('out', '/image')])])
PY
cat > /y/launch_both.py <<'PY'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='image_transport', executable='republish', name='decompress',
        arguments=['compressed', 'raw'],
        parameters=[{'in_transport': 'compressed', 'out_transport': 'raw'}],
        remappings=[('in/compressed', '/cam/compressed'), ('out', '/image')])])
PY
run_case D1-launch-arguments ros2 launch /y/launch_args.py
run_case D2-launch-parameters ros2 launch /y/launch_params.py
run_case D3-launch-arguments-and-parameters ros2 launch /y/launch_both.py

echo; echo "=== PHASE E: rate and size with the phase C source still running"
python3 /y/probe.py /camera/image_raw raw 10
python3 /y/probe.py /cam/compressed compressed 10

echo; echo "=== PHASE F: limiting published transports (raw -> all)"
stop_src
for P in "out.enable_pub_plugins:=['image_transport/raw']" "cam.enable_pub_plugins:=['image_transport/raw']" "out.enable_pub_plugins:=['image_transport/compressed']"; do
  start_src "F $P" ros2 run image_transport republish --ros-args -p in_transport:=raw -r in:=/camera/image_raw -r out:=/cam -p "$P"
  stop_src
  start_src "F-positional $P" ros2 run image_transport republish raw in:=/camera/image_raw out:=/cam --ros-args -p "$P"
  stop_src
done

kill -INT $PUB; sleep 1; kill -9 $PUB 2>/dev/null
pkill -9 -f republish 2>/dev/null
echo "=== core files: $(find / -xdev -name 'core*' -type f -newer /y/pub.py 2>/dev/null | wc -l)"
echo "=== done $(date -u +%FT%TZ)"
