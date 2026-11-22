#!/bin/bash
# Which value wins when the same ROS 2 parameter is set in several places?
# Run inside ros:<distro>-ros-base, isolated from other DDS traffic:
#   docker run --rm --name pk70-<distro> --network none -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# One ament_cmake package "pk" holds a Python node (pnode) and a C++ node (cnode). Both create a node
# named "pnode", declare string parameters a, b, c with default "default", print RESULT and exit.
# Not kept: two earlier Jazzy passes. In the first the build failed (invalid maintainer e-mail in package.xml).
# The second worked but lacked cases C5b, C14-C17, L15 and L9 with a:=yes, added after "-p a:=y" came out as a bool.
# Its results for the other cases matched out_jazzy.txt.
# The Python node also prints its argv and the content of every --params-file it got.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MAKEFLAGS=-j1
echo "=== distro=$ROS_DISTRO nproc=$(nproc) date=$(date -u +%FT%TZ)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-rcl \
  ros-$ROS_DISTRO-rcl-yaml-param-parser ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"

mkdir -p /ws/src/pk /cfg
cd /ws/src/pk
cat > package.xml <<'X'
<?xml version="1.0"?>
<package format="3">
  <name>pk</name><version>0.0.1</version><description>param order test</description>
  <maintainer email="a@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <depend>rclcpp</depend><exec_depend>rclpy</exec_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(pk)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
add_executable(cnode cnode.cpp)
target_link_libraries(cnode rclcpp::rclcpp)
install(TARGETS cnode DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS pnode.py DESTINATION lib/${PROJECT_NAME} RENAME pnode)
ament_package()
X
cat > cnode.cpp <<'X'
#include <cstdio>
#include <cstdlib>
#include <string>
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  rclcpp::NodeOptions o;
  const char * m = std::getenv("PMODE");
  std::string mode = m ? m : "";
  if (mode == "code_override" || mode == "code_override_noglobal")
    o.parameter_overrides({rclcpp::Parameter("a", std::string("code"))});
  if (mode == "code_override_noglobal") o.use_global_arguments(false);
  auto n = std::make_shared<rclcpp::Node>("pnode", o);
  std::string v[3];
  const char * names[3] = {"a", "b", "c"};
  for (int i = 0; i < 3; i++) v[i] = n->declare_parameter(names[i], std::string("default"));
  std::printf("RESULT cpp node=%s a=%s b=%s c=%s\n", n->get_fully_qualified_name(), v[0].c_str(), v[1].c_str(), v[2].c_str());
  rclcpp::shutdown();
  return 0;
}
X
cat > pnode.py <<'X'
#!/usr/bin/env python3
import os, sys
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
def main():
    rclpy.init(args=sys.argv)
    mode = os.environ.get('PMODE', '')
    kw = {}
    if mode in ('code_override', 'code_override_noglobal'):
        kw['parameter_overrides'] = [Parameter('a', value='code')]
    if mode == 'code_override_noglobal':
        kw['use_global_arguments'] = False
    n = Node('pnode', **kw)
    v = [n.declare_parameter(p, 'default').value for p in 'abc']
    print('RESULT py node=%s a=%s b=%s c=%s' % (n.get_fully_qualified_name(), *v), flush=True)
    if os.environ.get('SHOWARGV'):
        args = sys.argv[1:]
        print('ARGV', ' '.join(args))
        for i, x in enumerate(args):
            if x == '--params-file' and i + 1 < len(args):
                try:
                    body = open(args[i + 1]).read().strip().replace('\n', ' | ')
                except OSError as e:
                    body = repr(e)
                print('FILE', args[i + 1], '=>', body)
    n.destroy_node()
    rclpy.shutdown()
main()
X

