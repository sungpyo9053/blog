#!/bin/bash
# Usage (on a Docker host): bash repro.sh humble|jazzy|lyrical > out_<distro>.txt 2>&1
# Measures which ROS 2 imports pyright (the checker inside VS Code Pylance) can resolve,
# for unsourced/sourced shells, extraPaths configs and --symlink-install builds.
# Network is used only to download Node.js and pyright; it is disconnected before the tests.
set -u
D=$1
NAME=pk32-$D
IMG=ros:$D-ros-base
NODE_VER=v20.18.0
PYRIGHT_VER=1.1.389
ulimit -c 0
docker rm -f $NAME >/dev/null 2>&1
docker run -d --name $NAME --cpus 1.5 --memory 2g --pids-limit 256 --ulimit core=0 \
  -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  $IMG sleep 3600 >/dev/null
echo "### image $IMG"
docker image inspect $IMG --format '{{index .RepoDigests 0}}'

# --- setup (needs network): Node.js tarball + pyright from npm
docker exec $NAME bash -c "set -e; cd /opt; python3 - <<'PY'
import urllib.request
urllib.request.urlretrieve('https://nodejs.org/dist/$NODE_VER/node-$NODE_VER-linux-x64.tar.xz','/opt/node.tar.xz')
PY
mkdir -p /opt/node && tar -xJf /opt/node.tar.xz -C /opt/node --strip-components=1 && rm /opt/node.tar.xz
PATH=/opt/node/bin:\$PATH npm install -g --silent pyright@$PYRIGHT_VER >/dev/null 2>&1
echo setup-done" || { echo SETUP FAILED; exit 1; }
docker network disconnect bridge $NAME && echo "### network disconnected"

