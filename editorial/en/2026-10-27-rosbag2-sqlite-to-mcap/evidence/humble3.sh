source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
ros2 bag convert -i h_sqlite -o to_mcap.yaml; echo exit=$?
ls h_mcap; ros2 bag info h_mcap | grep -v "^$"
du -b h_sqlite/*.db3 h_mcap/*.mcap
ros2 bag info h_mcap/h_mcap_0.mcap 2>&1 | grep -i "storage\|messages\|error" 
grep -m3 "version\|storage_identifier" h_mcap/metadata.yaml h_sqlite/metadata.yaml
echo ---empty; printf "output_bags:\n- uri: h_empty\n  storage_id: mcap\n" > no_topics.yaml
ros2 bag convert -i h_sqlite -o no_topics.yaml; echo exit=$?; ros2 bag info h_empty | grep -i "messages"