cd /cfg
printf '/pnode:\n  ros__parameters:\n    a: f1\n    b: f1\n' > f1.yaml
printf '/pnode:\n  ros__parameters:\n    a: f2\n' > f2.yaml
printf '/**:\n  ros__parameters:\n    a: star\n' > star.yaml
printf '/**:\n  ros__parameters:\n    a: star\n/pnode:\n  ros__parameters:\n    a: name\n' > star_then_name.yaml
printf '/pnode:\n  ros__parameters:\n    a: name\n/**:\n  ros__parameters:\n    a: star\n' > name_then_star.yaml
printf '/pnode:\n  ros__parameters:\n    a: yes\n' > yes.yaml
printf '/pnode:\n  ros__parameters:\n    a: "yes"\n' > yes_quoted.yaml
printf 'pnode:\n  ros__parameters:\n    a: f1nest\n/ns/pnode:\n  ros__parameters:\n    a: nsname\n' > ns.yaml
for f in *.yaml; do echo "--- /cfg/$f"; cat $f; done

cd /ws
t0=$(date +%s%N)
colcon build --event-handlers console_direct- 2>&1 | tail -3
echo "build_ms=$(( ($(date +%s%N)-t0)/1000000 ))"
source /ws/install/setup.bash

waitload() { for i in $(seq 1 12); do l=$(cut -d' ' -f1 /proc/loadavg); awk "BEGIN{exit !($l < 3.5)}" && return; echo "LOAD $l, waiting 20 s"; sleep 20; done; }

# ---------- command line: ros2 run pk <exe> --ros-args ...
cli() {  # cli <label> <PMODE> args...
  local label=$1 mode=$2; shift 2
  for exe in pnode cnode; do
    echo "### CLI $label exe=$exe PMODE=$mode args: $*"
    PMODE=$mode timeout 30 ros2 run pk $exe "$@" 2>&1 | grep -v '^$'
    echo "exit=${PIPESTATUS[0]}"
  done
}
waitload
cli C0_nothing ""
cli C1_f1_then_f2 "" --ros-args --params-file /cfg/f1.yaml --params-file /cfg/f2.yaml
cli C2_f2_then_f1 "" --ros-args --params-file /cfg/f2.yaml --params-file /cfg/f1.yaml
cli C3_p_then_file "" --ros-args -p a:=cli --params-file /cfg/f1.yaml
cli C4_file_then_p "" --ros-args --params-file /cfg/f1.yaml -p a:=cli
cli C5_p_x_then_p_y "" --ros-args -p a:=x -p a:=y
cli C5b_p_first_then_p_second "" --ros-args -p a:=first -p a:=second
cli C6_one_file_star_then_name "" --ros-args --params-file /cfg/star_then_name.yaml
cli C7_one_file_name_then_star "" --ros-args --params-file /cfg/name_then_star.yaml
cli C8_namefile_then_starfile "" --ros-args --params-file /cfg/f1.yaml --params-file /cfg/star.yaml
cli C9_starfile_then_namefile "" --ros-args --params-file /cfg/star.yaml --params-file /cfg/f1.yaml
cli C10_p_node_prefixed "" --ros-args -p pnode:a:=prefixed
cli C11_p_other_node_prefixed "" --ros-args -p other:a:=prefixed
cli C12_two_ros_args_blocks "" --ros-args -p a:=first -- --ros-args -p a:=second
cli C13_ns_file "" --ros-args -r __ns:=/ns --params-file /cfg/ns.yaml
cli C14_p_on "" --ros-args -p a:=on
cli C15_p_quoted_y "" --ros-args -p "a:='y'"
cli C16_yaml_yes "" --ros-args --params-file /cfg/yes.yaml
cli C17_yaml_yes_quoted "" --ros-args --params-file /cfg/yes_quoted.yaml
waitload
cli C20_code_override_alone code_override
cli C21_code_override_and_p code_override --ros-args -p a:=cli
cli C22_code_override_and_file code_override --ros-args --params-file /cfg/f1.yaml
cli C23_code_override_noglobal_and_p code_override_noglobal --ros-args -p a:=cli

# ---------- launch files (launch_ros Node)
mkdir -p /l
cat > /l/case.launch.py <<'X'
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, SetParameter
C = os.environ['LCASE']
EXE = os.environ.get('EXE', 'pnode')
F1, F2, STAR = '/cfg/f1.yaml', '/cfg/f2.yaml', '/cfg/star.yaml'
def node(**kw):
    return Node(package='pk', executable=EXE, output='screen', **kw)
