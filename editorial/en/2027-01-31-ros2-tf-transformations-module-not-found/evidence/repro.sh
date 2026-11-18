#!/bin/bash
# Run inside ros:<distro>-ros-base (needs network for apt and rosdep; DDS isolated with domain 88 + localhost only):
#   docker run --rm --name pk48-tft-<distro> --pids-limit 40 --cpus 1.5 -v /tmp/en-pick63:/w ros:<distro>-ros-base bash /w/repro.sh
# Lyrical's tf2_echo hit the 40-pid limit (threads count as pids: "pthread_create failed"), so section H alone
# was rerun with:  docker run ... --pids-limit 120 -e ONLY=H ... bash /w/repro.sh   (appended to out_lyrical.txt)
# out_humble_try1.txt is the first Humble pass: sections A-G are complete, but section H hung because the
# script sent SIGINT to a background job (ignored in non-interactive bash); the kill line below is the fix.
# Its rosdep install --simulate also failed on a bad maintainer email in the test package.xml (fixed below).
ulimit -c 0
export ROS_DOMAIN_ID=88 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
D=$ROS_DISTRO
sec() { echo; echo "### $*"; }
run() { echo "\$ $*"; timeout 120 bash -c "$*" 2>&1 | tail -n 6; echo "exit=${PIPESTATUS[0]}"; }
tsec() { local s=$(date +%s.%N); "$@"; echo "took $(python3 -c "print(round($(date +%s.%N)-$s,1))") s"; }

if [ "$ONLY" = H ]; then source /opt/ros/$D/setup.bash; echo "=== rerun of section H only, pids-limit 120"; fi
[ "$ONLY" = H ] || {
echo "=== distro=$D nproc=$(nproc) date=$(date -u +%FT%TZ) load=$(cut -d' ' -f1-3 /proc/loadavg)"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw \
  ros-$D-rmw-implementation ros-$D-rmw-fastrtps-cpp ros-$D-tf2-ros ros-$D-tf2-ros-py python3-numpy 2>/dev/null

sec "A1 not sourced, nothing installed"
run "python3 -c 'import tf_transformations'"
source /opt/ros/$D/setup.bash
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
sec "A2 sourced, nothing installed"
run "python3 -c 'import tf_transformations'"
run "python3 -c 'from tf.transformations import euler_from_quaternion'"
run "python3 -c 'import tf2'"
run "python3 -c 'from tf2_ros.transformations import euler_from_quaternion'"
run "python3 -c 'import tf2_ros; print(\"tf2_ros ok\", [n for n in dir(tf2_ros) if \"euler\" in n.lower() or \"quat\" in n.lower()])'"
run "python3 -c 'import transforms3d'"
run "python3 -c 'import scipy'"
run "python3 -c 'import numpy; print(numpy.__version__)'"
run "ros2 pkg list | grep -c tf_transformations"

sec "B apt index and candidates"
tsec run "apt-get update -qq"
for p in ros-$D-tf-transformations python3-transforms3d python3-scipy; do
  echo "--- $p"; apt-cache policy $p | head -3
done
echo "--- depends of ros-$D-tf-transformations"; apt-cache depends ros-$D-tf-transformations 2>&1 | head -12

sec "C rosdep keys"
tsec run "rosdep update --rosdistro $D 2>&1 | tail -2"
run "rosdep resolve tf_transformations"
run "rosdep resolve python3-transforms3d"
run "rosdep resolve python3-scipy"
mkdir -p /tmp/ws/src/demo
cat > /tmp/ws/src/demo/package.xml <<'X'
<?xml version="1.0"?>
<package format="3">
  <name>demo</name><version>0.0.0</version><description>d</description>
  <maintainer email="demo@example.com">a</maintainer><license>MIT</license>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>tf_transformations</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>
X
run "cd /tmp/ws && rosdep install --from-paths src --ignore-src -y --simulate"

sec "D only python3-transforms3d installed"
tsec run "apt-get install -y -qq --no-install-recommends python3-transforms3d >/dev/null; echo installed"
run "python3 -c 'import transforms3d; print(transforms3d.__version__)'"
run "python3 -c 'import tf_transformations'"

sec "E install ros-$D-tf-transformations (shell was sourced before the install)"
tsec run "apt-get install -y --no-install-recommends ros-$D-tf-transformations | grep -E 'newly installed|Need to get|After this'"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-tf-transformations python3-transforms3d
run "python3 -c 'import tf_transformations as t; print(t.__file__); print(t.euler_from_quaternion([0,0,0.7071068,0.7071068]))'"
run "env -u PYTHONPATH python3 -c 'import tf_transformations'"
run "ros2 pkg list | grep tf_transformations"
run "rosdep check --from-paths /tmp/ws/src --ignore-src"

sec "F SciPy"
tsec run "apt-get install -y --no-install-recommends python3-scipy | grep -E 'newly installed|Need to get|After this'"

sec "G compare.py"
python3 /w/compare.py 2>&1

}
sec "H tf2_echo RPY output for roll=10 pitch=20 yaw=30 deg"
L=$(cut -d' ' -f1 /proc/loadavg); echo "load $L"
ros2 run tf2_ros static_transform_publisher --x 0 --y 0 --z 0 --roll 0.17453293 --pitch 0.34906585 --yaw 0.52359878 --frame-id a --child-frame-id b > /tmp/stp.log 2>&1 &
SP=$!
sleep 2
timeout 6 ros2 run tf2_ros tf2_echo a b 2>&1 | head -14
kill -TERM $SP; sleep 1; kill -TERM $(pgrep -f static_transform_publisher) 2>/dev/null; wait $SP 2>/dev/null
echo "=== done $D $(date -u +%FT%TZ)"
