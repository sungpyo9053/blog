#!/bin/bash
# Reproduces "CMakeCache.txt directory ... is different than the directory ..." with colcon.
# Usage inside ros:<distro>-ros-base:
#   bash repro.sh main            # all in-container tests (mv, cp -r, symlink-install, fixes)
#   bash repro.sh volbuild <dir>  # build the workspace mounted at <dir> (host-side volume test)
# Workspace: cpkg_a, cpkg_b (ament_cmake, plain C++ hello, no deps), ppkg (ament_python, console script).
#   bash repro.sh host <distro>   # ON THE DOCKER HOST: runs everything below for ros:<distro>-ros-base
if [ "$1" = host ]; then
  D=$2; I=ros:$D-ros-base; H=$(cd "$(dirname "$0")" && pwd)
  R="docker run --rm --pids-limit 40 --cpus 1.5 --ulimit core=0 -v $H/repro.sh:/repro.sh:ro"
  $R --name cmc-$D $I bash /repro.sh main
  echo; echo "##### T5 bind mount: same host dir mounted at /ws_a, then at /ws_b"
  V=$H/vol-$D; rm -rf $V; mkdir -p $V
  $R --name cmc-$D-va -v $V:/ws_a $I bash /repro.sh volbuild /ws_a
  $R --name cmc-$D-vb -v $V:/ws_b $I bash /repro.sh volbuild /ws_b
  $R --name cmc-$D-va2 -v $V:/ws_a $I bash /repro.sh volbuild /ws_a
  echo; echo "##### T6 named volume cmc-vol-$D: mounted at /ws_a, then at /ws_b"
  docker volume create cmc-vol-$D >/dev/null
  $R --name cmc-$D-na -v cmc-vol-$D:/ws_a $I bash /repro.sh volbuild /ws_a
  $R --name cmc-$D-nb -v cmc-vol-$D:/ws_b $I bash /repro.sh volbuild /ws_b
  docker volume rm cmc-vol-$D >/dev/null
  docker run --rm -v $H:/h $I rm -rf /h/vol-$D   # files are root-owned
  exit 0
fi
source /opt/ros/$ROS_DISTRO/setup.bash
TIMEFORMAT='TIME %R s'
B="colcon build --event-handlers console_direct-"

