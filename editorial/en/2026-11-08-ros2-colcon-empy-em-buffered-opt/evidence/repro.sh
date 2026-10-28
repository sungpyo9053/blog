#!/bin/bash
# Reproduce rosidl_generate_interfaces failures when CMake picks a venv Python.
# Host:  bash repro.sh            -> runs each distro in a fresh container, writes out_<distro>.txt
# Inner: bash repro.sh inner      -> runs inside ros:<distro>-ros-base
set -u
HERE=$(cd "$(dirname "$0")" && pwd)

if [ "${1:-}" != inner ]; then
  for d in humble jazzy lyrical; do
    docker run --rm --name "empy-$d" -v "$HERE:/w:ro" "ros:$d-ros-base" bash /w/repro.sh inner > "$HERE/out_$d.txt" 2>&1
    echo "$d done rc=$?"
  done
  exit 0
fi

# ---------------- inside the container ----------------
set +u
D=$ROS_DISTRO
source /opt/ros/$D/setup.bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq python3-venv >/dev/null 2>&1

echo "##### distro: $D"
echo "== versions"
python3 --version
cmake --version | head -1
dpkg-query -W -f='${Package} ${Version}\n' python3-empy python3-colcon-core python3-catkin-pkg python3-catkin-pkg-modules python3-lark python3-numpy \
  ros-$D-rosidl-generator-py ros-$D-rosidl-adapter ros-$D-ament-cmake-core 2>&1
python3 -c "import em; print('system em:', em.__version__, em.__file__)"
echo "-- how ament_cmake_core parses package.xml (catkin_pkg import lines):"
grep -nE "catkin_pkg|ImportError" /opt/ros/$D/share/ament_cmake_core/cmake/core/package_xml_2_cmake.py | head -6
echo "colcon: $(command -v colcon) shebang: $(head -1 "$(command -v colcon)")"

# --- part 1 workspace: one ament_cmake interfaces package
mkdir -p /ws/src/my_interfaces/msg
cd /ws/src/my_interfaces
echo "int64 num" > msg/Num.msg
cat > CMakeLists.txt <<'EOF'
cmake_minimum_required(VERSION 3.8)
project(my_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME} "msg/Num.msg")
ament_package()
EOF
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>my_interfaces</name><version>0.0.0</version><description>t</description>
  <maintainer email="user@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF

build() {  # $1 label, rest = extra colcon args
  local label=$1; shift
  echo; echo "=== CASE: $label"
  echo "python3 on PATH: $(command -v python3)  VIRTUAL_ENV=${VIRTUAL_ENV:-none}"
  [ -n "${VIRTUAL_ENV:-}" ] && pip list 2>/dev/null | grep -iE '^(empy|catkin.pkg|lark|numpy) ' | tr '\n' ';' && echo
  cd /ws && rm -rf build install log
  colcon build --packages-select my_interfaces "$@" > /tmp/b.log 2>&1
  echo "colcon exit code: $?"
  grep -E "No module named|AttributeError|ImportError|Error processing|CMake Error|execute_process\(|Failed <<<|Finished <<<|Summary:|package(s)? failed" /tmp/b.log | head -20
  echo "-- cmake chose: $(grep -hE '^(Python3_EXECUTABLE|PYTHON_EXECUTABLE)' build/my_interfaces/CMakeCache.txt 2>/dev/null | tr '\n' ' ')"
  echo "-- numpy in cache: $(grep -hiE '^(Python3_NumPy_INCLUDE_DIR|_Python3_NumPy_INCLUDE_DIR)' build/my_interfaces/CMakeCache.txt 2>/dev/null | tr '\n' ' ')"
  echo "-- generated py: $(ls install/my_interfaces/local/lib/python3*/dist-packages/my_interfaces/msg/_num.py install/my_interfaces/lib/python3*/site-packages/my_interfaces/msg/_num.py 2>/dev/null)"
}

full_error() {  # print the full stderr of the last build, once per error type
  echo "-- full stderr of last build (first 40 lines):"
  sed -n '/--- stderr/,$p' /tmp/b.log | head -40
  echo "-- interpreter / generator lines in the log:"
  grep -nE "bin/python3|env python|ImportError|Error processing|BUFFERED_OPT|No module named" /tmp/b.log | grep -v "^\s*$" | head -15
}

build "A: system python, no venv"

python3 -m venv /venv/bare
source /venv/bare/bin/activate
python3 -c "import catkin_pkg, sys; print('catkin_pkg importable in bare venv from', catkin_pkg.__file__)" 2>&1 | tail -1
python3 -c "import numpy" 2>&1 | tail -1
build "B: venv without system site packages, nothing installed"
full_error
build "B2: same venv + --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3" --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3; full_error
build "B3: same venv + -DPython3_EXECUTABLE and -DPYTHON_EXECUTABLE=/usr/bin/python3" --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 -DPYTHON_EXECUTABLE=/usr/bin/python3; full_error
deactivate

