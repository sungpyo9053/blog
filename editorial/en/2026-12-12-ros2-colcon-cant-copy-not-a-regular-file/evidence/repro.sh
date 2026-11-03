#!/bin/bash
# Run inside ros:<distro>-ros-base. Reproduces colcon build
#   "error: can't copy '...': doesn't exist or not a regular file"   (ament_python)
#   "failed to create symbolic link ... existing path cannot be removed: Is a directory" (ament_cmake)
# with one workspace per cause, then compares fixes.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-ament-cmake-core ros-$ROS_DISTRO-ament-cmake-python 2>/dev/null
python3 -c "import setuptools,colcon_core;print('setuptools',setuptools.__version__,'colcon-core',colcon_core.__version__)"
dpkg-query -W -f='${Package} ${Version}\n' python3-colcon-ros python3-colcon-python-setup-py cmake 2>/dev/null
python3 --version

ms() { echo $(( ($(date +%s%N) - T0) / 1000000 )); }
# b <label> <colcon args...>  : run a build in the current ws, print exit, time, error lines
b() { local l=$1; shift; T0=$(date +%s%N); timeout 300 colcon build "$@" > /tmp/b.log 2>&1; local rc=$?
  echo "  [$l] colcon build $* -> exit=$rc elapsed_ms=$(ms)"
  grep -E "error|Error|failed|Failed|Is a directory|regular file|Summary|finished|symbolic" /tmp/b.log | grep -v "^\s*$" | sort -u | head -14 | sed 's/^/      /'; }
lsl() { echo "  ls $1:"; ( cd "$1" 2>/dev/null && find . -mindepth 1 | sort | while read f; do if [ -L "$f" ]; then t=symlink; [ -e "$f" ] || t=DANGLING-symlink; elif [ -d "$f" ]; then t=dir; else t=file; fi; echo "      $f ($t)"; done ) || echo "      (missing)"; }

mkpy() { # mkpy <ws> <data_files python expr lines>
  local ws=$1; shift; mkdir -p $ws/src/py_pkg/py_pkg $ws/src/py_pkg/resource $ws/src/py_pkg/launch
  touch $ws/src/py_pkg/py_pkg/__init__.py $ws/src/py_pkg/resource/py_pkg
  cat > $ws/src/py_pkg/package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>py_pkg</name><version>0.0.0</version><description>d</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<export><build_type>ament_python</build_type></export></package>
X
  printf '[develop]\nscript_dir=$base/lib/py_pkg\n[install]\ninstall_scripts=$base/lib/py_pkg\n' > $ws/src/py_pkg/setup.cfg
  for f in a b; do echo "from launch import LaunchDescription
def generate_launch_description():
    return LaunchDescription([])" > $ws/src/py_pkg/launch/$f.launch.py; done
  { echo "import os"; echo "from glob import glob"; echo "from setuptools import setup"; echo "pn='py_pkg'"
    echo "def tree(src, dst):"
    echo "    out = []"
    echo "    for d, _, fs in os.walk(src):"
    echo "        out.append((os.path.join(dst, d), [os.path.join(d, f) for f in fs]))"
    echo "    return out"
    echo "setup(name=pn, version='0.0.0', packages=[pn], data_files=["
    echo "  ('share/ament_index/resource_index/packages', ['resource/' + pn]),"
    echo "  ('share/' + pn, ['package.xml']),"
    for l in "$@"; do echo "  $l"; done
    echo "], install_requires=['setuptools'], zip_safe=True)"; } > $ws/src/py_pkg/setup.py
}

echo "===== P0 baseline: glob('launch/*.launch.py')"
rm -rf /w0; mkpy /w0 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w0
b plain; b symlink --symlink-install; lsl install/py_pkg/share/py_pkg/launch

echo "===== P1 explicit path that does not exist (typo)"
rm -rf /w1; mkpy /w1 "('share/' + pn + '/worlds', ['worlds/my_world.wbt']),"; cd /w1; b plain
mkdir -p src/py_pkg/worlds; touch src/py_pkg/worlds/my_world.wbt
sed -i "s#\['worlds/my_world.wbt'\]#['my_world.wbt']#" src/py_pkg/setup.py; echo "  (file exists in worlds/, listed without the folder)"; b plain
sed -i "s#\['my_world.wbt'\]#['worlds/my_world.wbt']#" src/py_pkg/setup.py; echo "  (listed as worlds/my_world.wbt)"; b plain
echo "  (path written with ~)"; sed -i "s#\['worlds/my_world.wbt'\]#['~/my_world.wbt']#" src/py_pkg/setup.py; b plain

