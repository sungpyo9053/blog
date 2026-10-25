source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
t(){ rm -rf rep; (timeout -s INT 8 ros2 bag record -o rep /chatter >/dev/null 2>&1 &); sleep 2; "$@" 2>&1 | grep -i "error\|bad" | head -2; sleep 7; echo "  recorded: $(ros2 bag info rep 2>/dev/null | grep -i ^messages)"; }
echo ---j_to_h; t ros2 bag play j_to_h
echo ---rx+qos-override; t ros2 bag play rx --qos-profile-overrides-path qos.yaml
