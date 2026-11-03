#!/bin/bash
# Reproduce "UnsupportedTypeSupport: Could not import 'rosidl_typesupport_c' for package"
# with a custom message used from rclpy.
# Host:  bash repro.sh            -> one fresh container per distro, one after another, writes out_<distro>.txt
# Inner: bash repro.sh inner      -> runs inside ros:<distro>-ros-base
set -u
HERE=$(cd "$(dirname "$0")" && pwd)

if [ "${1:-}" != inner ]; then
  ulimit -c 0
  for d in ${DISTROS:-humble jazzy lyrical}; do
    # stay clear of the production jobs (10:20, 11:00, 14:02 KST) and wait for a low load
    while :; do
      hm=$(TZ=Asia/Seoul date +%H%M)
      busy=0; for t in 1018 1019 1020 1058 1059 1100 1400 1401 1402; do [ "$hm" = "$t" ] && busy=1; done
      load=$(cut -d' ' -f1 /proc/loadavg)
      if [ $busy = 0 ] && awk "BEGIN{exit !($load < 3.0)}"; then break; fi
      echo "waiting: time=$hm load=$load"; sleep 30
    done
    echo "start $d at $(TZ=Asia/Seoul date +%H:%M:%S) $(uptime)"
    docker run --rm --name "pk2-$d" --ulimit core=0 --pids-limit 256 --cpus 1.5 \
      -e MAKEFLAGS=-j1 -e UV_CONCURRENT_DOWNLOADS=2 -e UV_CONCURRENT_BUILDS=1 \
      -v "$HERE:/w:ro" "ros:$d-ros-base" bash /w/repro.sh inner > "$HERE/out_$d.txt" 2>&1
    echo "$d done rc=$? at $(TZ=Asia/Seoul date +%H:%M:%S)"
  done
  exit 0
fi

# ---------------- inside the container ----------------
set +u
ulimit -c 0
D=$ROS_DISTRO
source /opt/ros/$D/setup.bash
export DEBIAN_FRONTEND=noninteractive PIP_BREAK_SYSTEM_PACKAGES=1
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq python3-pip sudo ros-$D-geometry-msgs >/dev/null 2>&1
python3 -m pip install -q uv==0.5.31 >/dev/null 2>&1 || python3 -m pip install -q --break-system-packages uv==0.5.31 >/dev/null 2>&1

echo "##### distro: $D"
echo "== versions"
python3 --version
python3 -c "import importlib.machinery as m; print('system EXTENSION_SUFFIXES:', m.EXTENSION_SUFFIXES)"
cmake --version | head -1
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-rmw-fastrtps-cpp \
  ros-$D-rosidl-generator-py ros-$D-rosidl-typesupport-c python3-empy python3-colcon-core 2>&1
echo "uv: $(uv --version 2>&1)"
EMPY=$(python3 -c "import em; print(em.__version__)")

