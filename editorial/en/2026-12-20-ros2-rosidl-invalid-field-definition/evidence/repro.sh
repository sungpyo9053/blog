#!/bin/bash
# Run inside ros:<distro>-ros-base. Builds one tiny interface package per variant with
# colcon and prints the rosidl error lines (or OK) for each .msg/.srv mistake.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
for p in rosidl-adapter rosidl-parser rosidl-cmake rclpy rclcpp ros2cli rmw rmw-implementation geometry-msgs; do
  dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-$p 2>/dev/null; done
python3 --version; cmake --version | head -1

# mk <variant> <file name in msg/ or srv/> <content (printf %b)> [extra: nodeps|crlf]
mk() {
  local v=$1 f=$2 body=$3 extra=$4 W=/w/$1 P=/w/$1/src/v_$1
  mkdir -p $P/$(dirname $f)
  printf '%b' "$body" > $P/$f
  [ "$extra" = crlf ] && sed -i 's/$/\r/' $P/$f
  local fp='find_package(geometry_msgs REQUIRED)' dep='DEPENDENCIES geometry_msgs' xdep='<depend>geometry_msgs</depend>'
  [ "$extra" = nodeps ] && { fp=''; dep=''; xdep=''; }
  [ "$extra" = nodeparg ] && dep=''
  cat > $P/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>v_$v</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>rosidl_default_generators</buildtool_depend>
$xdep<exec_depend>rosidl_default_runtime</exec_depend><member_of_group>rosidl_interface_packages</member_of_group>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > $P/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project(v_$v)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
$fp
rosidl_generate_interfaces(\${PROJECT_NAME} "$f" $dep)
ament_package()
X
}
run() {  # run <variant>
  local v=$1; cd /w/$v
  local t0=$(date +%s%N)
  timeout 900 colcon build --parallel-workers 1 --event-handlers console_direct- > /w/$v.log 2>&1; local rc=$?
  local t1=$(date +%s%N)
  echo "--- $v rc=$rc ms=$(( (t1 - t0) / 1000000 ))"
  echo "content: $(cat -A /w/$v/src/v_$v/*/* | tr '\n' '|' )"
  if [ $rc -eq 0 ]; then echo OK; else
    grep -E 'rosidl_adapter\.parser\.|rosidl_parser|Error|error:|Exception|is an invalid|should have|Could not|Unknown|unknown|not found|No such' /w/$v.log | grep -v '^  File ' | sed 's/^ *//' | awk '!s[$0]++' | head -14
    echo "  [full exception text]"
    grep -E -A2 '^ *(rosidl_adapter\.parser\.[A-Za-z]+|NameError|ValueError|TypeError|KeyError):' /w/$v.log | sed 's/^ */  /' | awk '!s[$0]++' | head -8
  fi
}
export MAKEFLAGS=-j1
mkdir -p /w
mk no_name        msg/TwistAccel.msg 'geometry_msgs/Twist\ngeometry_msgs/Accel\n'
mk fixed          msg/TwistAccel.msg 'geometry_msgs/Twist twist\ngeometry_msgs/Accel accel\n'
mk msg_infix      msg/TwistAccel.msg 'geometry_msgs/msg/Twist twist\n'
mk lower_type     msg/TwistAccel.msg 'geometry_msgs/twist twist\n'
mk no_find_pkg    msg/TwistAccel.msg 'geometry_msgs/Twist twist\n' nodeps
mk upper_field    msg/Speed.msg 'float64 Speed\n'
mk camel_field    msg/Speed.msg 'float64 maxSpeed\n'
mk double_us      msg/Speed.msg 'float64 max__speed\n'
mk trailing_us    msg/Speed.msg 'float64 speed_\n'
mk digit_first    msg/Speed.msg 'float64 2d_speed\n'
mk dash_field     msg/Speed.msg 'float64 max-speed\n'
mk type_float     msg/Speed.msg 'float speed\n'
mk type_int       msg/Speed.msg 'int count\n'
mk type_double    msg/Speed.msg 'double speed\n'
mk kw_class       msg/Speed.msg 'int32 class\n'
mk kw_type        msg/Speed.msg 'float64 type\nint32 id\n'
mk no_dep_arg     msg/TwistAccel.msg 'geometry_msgs/Twist twist\n' nodeparg
mk dup_field      msg/Speed.msg 'int32 count\nint32 count\n'
mk const_ok       msg/Speed.msg 'int32 MAX_COUNT=10\nstring NAME="robot"\n'
mk const_lower    msg/Speed.msg 'int32 max_count=10\n'
mk default_ok     msg/Speed.msg 'int32 count 5\nfloat64 speed 1.5\nstring label "hi"\n'
mk default_bad    msg/Speed.msg 'int32 count 1.5\n'
mk array_space    msg/Speed.msg 'float64 [] values\n'
mk tab_sep        msg/Speed.msg 'float64\tspeed\n'
mk crlf           msg/Speed.msg 'float64 speed\nint32 count\n' crlf
mk comment_ok     msg/Speed.msg '# header comment\nfloat64 speed  # inline comment\n'
mk srv_no_sep     srv/AddTwo.srv 'int64 a\nint64 b\nint64 sum\n'
mk srv_two_sep    srv/AddTwo.srv 'int64 a\n---\nint64 sum\n---\nint64 extra\n'
mk srv_ok         srv/AddTwo.srv 'int64 a\nint64 b\n---\nint64 sum\n'
mk srv_dashes4    srv/AddTwo.srv 'int64 a\n----\nint64 sum\n'
mk action_one_sep action/Count.action 'int32 target\n---\nint32 result\n'
for v in no_name msg_infix lower_type no_find_pkg upper_field camel_field double_us trailing_us digit_first dash_field \
         type_float type_int type_double kw_class dup_field const_lower default_bad array_space tab_sep crlf \
         srv_no_sep srv_two_sep srv_dashes4 action_one_sep const_ok default_ok comment_ok srv_ok kw_type no_dep_arg fixed; do run $v; done

echo "=== check fixed message"
source /w/fixed/install/setup.bash
ros2 interface show v_fixed/msg/TwistAccel 2>&1 | head -3
python3 -c "from v_fixed.msg import TwistAccel; m=TwistAccel(); print('python import OK', type(m.twist).__name__, type(m.accel).__name__)" 2>&1 | tail -1
for v in const_ok default_ok; do [ -f /w/$v/install/setup.bash ] && source /w/$v/install/setup.bash; done
python3 -c "from v_const_ok.msg import Speed; print('const', Speed.MAX_COUNT, Speed.NAME)" 2>&1 | tail -1
python3 -c "from v_default_ok.msg import Speed; m=Speed(); print('defaults', m.count, m.speed, m.label)" 2>&1 | tail -1
[ -f /w/crlf/install/setup.bash ] && { source /w/crlf/install/setup.bash; python3 -c "from v_crlf.msg import Speed; print('crlf fields', Speed.get_fields_and_field_types())" 2>&1 | tail -1; }
[ -f /w/tab_sep/install/setup.bash ] && { source /w/tab_sep/install/setup.bash; python3 -c "from v_tab_sep.msg import Speed; print('tab fields', Speed.get_fields_and_field_types())" 2>&1 | tail -1; }
[ -f /w/kw_type/install/setup.bash ] && { source /w/kw_type/install/setup.bash; python3 -c "from v_kw_type.msg import Speed; m=Speed(); print('kw_type fields', Speed.get_fields_and_field_types(), m.type)" 2>&1 | tail -1; }
echo "=== done"
