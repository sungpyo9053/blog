#!/bin/bash
# Run inside ros:<distro>-ros-base as root:
#   docker run --rm -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh
# Reproduces colcon build "Permission denied" errors: a workspace first built
# as root (what `sudo colcon build` or a root Docker container leaves behind),
# a root-owned workspace folder, and absolute install destinations. Then
# compares the fixes. Root stands in for sudo; user "dev" (uid 1500) is the
# normal user.
ulimit -c 0
export MAKEFLAGS=-j1
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-ament-cmake ros-$ROS_DISTRO-ament-package 2>/dev/null
dpkg-query -W -f='${Package} ${Version}\n' 'python3-colcon-core' 'python3-colcon-cmake' 'python3-colcon-ros' 'python3-setuptools' 'cmake' 2>/dev/null
pip list 2>/dev/null | grep -i -E '^(colcon-core|colcon-cmake|colcon-ros|setuptools) ' | sed 's/^/pip: /'
useradd -m -u 1500 -s /bin/bash dev
id dev

# --- template packages: one ament_cmake (tiny C++ exe), one ament_python ---
mkdir -p /tpl/src/perm_cpp/src /tpl/src/perm_py/perm_py /tpl/src/perm_py/resource
cd /tpl/src/perm_cpp
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>perm_cpp</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
cat > CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(perm_cpp)
find_package(ament_cmake REQUIRED)
add_executable(hello src/hello.cpp)
install(TARGETS hello DESTINATION lib/${PROJECT_NAME})
ament_package()
X
echo '#include <cstdio>
int main(){std::puts("HELLO-CPP");}' > src/hello.cpp
cd /tpl/src/perm_py
cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>perm_py</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<export><build_type>ament_python</build_type></export></package>
X
touch resource/perm_py perm_py/__init__.py
echo 'def main():
    print("HELLO-PY")' > perm_py/hello.py
cat > setup.py <<'X'
from setuptools import setup
setup(name='perm_py', version='0.0.0', packages=['perm_py'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/perm_py']),
                  ('share/perm_py', ['package.xml'])],
      entry_points={'console_scripts': ['hello = perm_py.hello:main']})
X
printf '[develop]\nscript_dir=$base/lib/perm_py\n[install]\ninstall_scripts=$base/lib/perm_py\n' > setup.cfg
chown -R dev:dev /tpl

newws() { rm -rf "$1"; cp -a /tpl "$1"; chown -R dev:dev "$1"; }
asroot() { echo "--- [root] $2  (in $1)"; ( cd "$1" && bash -c "$2" ) 2>&1 | tail -n "${3:-40}"; echo "rc=${PIPESTATUS[0]}"; }
asdev()  { echo "--- [dev] $2  (in $1)"; su dev -s /bin/bash -c "ulimit -c 0; export MAKEFLAGS=-j1; source /opt/ros/$ROS_DISTRO/setup.bash; cd $1 && $2" 2>&1 | tail -n "${3:-40}"; echo "rc=${PIPESTATUS[0]}"; }
owners() { echo "owners in $1:"; ( cd "$1" && stat -c '%U %n' build install log 2>&1 | sed 's/^/  /' ); }
B='colcon build --parallel-workers 1'

echo; echo "################ C0 baseline: dev builds a clean workspace"
newws /ws0
asdev /ws0 "$B"
asdev /ws0 "source install/setup.bash && ros2 run perm_cpp hello && ros2 run perm_py hello"

echo; echo "################ C1 root built first (sudo colcon build), then dev"
newws /ws1
asroot /ws1 "$B"
owners /ws1
asdev /ws1 "$B" 60
echo "-- C1 a second time (same error?)"
asdev /ws1 "$B" 8
echo "-- C1 dev can still use the root-built install (read-only use)"
asdev /ws1 "source install/setup.bash && ros2 run perm_cpp hello && ros2 run perm_py hello"

echo; echo "################ C2 only build/ and install/ root-owned (log/ removed)"
newws /ws2
asroot /ws2 "$B"
rm -rf /ws2/log
owners /ws2
asdev /ws2 "$B" 80

echo; echo "################ C3 only install/ root-owned"
newws /ws3
asroot /ws3 "$B"
chown -R dev:dev /ws3/build /ws3/log
owners /ws3
asdev /ws3 "$B" 80

echo; echo "################ C4 only build/ root-owned"
newws /ws4
asroot /ws4 "$B"
chown -R dev:dev /ws4/install /ws4/log
owners /ws4
asdev /ws4 "$B" 80

