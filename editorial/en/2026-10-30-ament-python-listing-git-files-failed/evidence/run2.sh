#!/bin/bash
D=$1; SCM=$2; source /opt/ros/$D/setup.bash
export PIP_BREAK_SYSTEM_PACKAGES=1
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y git python3-pip >/dev/null 2>&1
W=/ws; mkdir -p $W/src; cd $W/src; ros2 pkg create --build-type ament_python demo_py --node-name talker >/dev/null 2>&1; cd $W
if [ "$D" = humble ]; then pip install -q "setuptools_scm==$SCM" 2>&1 | grep -v "Running pip as" ; else pip install -q --ignore-installed "setuptools_scm==$SCM" 2>&1 | grep -v "Running pip as"; fi
echo "## $D setuptools_scm $(python3 -c 'import importlib.metadata as m;print(m.version("setuptools_scm"))' 2>&1|tail -1) setuptools $(python3 -c 'import setuptools;print(setuptools.__version__)')"
build(){ rm -rf build install log; out=$(colcon build --event-handlers console_direct+ 2>&1); rc=$?
  echo "[$1] colcon exit=$rc"
  echo "$out" | grep -E "listing git files failed|Failed|ERROR|error:|fatal|dubious|introspection|Warning|warn" | grep -v "doesn't explicitly install" | sed -E 's/^\[[^]]*\] //' | sort | uniq -c | head -8 | sed 's/^/    /'
  ( source install/setup.bash; echo "    ros2 run: $(timeout 10 ros2 run demo_py talker 2>&1 | tail -1)" ) ; }
build D_not_git_repo
git init -q && git add -A && git -c user.email=t@example.com -c user.name=t commit -qm init
build E_git_repo_same_owner
chown -R nobody /ws/.git /ws/src
build F_git_repo_other_owner
git config --global --add safe.directory /ws
build G_safe_directory
git config --global --unset-all safe.directory
apt-get -qq remove -y git >/dev/null 2>&1; echo "    git now: $(command -v git || echo absent)"
build I_other_owner_git_uninstalled
