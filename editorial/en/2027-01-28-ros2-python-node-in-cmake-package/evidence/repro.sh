#!/bin/bash
# Python nodes inside an ament_cmake package: what each install mistake prints.
# Run inside ros:<distro>-ros-base, no network, one distro at a time:
#   docker run --rm --name pk48-<distro> --network none -e ROS_DOMAIN_ID=88 \
#     -v $PWD:/w ros:<distro>-ros-base bash /w/repro.sh > out_<distro>.txt 2>&1
# Each variant is its own package. Only mix_good also has a C++ node.
# Run on the runner (2 vCPU) with --cpus 1.5 --pids-limit 400 --ulimit core=0, Humble, Jazzy, Lyrical in turn.
# Earlier passes were discarded: the first had an invalid maintainer email (every build failed in
# catkin_pkg), later ones lacked --prefix and cut long tracebacks. out_<distro>.txt are the final pass.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
export ROS_DOMAIN_ID=88 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST  # container also has --network none
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MAKEFLAGS=-j1
S=/ws/src; rm -rf /ws /ws2; mkdir -p $S

echo "=== distro=$ROS_DISTRO $(python3 --version) $(cmake --version | head -1)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli \
  ros-$ROS_DISTRO-ros2run ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-ament-cmake \
  ros-$ROS_DISTRO-ament-cmake-python ros-$ROS_DISTRO-launch ros-$ROS_DISTRO-launch-ros 2>&1
echo "colcon-core $(python3 -c 'import colcon_core; print(colcon_core.__version__)' 2>&1)"
echo "default RMW: $(python3 -c 'import rclpy.utilities as u; print(u.get_rmw_implementation_identifier())' 2>&1)"
echo "/usr/bin/python: $(ls -l /usr/bin/python 2>&1)"

# mkpkg NAME OPTIONS... ; options:
#   noinstall bin files noshebang crlf wrongshebang nomodule nofind noinit nodep rename srcnox cpp
mkpkg() {
  local n=$1; shift; local o=" $* "; local d=$S/$n
  mkdir -p $d/scripts $d/$n
  has() { [[ "$o" == *" $1 "* ]]; }
  # package.xml
  local btd="  <buildtool_depend>ament_cmake_python</buildtool_depend>"; has nodep && btd=""
  local cppdep=""; has cpp && cppdep="  <depend>rclcpp</depend>"
  cat > $d/package.xml <<EOF
<?xml version="1.0"?>
<package format="3">
  <name>$n</name>
  <version>0.0.1</version>
  <description>test</description>
  <maintainer email="test@example.com">t</maintainer>
  <license>MIT</license>
  <buildtool_depend>ament_cmake</buildtool_depend>
$btd
$cppdep
  <exec_depend>rclpy</exec_depend>
  <export><build_type>ament_cmake</build_type></export>
</package>
EOF
  # python module
  has noinit || echo "" > $d/$n/__init__.py
  echo "def greeting():
    return 'hello from $n.helper v1'" > $d/$n/helper.py
  # script
  local sb='#!/usr/bin/env python3'
  has wrongshebang && sb='#!/usr/bin/python'
  local body="import rclpy
from $n.helper import greeting


def main():
    rclpy.init()
    node = rclpy.create_node('talker_$n')
    node.get_logger().info(greeting())
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()"
  if has noshebang; then printf '%s\n' "$body" > $d/scripts/talker.py
  else printf '%s\n%s\n' "$sb" "$body" > $d/scripts/talker.py; fi
  has crlf && sed -i 's/$/\r/' $d/scripts/talker.py
  has srcnox && chmod 644 $d/scripts/talker.py || chmod 755 $d/scripts/talker.py
  # CMakeLists.txt
  {
    echo "cmake_minimum_required(VERSION 3.8)"
    echo "project($n)"
    echo "find_package(ament_cmake REQUIRED)"
    has nofind || echo "find_package(ament_cmake_python REQUIRED)"
    if has cpp; then
      echo "find_package(rclcpp REQUIRED)"
      echo "add_executable(cpp_node src/cpp_node.cpp)"
      echo "target_link_libraries(cpp_node rclcpp::rclcpp)"
      echo "install(TARGETS cpp_node DESTINATION lib/\${PROJECT_NAME})"
    fi
    has nomodule || echo "ament_python_install_package(\${PROJECT_NAME})"
    if has noinstall; then :;
    elif has bin; then echo "install(PROGRAMS scripts/talker.py DESTINATION bin)"
    elif has files; then echo "install(FILES scripts/talker.py DESTINATION lib/\${PROJECT_NAME})"
    elif has rename; then echo "install(PROGRAMS scripts/talker.py DESTINATION lib/\${PROJECT_NAME} RENAME talker)"
    else echo "install(PROGRAMS scripts/talker.py DESTINATION lib/\${PROJECT_NAME})"; fi
    echo "ament_package()"
  } > $d/CMakeLists.txt
  if has cpp; then mkdir -p $d/src; cat > $d/src/cpp_node.cpp <<'EOF'
#include <rclcpp/rclcpp.hpp>
int main(int argc, char ** argv) {
  rclcpp::init(argc, argv);
  auto n = std::make_shared<rclcpp::Node>("cpp_node");
  RCLCPP_INFO(n->get_logger(), "hello from cpp_node");
  rclcpp::shutdown();
  return 0;
}
EOF
  fi
}

