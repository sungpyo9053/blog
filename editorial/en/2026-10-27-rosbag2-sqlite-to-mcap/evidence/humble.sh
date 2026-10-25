set -x
source /opt/ros/humble/setup.bash
cd /w
dpkg -l | grep -c rosbag2-storage-mcap
ros2 bag record -h 2>&1 | grep -A2 -- "--storage " | head -4
(ros2 topic pub -r 10 /chatter std_msgs/msg/String "{data: hi}" >/dev/null &) ; sleep 2
timeout -s INT 5 ros2 bag record -o h_sqlite /chatter; sleep 1
ros2 bag info h_sqlite
ls h_sqlite
cat > to_mcap.yaml <<Y
output_bags:
- uri: h_mcap
  storage_id: mcap
  all_topics: true
Y
ros2 bag convert -i h_sqlite -o to_mcap.yaml; echo exit=$?
ls h_mcap 2>&1; ros2 bag info h_mcap 2>&1 | head -12
