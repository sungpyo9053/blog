source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
rm -rf replay; (timeout -s INT 9 ros2 bag record -o replay /chatter >/dev/null 2>&1 &); sleep 2
ros2 bag play rx >/dev/null 2>&1; echo play_exit=$?; sleep 7
ros2 bag info replay | grep -i "messages"