PKGS="mix_good py_noinstall py_bin py_files py_noshebang py_crlf py_wrongshebang py_nomodule py_nofind py_noinit py_nodep py_rename py_srcnox"
mkpkg mix_good cpp
mkpkg py_noinstall noinstall
mkpkg py_bin bin
mkpkg py_files files
mkpkg py_noshebang noshebang
mkpkg py_crlf crlf
mkpkg py_wrongshebang wrongshebang
mkpkg py_nomodule nomodule
mkpkg py_nofind nofind
mkpkg py_noinit noinit
mkpkg py_nodep nodep
mkpkg py_rename rename
mkpkg py_srcnox srcnox

ms() { echo $(( ($(date +%s%N) - $1) / 1000000 )); }
build() { # build WS FLAGS PKG
  local ws=$1 fl=$2 p=$3
  echo "--- colcon build $fl --packages-select $p"
  local t0=$(date +%s%N)
  ( cd $ws && timeout 600 colcon build $fl --parallel-workers 1 --packages-select $p \
      --event-handlers console_cohesion+ > /tmp/b.log 2>&1 ); local rc=$?
  grep -v '^\s*$' /tmp/b.log | grep -Ev '^(Starting >>>|-- Installing|-- Symlinking|-- Up-to-date|Listing |Compiling )' | tail -n 25
  echo "build_exit=$rc time_ms=$(ms $t0)"
}
runit() { # runit LABEL CMD...
  echo "--- $1"; shift
  local t0=$(date +%s%N)
  timeout 60 "$@" > /tmp/r.log 2>&1; local rc=$?
  grep -v '^\s*$' /tmp/r.log > /tmp/r2.log
  if [ $(wc -l < /tmp/r2.log) -gt 40 ]; then head -n 28 /tmp/r2.log; echo "[... $(( $(wc -l < /tmp/r2.log) - 36 )) lines cut ...]"; tail -n 8 /tmp/r2.log; else cat /tmp/r2.log; fi
  echo "exit=$rc time_ms=$(ms $t0)"
}

echo "=== 1. plain build, one package at a time"
for p in $PKGS; do build /ws "" $p; done

echo "=== 2. what got installed"
for p in $PKGS; do
  echo "--- $p"
  for f in /ws/install/$p/lib/$p/* /ws/install/$p/bin/*; do [ -e "$f" ] && stat -c '%A %N' "$f"; done
  ls -d /ws/install/$p/lib/python3*/site-packages/$p 2>/dev/null || ls -d /ws/install/$p/local/lib/python3*/dist-packages/$p 2>/dev/null || echo "(no python module dir)"
done

echo "=== 3. ros2 pkg executables and ros2 run"
source /ws/install/setup.bash
for p in $PKGS; do
  [ -d /ws/install/$p ] || { echo "--- $p not installed (build failed)"; continue; }
  runit "ros2 pkg executables $p" ros2 pkg executables $p
  runit "ros2 run $p talker.py" ros2 run $p talker.py
done
runit "ros2 run mix_good cpp_node" ros2 run mix_good cpp_node
runit "ros2 run py_rename talker" ros2 run py_rename talker
runit "ros2 run mix_good talker (no .py)" ros2 run mix_good talker
runit "ros2 run --prefix python3 py_noshebang talker.py" ros2 run --prefix python3 py_noshebang talker.py
runit "talker.py from PATH (install/py_bin/bin)" talker.py
runit "direct exec install/py_noshebang/lib/py_noshebang/talker.py" /ws/install/py_noshebang/lib/py_noshebang/talker.py
runit "python3 install/py_noshebang/lib/py_noshebang/talker.py" python3 /ws/install/py_noshebang/lib/py_noshebang/talker.py
runit "python3 install/py_nomodule/lib/py_nomodule/talker.py" python3 /ws/install/py_nomodule/lib/py_nomodule/talker.py
runit "cd src/py_nomodule && python3 scripts/talker.py" bash -c "cd /ws/src/py_nomodule && python3 scripts/talker.py"
runit "head -c 40 of crlf script | od -c" bash -c "head -n1 /ws/install/py_crlf/lib/py_crlf/talker.py | od -c | head -3"

