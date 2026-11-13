#!/bin/bash
# Invalid topic / node / namespace names in ROS 2: which names fail, where, and with what message.
# Host side (runner, one distro at a time, no core dumps, no network, DDS isolated):
#   docker run --rm --name pk39-$D --network none --hostname robot-pc-01 --ulimit core=0 \
#     --pids-limit 256 --cpus 1.5 -e ROS_DOMAIN_ID=88 \
#     -e ROS_LOCALHOST_ONLY=1 (Humble) | -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST (Jazzy, Lyrical) \
#     -v /tmp/en-pick49:/w ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
set +u
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export RCUTILS_COLORIZED_OUTPUT=0 PYTHONUNBUFFERED=1
D=$ROS_DISTRO
echo "=== distro $D domain $ROS_DOMAIN_ID localhost_only=${ROS_LOCALHOST_ONLY:-} range=${ROS_AUTOMATIC_DISCOVERY_RANGE:-} hostname=$(hostname)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-rcl ros-$D-rmw ros-$D-ros2cli ros-$D-launch-ros ros-$D-rmw-fastrtps-cpp 2>&1
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset, default>}"

mkdir -p /y/ws/src/nameprobe/src
# ---------- cases: kind<TAB>name ----------
python3 - > /y/cases.tsv <<'PY'
rows = []
for n in ['cmd_vel', '/cmd_vel', 'Cmd_Vel', 'cmd-vel', 'cmd.vel', 'cmd vel', '1cmd', '/robot/1/imu',
          'livox/192_168_0_155/imu', 'robot_1/imu', '/a//b', 'imu/', '', '~imu', '~/imu',
          '{node}/status', '{bad}/x', 'a__b', '_imu', 'imu_', 'café', '/robot1/odom']:
    rows.append(('pub', n))
for n in ['talker', 'Talker', 'my_node', 'my-node', 'my.node', 'my node', '1node', '_node', 'node_',
          'a__b', 'ns/node', '', 'ros-pc-01', '~node', 'café']:
    rows.append(('node', n))
for n in ['', '/', 'robot1', '/robot1', '/robot-1', '/1robot', '/robot1/', '//robot1', '/robot1/arm', '/robot.1', '/r__1']:
    rows.append(('ns', n))
for n in ['reset_odom', 'reset-odom', '/1reset', '~/reset']:
    rows.append(('srv', n))
for n in ['max_speed', 'max-speed', 'max.speed', '1speed', 'max speed', 'a/b', '']:
    rows.append(('param', n))
for k in [180, 200, 230, 240, 245, 246, 247, 250, 255, 256, 300]:
    rows.append(('pub', '/' + 'a' * k))
for k in [200, 215, 220, 221, 222, 223, 225, 230, 255, 256, 300]:
    rows.append(('node', 'n' * k))
for kind, name in rows:
    print(f'{kind}\t{name}')
PY
echo "cases: $(wc -l < /y/cases.tsv)"

# ---------- rclpy probe ----------
cat > /y/probe.py <<'PY'
import sys, rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
rclpy.init()
base = Node('probe_base')
def show(name):
    return repr(name) if len(name) < 60 else f"<{name[:2]}...len={len(name)}>"
for line in open('/y/cases.tsv', encoding='utf-8'):
    kind, name = line.rstrip('\n').split('\t')
    try:
        if kind == 'node':
            n = Node(name); res = n.get_fully_qualified_name(); n.destroy_node()
        elif kind == 'ns':
            n = Node('probe_ns', namespace=name); res = n.get_fully_qualified_name(); n.destroy_node()
        elif kind == 'pub':
            p = base.create_publisher(String, name, 10); res = p.topic_name; base.destroy_publisher(p)
        elif kind == 'srv':
            s = base.create_service(Trigger, name, lambda rq, rs: rs); res = s.srv_name; base.destroy_service(s)
        elif kind == 'param':
            base.declare_parameter(name, 1); res = 'declared'
        print(f'PY {kind:<5} {show(name):<28} OK -> {show(res)}')
    except Exception as e:
        msg = str(e).replace('\n', ' | ')
        print(f'PY {kind:<5} {show(name):<28} FAIL {type(e).__module__}.{type(e).__name__}: {msg[:260]}')
base.destroy_node()
rclpy.shutdown()
PY
echo "### rclpy probe"
timeout 120 python3 /y/probe.py 2>&1

# ---------- validators and a sanitizer ----------
cat > /y/sanitize.py <<'PY'
import re, socket
from rclpy.validate_topic_name import validate_topic_name
from rclpy.validate_node_name import validate_node_name
from rclpy.validate_namespace import validate_namespace
from rclpy.validate_full_topic_name import validate_full_topic_name
def ros_token(s):
    s = re.sub(r'[^A-Za-z0-9_]', '_', s)
    return 'n' + s if (not s or s[0].isdigit()) else s
