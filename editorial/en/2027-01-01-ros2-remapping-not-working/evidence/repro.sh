#!/bin/bash
# Run inside ros:<distro>-ros-base (as measured, one distro after another):
#   docker run --rm --network none -e ROS_DOMAIN_ID=77 --pids-limit 512 --ulimit core=0 -v $PWD:/e ros:<distro>-ros-base bash /e/repro.sh
# Measures which ROS 2 remap rules (-r, launch remappings, SetRemap, bag play --remap)
# actually change the names a node ends up using, and which ones are silently ignored.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export PYTHONUNBUFFERED=1
echo "=== distro=$ROS_DISTRO rmw=${RMW_IMPLEMENTATION:-default}"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rcl ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp \
  ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-launch-ros ros-$ROS_DISTRO-rosbag2 ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>/dev/null
W=/w; mkdir -p $W

# rm_node: one node that uses every kind of name, then prints the names the graph reports for it.
cat > $W/rm_node.py <<'X'
#!/usr/bin/env python3
import sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rclpy.action import ActionServer
from tf2_msgs.action import LookupTransform
rclpy.init(args=sys.argv)
n = Node('rm_node')
pubs = [n.create_publisher(String, t, 10) for t in ('scan', '/abs_scan', '~/priv', '/tf')]
sub = n.create_subscription(String, 'cmd_vel', lambda m: None, 10)
srv = n.create_service(Trigger, 'reset', lambda req, res: res)
act = ActionServer(n, LookupTransform, 'fib', lambda gh: LookupTransform.Result())
skip = ('/rosout', '/parameter_events')
def mine():
    name, ns = n.get_name(), n.get_namespace()
    p = n.get_publisher_names_and_types_by_node(name, ns)
    s = n.get_subscriber_names_and_types_by_node(name, ns)
    v = n.get_service_names_and_types_by_node(name, ns)
    return p, s, v
t0 = time.time()
while time.time() - t0 < 5.0:
    rclpy.spin_once(n, timeout_sec=0.1)
    p, s, v = mine()
    if p and s and v:
        break
fq = n.get_fully_qualified_name()
print(f'NODE {fq}')
print('PUB  ' + ' '.join(sorted(t for t, _ in p if t not in skip)))
print('SUB  ' + ' '.join(sorted(t for t, _ in s if t not in skip)))
print('SRV  ' + ' '.join(sorted(t for t, _ in v if 'parameter' not in t and 'type_description' not in t)))
n.destroy_node()
rclpy.shutdown()
X
chmod +x $W/rm_node.py

run() {  # run <label> <ros args...>
  echo "--- CASE $1"
  shift
  local t0=$(date +%s.%N)
  timeout 30 python3 $W/rm_node.py "$@" > /tmp/o.txt 2>&1
  local rc=$?
  local t1=$(date +%s.%N)
  grep -E '^(NODE|PUB |SUB |SRV )' /tmp/o.txt
  grep -vE '^(NODE|PUB |SUB |SRV )' /tmp/o.txt | tail -3
  echo "exit=$rc secs=$(python3 -c "print(round($t1-$t0,2))")"
}

echo "##### 1. ros2 run / --ros-args -r rules"
run base               --ros-args
run rel                --ros-args -r scan:=scan_front
run abs_both           --ros-args -r /scan:=/scan_front
run rel_to_abs_target  --ros-args -r abs_scan:=front
run no_ros_args        -r scan:=scan_front
run no_ros_args_ns    -r __ns:=/robot1
run no_ros_args_p_and_r -r scan:=scan_front __ns:=/robot1
run long_remap_flag    --ros-args --remap scan:=scan_front
run ns_only            --ros-args -r __ns:=/robot1
run ns_rel             --ros-args -r __ns:=/robot1 -r scan:=scan_front
run ns_abs_rule        --ros-args -r __ns:=/robot1 -r /scan:=/scan_front
run ns_full_rule       --ros-args -r __ns:=/robot1 -r /robot1/scan:=/robot1/scan_front
run ns_rule_before_ns  --ros-args -r scan:=scan_front -r __ns:=/robot1
run ns_absname_rel_rule --ros-args -r __ns:=/robot1 -r abs_scan:=front
run ns_absname_abs_rule --ros-args -r __ns:=/robot1 -r /abs_scan:=front
run ns_tf_to_rel       --ros-args -r __ns:=/robot1 -r /tf:=tf
run priv_plain         --ros-args -r priv:=priv2
run priv_tilde         --ros-args -r '~/priv:=priv2'
run priv_full          --ros-args -r /rm_node/priv:=/priv2
run node_specific_ok   --ros-args -r rm_node:scan:=scan_front
run node_specific_bad  --ros-args -r other_node:scan:=scan_front
run two_rules_order    --ros-args -r scan:=first -r scan:=second
run chain              --ros-args -r scan:=a -r a:=b
run sub_rel            --ros-args -r cmd_vel:=/robot1/cmd_vel
run srv_rel            --ros-args -r reset:=reset2
run action_rel         --ros-args -r fib:=fib2
run action_inner_topic --ros-args -r /fib/_action/feedback:=/fb2
run wildcard_star      --ros-args -r '*/scan:=scan_front'
run wildcard_dstar     --ros-args -r '**/scan:=scan_front'
run bad_no_colon       --ros-args -r scan=scan_front
run bad_space          --ros-args -r scan:= scan_front
run bad_dash_name      --ros-args -r scan:=scan-front
run bad_digit_name     --ros-args -r scan:=2d_scan
run node_rename        --ros-args -r __node:=lidar -r scan:=scan_front
run node_rename_spec   --ros-args -r __node:=lidar -r rm_node:scan:=scan_front

