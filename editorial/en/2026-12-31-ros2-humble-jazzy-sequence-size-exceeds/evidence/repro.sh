#!/usr/bin/env bash
# Mixing ROS 2 distros on one DDS domain: "sequence size exceeds remaining buffer".
# Usage: repro.sh setup | sub <distro> | rclcpp | cyclone | fixes | versions
# Each container gets its own IP on a bridge network (no --net=host, no shared /dev/shm),
# so Fast DDS talks UDP between containers like two machines on a LAN.
set -u
ulimit -c 0
W=/tmp/en-pick32
NET=pk22-net
DOM=32
DISTROS="humble jazzy lyrical"
cd "$W"

cat > "$W/talker.py" <<'EOF'
import sys, rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
rclpy.init()
name = sys.argv[1]
n = Node(name)
pub = n.create_publisher(String, 'chatter', 10)
count = [0]
def tick():
    count[0] += 1
    m = String(); m.data = '%s %d' % (name, count[0]); pub.publish(m)
def trig(req, res):
    res.success = True; res.message = 'from ' + name; return res
n.create_timer(0.1, tick)
n.create_service(Trigger, 'trigger', trig)
rclpy.spin(n)
EOF

img() { case "$1" in *-cy) echo "pk22-${1%-cy}-cy";; *) echo "ros:$1-ros-base";; esac; }
rmwof() { case "$1" in *-cy) echo rmw_cyclonedds_cpp;; *) echo rmw_fastrtps_cpp;; esac; }
base() { echo "${1%-cy}"; }

start_pub() { # $1 = distro tag (humble | humble-cy ...), $2 = domain
  local d=$1 b; b=$(base "$1")
  docker rm -f "pk22-pub" >/dev/null 2>&1
  docker run -d --name pk22-pub --network $NET -e ROS_DOMAIN_ID="$2" \
    -e RMW_IMPLEMENTATION="$(rmwof "$d")" -v $W:/w:ro "$(img "$d")" \
    bash -c "source /opt/ros/$b/setup.bash; exec python3 -u /w/talker.py talker_$b" >/dev/null
  sleep 3
}

probe() { # $1 = subscriber distro tag, $2 = domain, $3 = talker node name
  local d=$1 b; b=$(base "$1")
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID="$2" \
    -e RMW_IMPLEMENTATION="$(rmwof "$d")" "$(img "$d")" bash -c "
    source /opt/ros/$b/setup.bash
    echo \"sub RMW=\$RMW_IMPLEMENTATION\"
    t0=\$(date +%s.%N)
    timeout -k 5 10 ros2 topic echo /chatter std_msgs/msg/String >/tmp/e.out 2>/tmp/e.err
    echo \"echo 10s: data lines=\$(grep -c '^data:' /tmp/e.out) seq_errors=\$(grep -c 'sequence size exceeds' /tmp/e.err) other_stderr=\$(grep -vc 'sequence size exceeds' /tmp/e.err)\"
    echo 'first data line:'; grep -m1 '^data:' /tmp/e.out
    echo 'stderr sample:'; grep -v '^\$' /tmp/e.err | sort | uniq -c | head -5
    echo '--- ros2 node list --no-daemon --spin-time 3'
    timeout -k 5 20 ros2 node list --no-daemon --spin-time 3 2>/tmp/n.err; echo \"exit=\$? seq_errors=\$(grep -c 'sequence size exceeds' /tmp/n.err)\"
    echo '--- ros2 topic list --no-daemon --spin-time 3'
    timeout -k 5 20 ros2 topic list --no-daemon --spin-time 3 2>/tmp/t.err; echo \"exit=\$? seq_errors=\$(grep -c 'sequence size exceeds' /tmp/t.err)\"
    echo '--- ros2 service call /trigger (timed)'
    s=\$(date +%s.%N); timeout -k 5 20 ros2 service call /trigger std_srvs/srv/Trigger >/tmp/s.out 2>/tmp/s.err; rc=\$?; e=\$(date +%s.%N)
    grep -E 'response|success|message|waiting' /tmp/s.out | head -4
    echo \"exit=\$rc seconds=\$(python3 -c \"print(round(\$e-\$s,2))\") seq_errors=\$(grep -c 'sequence size exceeds' /tmp/s.err)\"
    echo '--- ros2 param get --no-daemon --spin-time 3 $3 use_sim_time'
    timeout -k 5 20 ros2 param get --no-daemon --spin-time 3 $3 use_sim_time >/tmp/p.out 2>&1; rc=\$?
    grep -v 'sequence size exceeds' /tmp/p.out | tail -3; echo \"seq_errors=\$(grep -c 'sequence size exceeds' /tmp/p.out)\"; echo \"exit=\$rc\"
  " 2>&1
  echo "--- publisher ($(docker inspect -f '{{.Config.Image}}' pk22-pub)) log: seq_errors=$(docker logs pk22-pub 2>&1 | grep -c 'sequence size exceeds') other_lines=$(docker logs pk22-pub 2>&1 | grep -vc 'sequence size exceeds')"
  docker logs pk22-pub 2>&1 | grep -v 'sequence size exceeds' | head -3
  docker rm -f pk22-pub >/dev/null
}

