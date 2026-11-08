d=$ROS_DISTRO
dpkg-query -W -f='${Package} ${Version}\n' python3 ros-$d-rclpy ros-$d-rclcpp ros-$d-ros2cli ros-$d-rmw ros-$d-rmw-implementation ros-$d-rmw-fastrtps-cpp ros-$d-rosidl-generator-py ros-$d-std-msgs 2>&1
source /opt/ros/$d/setup.bash; echo "default RMW: $(ros2 doctor --report 2>/dev/null | grep -m1 'middleware name' | awk '{print $NF}')"
