#!/bin/bash
# Runs INSIDE a ros:<distro>-ros-base container started with --network none.
# Usage: docker run --rm --network none -v $PWD/repro.sh:/repro.sh:ro ros:<distro>-ros-base bash /repro.sh
ulimit -c 0
D=$ROS_DISTRO
h(){ echo; echo "===== $* ====="; }
run(){ echo "\$ $*"; timeout 60 bash -c "$*" 2>&1 | sed 's/^/  /'; echo "  [exit=${PIPESTATUS[0]}]"; }
h "distro $D"
source /opt/ros/$D/setup.bash
python3 -c "import rclpy,sys; print('python', sys.version.split()[0])"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-ros2run ros-$D-ros2launch ros-$D-ament-index-python ros-$D-rmw 2>/dev/null
mkdir -p /ws/src && cd /ws/src
ros2 pkg create --build-type ament_python --node-name talker demo_py >/dev/null 2>&1
ros2 pkg create --build-type ament_cmake demo_cmake >/dev/null 2>&1
mkdir -p demo_py/launch && cat > demo_py/launch/t.launch.py <<'L'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='demo_py', executable='talker', output='screen')])
L
sed -i "s|('share/' + package_name, \['package.xml'\]),|('share/' + package_name, ['package.xml']),\n        ('share/' + package_name + '/launch', ['launch/t.launch.py']),|" demo_py/setup.py
h "generated setup.py data_files"
grep -n -A4 "data_files" demo_py/setup.py
ls demo_py/resource
cd /ws
h "build"
S=$(date +%s.%N); colcon build >/tmp/b.log 2>&1; E=$?; echo "exit=$E seconds=$(python3 -c "print(round($(date +%s.%N)-$S,1))")"; tail -3 /tmp/b.log
ls install/demo_py/share/ament_index/resource_index/packages/

h "CASE A: built, only /opt/ros sourced (install/setup.bash not sourced)"
run "source /opt/ros/$D/setup.bash; ros2 run demo_py talker"
run "source /opt/ros/$D/setup.bash; ros2 launch demo_py t.launch.py"
run "source /opt/ros/$D/setup.bash; ros2 pkg prefix demo_py"
run "source /opt/ros/$D/setup.bash; ros2 pkg executables demo_py"
run "source /opt/ros/$D/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH"
h "CASE A timing: 5 failing ros2 run calls"
for i in 1 2 3 4 5; do bash -c "source /opt/ros/$D/setup.bash; S=\$(date +%s%N); ros2 run demo_py talker >/dev/null 2>&1; echo \"fail_ms=\$(( (\$(date +%s%N)-S)/1000000 ))\""; done

h "CASE B: install/setup.bash sourced"
run "source /opt/ros/$D/setup.bash; source /ws/install/setup.bash; ros2 run demo_py talker"
run "source /ws/install/setup.bash; timeout -s INT 8 ros2 launch demo_py t.launch.py"
run "source /ws/install/setup.bash; ros2 pkg prefix demo_py; ros2 pkg executables demo_py"
run "source /ws/install/setup.bash; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH"
h "CASE B timing: 5 working ros2 run calls"
for i in 1 2 3 4 5; do bash -c "source /ws/install/setup.bash; S=\$(date +%s%N); ros2 run demo_py talker >/dev/null 2>&1; echo \"ok_ms=\$(( (\$(date +%s%N)-S)/1000000 ))\""; done

h "CASE C: typo / wrong case in package name"
run "source /ws/install/setup.bash; ros2 run demo_pyy talker"
run "source /ws/install/setup.bash; ros2 run Demo_py talker"
run "source /ws/install/setup.bash; ros2 run demo-py talker"
h "CASE C2: executable name typo (package found)"
run "source /ws/install/setup.bash; ros2 run demo_py talkr"

h "CASE D: new package built AFTER sourcing (same shell, no re-source)"
run "source /ws/install/setup.bash; cd /ws/src && ros2 pkg create --build-type ament_python --node-name n2 new_pkg >/dev/null 2>&1; cd /ws && colcon build --packages-select new_pkg >/dev/null 2>&1; echo built=\$?; ros2 run new_pkg n2; echo '--- after re-source:'; source /ws/install/setup.bash; ros2 run new_pkg n2"

h "CASE E: --packages-select built a different package only (fresh ws)"
run "rm -rf /ws2 && mkdir -p /ws2/src && cp -r /ws/src/demo_py /ws/src/demo_cmake /ws2/src/ && cd /ws2 && colcon build --packages-select demo_cmake >/dev/null 2>&1; echo built=\$?; ls install; source install/setup.bash; ros2 run demo_py talker"

