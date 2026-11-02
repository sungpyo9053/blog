#!/bin/bash
# Run on the runner, one distro at a time: ./repro.sh humble|jazzy|lyrical
set -u
d=$1
ulimit -c 0
uptime
docker pull -q ros:$d-ros-base >/dev/null
docker run --rm --name pk2-p3-$d --cpus 1.5 --pids-limit 30 --ulimit core=0 -v /tmp/en-pick3:/w:ro ros:$d-ros-base bash -c '
source /opt/ros/$ROS_DISTRO/setup.bash
echo "### distro $ROS_DISTRO, RMW ${RMW_IMPLEMENTATION:-default}"
dpkg-query -W -f="\${Package} \${Version}\n" ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rosidl-generator-py ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-std-msgs python3-numpy 2>/dev/null
echo "### generated setter, std_msgs Float64.data"
grep -n -A8 "@data.setter" $(python3 -c "import std_msgs.msg._float64 as m; print(m.__file__)")
grep -n "ROS_PYTHON_CHECK_FIELDS\|_check_fields = " $(python3 -c "import std_msgs.msg._float64 as m; print(m.__file__)")
echo "### A. assignment table, default environment"
python3 -u /w/cases.py --time
echo "### B. assignment table, ROS_PYTHON_CHECK_FIELDS=1"
ROS_PYTHON_CHECK_FIELDS=1 python3 -u /w/cases.py --time
CASES="f64_int f64_np_float32 f64_np_int64 f64_str f64_none f32_1e39 i32_float i32_np_int64 i32_2pow31 u8_256 u8_neg1 bool_int str_int str_bytes frame_id_none stamp_time_time stamp_clock_now jtp_rclpy_duration wrench_force_list f64ma_ints f64ma_numpy imu_cov_len8 imu_cov_ints imu_eye"
for mode in default checkfields optimized; do
  echo "### C. serialize round trip, one process per case, mode=$mode"
  for c in $CASES; do
    case $mode in
      default) out=$(timeout 60 python3 /w/o_case.py $c 2>&1); rc=$? ;;
      checkfields) out=$(ROS_PYTHON_CHECK_FIELDS=1 timeout 60 python3 /w/o_case.py $c 2>&1); rc=$? ;;
      optimized) out=$(timeout 60 python3 -O /w/o_case.py $c 2>&1); rc=$? ;;
    esac
    echo "-- $c (exit=$rc)"; echo "$out" | grep -v "dumped core"
  done
done
echo "### D. real publisher.publish(), default environment"
for c in f64_int str_int f64ma_numpy; do out=$(timeout 60 python3 /w/o_case.py $c publish 2>&1); rc=$?; echo "-- $c publish (exit=$rc)"; echo "$out" | grep -v "dumped core"; done
' 2>&1
docker image inspect --format '{{index .RepoDigests 0}}' ros:$d-ros-base
