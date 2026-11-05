#!/bin/bash
# Run inside ros:<distro>-ros-base as root. Measures why ROS 2 DEBUG log lines do not show:
#  - --log-level forms on ros2 run (global, per-logger, node name vs namespaced/renamed logger name, child loggers)
#  - RCLCPP_LOG_MIN_SEVERITY at runtime (env) vs compile time, set_level() in code
#  - stdout vs stderr, the log file under ROS_LOG_DIR
#  - launch: arguments list, single string, ros_arguments, name=, namespace=, LaunchConfiguration, ros2 launch --ros-args / -d
#  - runtime change through the logger services (enable_logger_service)
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rcutils \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros \
  ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-rcl-logging-spdlog 2>/dev/null
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
echo "ros2 verbs containing 'log': $(ros2 --help 2>&1 | grep -io '^ *[a-z_]*log[a-z_]*' | tr -s ' \n' ' ')"
W=/ws; mkdir -p $W/src/lv/src $W/launch; cd $W/src/lv
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>lv</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<depend>rclcpp</depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(lv)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(lv_cpp src/lv.cpp)
target_link_libraries(lv_cpp rclcpp::rclcpp)
add_executable(lv_cpp_min src/lv.cpp)
target_link_libraries(lv_cpp_min rclcpp::rclcpp)
target_compile_definitions(lv_cpp_min PRIVATE RCLCPP_LOG_MIN_SEVERITY=RCLCPP_LOG_MIN_SEVERITY_INFO)
install(TARGETS lv_cpp lv_cpp_min DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS lv_py.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
cat > src/lv.cpp <<'X'
#include <chrono>
#include <cstdlib>
#include <string>
#include <thread>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/version.h>
#include <rcutils/logging.h>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  const char * m = std::getenv("LV_MODE"); std::string mode = m ? m : "once";
  rclcpp::NodeOptions opts;
#if RCLCPP_VERSION_MAJOR >= 21
  if (std::getenv("LV_LOGSVC")) opts.enable_logger_service(true);
#endif
  auto node = std::make_shared<rclcpp::Node>("lv_cpp", opts);
  auto child = node->get_logger().get_child("plugin");
  auto lib = rclcpp::get_logger("my_lib");
  if (mode == "setlevel") node->get_logger().set_level(rclcpp::Logger::Level::Debug);
  RCLCPP_INFO(node->get_logger(), "INFOLINE logger_name=%s debug_enabled=%d", node->get_logger().get_name(),
    (int)rcutils_logging_logger_is_enabled_for(node->get_logger().get_name(), RCUTILS_LOG_SEVERITY_DEBUG));
  auto emit = [&](int i) {
    RCLCPP_DEBUG(node->get_logger(), "MARK node debug %d", i);
    RCLCPP_INFO(node->get_logger(), "MARK node info %d", i);
    RCLCPP_DEBUG(child, "MARK child debug %d", i);
    RCLCPP_DEBUG(lib, "MARK lib debug %d", i);
  };
  if (mode == "loop") {
    for (int i = 0; i < 40; ++i) { emit(i); rclcpp::spin_some(node); std::this_thread::sleep_for(std::chrono::milliseconds(200)); }
  } else { emit(0); }
  rclcpp::shutdown();
  return 0;
}
X
cat > lv_py.py <<'X'
#!/usr/bin/env python3
import os, time
import rclpy
from rclpy.node import Node
from rclpy.logging import LoggingSeverity
def main():
    rclpy.init()
    mode = os.environ.get('LV_MODE', 'once')
    kw = {}
    if os.environ.get('LV_LOGSVC'):
        kw['enable_logger_service'] = True
    try:
        node = Node('lv_py', **kw)
    except TypeError as e:
        print('Node() TypeError:', e, flush=True)
        node = Node('lv_py')
    lg = node.get_logger()
    child = lg.get_child('plugin')
    lib = rclpy.logging.get_logger('my_lib')
    if mode == 'setlevel':
        lg.set_level(LoggingSeverity.DEBUG)
    lg.info('INFOLINE logger_name=%s debug_enabled=%d' % (lg.name, int(lg.is_enabled_for(LoggingSeverity.DEBUG))))
    def emit(i):
        lg.debug('MARK node debug %d' % i)
        lg.info('MARK node info %d' % i)
        child.debug('MARK child debug %d' % i)
        lib.debug('MARK lib debug %d' % i)
    if mode == 'loop':
        for i in range(40):
            emit(i)
            rclpy.spin_once(node, timeout_sec=0)
            time.sleep(0.2)
    else:
        emit(0)
    node.destroy_node()
    rclpy.shutdown()
if __name__ == '__main__':
    main()