# ---------- workspace: one ament_cmake interfaces package ----------
mkdir -p /ws/src/my_msgs/msg
cd /ws/src/my_msgs
echo "int64 num" > msg/Num.msg
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(my_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg")
ament_package()
EOF
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>my_msgs</name><version>0.0.0</version><description>t</description>
  <maintainer email="user@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <depend>geometry_msgs</depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
cat > /ws/t.py <<'EOF'
import sys
import rclpy
from my_msgs.msg import Num
rclpy.init()
node = rclpy.create_node('t')
pub = node.create_publisher(Num, 'num', 10)
pub.publish(Num(num=5))
print('OK publisher created and published', Num(num=5))
node.destroy_node()
rclpy.shutdown()
EOF
cat > /ws/t_std.py <<'EOF'
import rclpy
from std_msgs.msg import String
rclpy.init()
node = rclpy.create_node('t_std')
node.create_publisher(String, 's', 10).publish(String(data='x'))
print('OK std_msgs publisher')
rclpy.shutdown()
EOF

build() {  # $1 label, rest = extra colcon args
  local label=$1; shift
  echo; echo "=== BUILD: $label"
  echo "python3 on PATH: $(command -v python3) ($(python3 --version 2>&1))  VIRTUAL_ENV=${VIRTUAL_ENV:-none}"
  cd /ws
  local t0=$(date +%s.%N)
  colcon build --packages-select my_msgs "$@" > /tmp/b.log 2>&1
  local rc=$?
  local t1=$(date +%s.%N)
  echo "colcon exit code: $rc  wall: $(python3 -c "print(round($t1-$t0,1))")s"
  grep -E "CMake Error|Error|error:|Failed <<<|Finished <<<|Summary:" /tmp/b.log | head -15
  echo "-- cache: $(grep -hE '^(Python3_EXECUTABLE|PYTHON_EXECUTABLE):' build/my_msgs/CMakeCache.txt 2>/dev/null | tr '\n' ' ')"
  echo "-- python package dir(s): $(ls -d install/my_msgs/local/lib/python3*/dist-packages/my_msgs install/my_msgs/lib/python3*/site-packages/my_msgs 2>/dev/null | tr '\n' ' ')"
  echo "-- typesupport modules:"; ls install/my_msgs/local/lib/python3*/dist-packages/my_msgs/ install/my_msgs/lib/python3*/site-packages/my_msgs/ 2>/dev/null | grep '\.so$' | sed 's/^/   /'
}

run_t() {  # $1 label, rest = command prefix
  local label=$1; shift
  echo; echo "--- RUN: $label"
  ( cd /ws; source /opt/ros/$D/setup.bash; source install/setup.bash
    timeout 60 "$@" python3 /ws/t.py > /tmp/r.log 2>&1; echo "exit code: $?" >> /tmp/r.log )
  grep -vE "^\s+(File \"<frozen|return _bootstrap|\^+)$" /tmp/r.log | tail -45
}

# ---------- A0: baseline ----------
build "A0: system python, clean"
run_t "A0 t.py"
( cd /ws; source install/setup.bash; echo "LD_LIBRARY_PATH contains my_msgs: $(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -c my_msgs)"
  echo "PYTHONPATH entries for my_msgs: $(echo "$PYTHONPATH" | tr ':' '\n' | grep my_msgs)" )

# ---------- A: built with a different Python minor version ----------
echo; echo "##### A: interfaces built while a venv with another Python version is active"
uv python install 3.11 > /tmp/uvp.log 2>&1; tail -1 /tmp/uvp.log
uv venv -q -p 3.11 /venv311 2>&1 | tail -2
source /venv311/bin/activate
uv pip install -q "empy==$EMPY" catkin_pkg lark numpy setuptools 2>&1 | tail -2
uv pip list 2>/dev/null | grep -iE '^(empy|catkin.pkg|lark|numpy|setuptools) ' | tr -s ' ' | tr '\n' ';'; echo
python3 -c "import importlib.machinery as m; print('venv EXTENSION_SUFFIXES:', m.EXTENSION_SUFFIXES)"
cd /ws && rm -rf build install log
build "A1: venv python 3.11 active, clean"
echo; echo "--- RUN: A1b t.py with the venv python 3.11 still active"
( cd /ws; source install/setup.bash; timeout 60 python3 /ws/t.py 2>&1 | tail -3 )
deactivate
echo "after deactivate python3: $(command -v python3) ($(python3 --version))"
run_t "A1 t.py with system python3"
echo; echo "--- RUN: A1 ros2 topic pub --once"
( cd /ws; source install/setup.bash; timeout 30 ros2 topic pub --once /num my_msgs/msg/Num "{num: 1}" 2>&1 | tail -8; echo "exit code: ${PIPESTATUS[0]}" )
echo; echo "--- RUN: A1 ros2 interface show"
( cd /ws; source install/setup.bash; timeout 30 ros2 interface show my_msgs/msg/Num 2>&1 | tail -3 )
echo; echo "--- RUN: A1 import only (no publisher)"
( cd /ws; source install/setup.bash; timeout 30 python3 -c "from my_msgs.msg import Num; print('import ok', Num(num=3))" 2>&1 | tail -3 )
echo; echo "--- DIAG: one-liner check"
( cd /ws; source install/setup.bash; timeout 30 python3 - <<'EOF'
import importlib.util, importlib.machinery, glob, os
spec = importlib.util.find_spec('my_msgs')
d = os.path.dirname(spec.origin)
print('package dir:', d)
print('this python wants:', importlib.machinery.EXTENSION_SUFFIXES[0])
for f in sorted(glob.glob(d + '/*.so')): print('found:', os.path.basename(f))
EOF
)

# fix options, venv no longer active
build "F1: plain rebuild after deactivate (no clean)"
run_t "F1 t.py"
build "F2: --cmake-clean-cache" --cmake-clean-cache
run_t "F2 t.py"
# back to the broken state, then the other fixes
source /venv311/bin/activate; cd /ws && rm -rf build install log; build "A1 again (to reset)"; deactivate
build "F3: --cmake-force-configure" --cmake-force-configure
run_t "F3 t.py"
source /venv311/bin/activate; cd /ws && rm -rf build install log; build "A1 again (to reset)"; deactivate
cd /ws && rm -rf build/my_msgs install/my_msgs
build "F4: rm -rf build/my_msgs install/my_msgs, rebuild"
run_t "F4 t.py"
source /venv311/bin/activate; cd /ws && rm -rf build install log
build "F5: venv still active, clean, -DPython3_EXECUTABLE and -DPYTHON_EXECUTABLE=/usr/bin/python3" --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 -DPYTHON_EXECUTABLE=/usr/bin/python3
deactivate
run_t "F5 t.py"

# ---------- B: LD_LIBRARY_PATH stripped (env -u, sudo) ----------
echo; echo "##### B: good build, LD_LIBRARY_PATH removed"
cd /ws && rm -rf build install log; build "B0: system python, clean"
run_t "B1 env -u LD_LIBRARY_PATH" env -u LD_LIBRARY_PATH
echo; echo "--- RUN: B1 std_msgs only, env -u LD_LIBRARY_PATH"
( cd /ws; source install/setup.bash; timeout 30 env -u LD_LIBRARY_PATH python3 /ws/t_std.py 2>&1 | tail -4 )
echo; echo "--- sudo env check"
( cd /ws; source install/setup.bash
  echo "sudo -E keeps PYTHONPATH: $(sudo -E env | grep -c '^PYTHONPATH=')  keeps LD_LIBRARY_PATH: $(sudo -E env | grep -c '^LD_LIBRARY_PATH=')"
  echo "sudo keeps PYTHONPATH: $(sudo env | grep -c '^PYTHONPATH=')  keeps LD_LIBRARY_PATH: $(sudo env | grep -c '^LD_LIBRARY_PATH=')" )
run_t "B2 sudo -E" sudo -E
run_t "B3 sudo (no -E)" sudo
echo; echo "--- RUN: B4 sudo -E with LD_LIBRARY_PATH passed explicitly"
( cd /ws; source install/setup.bash; timeout 60 sudo -E env LD_LIBRARY_PATH="$LD_LIBRARY_PATH" python3 /ws/t.py 2>&1 | tail -3 )
echo; echo "--- RUN: B5 sudo bash -c 'source ... && python3 t.py'"
( cd /ws; timeout 60 sudo bash -c "source /opt/ros/$D/setup.bash && source /ws/install/setup.bash && python3 /ws/t.py" 2>&1 | tail -3 )
echo; echo "--- RUN: B6 only /opt/ros sourced, workspace added to PYTHONPATH by hand (IDE style)"
( cd /ws; source /opt/ros/$D/setup.bash
  export PYTHONPATH=$(ls -d /ws/install/my_msgs/local/lib/python3*/dist-packages /ws/install/my_msgs/lib/python3*/site-packages 2>/dev/null | head -1):$PYTHONPATH
  echo "LD_LIBRARY_PATH has /ws: $(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -c '^/ws')"
  timeout 60 python3 /ws/t.py > /tmp/r.log 2>&1; echo "exit code: $?" >> /tmp/r.log
  grep -vE "^\s+(File \"<frozen|return _bootstrap|\^+)$" /tmp/r.log | tail -30 )
echo; echo "--- RUN: B7 same, plus the workspace lib dir on LD_LIBRARY_PATH"
( cd /ws; source /opt/ros/$D/setup.bash
  export PYTHONPATH=$(ls -d /ws/install/my_msgs/local/lib/python3*/dist-packages /ws/install/my_msgs/lib/python3*/site-packages 2>/dev/null | head -1):$PYTHONPATH
  export LD_LIBRARY_PATH=/ws/install/my_msgs/lib:$LD_LIBRARY_PATH
  timeout 60 python3 /ws/t.py 2>&1 | tail -3 )
echo; echo "--- DIAG: ldd on the typesupport module without LD_LIBRARY_PATH"
( cd /ws; f=$(ls install/my_msgs/local/lib/python3*/dist-packages/my_msgs/*rosidl_typesupport_c*.so install/my_msgs/lib/python3*/site-packages/my_msgs/*rosidl_typesupport_c*.so 2>/dev/null | head -1)
  echo "file: $f"; env -u LD_LIBRARY_PATH ldd "$f" | grep "not found"; readelf -d "$f" | grep -E "RPATH|RUNPATH" || echo "no RPATH/RUNPATH" )

# ---------- C: message depends on another package, DEPENDENCIES missing ----------
echo; echo "##### C: Pose2 uses geometry_msgs/Point, rosidl_generate_interfaces without DEPENDENCIES"
cd /ws/src/my_msgs
printf 'geometry_msgs/Point position\nint64 id\n' > msg/Pose2.msg
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(my_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(geometry_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg" "msg/Pose2.msg")
ament_package()
EOF
cd /ws && rm -rf build install log; build "C1: find_package(geometry_msgs), no DEPENDENCIES"
sed -n '/--- stderr/,$p' /tmp/b.log | head -20
sed -i 's|"msg/Pose2.msg")|"msg/Pose2.msg" DEPENDENCIES geometry_msgs)|' src/my_msgs/CMakeLists.txt
cd /ws && rm -rf build install log; build "C2: with DEPENDENCIES geometry_msgs"
( cd /ws; source install/setup.bash; timeout 60 python3 -c "
import rclpy; from my_msgs.msg import Pose2; rclpy.init(); n=rclpy.create_node('c'); n.create_publisher(Pose2,'p',10); print('OK Pose2 publisher')" 2>&1 | tail -3 )

echo; echo "##### done $D"
