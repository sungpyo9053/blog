source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
ros2 bag play rx 2>&1 | grep -v "^$" | tail -5
echo ---h_mcap; timeout 10 ros2 bag play h_mcap 2>&1 | grep -v "^$" | tail -3; echo exit=$?