case "${1:-}" in
setup)
  docker network create $NET >/dev/null 2>&1
  for d in $DISTROS; do docker pull -q "ros:$d-ros-base"; done
  ;;
sub) # subscriber side = $2, publisher = every distro in turn
  s=$2
  echo "##### subscriber distro: $s  ($(date -Is))"
  for p in $DISTROS; do
    echo; echo "=== publisher $p (Fast DDS) -> subscriber $s (Fast DDS), domain $DOM"
    uptime
    start_pub "$p" $DOM
    probe "$s" $DOM "/talker_$p"
  done
  echo; echo "=== interface definitions on $s"
  docker run --rm "ros:$s-ros-base" bash -c "source /opt/ros/$s/setup.bash
    echo '# rmw_dds_common/msg/Gid'; ros2 interface show rmw_dds_common/msg/Gid | grep -v '^#' | grep -v '^\$'
    echo '# rmw_dds_common/msg/NodeEntitiesInfo'; ros2 interface show rmw_dds_common/msg/NodeEntitiesInfo | grep -v '^\s*#' | grep -v '^\s*\$'"
  ;;
rclcpp) # an rclcpp node (robot_state_publisher) on $2 while $3 publishes
  echo "=== rclcpp robot_state_publisher on $2 while talker on $3 runs, 10 s"
  uptime
  start_pub "$3" $DOM
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM "ros:$2-ros-base" bash -c "
    source /opt/ros/$2/setup.bash
    timeout -k 5 10 ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:='<robot name=\"r\"><link name=\"a\"/></robot>' >/tmp/r.out 2>&1
    echo \"seq_errors=\$(grep -c 'sequence size exceeds' /tmp/r.out)\"; grep -v 'sequence size exceeds' /tmp/r.out | head -4"
  docker rm -f pk22-pub >/dev/null
  ;;
cyclone)
  for d in $DISTROS; do
    docker image inspect "pk22-$d-cy" >/dev/null 2>&1 && continue
    uptime
    docker rm -f pk22-build >/dev/null 2>&1
    docker run --name pk22-build "ros:$d-ros-base" bash -c "apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$d-rmw-cyclonedds-cpp >/dev/null && dpkg-query -W ros-$d-rmw-cyclonedds-cpp ros-$d-cyclonedds" 2>&1 | tail -3
    docker commit pk22-build "pk22-$d-cy" >/dev/null && docker rm pk22-build >/dev/null
  done
  for pair in "jazzy-cy humble-cy" "humble-cy jazzy-cy" "lyrical-cy humble-cy" "lyrical-cy jazzy-cy" "jazzy-cy humble" "jazzy humble-cy"; do
    set -- $pair
    echo; echo "=== publisher $1 -> subscriber $2, domain $DOM"; uptime
    start_pub "$1" $DOM
    probe "$2" $DOM "/talker_$(base "$1")"
  done
  ;;
