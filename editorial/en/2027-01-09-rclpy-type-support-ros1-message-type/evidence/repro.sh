#!/bin/bash
# Reproduces rclpy "AttributeError: type object 'X' has no attribute '_TYPE_SUPPORT'
# This might be a ROS 1 message type but it should be a ROS 2 message type."
# Run inside ros:<distro>-ros-base with this folder mounted at /w, e.g.:
#   docker run --rm -e ROS_DOMAIN_ID=88 -v $PWD:/w ros:humble-ros-base bash /w/repro.sh
# Network is used only for apt-get (python3-pil, example-interfaces); DDS is kept on domain 88, localhost only.
ulimit -c 0
export ROS_DOMAIN_ID=88
# Humble: ROS_LOCALHOST_ONLY; Jazzy and later: ROS_AUTOMATIC_DISCOVERY_RANGE
if [ "$ROS_DISTRO" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
source /opt/ros/$ROS_DISTRO/setup.bash
echo "distro=$ROS_DISTRO python=$(python3 --version 2>&1)"
echo "rclpy=$(dpkg-query -W -f='${Version}' ros-$ROS_DISTRO-rclpy) ros2cli=$(dpkg-query -W -f='${Version}' ros-$ROS_DISTRO-ros2cli)"

# ros-base has neither PIL nor example_interfaces (AddTwoInts, Fibonacci)
echo "installing python3-pil and ros-$ROS_DISTRO-example-interfaces"
(apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pil ros-$ROS_DISTRO-example-interfaces) >/tmp/apt.log 2>&1 || { echo "apt failed"; tail -5 /tmp/apt.log; }
source /opt/ros/$ROS_DISTRO/setup.bash
python3 -c 'import PIL; print("PIL", PIL.__version__)'
echo "example_interfaces=$(dpkg-query -W -f='${Version}' ros-$ROS_DISTRO-example-interfaces)"

# A fake ROS 1 (genpy-style) std_msgs: plain Python classes, no ROS 2 metaclass.
# This stands in for /opt/ros/noetic/lib/python3/dist-packages ahead of ROS 2 on PYTHONPATH.
F=/tmp/fake_ros1/std_msgs/msg; mkdir -p $F
echo "" > /tmp/fake_ros1/std_msgs/__init__.py
cat > $F/__init__.py <<'X'
class Message(object):          # like genpy.Message
    __slots__ = []
class String(Message):
    _type = 'std_msgs/String'
    _md5sum = '992ce8a1687cec8c8bd883ec73ca41d1'
    __slots__ = ['data']
    def __init__(self, data=''):
        self.data = data
X

C=/w/cases.py
run() { echo; echo "=== $1"; timeout 60 python3 $C $1 2>&1; echo "   exit=$?"; }

echo; echo "##### rclpy cases (normal environment)"
for c in ok_publisher pil_shadow pil_alias_fix class_shadow_srv string_name_pub string_name_action \
         instance_pub module_pub plain_class_action srv_as_pub msg_as_service action_as_client \
         msg_as_action srv_request_as_pub wrong_msg_publish check_helper; do
  run $c
done

echo; echo "##### ROS 1 style std_msgs ahead of ROS 2 on PYTHONPATH"
OLDPP=$PYTHONPATH
export PYTHONPATH=/tmp/fake_ros1:$OLDPP
echo "PYTHONPATH=$PYTHONPATH"
echo "which std_msgs: $(python3 -c 'import std_msgs.msg as m; print(m.__file__)')"
run ros1_shadow_sub
run ros1_shadow_pub
echo; echo "=== ros2 topic pub with the shadow"
timeout 30 ros2 topic pub --once /chatter std_msgs/msg/String "{data: hi}" 2>&1 | tail -4
echo; echo "=== ros2 topic echo with the shadow"
timeout 10 ros2 topic echo /chatter std_msgs/msg/String 2>&1 | tail -4

echo; echo "##### fix: ROS 2 path first (fake ROS 1 path moved to the end)"
export PYTHONPATH=$OLDPP:/tmp/fake_ros1
echo "which std_msgs: $(python3 -c 'import std_msgs.msg as m; print(m.__file__)')"
run ros1_shadow_sub

echo; echo "##### fix: fake ROS 1 path removed"
export PYTHONPATH=$OLDPP
echo "which std_msgs: $(python3 -c 'import std_msgs.msg as m; print(m.__file__)')"
run ros1_shadow_sub

echo; echo "##### rclpy type_support.py source (the check)"
TS=$(python3 -c 'import rclpy.type_support as t; print(t.__file__)')
grep -n "_TYPE_SUPPORT\|def check\|ROS 1\|raise\|NoTypeSupportImportedException" $TS
