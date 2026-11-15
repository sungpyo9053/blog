#!/bin/bash
# Runs inside ros:<distro>-ros-base as: bash /w/repro.sh <distro>
# Host side (runner), one distro at a time, no network needed (ros-base ships colcon,
# ament_cmake and rosidl_default_generators):
#   docker run -d --name pk43-$D --network none -v /tmp/en-pick53:/w ros:$D-ros-base sleep infinity
#   docker exec pk43-$D bash /w/repro.sh $D > out_$D.txt 2>&1
set +e
ulimit -c 0
D=$1
export ROS_DOMAIN_ID=88 PYTHONUNBUFFERED=1 RCUTILS_COLORIZED_OUTPUT=0 MAKEFLAGS=-j1
if [ "$D" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
B="colcon build --parallel-workers 1 --event-handlers console_direct- console_cohesion- status- summary+"
W=/w/ws_$D; rm -rf $W; mkdir -p $W/src; cd $W/src
step() { echo; echo "##### $*"; }
imp() { # imp "<python code>"  -> prints the last traceback line or OK
  timeout 60 python3 -c "$1" > /tmp/imp.out 2>&1; rc=$?
  if [ $rc = 0 ]; then echo "OK: $(tail -1 /tmp/imp.out)"; else echo "rc=$rc $(tail -1 /tmp/imp.out)"; fi
}

# ---------- packages ----------
# 1) interface package (ament_cmake). Extra.msg sits in msg/ but is NOT listed at first.
mkdir -p my_interfaces/msg my_interfaces/srv
echo 'int64 num' > my_interfaces/msg/Num.msg
echo 'string note' > my_interfaces/msg/Extra.msg
printf 'int64 a\nint64 b\n---\nint64 sum\n' > my_interfaces/srv/AddTwoInts.srv
cat > my_interfaces/CMakeLists.txt <<'C'
cmake_minimum_required(VERSION 3.8)
project(my_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Num.msg"
  "srv/AddTwoInts.srv"
)
ament_package()
C
cat > my_interfaces/package.xml <<'X'
<?xml version="1.0"?>
<package format="3">
  <name>my_interfaces</name><version>0.0.0</version><description>t</description>
  <maintainer email="a@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
X
# 2) same package without <member_of_group>
cp -r my_interfaces nogroup_interfaces
sed -i 's/my_interfaces/nogroup_interfaces/g' nogroup_interfaces/CMakeLists.txt nogroup_interfaces/package.xml
sed -i '/member_of_group/d' nogroup_interfaces/package.xml

# 3) ament_python package with a msg/ folder (what an LLM or a tutorial mix-up gives you)
mkdir -p py_msgs/py_msgs py_msgs/msg py_msgs/resource
touch py_msgs/py_msgs/__init__.py py_msgs/resource/py_msgs
echo 'float64 x' > py_msgs/msg/Point2.msg
cat > py_msgs/setup.py <<'P'
from setuptools import setup
setup(name='py_msgs', version='0.0.0', packages=['py_msgs'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/py_msgs']),
                  ('share/py_msgs', ['package.xml'])])
P
cat > py_msgs/package.xml <<'X'
<?xml version="1.0"?>
<package format="3">
  <name>py_msgs</name><version>0.0.0</version><description>t</description>
  <maintainer email="a@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_python</build_type></export>
</package>
X

# 4) ament_python consumer node, NO depend on my_interfaces in package.xml
mkdir -p consumer/consumer consumer/resource
touch consumer/consumer/__init__.py consumer/resource/consumer
cat > consumer/consumer/node.py <<'P'
import rclpy
from my_interfaces.msg import Num
def main():
    rclpy.init()
    n = rclpy.create_node('consumer')
    m = Num(); m.num = 42
    n.get_logger().info(f'built Num num={m.num}')
    n.destroy_node(); rclpy.shutdown()
P
cat > consumer/setup.py <<'P'
from setuptools import setup
setup(name='consumer', version='0.0.0', packages=['consumer'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/consumer']),
                  ('share/consumer', ['package.xml'])],
      entry_points={'console_scripts': ['node = consumer.node:main']})
P
printf '[develop]\nscript_dir=$base/lib/consumer\n[install]\ninstall_scripts=$base/lib/consumer\n' > consumer/setup.cfg
cat > consumer/package.xml <<'X'
<?xml version="1.0"?>
<package format="3">
  <name>consumer</name><version>0.0.0</version><description>t</description>
  <maintainer email="a@example.com">a</maintainer><license>MIT</license>
  <exec_depend>rclpy</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>
X

# 5) mixed ament_cmake package whose script has the package's name (robotics.SE 110109)
mk_server() { # mk_server <pkg> <script name> [pyinstall]
  mkdir -p $1/msg $1/$1
  echo 'string data' > $1/msg/Ping.msg
  touch $1/$1/__init__.py
  cat > $1/$1/$2 <<P
#!/usr/bin/env python3
import sys
print('sys.path[0] =', sys.path[0])
from $1.msg import Ping
print('imported Ping, data field:', Ping().data == '')
P
  chmod +x $1/$1/$2
  cat > $1/CMakeLists.txt <<C
cmake_minimum_required(VERSION 3.8)
project($1)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(\${PROJECT_NAME} "msg/Ping.msg")
$( [ "$3" = pyinstall ] && echo "ament_python_install_package(\${PROJECT_NAME})" )
install(PROGRAMS $1/$2 DESTINATION lib/\${PROJECT_NAME})
ament_package()
C
  sed "s/my_interfaces/$1/; s#<buildtool_depend>ament_cmake</buildtool_depend>#<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>ament_cmake_python</buildtool_depend>#" my_interfaces/package.xml > $1/package.xml
}
mk_server my_server my_server.py
mk_server my_server2 server_node.py
mk_server my_server3 server_node.py pyinstall

step "versions"
source /opt/ros/$D/setup.bash
python3 --version; echo "colcon-core $(python3 -c 'import colcon_core;print(colcon_core.__version__)')"
cd $W

step "A. colcon build my_interfaces (fresh shell, only /opt/ros sourced), timed"
s=$(date +%s.%N); timeout 900 $B --packages-select my_interfaces 2>&1 | tail -3; e=$(date +%s.%N)
echo "build_seconds my_interfaces: $(python3 -c "print(round($e-$s,1))")"
step "A2. import with only /opt/ros sourced (never sourced the workspace)"
imp "from my_interfaces.msg import Num"
step "A3. ros2 interface show with only /opt/ros sourced"
timeout 60 ros2 interface show my_interfaces/msg/Num 2>&1 | tail -1
step "A4. generated module location"
find install/my_interfaces -name '_num.py' | sed "s#$W/##"
step "A5. after source install/setup.bash"
( source install/setup.bash
  imp "from my_interfaces.msg import Num; print(Num(num=3))"
  echo "PYTHONPATH entries with my_interfaces:"; echo $PYTHONPATH | tr ':' '\n' | grep my_interfaces | sed "s#$W/##"
  step "A6. import timing (fresh interpreter, 5 runs, ms)"
  for i in 1 2 3 4 5; do python3 -c "import time;t=time.perf_counter();from my_interfaces.msg import Num;print(round((time.perf_counter()-t)*1000,1))"; done | tr '\n' ' '; echo
  timeout 60 ros2 interface show my_interfaces/msg/Num 2>&1 | tail -1
)

step "B. wrong import forms (workspace sourced)"
( source install/setup.bash
  for c in "from my_interfaces import Num" \
           "from my_interfaces.msg import num" \
           "from my_interfaces.msg import NUM" \
           "import my_interfaces.msg.Num" \
           "from my_interfaces.msg import AddTwoInts" \
           "from my_interfaces.srv import AddTwoInts; print(AddTwoInts.Request(a=1,b=2))" \
           "from my_interfaces.msg import Extra" \
           "from my_interface.msg import Num" \
           "import my_interfaces.msg as m; print(m.Num)"; do
    echo "[$c]"; imp "$c"; done
)

step "C. Extra.msg in msg/ but not listed: build ok? then list it and rebuild"
( source install/setup.bash
  sed -i 's#"msg/Num.msg"#"msg/Num.msg"\n  "msg/Extra.msg"#' src/my_interfaces/CMakeLists.txt
  timeout 900 $B --packages-select my_interfaces 2>&1 | tail -2
  echo "same shell, not re-sourced:"; imp "from my_interfaces.msg import Extra; print(Extra(note='hi'))"
)

step "D. sourced BEFORE the interface package existed (new terminal order problem)"
W2=/w/ws2_$D; rm -rf $W2; mkdir -p $W2/src; cp -r $W/src/consumer $W2/src/
( cd $W2; timeout 900 $B 2>&1 | tail -2
  source install/setup.bash
  cp -r $W/src/my_interfaces src/
  timeout 900 $B --packages-select my_interfaces 2>&1 | tail -2
  echo "same shell after building my_interfaces:"; imp "from my_interfaces.msg import Num"
  echo "ros2 run consumer node:"; timeout 60 ros2 run consumer node 2>&1 | grep -E 'Error|INFO|ros2run' 
  echo "ros2 interface show:"; timeout 60 ros2 interface show my_interfaces/msg/Num 2>&1 | tail -1
  source install/setup.bash
  echo "after re-sourcing install/setup.bash:"; imp "from my_interfaces.msg import Num"
  echo "ros2 run consumer node:"; timeout 60 ros2 run consumer node 2>&1 | grep -E 'Error|INFO|ros2run' 
)
step "D2. same order with --merge-install"
W3=/w/ws3_$D; rm -rf $W3; mkdir -p $W3/src; cp -r $W/src/consumer $W3/src/
( cd $W3; timeout 900 $B --merge-install 2>&1 | tail -2
  source install/setup.bash
  cp -r $W/src/my_interfaces src/
  timeout 900 $B --merge-install --packages-select my_interfaces 2>&1 | tail -2
  echo "same shell after building my_interfaces:"; imp "from my_interfaces.msg import Num"
  source install/setup.bash
  echo "after re-sourcing:"; imp "from my_interfaces.msg import Num"
)
step "D3. only the package's own local_setup.bash sourced"
( source install/my_interfaces/share/my_interfaces/local_setup.bash 2>/dev/null
  imp "from my_interfaces.msg import Num" )

step "E. consumer with no <depend>my_interfaces</depend>, ros2 run in the same workspace"
timeout 900 $B --packages-select consumer 2>&1 | tail -2
( source install/setup.bash; timeout 60 ros2 run consumer node 2>&1 | tail -1 )

step "F. ament_python package with a msg/ folder"
timeout 900 $B --packages-select py_msgs 2>&1 | tail -3
echo "files named *point2* in install/py_msgs: $(find install/py_msgs -iname '*point2*' | wc -l)"
( source install/setup.bash
  imp "from py_msgs.msg import Point2"
  timeout 60 ros2 interface show py_msgs/msg/Point2 2>&1 | tail -1
  timeout 60 ros2 interface packages 2>&1 | grep -c py_msgs | sed 's/^/py_msgs in ros2 interface packages: /' )

step "G. package without <member_of_group>rosidl_interface_packages</member_of_group>"
timeout 900 $B --packages-select nogroup_interfaces 2>&1 | grep -iE -A3 'CMake Error at' | head -8; timeout 900 $B --packages-select nogroup_interfaces 2>&1 | grep -E 'Failed|finished'
( source install/setup.bash; imp "from nogroup_interfaces.msg import Num; print(Num(num=1))" )

step "H. script named like its package (my_server/my_server.py) vs renamed (server_node.py)"
timeout 900 $B --packages-select my_server my_server2 2>&1 | tail -2
( source install/setup.bash
  echo "[ros2 run my_server my_server.py]"; timeout 60 ros2 run my_server my_server.py 2>&1 | grep -E 'sys.path|Error|imported' | sed "s#$W/##"
  echo "[ros2 run my_server2 server_node.py]"; timeout 60 ros2 run my_server2 server_node.py 2>&1 | grep -E 'sys.path|Error|imported' | sed "s#$W/##"
  echo "[python3 -c import my_server.msg from another dir]"; (cd /tmp; imp "from my_server.msg import Ping; print('ok')")
)
step "H0. interface package that also calls ament_python_install_package(\${PROJECT_NAME})"
timeout 900 $B --packages-select my_server3 2>&1 | grep -E 'CMake Error|cannot create target|Failed|finished' | head -6
step "H2. a local file named std_msgs.py next to your script (robotics.SE 24881 pattern)"
mkdir -p /tmp/shadow; cd /tmp/shadow
echo 'x = 1' > std_msgs.py
printf 'from std_msgs.msg import String\nprint("ok", String(data="a"))\n' > talker.py
echo "[python3 talker.py next to std_msgs.py]"; timeout 60 python3 talker.py 2>&1 | tail -1
rm -f std_msgs.py; echo "[after deleting std_msgs.py, stale __pycache__ left in place]"; ls __pycache__ 2>/dev/null; timeout 60 python3 talker.py 2>&1 | tail -1
cd $W

step "I. stale install: interface package removed from src but install/ kept"
mv src/my_interfaces /tmp/moved_my_interfaces
( source install/setup.bash; echo "import with source gone, install/ kept:"; imp "from my_interfaces.msg import Num" )
rm -rf install/my_interfaces build/my_interfaces
( source install/setup.bash 2>&1 | tail -2; echo "after rm -rf install/my_interfaces:"; imp "from my_interfaces.msg import Num" )
mv /tmp/moved_my_interfaces src/my_interfaces
echo; echo "##### done $D"

# Supplement, run once on lyrical after the main run: docker exec -i pk43-lyrical bash -s < this block
# source /opt/ros/lyrical/setup.bash; cd /w/ws_lyrical; export ROS_DOMAIN_ID=88 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST MAKEFLAGS=-j1
# echo; echo "##### SUPPLEMENT (lyrical, same container, after the run above)"
# echo "##### S1. stderr of my_interfaces build"; cat log/latest_build/my_interfaces/stderr.log | head -8
# echo "##### S2. my_server3 (ament_python_install_package in an interface package) on lyrical: import + ros2 run"
# source install/setup.bash
# ls install/my_server3/lib/python3.14/site-packages/my_server3/ | tr '\n' ' '; echo
# timeout 60 ros2 run my_server3 server_node.py 2>&1 | tail -2
# echo "##### S3. import timing again, 5 runs, ms (rclpy import excluded), and plain 'import rclpy' ms"
# for i in 1 2 3 4 5; do python3 -c "import time;t=time.perf_counter();from my_interfaces.msg import Num;print(round((time.perf_counter()-t)*1000,1))"; done | tr '\n' ' '; echo
# for i in 1 2 3; do python3 -c "import time;t=time.perf_counter();import rclpy;print(round((time.perf_counter()-t)*1000,1))"; done | tr '\n' ' '; echo
# uptime