mkws() {  # mkws <dir>
  local W=$1; mkdir -p $W/src
  for p in cpkg_a cpkg_b; do
    mkdir -p $W/src/$p/src
    cat > $W/src/$p/package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>$p</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
    cat > $W/src/$p/CMakeLists.txt <<X
cmake_minimum_required(VERSION 3.8)
project($p)
find_package(ament_cmake REQUIRED)
add_executable(hello src/hello.cpp)
install(TARGETS hello DESTINATION lib/\${PROJECT_NAME})
ament_package()
X
    echo "#include <cstdio>
int main(){std::puts(\"hello from $p\");}" > $W/src/$p/src/hello.cpp
  done
  local P=$W/src/ppkg; mkdir -p $P/ppkg $P/resource; touch $P/ppkg/__init__.py $P/resource/ppkg
  echo 'def main(): print("hello from ppkg")' > $P/ppkg/hello.py
  cat > $P/package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>ppkg</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<export><build_type>ament_python</build_type></export></package>
X
  cat > $P/setup.py <<'X'
from setuptools import setup
setup(name='ppkg', version='0.0.0', packages=['ppkg'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/ppkg']),
                  ('share/ppkg', ['package.xml'])],
      entry_points={'console_scripts': ['hello = ppkg.hello:main']})
X
  printf '[develop]\nscript_dir=$base/lib/ppkg\n[install]\ninstall_scripts=$base/lib/ppkg\n' > $P/setup.cfg
}

b() {  # b <label> <colcon args...>
  echo "--- $1"; shift
  local s=$(date +%s.%N)
  $B "$@" > /tmp/b.log 2>&1; local rc=$?
  local e=$(date +%s.%N)
  echo "exit=$rc time=$(awk "BEGIN{printf \"%.1f\", $e - $s}") s"
  grep -E "CMake Error|is different than|binaries being created|Failed   <<<|Finished <<<|Aborted  <<<|Summary:|packages (finished|failed|aborted)|error|Error" /tmp/b.log | grep -v '^$' | head -25
}
runall() {  # runall <setup.bash>
  echo "--- source $1 then ros2 run (fresh shell)"
  bash -c "source $1 >/dev/null 2>&1; echo \"source_rc=\$?\"; ros2 run cpkg_a hello 2>&1 | head -5; echo rc=\${PIPESTATUS[0]}; ros2 run ppkg hello 2>&1 | tail -5; echo rc=\${PIPESTATUS[0]}; echo prefix_cpkg_a=\$(ros2 pkg prefix cpkg_a 2>&1); echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH"
  bash -c "source $1 2>&1 | head -3"
}

if [ "$1" = volbuild ]; then
  echo "=== volbuild in $2 distro=$ROS_DISTRO"
  [ -d $2/src ] || mkws $2
  cd $2; b "colcon build in $2"
  sed -n '/CMake Error/,/^$/p' /tmp/b.log | head -12
  exit 0
fi

echo "=== distro=$ROS_DISTRO nproc=$(nproc)"
cmake --version | head -1
dpkg-query -W -f='${Package} ${Version}\n' 'python3-colcon-core' 'python3-colcon-cmake' 'python3-colcon-ros' 'python3-colcon-python-setup-py' "ros-$ROS_DISTRO-ament-cmake" 2>/dev/null
python3 -c "import colcon_core,colcon_cmake; print('colcon_core', colcon_core.__version__); import importlib.metadata as m; print('colcon-cmake', m.version('colcon-cmake'))" 2>&1

echo; echo "##### T1 clean build at /ws_a, no-op rebuild, then mv /ws_a /ws_b"
mkws /ws_a; cd /ws_a
b "clean build /ws_a"
b "no-op rebuild /ws_a (nothing changed)"
touch src/cpkg_a/src/hello.cpp; b "rebuild /ws_a after touching cpkg_a/src/hello.cpp"
runall /ws_a/install/setup.bash
tar -C / -cf /tmp/ws_a_built.tar ws_a
cd /; mv /ws_a /ws_b
echo "--- after mv, before rebuild: grep for /ws_a in install/ setup files"
grep -rl "/ws_a" /ws_b/install --include='*.sh' --include='*.bash' --include='*.dsv' --include='*.ps1' 2>/dev/null | head; echo "count=$(grep -rl /ws_a /ws_b/install 2>/dev/null | wc -l) files under install/ mention /ws_a"
echo "--- source old path /ws_a/install/setup.bash (dir no longer exists)"
bash -c 'source /ws_a/install/setup.bash; echo source_rc=$?' 2>&1
runall /ws_b/install/setup.bash
cd /ws_b
b "colcon build in /ws_b after mv"
echo "--- full CMake error block:"
sed -n '/CMake Error/,/^$/p' /tmp/b.log | head -15
echo "--- colcon log lines:"; grep -E "^(Starting|Finished|Failed|Aborted)|Summary|packages" /tmp/b.log
b "second colcon build in /ws_b (does it repeat?)"
b "colcon build --packages-select ppkg (ament_python only) in /ws_b" --packages-select ppkg
b "colcon build --continue-on-error in /ws_b" --continue-on-error
grep -E "^(Starting|Finished|Failed|Aborted)|Summary|packages" /tmp/b.log

echo; echo "##### T2 cp -r /ws_a /ws_c"
rm -rf /ws_a /ws_b /ws_c; tar -C / -xf /tmp/ws_a_built.tar
cp -r /ws_a /ws_c; cd /ws_c
b "colcon build in /ws_c (copy)"
sed -n '/CMake Error/,/^$/p' /tmp/b.log | head -8
echo "--- where does the copy point? CMakeCache.txt in /ws_c:"
grep -E "^(CMAKE_CACHEFILE_DIR|CMAKE_HOME_DIRECTORY|cpkg_a_SOURCE_DIR|cpkg_a_BINARY_DIR|CMAKE_INSTALL_PREFIX)" /ws_c/build/cpkg_a/CMakeCache.txt
echo "--- edit the copy's source only, rebuild the copy, run both installs"
sed -i 's/hello from cpkg_a/hello from EDITED COPY/' /ws_c/src/cpkg_a/src/hello.cpp
b "colcon build in /ws_c after editing /ws_c/src/cpkg_a"
echo "/ws_c/install hello: $(/ws_c/install/cpkg_a/lib/cpkg_a/hello)"
echo "/ws_a/install hello: $(/ws_a/install/cpkg_a/lib/cpkg_a/hello)"
echo "/ws_c/build hello:   $(/ws_c/build/cpkg_a/hello 2>&1)"
echo "/ws_a/build hello:   $(/ws_a/build/cpkg_a/hello 2>&1)"
runall /ws_c/install/setup.bash
echo "--- delete /ws_a after copying, then build /ws_c again"
rm -rf /ws_a; cd /ws_c; b "colcon build in /ws_c after rm -rf /ws_a"
cd /; rm -rf /ws_c; tar -C / -xf /tmp/ws_a_built.tar; cp -r /ws_a /ws_c
cd /ws_a; b "colcon build in original /ws_a after copy"

echo; echo "##### T3 fixes (each starts from the built /ws_a moved to /ws_b)"
fix() {  # fix <label> <shell cmd>
  rm -rf /ws_a /ws_b /ws_c; tar -C / -xf /tmp/ws_a_built.tar; mv /ws_a /ws_b; cd /ws_b
  echo "--- FIX: $1"; echo "cmd: $2"
  local s=$(date +%s.%N)
  bash -c "source /opt/ros/$ROS_DISTRO/setup.bash; $2" > /tmp/b.log 2>&1; local rc=$?
  local e=$(date +%s.%N)
  echo "exit=$rc time=$(awk "BEGIN{printf \"%.1f\", $e - $s}") s"
  grep -E "is different than|Finished <<<|Failed   <<<|Aborted  <<<|Summary:|packages (finished|failed|aborted)" /tmp/b.log | head -10
  echo "after fix, plain colcon build:"; b "  follow-up build"
  runall /ws_b/install/setup.bash
}
fix "rm -rf build install log" "rm -rf build install log && $B"
fix "--cmake-clean-cache" "$B --cmake-clean-cache"
fix "--cmake-clean-first" "$B --cmake-clean-first"
fix "rm -rf build only (keep install)" "rm -rf build && $B"
fix "rm -rf build/cpkg_a only" "rm -rf build/cpkg_a && $B"
fix "rm -rf build/cpkg_a build/cpkg_b" "rm -rf build/cpkg_a build/cpkg_b && $B"
fix "rm -rf build/cpkg_a + --packages-select cpkg_a" "rm -rf build/cpkg_a && $B --packages-select cpkg_a"
fix "--packages-select cpkg_a --cmake-clean-cache" "$B --packages-select cpkg_a --cmake-clean-cache"

echo; echo "##### T4 --symlink-install"
rm -rf /ws_a /ws_b /ws_c; mkws /ws_a; cd /ws_a
b "clean build /ws_a --symlink-install" --symlink-install
echo "--- symlinks in install/ pointing into /ws_a: $(find install -type l -lname '/ws_a/*' | wc -l)"
find install -type l -lname '/ws_a/*' | head -4 | while read l; do echo "$l -> $(readlink $l)"; done
find install build -name '*.egg-link' -o -name '*.pth' | grep -i ppkg | while read f; do echo "$f: $(head -1 $f)"; done
runall /ws_a/install/setup.bash
cd /; mv /ws_a /ws_b; cd /ws_b
echo "--- after mv: broken symlinks in install/: $(find install -xtype l | wc -l)"
find install -xtype l | head -4 | while read l; do echo "$l -> $(readlink $l)"; done
runall /ws_b/install/setup.bash
b "colcon build --symlink-install in /ws_b after mv" --symlink-install
sed -n '/CMake Error/,/^$/p' /tmp/b.log | head -4
b "colcon build --symlink-install --packages-select ppkg in /ws_b" --symlink-install --packages-select ppkg
runall /ws_b/install/setup.bash
echo "--- fix: rm -rf build install log && --symlink-install"
rm -rf build install log; b "rebuild" --symlink-install
echo "broken symlinks now: $(find install -xtype l | wc -l); links into /ws_a: $(find install -type l -lname '/ws_a/*' | wc -l)"
runall /ws_b/install/setup.bash
echo "=== done"
