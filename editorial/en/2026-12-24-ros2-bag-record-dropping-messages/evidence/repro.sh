#!/bin/bash
# Run inside ros:<distro>-ros-base as root, with pub.py and count.py in /e and a disk-backed dir at /disk.
# Measures when ros2 bag record loses messages: write cache size, storage plugin and preset,
# compression, QoS (reliable vs best effort, depth) and disk vs tmpfs, and what the recorder prints.
# usage: repro.sh versions | repro.sh 'case_run name fsdir "pub args" "record args"' ...
ulimit -c 0
set -m   # job control: without it, background jobs ignore SIGINT and ros2 bag record never stops
source /opt/ros/$ROS_DISTRO/setup.bash
E=/e
# Lyrical removed the positional topic argument; Humble only has the positional form
if ros2 bag record --help 2>&1 | grep -q -- '--topics'; then TOPICARG="--topics /cam"; else TOPICARG="/cam"; fi
# Lyrical publishes per-topic loss statistics on a topic; older distros don't have the message type
ros2 interface list 2>/dev/null | grep -q rosbag2_interfaces/msg/MessagesLostEvent && LOST_EVENT=1
case_run() {  # name fsdir "pub args" "record args"
  local name=$1 fs=$2 pargs=$3 rargs=$4
  local bag=$fs/bag_$name n
  n=$(echo "$pargs" | sed -n 's/.*--n \([0-9]*\).*/\1/p'); n=${n:-300}
  rm -rf "$bag"
  echo "--- case=$name fs=$fs pub=[$pargs] record=[$rargs] load=$(cut -d' ' -f1 /proc/loadavg)"
  python3 $E/pub.py $pargs > /tmp/pub_$name.json 2> /tmp/pub_$name.err &
  local pp=$!
  local ep=""
  if [ -n "$LOST_EVENT" ]; then ros2 topic echo /events/rosbag2_messages_lost rosbag2_interfaces/msg/MessagesLostEvent > /tmp/ev_$name.txt 2>&1 & ep=$!; fi
  ros2 bag record -o "$bag" $TOPICARG $rargs > /tmp/rec_$name.log 2>&1 &
  local rp=$!
  wait $pp
  sleep 1
  kill -INT $rp
  for i in $(seq 180); do kill -0 $rp 2>/dev/null || break; sleep 0.5; done
  kill -0 $rp 2>/dev/null && { echo "recorder still running 90 s after SIGINT, killing"; kill -KILL $rp; }
  wait $rp; echo "recorder_exit=$?"
  if [ -n "$ep" ]; then kill -INT $ep; wait $ep 2>/dev/null
    awk '/messages_lost_in_transport/{t+=$2} /messages_lost_in_recorder/{r+=$2} /^node_name/{e++} END{printf "events on /events/rosbag2_messages_lost: %d, sum lost_in_transport=%d, sum lost_in_recorder=%d\n", e, t, r}' /tmp/ev_$name.txt; fi
  cat /tmp/pub_$name.json; tail -3 /tmp/pub_$name.err | grep -v '^$'
  echo "recorder output (lines with lost/drop/cache/warn/error/total):"
  grep -iE -A1 'lost|drop|cache|warn|error|total|fail|space|exception' /tmp/rec_$name.log | grep -vE 'Positional|Keyboard handling|^--$' | sed 's/^/  | /' | head -14
  python3 $E/count.py "$bag" $n 2>&1 | grep -v "^\[INFO\]" | tail -3
  echo "bag dir: $(ls -l "$bag" 2>&1 | awk 'NR>1{printf "%s=%s ", $9, $5}')"
  rm -rf "$bag"
}
if [ "$1" = versions ]; then
  echo "=== distro=$ROS_DISTRO $(date -u +%FT%TZ)"
  dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
    ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rosbag2 ros-$ROS_DISTRO-ros2bag \
    ros-$ROS_DISTRO-rosbag2-transport ros-$ROS_DISTRO-rosbag2-cpp ros-$ROS_DISTRO-rosbag2-storage-default-plugins \
    ros-$ROS_DISTRO-rosbag2-storage-mcap ros-$ROS_DISTRO-rosbag2-compression-zstd 2>/dev/null
  echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
  ros2 bag record --help 2>&1 | grep -E -A3 -- '--max-cache-size|--storage-preset-profile|--storage STORAGE|-s STORAGE' | head -40
  echo "storage plugins: $(ros2 bag list storage 2>&1 | tr '\n' ' ')"
  echo "rosbag2_interfaces with Lost/Event: $(ros2 interface list 2>/dev/null | grep rosbag2_interfaces | grep -iE 'lost|event' | tr '\n' ' ')"
  exit 0
fi
cat > /tmp/udp.xml <<'X'
<?xml version="1.0" encoding="UTF-8"?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <transport_descriptors><transport_descriptor><transport_id>udp</transport_id><type>UDPv4</type></transport_descriptor></transport_descriptors>
  <participant profile_name="udp_only" is_default_profile="true"><rtps>
    <userTransports><transport_id>udp</transport_id></userTransports><useBuiltinTransports>false</useBuiltinTransports>
  </rtps></participant>
</profiles>
X
CAM="--size 921600"   # 640x480 rgb8 = 921,600 bytes, random (incompressible) payload
suite_normal() {   # container without disk throttling
  case_run n_disk_30hz /disk "$CAM --rate 30 --n 1200" ""
  export FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/udp.xml   # force UDP loopback, as between two hosts or containers
  case_run n_udp_besteffort_100hz /disk "$CAM --rate 100 --n 300 --rel best_effort" ""
  case_run n_udp_reliable_100hz /disk "$CAM --rate 100 --n 300 --rel reliable" ""
  unset FASTRTPS_DEFAULT_PROFILES_FILE
  # nearly full filesystem: leave about 150 MB free on the 800 MB /dev/shm, then record 276 MB
  local free_mb=$(df -m --output=avail /dev/shm | tail -1)
  fallocate -l $(( (free_mb - 150) * 1024 * 1024 )) /dev/shm/filler && echo "filler written, avail now $(df -m --output=avail /dev/shm | tail -1) MB"
  case_run n_full_fs /dev/shm "$CAM --rate 30 --n 300" ""
  echo "full log of the full-filesystem recorder run:"; grep -v Positional /tmp/rec_n_full_fs.log | sed 's/^/  | /'
  rm -f /dev/shm/filler
}
suite_slow_a() {   # container started with --device-write-bps <disk>:10mb, bag on that disk
  local def=$(ros2 bag record --help 2>&1 | grep -A8 -- '--storage' | tr -s ' \n' ' ' | grep -oiE 'default[^.]{0,40}' | head -1)
  echo "default storage line: ${def:-<not printed>}"
  case_run s_default_30hz /disk "$CAM --rate 30 --n 1200" ""
  case_run s_cache0_30hz /disk "$CAM --rate 30 --n 1200" "--max-cache-size 0"
  case_run s_cache300m_30hz /disk "$CAM --rate 30 --n 1200" "--max-cache-size 314572800"
  case_run s_default_8hz /disk "$CAM --rate 8 --n 320" ""
}
suite_slow_b() {   # second half, split only to keep each ssh call short
  case_run s_zstd_zeros_30hz /disk "$CAM --rate 30 --n 1200 --data zeros" "--compression-mode message --compression-format zstd"
  case_run s_zstd_random_30hz /disk "$CAM --rate 30 --n 1200" "--compression-mode message --compression-format zstd"
  case_run s_sqlite3_30hz /disk "$CAM --rate 30 --n 1200" "-s sqlite3"
}
for c in "$@"; do eval "$c"; done