echo; echo "################ C5 workspace folder itself created by root (sudo mkdir), src readable"
rm -rf /ws5; mkdir /ws5; cp -a /tpl/src /ws5/src; chown -R root:root /ws5; chmod -R a+rX /ws5
stat -c '%U %a %n' /ws5
asdev /ws5 "$B" 30

echo; echo "################ C6 root-built, dev edits one package and rebuilds only it, logs elsewhere"
newws /ws6
asroot /ws6 "$B"
su dev -c "echo '// edit' >> /ws6/src/perm_cpp/src/hello.cpp" 2>&1 || echo "dev cannot edit src? rc=$?"
asdev /ws6 "colcon --log-base /tmp/devlog6 build --parallel-workers 1 --packages-select perm_cpp" 60

echo; echo "################ C7 absolute install DESTINATION /lib/\${PROJECT_NAME} (CMake)"
newws /ws7
sed -i 's#DESTINATION lib/#DESTINATION /lib/#' /ws7/src/perm_cpp/CMakeLists.txt
grep -n DESTINATION /ws7/src/perm_cpp/CMakeLists.txt
asdev /ws7 "$B --packages-select perm_cpp" 40
echo "-- C7 same as root: succeeds?"
newws /ws7r
sed -i 's#DESTINATION lib/#DESTINATION /lib/#' /ws7r/src/perm_cpp/CMakeLists.txt
asroot /ws7r "$B --packages-select perm_cpp" 15
ls -l /lib/perm_cpp 2>&1 | sed 's/^/  /'
ls /ws7r/install/perm_cpp/lib 2>&1 | sed 's/^/  install lib: /'
asroot /ws7r "source install/setup.bash && ros2 run perm_cpp hello" 5
echo "-- C7 dev again, now that root has created /lib/perm_cpp"
asdev /ws7 "$B --packages-select perm_cpp" 20
echo "-- C7 dev after editing hello.cpp (binary differs from the root-installed one)"
su dev -c "sed -i 's/HELLO-CPP/HELLO-CPP-v2/' /ws7/src/perm_cpp/src/hello.cpp"
asdev /ws7 "$B --packages-select perm_cpp" 20
rm -rf /lib/perm_cpp

echo; echo "################ C8 absolute data_files path ('/share/perm_py') in setup.py"
newws /ws8
sed -i "s#('share/perm_py'#('/share/perm_py'#" /ws8/src/perm_py/setup.py
grep -n "share/perm_py'" /ws8/src/perm_py/setup.py
asdev /ws8 "$B --packages-select perm_py" 40
echo "-- C8 as root"
newws /ws8r
sed -i "s#('share/perm_py'#('/share/perm_py'#" /ws8r/src/perm_py/setup.py
asroot /ws8r "$B --packages-select perm_py" 15
ls -l /share/perm_py 2>&1 | sed 's/^/  /'
ls /ws8r/install/perm_py/share/perm_py 2>&1 | sed 's/^/  install share: /'
rm -rf /share

echo; echo "################ F1 fix: chown -R dev:dev the workspace, rebuild"
newws /wf1; asroot /wf1 "$B" 3; owners /wf1
t0=$(date +%s.%N); chown -R dev:dev /wf1; t1=$(date +%s.%N)
python3 -c "print('chown took %.3f s' % ($t1-$t0))"
asdev /wf1 "s=\$(date +%s.%N); $B | tail -n 3; python3 -c \"print('rebuild elapsed %.1f s' % (\$(date +%s.%N)-\$s))\""
asdev /wf1 "source install/setup.bash && ros2 run perm_cpp hello && ros2 run perm_py hello"

echo; echo "################ F2 fix: delete build install log (as root), rebuild as dev"
newws /wf2; asroot /wf2 "$B" 3
asroot /wf2 "rm -rf build install log" 3
asdev /wf2 "s=\$(date +%s.%N); $B | tail -n 3; python3 -c \"print('rebuild elapsed %.1f s' % (\$(date +%s.%N)-\$s))\""

echo; echo "################ F3 workaround: --log-base only"
newws /wf3; asroot /wf3 "$B" 3
asdev /wf3 "colcon --log-base /tmp/devlog3 build --parallel-workers 1" 30

echo; echo "################ F4 workaround: separate bases for dev"
newws /wf4; asroot /wf4 "$B" 3
asdev /wf4 "colcon --log-base log_dev build --parallel-workers 1 --build-base build_dev --install-base install_dev" 8
asdev /wf4 "source install_dev/setup.bash && ros2 run perm_cpp hello"

echo; echo "################ F5 'fix' by building as root again (sudo colcon build): what dev is left with"
newws /wf5; asroot /wf5 "$B" 3
asroot /wf5 "$B" 4
owners /wf5
asdev /wf5 "touch install/x" 3

echo "=== done $ROS_DISTRO"