X
chmod +x lv_py.py
cd $W
T0=$(date +%s.%N)
MAKEFLAGS=-j1 colcon build --parallel-workers 1 --event-handlers console_direct- > /tmp/build.log 2>&1
echo "BUILD exit=$? seconds=$(python3 -c "print(round($(date +%s.%N)-$T0,1))")"; tail -3 /tmp/build.log
source $W/install/setup.bash

summ() { # $1 stdout file, $2 stderr file
  local all; all=$(cat $1 $2)
  echo "  node_debug=$(grep -c 'MARK node debug' <<<"$all") node_info=$(grep -c 'MARK node info' <<<"$all") child_debug=$(grep -c 'MARK child debug' <<<"$all") lib_debug=$(grep -c 'MARK lib debug' <<<"$all") other_DEBUG_lines=$(grep '\[DEBUG\]' <<<"$all" | grep -vc MARK) stdout_lines=$(wc -l < $1) stderr_lines=$(wc -l < $2)"
  echo "  infoline: $(grep -h -m1 INFOLINE $1 $2 | sed 's/^.*INFOLINE/INFOLINE/')"
  grep -h -v 'MARK\|INFOLINE\|\[DEBUG\]' $1 $2 | head -6 | sed 's/^/  | /'
}
rc_run() { # label, env-prefix, exe, args...
  local label=$1 envs=$2 exe=$3; shift 3
  echo; echo "### RUN $label :: ${envs:+$envs }ros2 run lv $exe $*"
  export ROS_LOG_DIR=/tmp/rl/$label-$exe; mkdir -p $ROS_LOG_DIR
  env $envs timeout 20 ros2 run lv $exe "$@" > /tmp/o.txt 2> /tmp/e.txt; local rc=$?; echo "  exit=$rc"
  summ /tmp/o.txt /tmp/e.txt
  [ $rc -ne 0 ] && tail -2 /tmp/e.txt | sed 's/^/  last> /' 
  echo "  logfile_node_debug=$(cat $ROS_LOG_DIR/*.log 2>/dev/null | grep -c 'MARK node debug') logfile_node_info=$(cat $ROS_LOG_DIR/*.log 2>/dev/null | grep -c 'MARK node info') logfiles=$(ls $ROS_LOG_DIR | wc -l)"
  unset ROS_LOG_DIR
}
for exe in lv_cpp lv_py.py; do
  N=lv_cpp; [ $exe = lv_py.py ] && N=lv_py
  echo; echo "########## ros2 run cases, exe=$exe node=$N"
  rc_run c01_none "" $exe
  rc_run c02_global_lower "" $exe --ros-args --log-level debug
  rc_run c03_global_upper "" $exe --ros-args --log-level DEBUG
  rc_run c04_node_name "" $exe --ros-args --log-level $N:=debug
  rc_run c05_global_plus_rcl_info "" $exe --ros-args --log-level DEBUG --log-level rcl:=INFO
  rc_run c06_no_ros_args "" $exe --log-level debug
  rc_run c07_invalid_level "" $exe --ros-args --log-level verbose
  rc_run c08_ns_plain_name "" $exe --ros-args -r __ns:=/robot1 --log-level $N:=debug
  rc_run c09_ns_dotted "" $exe --ros-args -r __ns:=/robot1 --log-level robot1.$N:=debug
  rc_run c10_ns_slashes "" $exe --ros-args -r __ns:=/robot1 --log-level /robot1/$N:=debug
  rc_run c11_renamed_old_name "" $exe --ros-args -r __node:=my_name --log-level $N:=debug
  rc_run c12_renamed_new_name "" $exe --ros-args -r __node:=my_name --log-level my_name:=debug
  rc_run c13_lib_logger "" $exe --ros-args --log-level my_lib:=debug
  rc_run c14_child_only "" $exe --ros-args --log-level $N.plugin:=debug
  rc_run c15_env_min_severity "RCLCPP_LOG_MIN_SEVERITY=RCLCPP_LOG_MIN_SEVERITY_DEBUG" $exe
  rc_run c16_setlevel_in_code "LV_MODE=setlevel" $exe
  rc_run c17_stdout_env "RCUTILS_LOGGING_USE_STDOUT=1" $exe --ros-args --log-level debug
  rc_run c18_node_info_global_debug "" $exe --ros-args --log-level debug --log-level $N:=info
done
rc_run c19_compiled_min_info "" lv_cpp_min --ros-args --log-level debug