echo "=== 4. ros2 launch with the same executables"
mkdir -p /tmp/lf
for p in mix_good py_noshebang py_crlf py_noinstall py_files; do
  cat > /tmp/lf/$p.launch.py <<EOF
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='$p', executable='talker.py', output='screen')])
EOF
  runit "ros2 launch $p.launch.py" ros2 launch /tmp/lf/$p.launch.py
done

echo "=== 5. edit helper.py without rebuilding (plain install)"
sed -i 's/v1/v2/' /ws/src/mix_good/mix_good/helper.py
runit "ros2 run mix_good talker.py after edit, no rebuild" ros2 run mix_good talker.py
sed -i 's/v1/v2/' /ws/src/mix_good/scripts/talker.py  # no-op marker, script has no v1
build /ws "" mix_good
runit "ros2 run mix_good talker.py after rebuild" ros2 run mix_good talker.py
sed -i 's/v2/v1/' /ws/src/mix_good/mix_good/helper.py

echo "=== 6. --symlink-install in a fresh workspace"
mkdir -p /ws2/src; cp -a /ws/src/mix_good /ws/src/py_srcnox /ws/src/py_files /ws2/src/
for p in mix_good py_srcnox py_files; do build /ws2 "--symlink-install" $p; done
for p in mix_good py_srcnox py_files; do
  echo "--- installed $p"
  for f in /ws2/install/$p/lib/$p/*; do [ -e "$f" ] || [ -L "$f" ]; stat -c '%A %N' "$f"; done
  find /ws2/install/$p -path '*-packages*' -maxdepth 6 -name $p -exec stat -c '%A %N' {} \; 2>/dev/null
done
(
  source /ws2/install/setup.bash
  for p in mix_good py_srcnox py_files; do runit "ws2 ros2 run $p talker.py" ros2 run $p talker.py; done
  sed -i 's/v1/v3/' /ws2/src/mix_good/mix_good/helper.py
  runit "ws2 ros2 run mix_good talker.py after editing helper.py, no rebuild" ros2 run mix_good talker.py
  echo "# fix py_srcnox in place: chmod +x on the source file"
  chmod 755 /ws2/src/py_srcnox/scripts/talker.py
  runit "ws2 ros2 run py_srcnox talker.py after chmod +x, no rebuild" ros2 run py_srcnox talker.py
)

echo "=== 7. fixes applied to the broken packages, rebuilt"
fix() { echo "# fix $1: $2"; }
fix py_noinstall "add install(PROGRAMS ... DESTINATION lib/\${PROJECT_NAME})"
sed -i 's|^ament_package()|install(PROGRAMS scripts/talker.py DESTINATION lib/${PROJECT_NAME})\nament_package()|' $S/py_noinstall/CMakeLists.txt
fix py_bin "DESTINATION bin -> lib/\${PROJECT_NAME}"
sed -i 's|DESTINATION bin|DESTINATION lib/${PROJECT_NAME}|' $S/py_bin/CMakeLists.txt
fix py_files "FILES -> PROGRAMS"
sed -i 's|install(FILES|install(PROGRAMS|' $S/py_files/CMakeLists.txt
fix py_noshebang "add #!/usr/bin/env python3 as line 1"
sed -i '1i #!/usr/bin/env python3' $S/py_noshebang/scripts/talker.py
fix py_crlf "strip CR (dos2unix equivalent)"
sed -i 's/\r$//' $S/py_crlf/scripts/talker.py
fix py_wrongshebang "#!/usr/bin/python -> #!/usr/bin/env python3"
sed -i '1s|.*|#!/usr/bin/env python3|' $S/py_wrongshebang/scripts/talker.py
fix py_nomodule "add ament_python_install_package(\${PROJECT_NAME})"
sed -i 's|^ament_package()|ament_python_install_package(${PROJECT_NAME})\nament_package()|' $S/py_nomodule/CMakeLists.txt
fix py_nofind "add find_package(ament_cmake_python REQUIRED)"
sed -i 's|^find_package(ament_cmake REQUIRED)|find_package(ament_cmake REQUIRED)\nfind_package(ament_cmake_python REQUIRED)|' $S/py_nofind/CMakeLists.txt
fix py_noinit "add an empty __init__.py"
touch $S/py_noinit/py_noinit/__init__.py
for p in py_noinstall py_bin py_files py_noshebang py_crlf py_wrongshebang py_nomodule py_nofind py_noinit; do
  build /ws "" $p
done
source /ws/install/setup.bash
for p in py_noinstall py_bin py_files py_noshebang py_crlf py_wrongshebang py_nomodule py_nofind py_noinit; do
  runit "after fix: ros2 run $p talker.py" ros2 run $p talker.py
done
echo "--- py_bin: stale copy left in install/py_bin/bin after the fix?"
ls -l /ws/install/py_bin/bin 2>&1
echo "=== done"
