#!/bin/bash
# Run inside ros:<distro>-ros-base as: bash /r/repro.sh
# Builds small ament_python packages with colcon and records what ros2 run /
# ros2 launch print, and where the console script actually lands.
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
. /etc/os-release; echo "os=$PRETTY_NAME"
python3 --version
python3 -c 'import setuptools; print("setuptools", setuptools.__version__)'
python3 -c 'import colcon_core; print("colcon-core", colcon_core.__version__)'
dpkg-query -W -f='${Package} ${Version}\n' python3-setuptools python3-colcon-core python3-colcon-ros ros-$ROS_DISTRO-ros2run ros-$ROS_DISTRO-launch-ros 2>/dev/null

# mkpkg <ws> <entry_points line or NONE> <cfg: full|none|install_only|dash>
mkpkg() {
  local ws=$1 entry=$2 cfg=$3 p=$1/src/my_pkg
  mkdir -p $p/my_pkg $p/resource; touch $p/resource/my_pkg $p/my_pkg/__init__.py
  cat > $p/package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>my_pkg</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<exec_depend>rclpy</exec_depend>
<export><build_type>ament_python</build_type></export></package>
X
  cat > $p/my_pkg/my_node.py <<'X'
def main():
    print('HELLO from my_node v1')
X
  if [ "$entry" = NONE ]; then EP=""; else EP="entry_points={'console_scripts': ['$entry']},"; fi
  cat > $p/setup.py <<X
from setuptools import setup
setup(
    name='my_pkg', version='0.0.0', packages=['my_pkg'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/my_pkg']),
                ('share/my_pkg', ['package.xml'])],
    install_requires=['setuptools'], zip_safe=True,
    $EP
)
X
  case $cfg in
    full) printf '[develop]\nscript_dir=$base/lib/my_pkg\n[install]\ninstall_scripts=$base/lib/my_pkg\n' > $p/setup.cfg ;;
    install_only) printf '[install]\ninstall_scripts=$base/lib/my_pkg\n' > $p/setup.cfg ;;
    dash) printf '[develop]\nscript-dir=$base/lib/my_pkg\n[install]\ninstall-scripts=$base/lib/my_pkg\n' > $p/setup.cfg ;;
    none) ;;
  esac
}
build() { (cd $1 && shift && colcon build "$@" 2>&1 | grep -v -E '^\s*$' | tail -25); }
where() { echo "--- find install -name my_node / talker:"; (cd $1 && find install \( -name my_node -o -name talker \) | sort); }
run() { echo "\$ ros2 run $*"; timeout 30 ros2 run "$@" 2>&1 | tail -6; echo "exit=${PIPESTATUS[0]}"; }
cat > /tmp/l.launch.py <<'X'
from launch import LaunchDescription
from launch_ros.actions import Node
def generate_launch_description():
    return LaunchDescription([Node(package='my_pkg', executable='my_node', output='screen')])
X
launch() { echo "\$ ros2 launch /tmp/l.launch.py"; timeout 30 ros2 launch /tmp/l.launch.py 2>&1 | grep -v -E '^\[INFO\] \[launch\]: (All log files|Default logging)' | tail -6; echo "exit=${PIPESTATUS[0]}"; }
fresh() { (source /opt/ros/$ROS_DISTRO/setup.bash; source $1/install/setup.bash; shift; "$@"); }

E='my_node = my_pkg.my_node:main'

echo; echo "##### CASE good: entry point + full setup.cfg, plain build"
W=/ws_good; mkpkg $W "$E" full; build $W; where $W
fresh $W run my_pkg my_node; fresh $W launch
fresh $W bash -c 'echo "\$ ros2 pkg executables my_pkg"; ros2 pkg executables my_pkg'
echo "--- head -1 of installed script:"; head -1 $W/install/my_pkg/lib/my_pkg/my_node

echo; echo "##### CASE a1: no entry_points at all"
W=/ws_a1; mkpkg $W NONE full; build $W; where $W
fresh $W run my_pkg my_node; fresh $W launch
echo "--- ls install/my_pkg/lib/my_pkg:"; ls $W/install/my_pkg/lib/my_pkg 2>&1

echo; echo "##### CASE a2: entry point with wrong module path (my_pkg.wrong_mod:main)"
W=/ws_a2; mkpkg $W 'my_node = my_pkg.wrong_mod:main' full; build $W; where $W
fresh $W run my_pkg my_node