cat > /tmp/en-pick42/inner.sh <<'INNER'
#!/bin/bash
set +e
ulimit -c 0
export PATH=/opt/node/bin:$PATH
D=$ROS_DISTRO
PYV=$(python3 -c 'import sys;print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
echo "### versions"
echo "distro=$D python=$PYV pyright=$(pyright --version | tail -1) node=$(node --version)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-launch-ros ros-$D-rmw-implementation 2>/dev/null
python3 -c 'import setuptools;print("setuptools", setuptools.__version__)'
colcon version-check 2>/dev/null | grep -E "colcon-core|colcon-python-setup-py|colcon-ros " | head -3

# --- workspace: ament_cmake interface package + ament_python package
mkdir -p /ws/src/my_interfaces/msg && cd /ws/src
printf 'float64 x\nfloat64 y\n' > my_interfaces/msg/Point2.msg
cat > my_interfaces/CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(my_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Point2.msg")
ament_package()
EOF
cat > my_interfaces/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>my_interfaces</name><version>0.0.1</version><description>test msgs</description>
  <maintainer email="user@example.com">user</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
source /opt/ros/$D/setup.bash
ros2 pkg create --build-type ament_python my_py_pkg >/dev/null 2>&1
printf 'def add(a: int, b: int) -> int:\n    return a + b\n' > my_py_pkg/my_py_pkg/helpers.py
cp -r /ws /ws_sym
cd /ws && MAKEFLAGS=-j1 colcon build --parallel-workers 1 2>&1 | tail -2
cd /ws_sym && MAKEFLAGS=-j1 colcon build --parallel-workers 1 --symlink-install 2>&1 | tail -2
for W in /ws /ws_sym; do for P in my_interfaces my_py_pkg; do [ -s $W/log/latest_build/$P/stderr.log ] && { echo "### stderr $W $P"; tail -12 $W/log/latest_build/$P/stderr.log; }; done; done
for W in /ws /ws_sym; do
  echo "### python files in $W/install"
  find $W/install -name '_point2.py' -o -name 'helpers.py' -o -name '*.egg-link' -o -name '*.pth' -o -name '__editable__*' | sed "s|^|  |"
done

mkdir -p /proj && cd /proj
cat > node.py <<'EOF'
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from launch import LaunchDescription
from launch_ros.actions import Node as LaunchNode
from my_interfaces.msg import Point2
from my_py_pkg.helpers import add


def main() -> None:
    rclpy.init()
    node = Node("t")
    p = Point2()
    p.x = 1.0
    s = String()
    s.data = "x"
    print(node, p, s, LaunchDescription, LaunchNode, add(1, 2))
EOF

run() { # $1 label, rest: command prefix
  local label=$1; shift
  echo "### case $label"
  local t0=$(date +%s.%N)
  "$@" bash -c 'cd /proj && pyright node.py' 2>&1 | grep -E 'error|warning|informations|0 errors' | sed "s|/proj/||"
  local t1=$(date +%s.%N)
  python3 -c "print('  wall_s=%.2f' % ($t1-$t0))"
}
cfg() { python3 - "$@" <<'PY'
import json,sys
json.dump({"extraPaths": sys.argv[1:]}, open('/proj/pyrightconfig.json','w'))
print('  pyrightconfig.json extraPaths =', sys.argv[1:])
PY
}
CLEAN="env -i HOME=/root PATH=/opt/node/bin:/usr/bin:/bin"

rm -f /proj/pyrightconfig.json
run A_unsourced_no_config $CLEAN
run B_sourced_opt_ros_only $CLEAN bash -c "source /opt/ros/$D/setup.bash && exec \"\$@\"" _
run C_sourced_ws_install $CLEAN bash -c "source /ws/install/setup.bash && exec \"\$@\"" _
run C2_sourced_ws_symlink_install $CLEAN bash -c "source /ws_sym/install/setup.bash && exec \"\$@\"" _

echo "### where python finds the modules (sourced /ws_sym)"
$CLEAN bash -c "source /ws_sym/install/setup.bash && python3 -c 'import rclpy,std_msgs,launch,launch_ros,my_interfaces,my_py_pkg;[print(\"  \"+m.__name__, m.__file__) for m in (rclpy,std_msgs,launch,launch_ros,my_interfaces,my_py_pkg)]'"
echo "### PYTHONPATH after sourcing /ws/install/setup.bash"
WS_PP=$($CLEAN bash -c "source /ws/install/setup.bash && echo \$PYTHONPATH")
echo "$WS_PP" | tr ':' '\n' | sed 's/^/  /'
echo "### PYTHONPATH after sourcing /ws_sym/install/setup.bash"
SYM_PP=$($CLEAN bash -c "source /ws_sym/install/setup.bash && echo \$PYTHONPATH")
echo "$SYM_PP" | tr ':' '\n' | sed 's/^/  /'

cfg /opt/ros/$D/lib/python$PYV/site-packages
run D1_extraPaths_opt_ros_only $CLEAN
cfg $(echo "$WS_PP" | tr ':' ' ')
run D2_extraPaths_full_PYTHONPATH $CLEAN
cfg $(echo "$SYM_PP" | tr ':' ' ')
run D3_extraPaths_full_PYTHONPATH_symlink $CLEAN
cfg $(echo "$SYM_PP" | tr ':' '\n' | grep -v '/build/' | tr '\n' ' ')
run D3b_symlink_PYTHONPATH_without_build_dir $CLEAN
OTHER=3.10; [ "$PYV" = "3.10" ] && OTHER=3.12
cfg /opt/ros/$D/lib/python$OTHER/site-packages /ws/install/my_interfaces/lib/python$OTHER/site-packages
run D4_extraPaths_wrong_python_version $CLEAN
cfg /opt/ros/$D/lib/python$PYV/site-packages /ws/install/my_interfaces/lib/python$PYV/site-packages /ws/install/my_py_pkg/lib/python$PYV/site-packages
run D5_extraPaths_guessed_lib_site_packages $CLEAN
cfg /opt/ros/$D/lib/python$PYV/site-packages /ws/src/my_py_pkg
run D6_extraPaths_src_folder_for_own_pkg $CLEAN
rm -f /proj/pyrightconfig.json
# sourced shell AND a config file: does extraPaths add to or replace PYTHONPATH?
cfg /opt/ros/$D/lib/python$PYV/site-packages
run E_sourced_ws_plus_config_opt_only $CLEAN bash -c "source /ws/install/setup.bash && exec \"\$@\"" _
rm -f /proj/pyrightconfig.json
echo "### done"
INNER
docker cp /tmp/en-pick42/inner.sh $NAME:/inner.sh
docker exec $NAME bash /inner.sh
docker rm -f $NAME >/dev/null && echo "### container removed"