fixes)
  echo "=== fix: separate ROS_DOMAIN_ID (jazzy talker on 32, humble probe on 33)"; uptime
  start_pub jazzy 32; probe humble 33 /talker_jazzy
  echo; echo "=== workaround: call the jazzy node's parameter service directly from humble"
  start_pub jazzy $DOM
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM ros:humble-ros-base bash -c "
    source /opt/ros/humble/setup.bash
    timeout -k 5 20 ros2 service call /talker_jazzy/get_parameters rcl_interfaces/srv/GetParameters '{names: [use_sim_time]}' 2>&1 | grep -v '^\$' | tail -3"
  docker rm -f pk22-pub >/dev/null
  echo; echo "=== count over time: humble echo for 30 s while jazzy talker runs"
  start_pub jazzy $DOM
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM ros:humble-ros-base bash -c "
    source /opt/ros/humble/setup.bash
    timeout 30 ros2 topic echo /chatter std_msgs/msg/String 2>&1 >/dev/null | while read -r l; do echo \"\$(date +%s) \$l\"; done > /tmp/ts.txt
    awk '{print \$1}' /tmp/ts.txt | uniq -c | awk '{print \"t+\" NR-1 \"s window: \" \$1 \" lines\"}' | head -40
    echo total=\$(wc -l </tmp/ts.txt)"
  echo "--- start a second jazzy node (ros2 topic pub) during a 20 s humble echo"
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM ros:humble-ros-base bash -c "
    source /opt/ros/humble/setup.bash
    timeout -k 5 20 ros2 topic echo /chatter std_msgs/msg/String 2>&1 >/dev/null | while read -r l; do echo \"\$(date +%s) \$l\"; done > /tmp/ts.txt &
    sleep 10; echo before_second_node=\$(wc -l </tmp/ts.txt); wait; echo after_20s_total=\$(wc -l </tmp/ts.txt)" &
  sleep 12
  docker run --rm --name pk22-pub2 --network $NET -e ROS_DOMAIN_ID=$DOM ros:jazzy-ros-base bash -c "source /opt/ros/jazzy/setup.bash; timeout 5 ros2 topic pub -r 1 /other std_msgs/msg/String '{data: x}' >/dev/null 2>&1"
  wait
  docker rm -f pk22-pub >/dev/null
  ;;
cydetail) # full stderr of the Cyclone-on-Humble cases
  echo "=== jazzy-cy talker, humble-cy: ros2 node list stderr"; uptime
  start_pub jazzy-cy $DOM
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp pk22-humble-cy bash -c "
    source /opt/ros/humble/setup.bash; timeout -k 5 20 ros2 node list --no-daemon --spin-time 3 2>&1 | tail -4"
  docker rm -f pk22-pub >/dev/null
  echo; echo "=== humble-cy talker log while a jazzy-cy ros2 topic list runs"
  start_pub humble-cy $DOM
  docker run --rm --name pk22-sub --network $NET -e ROS_DOMAIN_ID=$DOM -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp pk22-jazzy-cy bash -c "
    source /opt/ros/jazzy/setup.bash; timeout -k 5 10 ros2 topic list --no-daemon --spin-time 3 >/dev/null 2>&1"
  echo "log lines=$(docker logs pk22-pub 2>&1 | wc -l)"; docker logs pk22-pub 2>&1 | grep -v '^\s*$' | sed 's/[0-9]\{6,\}/N/g' | sort | uniq -c | sort -rn | head -8
  docker rm -f pk22-pub >/dev/null
  ;;
versions)
  for d in $DISTROS; do
    echo "== $d"; docker image inspect -f '{{index .RepoDigests 0}}' "ros:$d-ros-base"
    docker run --rm "ros:$d-ros-base" bash -c "grep PRETTY /etc/os-release; dpkg-query -W -f='\${Package} \${Version}\n' ros-$d-rclpy ros-$d-rclcpp ros-$d-ros2cli ros-$d-rmw ros-$d-rmw-fastrtps-cpp ros-$d-rmw-dds-common ros-$d-rosidl-typesupport-fastrtps-cpp 'ros-$d-fastrtps' 'ros-$d-fastdds' 2>/dev/null; echo default RMW: \$(. /opt/ros/$d/setup.bash; ros2 doctor --report 2>/dev/null | grep -m1 'middleware name' )"
  done
  for d in $DISTROS; do docker image inspect -f "pk22-$d-cy {{.Id}}" "pk22-$d-cy" 2>/dev/null; done
  ;;
*) echo "usage: $0 setup|sub <distro>|rclcpp <sub> <pub>|cyclone|fixes|versions"; exit 2;;
esac