echo "##### 2. launch remappings"
cat > $W/rm.launch.py <<'X'
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace, SetRemap
def generate_launch_description():
    return LaunchDescription([
        Node(executable='/w/rm_node.py', name='l_rel', namespace='robot1',
             remappings=[('scan', 'scan_front')], output='screen'),
        Node(executable='/w/rm_node.py', name='l_abs', namespace='robot1',
             remappings=[('/scan', '/scan_front')], output='screen'),
        Node(executable='/w/rm_node.py', name='l_tf', namespace='robot1',
             remappings=[('/tf', 'tf')], output='screen'),
        GroupAction([PushRosNamespace('robot2'), SetRemap(src='scan', dst='scan_front'),
                     Node(executable='/w/rm_node.py', name='l_group', output='screen')]),
        GroupAction([PushRosNamespace('robot3'), SetRemap(src='/robot3/scan', dst='/robot3/scan_front'),
                     Node(executable='/w/rm_node.py', name='l_group_full', output='screen')]),
    ])
X
timeout 60 ros2 launch $W/rm.launch.py > /tmp/l.txt 2>&1; echo "launch exit=$?"
grep -E 'NODE|PUB |SUB |SRV |rror' /tmp/l.txt | sed -E 's/^\[[^]]*\] //' | sort

echo "##### 3. ros2 bag play --remap"
cd /tmp && rm -rf bag1
# Lyrical's ros2 bag record dropped positional topics; it needs --topics
if [ "$ROS_DISTRO" = lyrical ]; then TOP="--topics /scan --disable-keyboard-controls"; else TOP="/scan"; fi
# background jobs of a non-interactive bash start with SIGINT ignored; reset it so Ctrl+C-style stop works
timeout -k 5 -s INT 11 python3 -c 'import os,signal,sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execvp(sys.argv[1], sys.argv[1:])' ros2 bag record -o bag1 $TOP > /tmp/rec.txt 2>&1 &
RP=$!
sleep 3
timeout 6 ros2 topic pub -r 10 /scan std_msgs/msg/String "data: hi" > /dev/null 2>&1
wait $RP; echo "record exit=$?"
grep -iE 'rror|usage' /tmp/rec.txt | tail -3
ros2 bag info bag1 2>&1 | grep -E 'Count|Topic:|Storage'
play() {  # play <label> <args...>; listens on /scan_front
  echo "--- PLAY $1"; shift
  timeout 15 ros2 topic echo --once /scan_front std_msgs/msg/String > /tmp/e.txt 2>&1 &
  local EP=$!
  sleep 3
  timeout 20 ros2 bag play bag1 "$@" > /tmp/p.txt 2>&1; echo "play exit=$?"
  grep -iE 'rror|unrecognized' /tmp/p.txt | tail -2
  wait $EP; echo "echo exit=$? got=$(grep -c 'data: hi' /tmp/e.txt)"
}
play remap_abs     --remap /scan:=/scan_front
play remap_rel     --remap scan:=scan_front
play short_m       -m /scan:=/scan_front
play ros_args_r    --ros-args -r /scan:=/scan_front
play none

echo "##### 4. changing a topic at runtime (recreate subscription on parameter change)"
cat > $W/dyn_node.py <<'X'
#!/usr/bin/env python3
import sys, rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from std_msgs.msg import String
rclpy.init(args=sys.argv)
n = Node('dyn_node')
n.declare_parameter('in_topic', 'scan')
state = {'sub': n.create_subscription(String, 'scan', lambda m: None, 10)}
def on_set(params):
    for p in params:
        if p.name == 'in_topic':
            n.destroy_subscription(state['sub'])
            state['sub'] = n.create_subscription(String, p.value, lambda m: None, 10)
            n.get_logger().info(f'now subscribed to {state["sub"].topic_name}')
    return SetParametersResult(successful=True)
n.add_on_set_parameters_callback(on_set)
def show():
    subs = n.get_subscriber_names_and_types_by_node('dyn_node', '/')
    print('SUBS ' + ' '.join(sorted(t for t, _ in subs if t != '/parameter_events')), flush=True)
n.create_timer(1.0, show)
try:
    rclpy.spin(n)
except Exception:
    pass
X
chmod +x $W/dyn_node.py
timeout 40 python3 $W/dyn_node.py > /tmp/d.txt 2>&1 &
DP=$!
sleep 6
ros2 param set /dyn_node in_topic scan_front 2>&1
sleep 3
kill -INT $DP; wait $DP 2>/dev/null
grep -E 'now subscribed|^SUBS' /tmp/d.txt | uniq -c
ros2 daemon stop > /dev/null 2>&1
echo "=== done"
