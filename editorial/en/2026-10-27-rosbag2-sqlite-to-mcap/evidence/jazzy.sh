source /opt/ros/jazzy/setup.bash; cd /w
ros2 bag record -h 2>&1 | grep -A1 -- "--storage " | head -3
dpkg -l | grep -c rosbag2-storage-mcap
(ros2 topic pub -r 10 /chatter std_msgs/msg/String "{data: hi}" >/dev/null &) ; sleep 2
timeout -s INT 5 ros2 bag record -o j_mcap /chatter >/dev/null 2>&1; sleep 1
ls j_mcap; ros2 bag info j_mcap | grep -i "storage\|messages"
grep -m2 "version\|storage_identifier" j_mcap/metadata.yaml
printf "output_bags:\n- uri: j_sqlite\n  storage_id: sqlite3\n  all_topics: true\n" > to_sqlite.yaml
ros2 bag convert -i j_mcap -o to_sqlite.yaml; echo exit=$?; ls j_sqlite; ros2 bag info j_sqlite | grep -i "storage\|messages"