def generate_launch_description():
    if C == 'L1_file_then_dict':
        return LaunchDescription([node(parameters=[F1, {'a': 'dict'}])])
    if C == 'L2_dict_then_file':
        return LaunchDescription([node(parameters=[{'a': 'dict'}, F1])])
    if C == 'L3_f1_then_f2':
        return LaunchDescription([node(parameters=[F1, F2])])
    if C == 'L4_setparam_then_node_file':
        return LaunchDescription([SetParameter(name='a', value='global'), node(parameters=[F1])])
    if C == 'L5_setparam_then_node_dict_b':
        return LaunchDescription([SetParameter(name='a', value='global'), node(parameters=[{'b': 'dict'}])])
    if C == 'L6_node_then_setparam':
        return LaunchDescription([node(parameters=[F1]), SetParameter(name='a', value='global')])
    if C == 'L7_file_and_ros_arguments':
        return LaunchDescription([node(parameters=[F1], ros_arguments=['-p', 'a:=rosarg'])])
    if C == 'L8_file_and_arguments_ros_args':
        return LaunchDescription([node(parameters=[F1], arguments=['--ros-args', '-p', 'a:=arg'])])
    if C == 'L9_file_then_launcharg_dict':
        return LaunchDescription([DeclareLaunchArgument('a', default_value='argdefault'),
                                  node(parameters=[F1, {'a': LaunchConfiguration('a')}])])
    if C == 'L10_launcharg_dict_then_file':
        return LaunchDescription([DeclareLaunchArgument('a', default_value='argdefault'),
                                  node(parameters=[{'a': LaunchConfiguration('a')}, F1])])
    if C == 'L11_star_file_then_dict':
        return LaunchDescription([node(parameters=[STAR, {'a': 'dict'}])])
    if C == 'L12_setparametersfromfile':
        from launch_ros.actions import SetParametersFromFile
        return LaunchDescription([SetParametersFromFile(F2), node(parameters=[F1])])
    if C == 'L13_node_name_override_file':
        return LaunchDescription([node(name='imu', parameters=[F1])])
    if C == 'L15_dict_value_y':
        return LaunchDescription([node(parameters=[{'a': 'y'}])])
    if C == 'L14_code_override_and_dict':
        return LaunchDescription([node(parameters=[{'a': 'dict'}])])
    raise RuntimeError('unknown case ' + C)
X
lc() {  # lc <case> [PMODE] [launch args...]
  local c=$1 mode=$2; shift 2
  for exe in pnode cnode; do
    echo "### LAUNCH $c exe=$exe PMODE=$mode launch_args: $*"
    t0=$(date +%s%N)
    SHOWARGV=1 PMODE=$mode EXE=$exe LCASE=$c timeout 40 ros2 launch /l/case.launch.py "$@" 2>&1 \
      | grep -E 'RESULT|ARGV|FILE|ERROR|rror|xception|process has finished' | sed -E 's/pid [0-9]+/pid N/; s#/tmp/launch_params_[a-z0-9_]+#/tmp/launch_params_X#g'
    echo "exit=${PIPESTATUS[0]} wall_ms=$(( ($(date +%s%N)-t0)/1000000 ))"
  done
}
waitload
lc L1_file_then_dict ""
lc L2_dict_then_file ""
lc L3_f1_then_f2 ""
lc L4_setparam_then_node_file ""
lc L5_setparam_then_node_dict_b ""
lc L6_node_then_setparam ""
waitload
lc L7_file_and_ros_arguments ""
lc L8_file_and_arguments_ros_args ""
lc L9_file_then_launcharg_dict "" a:=fromcli
lc L9_file_then_launcharg_dict ""
lc L10_launcharg_dict_then_file "" a:=fromcli
waitload
lc L11_star_file_then_dict ""
lc L12_setparametersfromfile ""
lc L13_node_name_override_file ""
lc L14_code_override_and_dict code_override
lc L15_dict_value_y ""
lc L9_file_then_launcharg_dict "" a:=yes
echo "=== done $ROS_DISTRO $(date -u +%FT%TZ)"