echo "===== P2 directory in the file list"
rm -rf /w2; mkpy /w2 "('share/' + pn + '/models', glob('models/**', recursive=True)),"; cd /w2
mkdir -p src/py_pkg/models/robot/meshes; echo m > src/py_pkg/models/robot/model.sdf; echo m > src/py_pkg/models/robot/meshes/base.dae
echo "  glob('models/**', recursive=True) gives: $(cd src/py_pkg && python3 -c "from glob import glob;print(glob('models/**', recursive=True))")"
b plain
echo "  -- glob('launch/*') with a subfolder launch/include"
rm -rf /w2b; mkpy /w2b "('share/' + pn + '/launch', glob('launch/*')),"; mkdir -p /w2b/src/py_pkg/launch/include; cd /w2b; b plain; b symlink --symlink-install
echo "  -- fix A: glob('models/**', recursive=True) filtered with os.path.isfile (flattens)"
cd /w2; sed -i "s#glob('models/\*\*', recursive=True)#[f for f in glob('models/**', recursive=True) if os.path.isfile(f)]#" src/py_pkg/setup.py; rm -rf build install log; b plain; lsl install/py_pkg/share/py_pkg/models
echo "  -- fix B: one entry per folder with os.walk (keeps the tree)"
rm -rf /w2c; mkpy /w2c "*tree('models', 'share/' + pn),"; cp -r /w2/src/py_pkg/models /w2c/src/py_pkg/; cd /w2c; b plain; lsl install/py_pkg/share/py_pkg/models
rm -rf build install log; b symlink --symlink-install; lsl install/py_pkg/share/py_pkg/models
echo "  -- empty folder in the tree with fix B"; mkdir -p src/py_pkg/models/empty; rm -rf build install log; b plain; lsl install/py_pkg/share/py_pkg/models

echo "===== P3 delete / rename a file after a --symlink-install build"
for mode in delete rename; do
 for second in symlink plain; do
  rm -rf /w3; mkpy /w3 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w3
  b first-symlink --symlink-install >/dev/null
  if [ $mode = delete ]; then rm src/py_pkg/launch/b.launch.py; else mv src/py_pkg/launch/b.launch.py src/py_pkg/launch/c.launch.py; fi
  echo "  --- $mode b.launch.py, then $second build"
  lsl build/py_pkg/launch
  if [ $second = symlink ]; then b second --symlink-install; else b second; fi
  echo "    glob('launch/*.launch.py') run in build/py_pkg: $(cd build/py_pkg && python3 -c "from glob import glob;print(sorted(glob('launch/*.launch.py')))")"
  lsl install/py_pkg/share/py_pkg/launch
 done
done
echo "  --- same delete after a PLAIN first build, plain rebuild"
rm -rf /w3; mkpy /w3 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w3; b first-plain >/dev/null; rm src/py_pkg/launch/b.launch.py; b second; lsl install/py_pkg/share/py_pkg/launch
echo "  --- explicit list (no glob): delete b and remove it from setup.py, symlink rebuild"
rm -rf /w3; mkpy /w3 "('share/' + pn + '/launch', ['launch/a.launch.py', 'launch/b.launch.py']),"; cd /w3; b first-symlink --symlink-install >/dev/null
rm src/py_pkg/launch/b.launch.py; sed -i "s#, 'launch/b.launch.py'##" src/py_pkg/setup.py; b second --symlink-install; lsl install/py_pkg/share/py_pkg/launch
echo "  --- deleted python module (not a data file) after symlink build"
rm -rf /w3; mkpy /w3 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w3; echo x=1 > src/py_pkg/py_pkg/old_mod.py; b first-symlink --symlink-install >/dev/null
rm src/py_pkg/py_pkg/old_mod.py; b second --symlink-install

echo "===== P3 fixes compared (delete b, then each fix, then --symlink-install)"
for fix in none rm_build_pkg rm_build_install_pkg find_xtype_delete clean_all; do
  rm -rf /w3; mkpy /w3 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w3
  b first --symlink-install >/dev/null; rm src/py_pkg/launch/b.launch.py
  echo "  --- fix=$fix"
  case $fix in
    rm_build_pkg) rm -rf build/py_pkg;;
    rm_build_install_pkg) rm -rf build/py_pkg install/py_pkg;;
    find_xtype_delete) find build/py_pkg -xtype l -print -delete | sed 's/^/      deleted: /';;
    clean_all) rm -rf build install log;;
  esac
  b after-fix --symlink-install; lsl install/py_pkg/share/py_pkg/launch
  if [ $fix = rm_build_pkg ]; then source install/setup.bash
    echo "    ros2 launch py_pkg b.launch.py with the dangling install link:"; timeout 30 ros2 launch py_pkg b.launch.py 2>&1 | tail -3 | sed 's/^/      /'
    echo "    ros2 launch py_pkg a.launch.py:"; timeout 30 ros2 launch py_pkg a.launch.py 2>&1 | tail -2 | sed 's/^/      /'; fi
done

