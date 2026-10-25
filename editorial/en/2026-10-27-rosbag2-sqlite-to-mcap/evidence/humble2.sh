source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1; echo install=$?
dpkg -l ros-humble-rosbag2-storage-mcap | tail -1 | cut -c1-90
ros2 bag record -h 2>&1 | grep -- "-s {"
ros2 bag convert -i h_sqlite -o to_mcap.yaml; echo exit=$?
ls h_mcap; ros2 bag info h_mcap | grep -v "^$"
du -b h_sqlite/*.db3 h_mcap/*.mcap
echo ---missing-topics; printf "output_bags:\n- uri: h_empty\n  storage_id: mcap\n" > no_topics.yaml
ros2 bag convert -i h_sqlite -o no_topics.yaml; echo exit=$?; ros2 bag info h_empty | grep -i "messages\|count"
