#!/bin/bash
# Run inside ros:<distro>-ros-base, no network:
#   docker run --rm --network none -e ROS_DOMAIN_ID=88 -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Jazzy ran twice on the runner (the first pass lacked the sqlite3/100k kill cases); out_jazzy.txt is the second, complete pass.
# DDS isolated: --network none, domain 88, ROS_LOCALHOST_ONLY=1 / ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST.
# Exercises rosbag2_py SequentialWriter / SequentialReader: API shape, finalizing (metadata.yaml),
# reopen errors, bad write arguments, reader errors, reindex, and an rclpy node stopped by signals.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
P="timeout 60 python3 /w/bag.py"
B=/tmp/bags; rm -rf $B; mkdir -p $B
run() { echo "--- $*"; $P "$@" 2>&1 | grep -v '^\s*$'; echo "exit=${PIPESTATUS[0]}"; }
ls_() { echo "--- ls $1"; if [ -d "$1" ]; then ls -la "$1" | tail -n +2; else ls -la "$1" 2>&1; fi; }
echo "=== distro=$ROS_DISTRO $(python3 --version)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rosbag2-py ros-$ROS_DISTRO-rosbag2-cpp \
  ros-$ROS_DISTRO-rosbag2-storage-default-plugins ros-$ROS_DISTRO-rosbag2-storage-mcap ros-$ROS_DISTRO-mcap-vendor \
  ros-$ROS_DISTRO-rosbag2 ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw \
  ros-$ROS_DISTRO-rmw-fastrtps-cpp 2>&1
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
run info
run tm_positional

echo "=== 1. write and finalize"
for sid in none sqlite3 mcap; do run write $B/w_$sid $sid 1000 del; done
run write $B/w_close none 100 close
run write $B/w_exit none 100 exit;   ls_ $B/w_exit
run write $B/w_osexit none 100 osexit; ls_ $B/w_osexit
run write $B/w_kill none 100 kill;   ls_ $B/w_kill
run write $B/w_kill_sqlite3 sqlite3 1000 kill;   ls_ $B/w_kill_sqlite3
run write $B/w_kill_mcap100k mcap 100000 kill;   ls_ $B/w_kill_mcap100k
echo "--- timing: 10000 and 100000 small messages"
run write $B/t10k none 10000 del
run write $B/t100k none 100000 del
for sid in sqlite3 mcap; do run write $B/t100k_$sid $sid 100000 del; done

echo "=== 2. reopen an existing bag folder"
run reopen $B/w_none none
mkdir -p $B/empty_dir; run reopen $B/empty_dir none

echo "=== 3. bad write arguments"
run no_create $B/nocreate
run bad_write_args $B/badargs

echo "=== 4. read"
for d in w_none w_sqlite3 w_mcap; do for sid in none sqlite3 mcap; do run read $B/$d $sid; done; done
for f in $B/w_none/* ; do case $f in *.yaml) ;; *) run read $f none ;; esac; done
run read $B/does_not_exist none
run read $B/empty_dir none
run read $B/t100k none
run read_after_end $B/w_none
run read_filter $B/w_none

echo "=== 5. unfinalized bags: reader, ros2 bag info, reindex"
for d in w_osexit w_kill w_kill_sqlite3 w_kill_mcap100k; do
  run read $B/$d none
  for f in $B/$d/*; do run read $f none; done
  echo "--- ros2 bag info $d"; timeout 60 ros2 bag info $B/$d 2>&1 | tail -n 6; echo "exit=${PIPESTATUS[0]}"
  s=$(ls $B/$d | sed -n 's/.*\.\(db3\|mcap\)$/\1/p' | head -1); [ "$s" = db3 ] && s=sqlite3
  echo "--- ros2 bag reindex $d (no -s)"; timeout 60 ros2 bag reindex $B/$d 2>&1 | tail -n 4; echo "exit=${PIPESTATUS[0]}"
  echo "--- ros2 bag reindex $d -s $s"; timeout 60 ros2 bag reindex $B/$d -s $s 2>&1 | tail -n 4; echo "exit=${PIPESTATUS[0]}"
  ls_ $B/$d
  run read $B/$d none
done

echo "=== 6. reader while writer is alive"
for sid in sqlite3 mcap; do run concurrent $B/conc_$sid $sid; done

echo "=== 7. rclpy node writing from a timer, stopped by a signal"
for sig in INT TERM KILL; do for mode in none del; do
  [ $sig = KILL ] && [ $mode = del ] && continue
  for sid in none sqlite3; do
  [ $sid = sqlite3 ] && [ $sig != KILL ] && continue
  d=$B/node_${sig}_${mode}_$sid
  echo "--- node sig=$sig finalize=$mode storage=$sid"
  python3 /w/bag.py node $d $mode $sid > /tmp/node.log 2>&1 &
  pid=$!; sleep 3; kill -$sig $pid; wait $pid; echo "exit=$?"
  grep -v '^\s*$' /tmp/node.log | tail -n 8
  ls_ $d
  run read $d none
  done
done; done
echo "=== done"