def ros_topic(s):
    toks = [ros_token(t) for t in s.split('/') if t]   # empty tokens (from //, leading or trailing /) dropped
    return '/'.join(toks) if toks else 'n'
def check(fn, v):
    try:
        fn(v); return 'valid'
    except Exception as e:
        return f'{type(e).__name__}: {e}'.replace('\n', ' | ')[:200]
print('hostname:', socket.gethostname(), '->', check(validate_node_name, socket.gethostname()))
for raw in ['my-node', 'ros-pc-01', '1node', 'my.node', 'café']:
    print(f'node {raw!r:<14} raw={check(validate_node_name, raw)[:90]} | fixed={ros_token(raw)!r} {check(validate_node_name, ros_token(raw))}')
for raw in ['cmd-vel', 'livox/192_168_0_155/imu', '/robot/1/imu', 'imu/', '/a//b']:
    print(f'topic {raw!r:<26} raw={check(validate_topic_name, raw)[:90]} full={check(validate_full_topic_name, "/" + raw.lstrip("/"))[:70]} | fixed={ros_topic(raw)!r} {check(validate_topic_name, ros_topic(raw))}')
for raw in ['/robot-1', '/1robot']:
    print(f'ns {raw!r:<12} raw={check(validate_namespace, raw)[:90]} | fixed={"/" + ros_topic(raw)!r} {check(validate_namespace, "/" + ros_topic(raw))}')
PY
echo "### validators + sanitizer"
timeout 60 python3 /y/sanitize.py 2>&1

# ---------- rclcpp probe (colcon package) ----------
cat > /y/ws/src/nameprobe/package.xml <<'XML'
<?xml version="1.0"?>
<package format="3">
  <name>nameprobe</name><version>0.0.1</version><description>name probe</description>
  <maintainer email="probe@example.com">x</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><depend>std_msgs</depend><depend>std_srvs</depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
XML
cat > /y/ws/src/nameprobe/CMakeLists.txt <<'CM'
cmake_minimum_required(VERSION 3.8)
project(nameprobe)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
foreach(t probe talker)
  add_executable(${t} src/${t}.cpp)
  target_link_libraries(${t} rclcpp::rclcpp ${std_msgs_TARGETS} ${std_srvs_TARGETS})
  install(TARGETS ${t} DESTINATION lib/${PROJECT_NAME})
endforeach()
ament_package()
CM
cat > /y/ws/src/nameprobe/src/probe.cpp <<'CPP'
#include <fstream>
#include <iostream>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
static std::string show(const std::string & s) {
  return s.size() < 60 ? "'" + s + "'" : "<" + s.substr(0, 2) + "...len=" + std::to_string(s.size()) + ">";
}
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  if (argc > 1 && std::string(argv[1]) == "uncaught") {
    auto n = std::make_shared<rclcpp::Node>("livox_driver");
    auto p = n->create_publisher<std_msgs::msg::String>("livox/192_168_0_155/imu", 10);
    std::cout << "not reached" << std::endl;
    return 0;
  }
  auto base = std::make_shared<rclcpp::Node>("probe_base_cpp");
  std::ifstream f("/y/cases.tsv");
  std::string line;
  while (std::getline(f, line)) {
    auto tab = line.find('\t');
    std::string kind = line.substr(0, tab), name = line.substr(tab + 1), res;
    try {
      if (kind == "node") { auto n = std::make_shared<rclcpp::Node>(name); res = n->get_fully_qualified_name(); }
      else if (kind == "ns") { auto n = std::make_shared<rclcpp::Node>("probe_ns", name); res = n->get_fully_qualified_name(); }
      else if (kind == "pub") { auto p = base->create_publisher<std_msgs::msg::String>(name, 10); res = p->get_topic_name(); }
      else if (kind == "srv") {
        auto s = base->create_service<std_srvs::srv::Trigger>(name,
          [](const std::shared_ptr<std_srvs::srv::Trigger::Request>, std::shared_ptr<std_srvs::srv::Trigger::Response>) {});
        res = s->get_service_name(); }
      else if (kind == "param") { base->declare_parameter(name, 1); res = "declared"; }
      std::cout << "CPP " << kind << " " << show(name) << " OK -> " << show(res) << std::endl;
    } catch (const rclcpp::exceptions::InvalidTopicNameError & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL InvalidTopicNameError: " << e.what() << std::endl;
    } catch (const rclcpp::exceptions::InvalidServiceNameError & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL InvalidServiceNameError: " << e.what() << std::endl;
    } catch (const rclcpp::exceptions::InvalidNodeNameError & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL InvalidNodeNameError: " << e.what() << std::endl;
    } catch (const rclcpp::exceptions::InvalidNamespaceError & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL InvalidNamespaceError: " << e.what() << std::endl;
    } catch (const rclcpp::exceptions::InvalidParametersException & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL InvalidParametersException: " << e.what() << std::endl;
    } catch (const std::exception & e) {
      std::cout << "CPP " << kind << " " << show(name) << " FAIL std::exception(" << typeid(e).name() << "): " << e.what() << std::endl;
    }
  }
  rclcpp::shutdown();
  return 0;
}
CPP
cat > /y/ws/src/nameprobe/src/talker.cpp <<'CPP'
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("talker");
  auto p = n->create_publisher<std_msgs::msg::String>("chatter", 10);
  RCLCPP_INFO(n->get_logger(), "started as %s, publishing on %s", n->get_fully_qualified_name(), p->get_topic_name());
  rclcpp::shutdown();
  return 0;
}
CPP
echo "### colcon build"
cd /y/ws
SECONDS=0
MAKEFLAGS=-j1 timeout 900 colcon build --event-handlers console_direct- --cmake-args -DCMAKE_BUILD_TYPE=Release > /y/build.log 2>&1
echo "colcon exit=$? seconds=$SECONDS"; tail -3 /y/build.log; grep -iE "error" /y/build.log | head -15; cat /y/ws/log/latest_build/nameprobe/stderr.log 2>/dev/null | head -30
source /y/ws/install/setup.bash
echo "### rclcpp probe"
timeout 120 ros2 run nameprobe probe 2>&1
echo "### rclcpp uncaught (livox case)"
S=$(date +%s.%N); timeout 30 ros2 run nameprobe probe uncaught 2>&1; echo "exit=$? elapsed=$(python3 -c "print(round($(date +%s.%N)-$S,2))")s"

