#!/bin/bash
# runs inside ros:<distro>-ros-base as root
D=$1; source /opt/ros/$D/setup.bash
export PIP_BREAK_SYSTEM_PACKAGES=1
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y git python3-pip >/dev/null 2>&1
echo "## $D python $(python3 -c 'import sys;print(sys.version.split()[0])') setuptools $(python3 -c 'import setuptools;print(setuptools.__version__)') colcon-ros $(python3 -c 'import importlib.metadata as m;print(m.version("colcon-ros"))') git $(git --version | cut -d' ' -f3)"
W=/ws; mkdir -p $W/src; cd $W/src
ros2 pkg create --build-type ament_python demo_py --node-name talker >/dev/null 2>&1
cd $W
build(){ rm -rf build install log; out=$(colcon build --event-handlers console_direct+ 2>&1); rc=$?
  echo "[$1] colcon exit=$rc"
  echo "$out" | grep -E "listing git files failed|marker|Failed|ERROR|error:|fatal|dubious" | sort | uniq -c | sed 's/^/    /'
  ( source install/setup.bash; echo "    ros2 pkg list has demo_py: $(ros2 pkg list 2>/dev/null | grep -cx demo_py)"; echo "    ros2 run: $(timeout 10 ros2 run demo_py talker 2>&1 | tail -1)" ) ; }
build A_baseline
cp src/demo_py/setup.py /tmp/setup.py.orig
python3 - <<'P'
p='/ws/src/demo_py/setup.py';s=open(p).read()
s=s.replace("('share/ament_index/resource_index/packages',\n            ['resource/' + package_name]),\n","")
open(p,'w').write(s)
P
grep -c resource_index src/demo_py/setup.py | sed 's/^/    resource_index lines left: /'
build B_no_marker_data_files
cp /tmp/setup.py.orig src/demo_py/setup.py
rm src/demo_py/resource/demo_py
build C_marker_file_deleted
touch src/demo_py/resource/demo_py
pip install -q setuptools_scm 2>&1 | tail -1
echo "    setuptools_scm $(python3 -c 'import importlib.metadata as m;print(m.version("setuptools_scm"))') setuptools now $(python3 -c 'import setuptools;print(setuptools.__version__)')"
build D_scm_not_git_repo
cd /ws && git init -q && git add -A && git -c user.email=t@example.com -c user.name=t commit -qm init && cd /ws
build E_scm_git_repo_same_owner
chown -R nobody /ws/.git /ws/src
echo "    git ls-files as root: $(cd /ws && git ls-files 2>&1 | head -1)"
build F_scm_git_repo_other_owner
git config --global --add safe.directory /ws
build G_other_owner_safe_directory
git config --global --unset-all safe.directory
pip uninstall -q -y setuptools_scm 2>&1 | tail -1
build H_scm_uninstalled_other_owner
