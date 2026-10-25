source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
echo ---humble-info-jazzy-dir; ros2 bag info j_mcap 2>&1 | grep -v "^$" | head -6
echo ---humble-info-jazzy-file; ros2 bag info j_mcap/j_mcap_0.mcap 2>&1 | grep -v "^$" | head -6
echo ---humble-play-jazzy-dir; timeout 8 ros2 bag play j_mcap 2>&1 | grep -v "^\[INFO\]" | head -5; echo exit=$?
