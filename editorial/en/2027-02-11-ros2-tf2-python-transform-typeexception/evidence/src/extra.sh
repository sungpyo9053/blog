#!/bin/bash
# Second pass inside the same image: exception class and what happens in rclpy.spin()
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== extra $ROS_DISTRO $(date -u +%FT%TZ)"
timeout 60 python3 /src/extra.py 2>&1 | grep -v "LOCALHOST_ONLY is deprecated\|'localhost_only' is enabled"
echo "exit code: ${PIPESTATUS[0]}"
echo "=== uncaught version: plain rclpy.spin, no try/except around spin"
timeout 60 python3 - <<'EOF' 2>&1 | grep -v "LOCALHOST_ONLY is deprecated\|'localhost_only' is enabled" | tail -4
import rclpy, tf2_ros
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
rclpy.init()
n = Node('crash_test')
buf = tf2_ros.Buffer()
def cb():
    ps = PoseStamped(); ps.header.frame_id = 'child'
    buf.transform(ps, 'world')
n.create_timer(0.1, cb)
rclpy.spin(n)
EOF
echo "exit code: ${PIPESTATUS[0]}"