# ladder: add packages one at a time to see each error in order
python3 -m venv /venv/ladder
source /venv/ladder/bin/activate
pip install -q -U pip >/dev/null 2>&1
pip install -q catkin_pkg >/dev/null 2>&1; build "C1: venv + catkin_pkg"; full_error
pip install -q empy >/dev/null 2>&1;       build "C2: venv + catkin_pkg + empy (latest from PyPI)"; full_error
pip install -q empy==3.3.4 >/dev/null 2>&1; build "C3: venv + catkin_pkg + empy==3.3.4"; full_error
pip install -q lark >/dev/null 2>&1;       build "C4: venv + catkin_pkg + empy==3.3.4 + lark"; full_error
pip install -q numpy >/dev/null 2>&1;      build "C5: venv + catkin_pkg + empy==3.3.4 + lark + numpy"; full_error
pip install -q setuptools >/dev/null 2>&1; build "C6: venv + catkin_pkg + empy==3.3.4 + lark + numpy + setuptools"
deactivate

# realistic case: everything installed, but latest empy
python3 -m venv /venv/e4
source /venv/e4/bin/activate
pip install -q -U pip >/dev/null 2>&1
pip install -q empy catkin_pkg lark numpy >/dev/null 2>&1
build "E1: venv with empy latest + catkin_pkg lark numpy"; full_error
pip install -q setuptools >/dev/null 2>&1
build "E1b: venv with empy latest + catkin_pkg lark numpy setuptools"; full_error
build "E2: same venv + --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3" --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3; full_error
build "E2b: same venv + -DPython3_EXECUTABLE and -DPYTHON_EXECUTABLE=/usr/bin/python3" --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 -DPYTHON_EXECUTABLE=/usr/bin/python3; full_error
deactivate
build "E3: same shell after deactivate"
source /venv/e4/bin/activate
pip install -q empy==3.3.4 >/dev/null 2>&1
build "E4: venv E1 after pip install empy==3.3.4"
deactivate

# catkin_pkg missing while em is present (the ladder above installs catkin_pkg first)
python3 -m venv /venv/nocatkin
source /venv/nocatkin/bin/activate
pip install -q empy==3.3.4 >/dev/null 2>&1
build "K: venv + empy==3.3.4 only (no catkin_pkg)"; full_error
deactivate

python3 -m venv --system-site-packages /venv/ssp
source /venv/ssp/bin/activate
build "S1: venv --system-site-packages, nothing installed"
pip install -q empy >/dev/null 2>&1
build "S2: venv --system-site-packages + pip install empy (no -U)"
pip install -q -U empy >/dev/null 2>&1
build "S3: venv --system-site-packages + pip install -U empy"; full_error
deactivate

# ---------------- part 2: ament_python package with msg/ ----------------
echo; echo "##### part 2: ament_python + custom message"
mkdir -p /ws2/src/py_with_msg/{msg,py_with_msg,resource}
cd /ws2/src/py_with_msg
echo "int64 num" > msg/Num.msg
touch resource/py_with_msg py_with_msg/__init__.py
printf '[develop]\nscript_dir=$base/lib/py_with_msg\n[install]\ninstall_scripts=$base/lib/py_with_msg\n' > setup.cfg
cat > py_with_msg/talker.py <<'EOF'
from py_with_msg.msg import Num
def main():
    print("OK", Num(num=5))
EOF
cat > setup.py <<'EOF'
from setuptools import setup
setup(name='py_with_msg', version='0.0.0', packages=['py_with_msg'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/py_with_msg']),
                  ('share/py_with_msg', ['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': ['talker = py_with_msg.talker:main']})
EOF
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>py_with_msg</name><version>0.0.0</version><description>t</description>
  <maintainer email="user@example.com">a</maintainer><license>MIT</license>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <exec_depend>rclpy</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>
  <export><build_type>ament_python</build_type></export>
</package>
EOF
cd /ws2
colcon build > /tmp/p.log 2>&1; echo "colcon exit code: $?"
grep -vE '^\s*$' /tmp/p.log | head -20
echo "-- generated msg files under install/: $(find install -path '*py_with_msg/msg*' 2>/dev/null | head -5)"
echo "-- interface registered: $(ls install/py_with_msg/share/ament_index/resource_index/rosidl_interfaces 2>/dev/null || echo none)"
source install/setup.bash
echo "-- ros2 run py_with_msg talker:"
ros2 run py_with_msg talker 2>&1 | tail -4
echo "-- ros2 interface show py_with_msg/msg/Num:"
ros2 interface show py_with_msg/msg/Num 2>&1 | tail -2

# fix: separate ament_cmake interfaces package + ament_python node package
echo; echo "=== FIX: separate interfaces package"
rm -rf /ws3 && mkdir -p /ws3/src
cp -r /ws/src/my_interfaces /ws3/src/
mkdir -p /ws3/src/py_node/{py_node,resource}
cd /ws3/src/py_node
touch resource/py_node py_node/__init__.py
cat > py_node/talker.py <<'EOF'
from my_interfaces.msg import Num
def main():
    print("OK", Num(num=5))
EOF
sed 's/py_with_msg/py_node/g' /ws2/src/py_with_msg/setup.py > setup.py
sed 's/py_with_msg/py_node/g' /ws2/src/py_with_msg/setup.cfg > setup.cfg
cat > package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>py_node</name><version>0.0.0</version><description>t</description>
  <maintainer email="user@example.com">a</maintainer><license>MIT</license>
  <exec_depend>rclpy</exec_depend>
  <exec_depend>my_interfaces</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>
EOF
cd /ws3
colcon build > /tmp/f.log 2>&1; echo "colcon exit code: $?"
grep -E "Finished|Failed|Summary" /tmp/f.log
source install/setup.bash
echo "-- ros2 run py_node talker:"
ros2 run py_node talker 2>&1 | tail -3
echo "##### end $D"