echo "===== P4 ament_cmake + ament_cmake_python: switch plain <-> --symlink-install"
mkcm() { local ws=$1; mkdir -p $ws/src/cm_pkg/cm_pkg $ws/src/cm_pkg/launch $ws/src/cm_pkg/scripts
  echo "x=1" > $ws/src/cm_pkg/cm_pkg/__init__.py; echo "# launch" > $ws/src/cm_pkg/launch/a.launch.py
  printf '#!/usr/bin/env python3\nprint("hi")\n' > $ws/src/cm_pkg/scripts/tool.py; chmod +x $ws/src/cm_pkg/scripts/tool.py
  cat > $ws/src/cm_pkg/package.xml <<'X'
<?xml version="1.0"?>
<package format="3"><name>cm_pkg</name><version>0.0.0</version><description>d</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><buildtool_depend>ament_cmake_python</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > $ws/src/cm_pkg/CMakeLists.txt <<'X'
cmake_minimum_required(VERSION 3.8)
project(cm_pkg)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS scripts/tool.py DESTINATION lib/${PROJECT_NAME})
ament_package()
X
}
srcsum() { echo "    src check: $(cd /w4/src/cm_pkg && for f in cm_pkg/__init__.py launch/a.launch.py scripts/tool.py; do [ -L $f ] && echo "$f=SYMLINK" || echo "$f=$(head -c 20 $f | tr '\n' ' ')"; done)"; }
echo "  --- plain first, then --symlink-install"
rm -rf /w4; mkcm /w4; cd /w4; b first-plain; b second --symlink-install; srcsum
cp /tmp/b.log /tmp/p4.log; grep -n -B2 -A3 "Is a directory" /tmp/p4.log | head -20 | sed 's/^/      LOG /'
echo "    build/cm_pkg/ament_cmake_python/cm_pkg/cm_pkg: $(ls -ld build/cm_pkg/ament_cmake_python/cm_pkg/cm_pkg 2>&1 | cut -c1-11)"
echo "  --- fixes for plain->symlink"
for fix in none cmake_clean_cache cmake_clean_first rm_build_pkg rm_ament_cmake_python_dir; do
  rm -rf /w4; mkcm /w4; cd /w4; b first-plain >/dev/null
  case $fix in
    none) b fix-none --symlink-install;;
    cmake_clean_cache) b fix-cmake-clean-cache --symlink-install --cmake-clean-cache;;
    cmake_clean_first) b fix-cmake-clean-first --symlink-install --cmake-clean-first;;
    rm_build_pkg) rm -rf build/cm_pkg; b fix-rm-build-pkg --symlink-install;;
    rm_ament_cmake_python_dir) rm -rf build/cm_pkg/ament_cmake_python; b fix-rm-ament_cmake_python --symlink-install;;
  esac
  [ $fix != none ] && { srcsum; echo "    installed cm_pkg python: $(ls -ld install/cm_pkg/local/lib/python3*/dist-packages/cm_pkg install/cm_pkg/lib/python3*/site-packages/cm_pkg 2>/dev/null | cut -c1-11 | tr '\n' ' ')"; }
done
echo "  --- symlink first, then plain"
rm -rf /w4; mkcm /w4; cd /w4; b first-symlink --symlink-install; b second-plain; srcsum
echo "    install launch: $(ls -l install/cm_pkg/share/cm_pkg/launch/ | tail -n +2 | cut -c1-1 | tr '\n' ' ')"
echo "  --- symlink first, then plain, then symlink again"; b third --symlink-install; srcsum
echo "  --- ament_python: plain first, then --symlink-install (and back)"
rm -rf /w0; mkpy /w0 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w0; b first-plain >/dev/null; b second --symlink-install; b third-plain

echo "===== P5 timing: fresh symlink build, no-op rebuild, rebuild after rm build/pkg (py_pkg, 3x)"
for i in 1 2 3; do rm -rf /w5; mkpy /w5 "('share/' + pn + '/launch', glob('launch/*.launch.py')),"; cd /w5
  b t$i-fresh --symlink-install | head -1; b t$i-noop --symlink-install | head -1; rm -rf build/py_pkg; b t$i-after-rm-build --symlink-install | head -1; done
echo "===== P6 ament_cmake_python: does a source edit show up without rebuilding?"
for seq in fresh-symlink plain-then-symlink plain-then-rm-build-then-symlink; do
  rm -rf /w4; mkcm /w4; cd /w4
  case $seq in
    fresh-symlink) b s1 --symlink-install | head -1;;
    plain-then-symlink) b s1 | head -1; b s2 --symlink-install | head -1;;
    plain-then-rm-build-then-symlink) b s1 | head -1; rm -rf build/cm_pkg; b s2 --symlink-install | head -1;;
  esac
  echo "  --- $seq"
  echo "    build/cm_pkg/ament_cmake_python/cm_pkg/cm_pkg is: $( [ -L build/cm_pkg/ament_cmake_python/cm_pkg/cm_pkg ] && echo symlink || echo directory)"
  i=$(ls install/cm_pkg/local/lib/python3*/dist-packages/cm_pkg/__init__.py install/cm_pkg/lib/python3*/site-packages/cm_pkg/__init__.py 2>/dev/null | head -1)
  echo "    installed __init__.py resolves to: $(readlink -f $i)"
  echo "x=2" > src/cm_pkg/cm_pkg/__init__.py
  ( source install/setup.bash; echo "    after editing src to x=2, no rebuild: import gives x=$(python3 -c 'import cm_pkg;print(cm_pkg.x)' 2>&1 | tail -1)" )
done
echo "=== done"
