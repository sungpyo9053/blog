#!/bin/bash
# Run inside ros:<distro>-ros-base as root. Reproduces colcon's
# "ignoring unknown package '...' in --packages-select" warning and related selection cases.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation 2>/dev/null
python3 - <<'P'
from importlib.metadata import distributions
for d in sorted(distributions(), key=lambda d: d.metadata['Name'].lower()):
    n = d.metadata['Name']
    if n.lower().startswith('colcon'): print(n, d.version)
P
echo "rmw default: ${RMW_IMPLEMENTATION:-unset}"

mkpkg_cmake() { # dir name
  mkdir -p "$1"
  cat > "$1/package.xml" <<X
<?xml version="1.0"?>
<package format="3"><name>$2</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
X
  cat > "$1/CMakeLists.txt" <<X
cmake_minimum_required(VERSION 3.8)
project($2)
find_package(ament_cmake REQUIRED)
ament_package()
X
}
mkpkg_py() { # dir name
  mkdir -p "$1/$2" "$1/resource"
  touch "$1/$2/__init__.py" "$1/resource/$2"
  cat > "$1/package.xml" <<X
<?xml version="1.0"?>
<package format="3"><name>$2</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<export><build_type>ament_python</build_type></export></package>
X
  cat > "$1/setup.py" <<X
from setuptools import setup
setup(name='$2', version='0.0.0', packages=['$2'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/$2']), ('share/$2', ['package.xml'])])
X
  printf '[develop]\nscript_dir=$base/lib/%s\n[install]\ninstall_scripts=$base/lib/%s\n' "$2" "$2" > "$1/setup.cfg"
}

W=/ws; rm -rf $W; mkdir -p $W/src; cd $W
mkpkg_cmake src/pkg_a pkg_a
mkpkg_py src/my_py_pkg my_py_pkg
mkpkg_cmake src/folder_name real_name           # folder differs from <name>
mkpkg_cmake src/ignored/pkg_ign pkg_ign; touch src/ignored/COLCON_IGNORE
mkpkg_py src/py_nosetup py_nosetup; rm src/py_nosetup/setup.py
mkpkg_cmake src/bad_xml bad_xml; sed -i 's#</name>#</nam>#' src/bad_xml/package.xml
mkdir -p src/plain_cmake; printf 'cmake_minimum_required(VERSION 3.8)\nproject(plain_proj NONE)\n' > src/plain_cmake/CMakeLists.txt  # no package.xml
mkpkg_cmake src/outer outer; mkpkg_cmake src/outer/inner_pkg inner_pkg  # nested in a package
mkpkg_cmake src/.hidden/pkg_hid pkg_hid
mkpkg_cmake /elsewhere/pkg_link pkg_link; ln -s /elsewhere/pkg_link src/pkg_link
mkpkg_cmake /ws2/src/other_ws_pkg other_ws_pkg

echo "=== colcon list (names, paths, types)"
colcon list 2>&1; echo "exit=$?"

run() { # label dir cmd...
  local label=$1 dir=$2; shift 2
  rm -rf $W/build $W/install $W/log /tmp/empty/build /tmp/empty/install /tmp/empty/log $W/src/build $W/src/install $W/src/log $W/src/pkg_a/build $W/src/pkg_a/install $W/src/pkg_a/log
  echo; echo "### CASE $label"; echo "cwd=$dir"; echo "cmd=$*"
  local t0=$(date +%s.%N)
  ( cd $dir && timeout 120 "$@" ) > /tmp/case.out 2>&1; local rc=$?
  local t1=$(date +%s.%N)
  cat /tmp/case.out
  echo "exit=$rc seconds=$(python3 -c "print(round($t1-$t0,3))")"
  for b in $dir/install; do [ -d $b ] && echo "installed: $(ls $b | grep -v -e '\.sh$' -e '\.bash$' -e '\.zsh$' -e '\.ps1$' -e '\.py$' -e '\.dsv$' -e COLCON_IGNORE | tr '\n' ' ')" || echo "installed: (no install dir)"; done
  [ -e $dir/install/pkg_a/share/pkg_a/package.xml ] && { [ -L $dir/install/pkg_a/share/pkg_a/package.xml ] && echo "pkg_a package.xml in install: symlink" || echo "pkg_a package.xml in install: regular file"; }
  [ -f $dir/log/latest_build/logger_all.log ] && echo "logger_all.log lines with 'unknown package': $(grep -c 'unknown package' $dir/log/latest_build/logger_all.log)"
}
mkdir -p /tmp/empty
run correct           $W colcon build --packages-select pkg_a
run typo              $W colcon build --packages-select pkg_aa
run dash              $W colcon build --packages-select my-py-pkg
run uppercase         $W colcon build --packages-select Pkg_A
run folder_name       $W colcon build --packages-select folder_name
run real_name         $W colcon build --packages-select real_name
run colcon_ignore     $W colcon build --packages-select pkg_ign
run py_no_setup       $W colcon build --packages-select py_nosetup
run bad_xml           $W colcon build --packages-select bad_xml
run plain_cmake_dir   $W colcon build --packages-select plain_cmake
run plain_cmake_proj  $W colcon build --packages-select plain_proj
run nested_inner      $W colcon build --packages-select inner_pkg
run nested_outer      $W colcon build --packages-select outer
run hidden_dir        $W colcon build --packages-select pkg_hid
run symlink_dir       $W colcon build --packages-select pkg_link
run other_workspace   $W colcon build --packages-select other_ws_pkg
run wrong_cwd_empty   /tmp/empty colcon build --packages-select pkg_a
run cwd_src           $W/src colcon build --packages-select pkg_a
run cwd_pkg           $W/src/pkg_a colcon build --packages-select pkg_a
run base_paths_wrong  $W colcon build --base-paths /ws2 --packages-select pkg_a
run base_paths_fix    $W colcon build --base-paths src /ws2/src --packages-select other_ws_pkg
run one_good_one_bad  $W colcon build --packages-select pkg_a pkg_aa
run comma_list        $W colcon build --packages-select pkg_a,my_py_pkg
run flag_typo_dash1   $W colcon build --packages-select pkg_a -symlink-install
run flag_typo_dash2   $W colcon build --packages-select pkg_a --symlink-instal
run flag_full         $W colcon build --packages-select pkg_a --symlink-install
run select_no_names   $W colcon build --packages-select
run stderr_only       $W bash -c 'colcon build --packages-select pkg_aa 2>&1 >/dev/null'
run stdout_only       $W bash -c 'colcon build --packages-select pkg_aa 2>/dev/null'
run grep_guard        $W bash -c 'colcon build --packages-select pkg_aa 2>&1 | tee /tmp/b.log; ! grep -q "ignoring unknown package" /tmp/b.log'
run ignore_typo       $W colcon build --packages-ignore pkg_aa --packages-select pkg_a
run up_to_typo        $W colcon build --packages-up-to pkg_aa
run skip_typo         $W colcon build --packages-skip pkg_aa
run select_regex      $W colcon build --packages-select-regex pkg_aa
run test_typo         $W colcon test --packages-select pkg_aa
run list_typo         $W colcon list --packages-select pkg_aa
run select_names_only $W colcon list --names-only
echo; echo "### grep names in package.xml"
grep -rho --include=package.xml '<name>[^<]*</name>' $W/src | sort
