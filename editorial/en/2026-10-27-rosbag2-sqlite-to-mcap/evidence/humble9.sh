source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
rm -rf rep; (timeout -s INT 8 ros2 bag record -o rep /chatter >/dev/null 2>&1 &); sleep 2
ros2 bag play j_mcap/j_mcap_0.mcap --qos-profile-overrides-path qos.yaml 2>&1 | grep -i "error\|bad" | head -2; sleep 7
echo "file+override recorded: $(ros2 bag info rep | grep -i ^messages)"
ros2 bag play -h | grep -A1 -- "--qos-profile-overrides-path" | head -2