echo; echo "##### CASE a3: entry point with wrong function name (my_pkg.my_node:mian)"
W=/ws_a3; mkpkg $W 'my_node = my_pkg.my_node:mian' full; build $W; where $W
fresh $W run my_pkg my_node

echo; echo "##### CASE a4: entry name differs from what is run (talker = ...)"
W=/ws_a4; mkpkg $W 'talker = my_pkg.my_node:main' full; build $W; where $W
fresh $W run my_pkg my_node; fresh $W launch
fresh $W bash -c 'echo "\$ ros2 pkg executables my_pkg"; ros2 pkg executables my_pkg'
fresh $W run my_pkg talker

echo; echo "##### CASE b1: no setup.cfg, plain build"
W=/ws_b1; mkpkg $W "$E" none; build $W; where $W
fresh $W run my_pkg my_node; fresh $W launch
fresh $W bash -c 'echo "\$ ros2 pkg executables my_pkg"; ros2 pkg executables my_pkg; echo "\$ which my_node"; which my_node; echo "\$ my_node"; my_node'

echo; echo "##### CASE b2: no setup.cfg, --symlink-install"
W=/ws_b2; mkpkg $W "$E" none; build $W --symlink-install; where $W
fresh $W run my_pkg my_node; fresh $W launch

echo; echo "##### CASE b3: setup.cfg with [install] only, --symlink-install"
W=/ws_b3; mkpkg $W "$E" install_only; build $W --symlink-install; where $W
fresh $W run my_pkg my_node
echo "##### CASE b3p: setup.cfg with [install] only, plain build"
W=/ws_b3p; mkpkg $W "$E" install_only; build $W; where $W
fresh $W run my_pkg my_node

echo; echo "##### CASE b4: setup.cfg with dash keys (script-dir / install-scripts), plain build"
W=/ws_b4; mkpkg $W "$E" dash; build $W; where $W
fresh $W run my_pkg my_node
echo "##### CASE b4s: dash keys, --symlink-install"
W=/ws_b4s; mkpkg $W "$E" dash; build $W --symlink-install; where $W
fresh $W run my_pkg my_node

echo; echo "##### CASE c1: built but install/setup.bash not sourced (new terminal)"
W=/ws_good
(source /opt/ros/$ROS_DISTRO/setup.bash; run my_pkg my_node; launch)
echo "##### CASE c2: workspace sourced, then a NEW package built (not re-sourced)"
W=/ws_c2; mkdir -p $W/src; mkpkg /ws_c2tmp "$E" full
( source /opt/ros/$ROS_DISTRO/setup.bash; source /ws_good/install/setup.bash
  mkdir -p $W/src; cp -r /ws_c2tmp/src/my_pkg $W/src/my_pkg
  sed -i 's/my_pkg/other_pkg/g' $W/src/my_pkg/package.xml $W/src/my_pkg/setup.py $W/src/my_pkg/setup.cfg
  mv $W/src/my_pkg/resource/my_pkg $W/src/my_pkg/resource/other_pkg; mv $W/src/my_pkg/my_pkg $W/src/my_pkg/other_pkg; mv $W/src/my_pkg $W/src/other_pkg
  build $W | tail -3
  echo "(shell sourced only /ws_good; other_pkg is in /ws_c2)"; run other_pkg my_node
  source $W/install/setup.bash; echo "(after sourcing /ws_c2/install/setup.bash)"; run other_pkg my_node )
echo "##### CASE c3: sourced shell, new entry point added to existing package, rebuild, NO re-source"
W=/ws_c3; mkpkg $W "$E" full; build $W >/dev/null
( source /opt/ros/$ROS_DISTRO/setup.bash; source $W/install/setup.bash
  sed -i "s/'$E'/'$E', 'my_node2 = my_pkg.my_node:main'/" $W/src/my_pkg/setup.py
  build $W | tail -2; run my_pkg my_node2 )

echo; echo "##### CASE d: package / executable name mix-ups"
W=/ws_good
fresh $W run my_node my_pkg
fresh $W run my_pkg my_node.py
fresh $W run my_pkg my_pkg
fresh $W run my-pkg my_node