# ---------- python script with the same uncaught error ----------
cat > /y/py_uncaught.py <<'PY'
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
rclpy.init()
n = Node('livox_driver')
n.create_publisher(String, 'livox/192_168_0_155/imu', 10)
PY
echo "### rclpy uncaught (livox case)"
S=$(date +%s.%N); timeout 30 python3 /y/py_uncaught.py 2>&1 | tail -6; echo "exit=${PIPESTATUS[0]} elapsed=$(python3 -c "print(round($(date +%s.%N)-$S,2))")s"
cat > /y/py_badnode.py <<'PY'
import rclpy
from rclpy.node import Node
rclpy.init()
Node('my-node')
PY
echo "### rclpy uncaught bad node name"
timeout 30 python3 /y/py_badnode.py 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"

# ---------- command line remaps ----------
for R in "__node:=my_talker" "__node:=my-talker" "__node:=1talker" "__ns:=/robot1" "__ns:=/robot-1" "__ns:=robot1" "chatter:=chat_ter" "chatter:=chat-ter" "chatter:=/1chat" "chatter:=~/chat"; do
  echo "### ros2 run talker --ros-args -r $R"
  timeout 30 ros2 run nameprobe talker --ros-args -r "$R" 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
done

# ---------- ros2 CLI ----------
echo "### ros2 topic pub /cmd-vel"
timeout 30 ros2 topic pub --once /cmd-vel std_msgs/msg/String "{data: hi}" 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
echo "### ros2 topic pub /robot/1/imu"
timeout 30 ros2 topic pub --once /robot/1/imu std_msgs/msg/String "{data: hi}" 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
echo "### ros2 topic echo /cmd-vel"
timeout 15 ros2 topic echo /cmd-vel std_msgs/msg/String 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
echo "### ros2 service call /reset-odom"
timeout 30 ros2 service call /reset-odom std_srvs/srv/Trigger 2>&1 | tail -4; echo "exit=${PIPESTATUS[0]}"
echo "### ros2 topic pub /cmd_vel (control)"
timeout 10 ros2 topic pub --once /cmd_vel std_msgs/msg/String "{data: hi}" 2>&1 | tail -2; echo "exit=${PIPESTATUS[0]}"

# ---------- launch ----------
mklaunch() {  # $1 file, $2 Node kwargs
cat > "$1" <<EOF
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='nameprobe', executable='talker', output='screen', $2)])
EOF
}
mklaunch /y/l_ok.launch.py "name='my_talker', namespace='robot1'"
mklaunch /y/l_node.launch.py "name='my-talker'"
mklaunch /y/l_ns.launch.py "namespace='robot-1'"
mklaunch /y/l_remap.launch.py "remappings=[('chatter', 'chat-ter')]"
mklaunch /y/l_ns_digit.launch.py "namespace='1robot'"
for L in l_ok l_node l_ns l_remap l_ns_digit; do
  echo "### ros2 launch $L"
  timeout 40 ros2 launch /y/$L.launch.py 2>&1 | grep -v '^\[INFO\] \[launch\]: All log files' | tail -7; echo "exit=${PIPESTATUS[0]}"
done
echo "=== done $D"