h "CASE F: setup.py without the ament_index resource marker in data_files"
run "rm -rf /ws3 && mkdir -p /ws3/src && cp -r /ws/src/demo_py /ws3/src/ && cd /ws3 && sed -i '/resource_index\/packages/,+1d' src/demo_py/setup.py && grep -n -A3 data_files src/demo_py/setup.py && colcon build >/tmp/f.log 2>&1; echo build_exit=\$?; tail -2 /tmp/f.log; ls install/demo_py/share/ament_index/resource_index/packages 2>&1; source install/setup.bash; ros2 run demo_py talker; echo '--- ros2 pkg list | grep demo:'; ros2 pkg list | grep demo; echo '--- console script still present:'; ls install/demo_py/lib/demo_py/; echo '--- direct exec:'; install/demo_py/lib/demo_py/talker"

h "CASE G: resource/demo_py marker file deleted"
run "rm -rf /ws4 && mkdir -p /ws4/src && cp -r /ws/src/demo_py /ws4/src/ && cd /ws4 && rm src/demo_py/resource/demo_py && colcon build >/tmp/g.log 2>&1; echo build_exit=\$?; grep -iE 'error|No such' /tmp/g.log log/latest_build/demo_py/stdout_stderr.log | head -5"

h "CASE H: package.xml <name> differs from setup.py package_name"
run "rm -rf /ws5 && mkdir -p /ws5/src && cp -r /ws/src/demo_py /ws5/src/ && cd /ws5 && sed -i 's|<name>demo_py</name>|<name>demo_pkg</name>|' src/demo_py/package.xml && colcon build >/tmp/h.log 2>&1; echo build_exit=\$?; tail -3 /tmp/h.log; ls install; ls install/*/share/ament_index/resource_index/packages; source install/setup.bash; echo '--- ros2 run demo_pkg talker:'; ros2 run demo_pkg talker; echo '--- ros2 run demo_py talker:'; ros2 run demo_py talker"

h "CASE I: install/ deleted while shell still has it sourced"
run "rm -rf /ws6 && cp -r /ws /ws6 && cd /ws6 && rm -rf build install log && colcon build >/dev/null 2>&1; source /ws6/install/setup.bash; rm -rf /ws6/install; ros2 run demo_py talker; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH"

h "CASE J: ament_index_python view"
run "source /ws/install/setup.bash; python3 -c \"from ament_index_python.packages import get_package_prefix as g; print(g('demo_py')); g('nope_pkg')\""

h "CASE K: sourced with install/local_setup.bash only (underlay not sourced first)"
run "env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root bash -c 'source /ws/install/local_setup.bash; which ros2; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH'"
h "CASE M: colcon build run from inside src/ (install lands in src/install)"
run "rm -rf /ws7 && mkdir -p /ws7/src && cp -r /ws/src/demo_py /ws7/src/ && cd /ws7/src && colcon build >/dev/null 2>&1; echo built=\$?; ls -d /ws7/install /ws7/src/install 2>&1; source /ws7/install/setup.bash 2>&1; ros2 run demo_py talker; echo '--- sourcing src/install:'; source /ws7/src/install/setup.bash; ros2 run demo_py talker"
h "CASE N: ament_cmake package whose package.xml says build_type cmake / no export / catkin"
for V in cmake none catkin; do
  rm -rf /ws8 && mkdir -p /ws8/src && cp -r /ws/src/demo_cmake /ws8/src/ && cd /ws8
  case $V in
    cmake) sed -i 's|<build_type>ament_cmake</build_type>|<build_type>cmake</build_type>|' src/demo_cmake/package.xml;;
    none) sed -i '/<build_type>/d' src/demo_cmake/package.xml;;
    catkin) sed -i 's|<build_type>ament_cmake</build_type>|<build_type>catkin</build_type>|' src/demo_cmake/package.xml;;
  esac
  echo "--- variant=$V"; grep -n -E 'build_type|buildtool_depend|<export' src/demo_cmake/package.xml
  colcon build >/tmp/n.log 2>&1; echo "build_exit=$?"; grep -E 'Finished|Failed|WARNING|error' /tmp/n.log | head -4
  ls install/demo_cmake/share/ament_index/resource_index/packages 2>&1 | head -3
  bash -c "source /ws8/install/setup.bash; ros2 pkg prefix demo_cmake; ros2 pkg list | grep -c demo_cmake; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH; echo CMAKE_PREFIX_PATH=\$CMAKE_PREFIX_PATH" 2>&1 | sed 's/^/  /'
  cd /
done
h "end"

# --- Host-side commands used for the run (2026-11-22, runner) ---
# for d in humble jazzy lyrical; do
#   docker run --rm --name pk72-$d --network none --pids-limit 300 --ulimit core=0 \
#     -v $PWD/repro.sh:/repro.sh:ro ros:$d-ros-base bash /repro.sh > out_$d.txt 2>&1
# done
# colcon_ros_src.txt: in order humble, jazzy (grep of colcon_ros/task/ament_python/build.py for
# resource_index + dpkg python3-colcon-ros), then lyrical (colcon-core, colcon-ros, count of
# create_file), then colcon-core for humble and jazzy.