# ---------- launch ----------
mk() { cat > $W/launch/$1.launch.py; }
mk la_args_list <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', output='screen', arguments=['--ros-args', '--log-level', 'debug'])])
X
mk lb_single_string <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', output='screen', arguments=['--ros-args --log-level DEBUG --'])])
X
mk lc_ros_arguments <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', output='screen', ros_arguments=['--log-level', 'debug'])])
X
mk ld_name_old_logger <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', name='my_name', output='screen', arguments=['--ros-args', '--log-level', 'lv_cpp:=debug'])])
X
mk le_name_new_logger <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', name='my_name', output='screen', arguments=['--ros-args', '--log-level', 'my_name:=debug'])])
X
mk lf_namespace_dotted <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', namespace='robot1', output='screen', arguments=['--ros-args', '--log-level', 'robot1.lv_cpp:=debug'])])
X
mk lg_launch_config <<'X'
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('log_level', default_value='info'),
        Node(package='lv', executable='lv_cpp', output='screen', arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')])])
X
mk lh_plain <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_cpp', output='screen')])
X
mk lj_py_args_list <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_py.py', output='screen', arguments=['--ros-args', '--log-level', 'debug'])])
X
mk lk_py_ros_arguments <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='lv', executable='lv_py.py', output='screen', ros_arguments=['--log-level', 'debug'])])
X
la_run() { # label, then args to ros2 launch
  local label=$1; shift
  echo; echo "### LAUNCH $label :: ros2 launch $*"
  timeout -s INT 25 ros2 launch "$@" > /tmp/o.txt 2> /tmp/e.txt; echo "  exit=$?"
  summ /tmp/o.txt /tmp/e.txt
  echo "  cmd/died lines:"; grep -h -i 'process has died\|exit code\|cmd \|Traceback\|Error\|error:' /tmp/o.txt /tmp/e.txt | grep -v MARK | head -5 | cut -c1-400 | sed 's/^/  > /'
  echo "  [launch] DEBUG lines=$(grep -h '\[DEBUG\] \[launch' /tmp/o.txt /tmp/e.txt | wc -l)"
}
la_run LA_args_list $W/launch/la_args_list.launch.py
la_run LB_single_string $W/launch/lb_single_string.launch.py
la_run LC_ros_arguments $W/launch/lc_ros_arguments.launch.py
la_run LD_name_old_logger $W/launch/ld_name_old_logger.launch.py
la_run LE_name_new_logger $W/launch/le_name_new_logger.launch.py
la_run LF_namespace_dotted $W/launch/lf_namespace_dotted.launch.py
la_run LG_launch_config_default $W/launch/lg_launch_config.launch.py
la_run LG_launch_config_debug $W/launch/lg_launch_config.launch.py log_level:=debug
la_run LH_plain $W/launch/lh_plain.launch.py
la_run LH_plain_with_ros_args $W/launch/lh_plain.launch.py --ros-args --log-level debug
la_run LI_plain_launch_debug_flag -d $W/launch/lh_plain.launch.py
la_run LJ_py_args_list $W/launch/lj_py_args_list.launch.py
la_run LK_py_ros_arguments $W/launch/lk_py_ros_arguments.launch.py

# ---------- runtime change through logger services ----------
svc_run() { # exe node
  local exe=$1 N=$2
  echo; echo "### LOGGER SERVICE $exe (LV_MODE=loop LV_LOGSVC=1, 40 iterations x 0.2 s)"
  ros2 daemon stop > /dev/null 2>&1; ros2 daemon start > /dev/null 2>&1
  LV_MODE=loop LV_LOGSVC=1 timeout 30 ros2 run lv $exe > /tmp/so.txt 2> /tmp/se.txt &
  local np=$!
  sleep 3
  echo "  services: $(timeout 20 ros2 service list 2>&1 | grep -i logger | tr '\n' ' ')"
  echo "  get before: $(timeout 20 ros2 service call /$N/get_logger_levels rcl_interfaces/srv/GetLoggerLevels "{names: [$N]}" 2>&1 | tail -2 | tr '\n' ' ' | cut -c1-300)"
  local t=$(date +%s.%N)
  echo "  set: $(timeout 20 ros2 service call /$N/set_logger_levels rcl_interfaces/srv/SetLoggerLevels "{levels: [{name: $N, level: 10}]}" 2>&1 | tail -2 | tr '\n' ' ' | cut -c1-300)"
  echo "  set call seconds=$(python3 -c "print(round($(date +%s.%N)-$t,2))")"
  echo "  get after: $(timeout 20 ros2 service call /$N/get_logger_levels rcl_interfaces/srv/GetLoggerLevels "{names: [$N]}" 2>&1 | tail -2 | tr '\n' ' ' | cut -c1-300)"
  wait $np; echo "  exit=$?"
  summ /tmp/so.txt /tmp/se.txt
  echo "  first node debug line index: $(grep -h -m1 'MARK node debug' /tmp/so.txt /tmp/se.txt | grep -o 'debug [0-9]*')"
}
svc_run lv_cpp lv_cpp
svc_run lv_py.py lv_py
ros2 daemon stop > /dev/null 2>&1
echo "=== done"