echo; echo "##### CASE e: --symlink-install behaviour"
W=/ws_e; mkpkg $W "$E" full
echo "--- full build output with --symlink-install:"
(cd $W && colcon build --symlink-install 2>&1 | tail -30)
where $W
echo "--- commands colcon ran (log/latest_build/my_pkg/command.log):"; cut -c1-1200 $W/log/latest_build/my_pkg/command.log | sed "s|PYTHONPATH=[^ ]* ||"
echo "--- ls -l install/my_pkg/lib/my_pkg/my_node:"; ls -l $W/install/my_pkg/lib/my_pkg/my_node
echo "--- what is in install/my_pkg/lib/python3*/site-packages:"; ls -la $W/install/my_pkg/lib/python3*/site-packages/ 2>&1
fresh $W run my_pkg my_node
echo "--- e1: edit my_node.py (v1 -> v2), NO rebuild"
sed -i 's/v1/v2/' $W/src/my_pkg/my_pkg/my_node.py; fresh $W run my_pkg my_node
echo "--- e2: add entry point my_node2 in setup.py, NO rebuild"
sed -i "s/'$E'/'$E', 'my_node2 = my_pkg.my_node:main'/" $W/src/my_pkg/setup.py
fresh $W run my_pkg my_node2
echo "--- e3: rebuild with --symlink-install"; build $W --symlink-install | tail -3
fresh $W run my_pkg my_node2
echo "--- e4: same edit test WITHOUT --symlink-install"
W=/ws_e4; mkpkg $W "$E" full; build $W >/dev/null
sed -i 's/v1/v2/' $W/src/my_pkg/my_pkg/my_node.py; fresh $W run my_pkg my_node
echo "--- e5: plain build output (stderr warnings):"
(cd $W && colcon build 2>&1 | tail -20)
fresh $W run my_pkg my_node
echo "--- e6: plain build after a --symlink-install build in same workspace"
(cd /ws_e && colcon build 2>&1 | tail -15)

echo; echo "##### CASE e7: newer setuptools (>=80, from pip) put in front via PYTHONPATH, then colcon"
command -v pip3 >/dev/null || { apt-get update -qq >/dev/null 2>&1; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip >/dev/null 2>&1; }
pip3 install -q --target /st "setuptools>=80" "packaging>=24.2" 2>&1 | tail -3
export PYTHONPATH=/st:$PYTHONPATH
python3 -c 'import packaging; print("now packaging", packaging.__version__)'; python3 -c 'import setuptools; print("now setuptools", setuptools.__version__, setuptools.__file__)'
W=/ws_e7; mkpkg $W "$E" full
echo "--- e7 plain build:"; (cd $W && colcon build 2>&1 | tail -20)
where $W; fresh $W run my_pkg my_node
rm -rf $W/build $W/install $W/log
echo "--- e7 --symlink-install build:"; (cd $W && colcon build --symlink-install 2>&1 | tail -30)
where $W; fresh $W run my_pkg my_node
echo "--- e7 commands colcon ran:"; cut -c1-1200 $W/log/latest_build/my_pkg/command.log | sed "s|PYTHONPATH=[^ ]* ||"
echo "--- e7 site-packages:"; ls -la $W/install/my_pkg/lib/python3*/site-packages/ $W/install/my_pkg/lib/python3*/site-packages/my_pkg 2>&1
echo "--- e7 colcon log lines about --editable:"; grep -h -i "editable" $W/log/latest_build/logger_all.log | cut -c1-300
echo "--- e7 edit v1->v2 no rebuild:"; sed -i 's/v1/v2/' $W/src/my_pkg/my_pkg/my_node.py; fresh $W run my_pkg my_node

echo; echo "##### CASE e8: workspace built with --symlink-install under apt setuptools, then rebuilt under setuptools>=80"
W=/ws_e8; mkpkg $W "$E" full
(export PYTHONPATH=${PYTHONPATH#/st:}; cd $W && colcon build --symlink-install 2>&1 | tail -3)
python3 -c 'import setuptools; print("rebuild with setuptools", setuptools.__version__)'
echo "--- e8 rebuild --symlink-install:"; (cd $W && colcon build --symlink-install 2>&1 | tail -25)
where $W; fresh $W run my_pkg my_node
echo "--- e8 rebuild plain:"; (cd $W && colcon build 2>&1 | tail -25)
where $W; fresh $W run my_pkg my_node
echo "--- e8 fix: rm -rf build install log, rebuild:"; rm -rf $W/build $W/install $W/log; (cd $W && colcon build --symlink-install 2>&1 | tail -3)
where $W; fresh $W run my_pkg my_node
echo "=== done"
