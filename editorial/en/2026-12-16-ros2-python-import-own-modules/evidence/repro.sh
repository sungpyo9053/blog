#!/bin/bash
# Run inside ros:<distro>-ros-base (no network needed).
# One ament_python package "imp_pkg" with sibling modules, a subfolder and a top-level
# folder. Each setup.py variant is built with and without --symlink-install, then every
# entry point is started with ros2 run and the last line of output is printed.
ulimit -c 0
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
python3 --version
dpkg-query -W -f='${Package} ${Version}\n' python3-setuptools python3-colcon-core python3-colcon-python-setup-py python3-colcon-ros 2>/dev/null
python3 -c 'import setuptools;print("setuptools module", setuptools.__version__)'

mk_src() {  # $1 = dir, $2 = packages expression, $3 = utils has __init__ (1/0), $4 = extra data_files
  local D=$1; rm -rf $D; mkdir -p $D/src/imp_pkg; cd $D/src/imp_pkg
  mkdir -p resource imp_pkg/utils configs; touch resource/imp_pkg imp_pkg/__init__.py configs/__init__.py
  [ "$3" = 1 ] && touch imp_pkg/utils/__init__.py
  echo "VALUE = 'helper ok'" > imp_pkg/helper.py
  echo "VALUE = 'common ok'" > imp_pkg/utils/common.py
  echo "VALUE = 'settings ok'" > configs/settings.py
  cat > package.xml <<X
<?xml version="1.0"?>
<package format="3"><name>imp_pkg</name><version>0.0.0</version><description>t</description>
<maintainer email="dev@example.com">a</maintainer><license>MIT</license>
<exec_depend>rclpy</exec_depend><export><build_type>ament_python</build_type></export></package>
X
  printf '[develop]\nscript_dir=$base/lib/imp_pkg\n[install]\ninstall_scripts=$base/lib/imp_pkg\n' > setup.cfg
  w() { printf 'import sys\nimport rclpy\n%s\n\n\ndef main():\n    print("OK", %s.VALUE, "file=" + %s.__file__, "sys.path[0]=" + sys.path[0])\n\n\nif __name__ == "__main__":\n    main()\n' "$2" "$3" "$3" > imp_pkg/$1.py; }
  w n_bare     'import helper' helper
  w n_abs      'from imp_pkg import helper' helper
  w n_rel      'from . import helper' helper
  w n_sub      'from imp_pkg.utils import common' common
  w n_subbare  'from utils import common' common
  w n_cfg      'from configs import settings' settings
  w n_late     'from imp_pkg import late' late
  cat > setup.py <<X
from glob import glob
from setuptools import setup, find_packages, find_namespace_packages
package_name = 'imp_pkg'
setup(
    name=package_name, version='0.0.0',
    packages=$2,
    data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                ('share/' + package_name, ['package.xml'])$4],
    install_requires=['setuptools'], zip_safe=True,
    entry_points={'console_scripts': [
$(for n in n_bare n_abs n_rel n_sub n_subbare n_cfg n_late; do echo "        '$n = imp_pkg.$n:main',"; done)
    ]},
)
X
}

declare -A PK UI
PK[V1]="[package_name]";                                UI[V1]=1
PK[V2]="find_packages(exclude=['test'])";               UI[V2]=1
PK[V3]="find_packages(exclude=['test'])";               UI[V3]=0
PK[V4]="[package_name, package_name + '.utils']";       UI[V4]=1
PK[V5]="find_namespace_packages(include=['imp_pkg*'])"; UI[V5]=0
PK[V6]="[package_name]";                                UI[V6]=1
EXTRA6=",
                ('lib/' + package_name, glob('imp_pkg/*.py'))"

