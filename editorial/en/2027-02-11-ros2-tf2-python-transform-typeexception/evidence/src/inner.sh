#!/bin/bash
# Runs inside ros:<distro>-ros-base with --network none.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro $ROS_DISTRO $(date -u +%FT%TZ)"
python3 --version
dpkg-query -W -f '${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-tf2-ros-py ros-$ROS_DISTRO-tf2-geometry-msgs \
  ros-$ROS_DISTRO-tf2-sensor-msgs ros-$ROS_DISTRO-geometry-msgs 2>&1
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
echo "=== tf2_geometry_msgs python files"
find /opt/ros/$ROS_DISTRO/lib/python3*/site-packages/tf2_geometry_msgs -name '*.py' 2>&1
echo "=== do_transform_pose source"
python3 - <<'EOF'
import inspect, tf2_geometry_msgs
src = inspect.getsource(tf2_geometry_msgs.do_transform_pose)
print(src[:900])
EOF
echo "=== tfpy.py"
timeout 120 python3 /src/tfpy.py 2>&1
echo "=== import variants (fresh interpreter each)"
for v in "import tf2_geometry_msgs" "from tf2_geometry_msgs import do_transform_pose" "import tf2_geometry_msgs.tf2_geometry_msgs" "from tf2_geometry_msgs.tf2_geometry_msgs import do_transform_pose" "import tf2_sensor_msgs"; do
  timeout 60 python3 - "$v" <<'EOF' 2>&1 | tail -1
import sys
from tf2_ros.buffer_interface import TransformRegistration
try:
    exec(sys.argv[1])
    m = TransformRegistration._TransformRegistration__type_map
    print(f'VARIANT "{sys.argv[1]}": OK, registered {len(m)} types: {sorted(k.__name__ for k in m)}')
except Exception as e:
    print(f'VARIANT "{sys.argv[1]}": {type(e).__name__}: {e}')
EOF
done
echo "=== node with TransformListener + static_transform_publisher"
/opt/ros/$ROS_DISTRO/lib/tf2_ros/static_transform_publisher --x 1.0 --y 2.0 --yaw 1.5707963 --frame-id world --child-frame-id child > /tmp/stp.log 2>&1 &
STP=$!
sleep 2
for m in noimport import; do
  timeout 60 python3 /src/tfnode.py $m 2>&1
done
kill -TERM $STP; sleep 1; kill -KILL $STP 2>/dev/null; wait $STP 2>/dev/null
echo "=== done $(date -u +%FT%TZ)"
