source /opt/ros/humble/setup.bash; cd /w
apt-get update -qq >/dev/null && apt-get install -y -qq ros-humble-rosbag2-storage-mcap >/dev/null 2>&1
(ros2 topic echo /chatter --once 2>/dev/null | head -1 > echo_out.txt &) ; sleep 1
echo ---play-file; timeout 10 ros2 bag play j_mcap/j_mcap_0.mcap 2>&1 | grep -iv "^\[INFO\]" | head -3; sleep 1; echo echoed: $(cat echo_out.txt)
echo ---reindex; mkdir -p rx && cp j_mcap/j_mcap_0.mcap rx/ && ros2 bag reindex rx -s mcap 2>&1 | grep -iv "^\[INFO\]" | head -3; echo exit=$?
grep -m1 "version" rx/metadata.yaml; ros2 bag info rx 2>&1 | grep -i "storage\|messages\|exception"
echo ---convert-from-file; printf "output_bags:\n- uri: j_to_h\n  storage_id: sqlite3\n  all_topics: true\n" > j2h.yaml
ros2 bag convert -i j_mcap/j_mcap_0.mcap mcap -o j2h.yaml 2>&1 | grep -iv "^\[INFO\]" | head -3; ros2 bag info j_to_h 2>&1 | grep -i "storage\|messages"