last() { grep -E "Error|^OK" | tail -1; }
for V in V1 V2 V3 V4 V5 V6; do
  for MODE in copy symlink; do
  (  # subshell: each variant starts from a clean /opt/ros environment
    ex=""; [ $V = V6 ] && ex="$EXTRA6"
    mk_src /ws_$V$MODE "${PK[$V]}" ${UI[$V]} "$ex"
    cd /ws_$V$MODE
    flag=""; [ $MODE = symlink ] && flag="--symlink-install"
    echo "=== $V packages=${PK[$V]} utils/__init__.py=${UI[$V]} mode=$MODE"
    t0=$(date +%s.%N)
    timeout 300 colcon build $flag >/tmp/b.log 2>&1; rc=$?
    t1=$(date +%s.%N)
    echo "  build rc=$rc seconds=$(python3 -c "print(round($t1-$t0,2))")"
    [ $rc != 0 ] && tail -5 /tmp/b.log
    grep -i -m3 "warn" /tmp/b.log | cut -c1-200
    sp=$(ls -d install/imp_pkg/lib/python3*/site-packages)
    echo "  site-packages ($sp):"
    ( cd $sp && find . -maxdepth 3 \( -name '*.py' -o -name '*.egg-link' -o -name '*.pth' -o -type l \) | sort | sed 's/^/    /' )
    for f in $sp/*.pth $sp/*.egg-link; do [ -f "$f" ] && echo "    [$(basename $f)] $(tr '\n' ' ' < $f | sed "s#$PWD#<ws>#g" | cut -c1-200)"; done
    echo "  build/imp_pkg/imp_pkg: $(ls -ld build/imp_pkg/imp_pkg | awk '{print $1, $NF}' | sed "s#$PWD#<ws>#g")"
    echo "  lib/imp_pkg: $(ls install/imp_pkg/lib/imp_pkg | tr '\n' ' ')"
    source install/setup.bash
    for n in n_bare n_abs n_rel n_sub n_subbare n_cfg n_late; do
      echo "  $n: $(timeout 30 ros2 run imp_pkg $n 2>&1 | last | sed "s#$PWD#<ws>#g")"
    done
    echo "VALUE = 'late ok'" > src/imp_pkg/imp_pkg/late.py
    echo "  n_late after adding imp_pkg/late.py, no rebuild: $(timeout 30 ros2 run imp_pkg n_late 2>&1 | last | sed "s#$PWD#<ws>#g")"
    timeout 300 colcon build $flag >/dev/null 2>&1
    echo "  n_late after rebuild: $(timeout 30 ros2 run imp_pkg n_late 2>&1 | last | sed "s#$PWD#<ws>#g")"
  )
  done
done

( cd /ws_V1copy && source install/setup.bash
  echo "=== full traceback, V1 copy, n_sub"; timeout 30 ros2 run imp_pkg n_sub 2>&1 | sed "s#$PWD#<ws>#g"
  echo "=== full traceback, V1 copy, n_bare"; timeout 30 ros2 run imp_pkg n_bare 2>&1 | sed "s#$PWD#<ws>#g"
  echo "=== generated wrapper lib/imp_pkg/n_abs (V1 copy)"; sed "s#$PWD#<ws>#g" install/imp_pkg/lib/imp_pkg/n_abs )
echo "=== two workspaces sourced in one shell: V2copy (installs configs) then V1copy"
( source /ws_V2copy/install/setup.bash; source /ws_V1copy/install/setup.bash
  echo "  ros2 pkg prefix imp_pkg: $(ros2 pkg prefix imp_pkg)"
  for n in n_cfg n_sub; do echo "  $n: $(timeout 30 ros2 run imp_pkg $n 2>&1 | last)"; done )
echo "=== running source files directly, workspace not sourced (V2 source tree)"
cd /ws_V2copy/src/imp_pkg/imp_pkg
for m in n_bare n_abs n_rel n_sub n_subbare; do
  echo "  cd src/imp_pkg/imp_pkg; python3 $m.py: $(timeout 30 python3 $m.py 2>&1 | last | sed "s#/ws_V2copy#<ws>#g")"
done
cd /ws_V2copy/src/imp_pkg
for m in n_bare n_abs n_rel n_sub; do
  echo "  cd src/imp_pkg; python3 -m imp_pkg.$m: $(timeout 30 python3 -m imp_pkg.$m 2>&1 | last | sed "s#/ws_V2copy#<ws>#g")"
done
echo "=== done"
