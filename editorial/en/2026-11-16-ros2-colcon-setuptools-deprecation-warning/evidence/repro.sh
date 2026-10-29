#!/bin/bash
# Run inside ros:<distro>-ros-base as root.
# Builds a minimal ament_python package (ros2 pkg create --build-type ament_python)
# with colcon under different setuptools versions, setup.cfg variants and
# PYTHONWARNINGS values, and records: deprecation warnings, colcon exit code,
# and whether `ros2 run` still works.
ulimit -c 0
export PIP_BREAK_SYSTEM_PACKAGES=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore
export DEBIAN_FRONTEND=noninteractive
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO"
. /etc/os-release; echo "os=$PRETTY_NAME"
python3 --version
python3 -m pip --version >/dev/null 2>&1 || { apt-get update -qq >/dev/null && apt-get install -y -qq python3-pip >/dev/null 2>&1; }
python3 -m pip --version
dpkg-query -W -f='${Package} ${Version}\n' python3-setuptools python3-pip python3-packaging 'python3-colcon-*' 2>/dev/null | grep -E 'setuptools|pip |packaging|colcon-core|colcon-python-setup-py|colcon-ros|colcon-library-path'
sv() { python3 -c 'import setuptools,sys; print("setuptools", setuptools.__version__, setuptools.__file__)' 2>&1 | tail -1; }
sv
# remove any pip-installed setuptools from /usr/local (also when it is too old to import)
cleanst() { rm -rf /usr/local/lib/python3*/dist-packages/setuptools /usr/local/lib/python3*/dist-packages/setuptools-*.dist-info /usr/local/lib/python3*/dist-packages/pkg_resources /usr/local/lib/python3*/dist-packages/_distutils_hack /usr/local/lib/python3*/dist-packages/distutils-precedence.pth; }
echo "dpkg -V python3-setuptools (empty = unmodified): [$(dpkg -V python3-setuptools)]"

W=/ws; mkdir -p $W/src && cd $W/src
ros2 pkg create --build-type ament_python --node-name stl_node stl_pkg >/dev/null 2>&1
echo "--- generated setup.cfg"; cat $W/src/stl_pkg/setup.cfg
cp $W/src/stl_pkg/setup.cfg /tmp/setup.cfg.orig
cd $W

# summarize one colcon run: exit code, warning names, stderr header, errors
summ() { # $1 log $2 rc
  echo "rc=$2"
  echo "SetuptoolsDeprecationWarning=$(grep -c 'SetuptoolsDeprecationWarning' $1) EasyInstallDeprecationWarning=$(grep -c 'EasyInstallDeprecationWarning' $1) stderr_block=$(grep -c -- '--- stderr' $1) dash_warning=$(grep -c 'dash-separated' $1)"
  grep -E 'Warning:|^error|[Ee]rror:|Summary:|Failed|aborted|finished' $1 | grep -v '^\s*$' | sort | uniq -c | head -12
}
runnode() {
  out=$(bash -c "source $W/install/setup.bash && timeout 20 ros2 run stl_pkg stl_node" 2>&1); rc=$?
  echo "ros2_run rc=$rc out=$(echo "$out" | head -2 | tr '\n' '|')"
}
# case: clean default build, run, clean symlink build, run, switch back to default build, run
cas() { # $1 label
  echo; echo "##### CASE $1 | $(sv) | PYTHONWARNINGS=${PYTHONWARNINGS:-unset}"
  rm -rf build install log
  colcon build >/tmp/b1.log 2>&1; r1=$?; echo "[default build]"; summ /tmp/b1.log $r1; runnode
  [ $r1 -ne 0 ] && [ -z "$FULL" ] && { echo "--- default tail"; tail -25 /tmp/b1.log; }
  [ -n "$FULL" ] && { echo "--- full colcon output (default build)"; cat /tmp/b1.log; }
  rm -rf build install log
  colcon build --symlink-install >/tmp/b2.log 2>&1; r=$?; echo "[symlink build]"; summ /tmp/b2.log $r; runnode
  echo "symlink_check: $(find install/stl_pkg \( -name '*.egg-link' -o -name '__editable__*' -o -type l \) 2>/dev/null | sed 's#.*/##' | sort | head -4 | tr '\n' ' ')"
  [ -n "$FULL" ] && { echo "--- full colcon output (symlink build)"; cat /tmp/b2.log; }
  [ $r -ne 0 ] && { echo "--- symlink tail"; tail -25 /tmp/b2.log; }
  colcon build >/tmp/b3.log 2>&1; r=$?; echo "[switch symlink->default, no clean]"; summ /tmp/b3.log $r; runnode
  [ $r -ne 0 ] && { echo "--- switch tail"; tail -25 /tmp/b3.log; }
}

if [ -z "$1" ]; then  # no argument: all sections A-H. "repro.sh FG" runs only F and G, "repro.sh H" only H
echo; echo "======== A. apt setuptools (image default)"
FULL=1 cas apt-default

echo; echo "======== B. PYTHONWARNINGS filters (apt setuptools)"
for pw in "ignore:::setuptools.command.install" \
          "ignore:::setuptools.command.develop" \
          "ignore:::setuptools.command.easy_install" \
          "ignore:::setuptools.command.install,ignore:::setuptools.command.easy_install,ignore:::pkg_resources" \
          "ignore:::setuptools.command.install,ignore:::setuptools.command.develop,ignore:::setuptools.command.easy_install" \
          "ignore::UserWarning" "ignore::DeprecationWarning" "ignore"; do
  PYTHONWARNINGS="$pw" cas "pw"
done

echo; echo "======== C. setup.cfg variants (apt setuptools)"
printf '[develop]\nscript-dir=$base/lib/stl_pkg\n[install]\ninstall-scripts=$base/lib/stl_pkg\n' > src/stl_pkg/setup.cfg
cas dash-keys
rm src/stl_pkg/setup.cfg; cas no-setup-cfg
cp /tmp/setup.cfg.orig src/stl_pkg/setup.cfg

echo; echo "======== D. pip setuptools versions"
for v in 58.2.0 59.6.0 65.5.0 68.1.2 68.2.0 69.5.1 70.1.1 70.3.0 71.1.0 72.1.0 72.2.0 74.1.3 75.8.0 78.1.0 79.0.1 80.0.0 80.9.0 latest; do
  cleanst
  if [ $v = latest ]; then spec=setuptools; else spec=setuptools==$v; fi
  python3 -m pip install -q --ignore-installed "$spec" >/tmp/pip.log 2>&1 || { echo; echo "##### CASE pip-$v pip install FAILED"; tail -3 /tmp/pip.log; continue; }
  cas pip-$v
  if [ $v = latest ] || [ $v = 80.9.0 ] || [ $v = 75.8.0 ]; then
    PYTHONWARNINGS="ignore:::setuptools.command.install,ignore:::setuptools.command.develop,ignore:::setuptools.command.easy_install" cas pip-$v-pw
    printf '[develop]\nscript-dir=$base/lib/stl_pkg\n[install]\ninstall-scripts=$base/lib/stl_pkg\n' > src/stl_pkg/setup.cfg
    cas pip-$v-dash-keys
    cp /tmp/setup.cfg.orig src/stl_pkg/setup.cfg
  fi
done

echo; echo "======== E. remove pip setuptools, fall back to apt"
python3 -m pip uninstall -y setuptools 2>&1 | tail -2
cas after-uninstall
fi

case "${1:-FG}" in *F*)
echo; echo "======== F. older colcon-core from pip (before the -W suppression added in colcon-core 0.16.0)"
python3 -m pip install -q --ignore-installed --no-deps colcon-core==0.15.2 >/tmp/pip.log 2>&1 || tail -3 /tmp/pip.log
python3 -c 'import colcon_core; print("colcon-core", colcon_core.__version__, colcon_core.__file__)'
FULL=1 cas old-colcon-apt
for pw in "ignore:::setuptools.command.install" \
          "ignore:::setuptools.command.develop" \
          "ignore:::setuptools.command.install,ignore:::setuptools.command.easy_install,ignore:::pkg_resources" \
          "ignore:::setuptools.command.install,ignore:::setuptools.command.develop,ignore:::setuptools.command.easy_install" \
          "ignore::UserWarning" "ignore"; do
  PYTHONWARNINGS="$pw" cas old-colcon-pw
done
printf '[develop]\nscript-dir=$base/lib/stl_pkg\n[install]\ninstall-scripts=$base/lib/stl_pkg\n' > src/stl_pkg/setup.cfg
cas old-colcon-dash-keys
cp /tmp/setup.cfg.orig src/stl_pkg/setup.cfg
for v in 58.2.0 59.6.0 65.5.0 69.5.1 75.8.0 latest; do
  cleanst
  if [ $v = latest ]; then spec=setuptools; else spec=setuptools==$v; fi
  python3 -m pip install -q --ignore-installed "$spec" >/tmp/pip.log 2>&1 || { echo; echo "##### CASE old-colcon-pip-$v pip install FAILED"; tail -3 /tmp/pip.log; continue; }
  if [ $v = 58.2.0 ] || [ $v = latest ]; then FULL=1 cas old-colcon-pip-$v; else cas old-colcon-pip-$v; fi
done
cleanst
;; esac

case "${1:-G}" in *G*)
echo; echo "======== G. recent setuptools with packaging upgraded from pip"
python3 -c "import colcon_core,sys; sys.exit(0 if colcon_core.__file__.startswith('/usr/local') else 1)" && python3 -m pip uninstall -y colcon-core >/dev/null 2>&1  # drop pip colcon-core from F
hash -r; command -v colcon
python3 -c 'import colcon_core; print("colcon-core", colcon_core.__version__, colcon_core.__file__)'
python3 -m pip install -q --ignore-installed packaging >/tmp/pip.log 2>&1 || tail -3 /tmp/pip.log
python3 -c 'import packaging; print("packaging", packaging.__version__, packaging.__file__)'
for v in 71.1.0 75.8.0 79.0.1 80.0.0 80.9.0 latest; do
  cleanst
  if [ $v = latest ]; then spec=setuptools; else spec=setuptools==$v; fi
  python3 -m pip install -q --ignore-installed "$spec" >/tmp/pip.log 2>&1 || { echo; echo "##### CASE pkg-pip-$v pip install FAILED"; tail -3 /tmp/pip.log; continue; }
  if [ $v = latest ]; then FULL=1 cas pkg-pip-$v; else cas pkg-pip-$v; fi
done
cleanst
python3 -m pip uninstall -y packaging >/dev/null 2>&1
python3 -c 'import packaging; print("packaging", packaging.__version__, packaging.__file__)'
;; esac
case "${1:-H}" in *H*)
echo; echo "======== H. workspace built under apt setuptools, then rebuilt after pip install -U setuptools (no clean)"
rm -rf build install log
colcon build --symlink-install >/tmp/h1.log 2>&1; r=$?; echo "[apt symlink build] $(sv)"; summ /tmp/h1.log $r; runnode
python3 -m pip install -q --ignore-installed setuptools >/tmp/pip.log 2>&1 || tail -3 /tmp/pip.log
[ "$ROS_DISTRO" = humble ] && { python3 -m pip install -q --ignore-installed packaging >/tmp/pip.log 2>&1; python3 -c 'import packaging; print("packaging", packaging.__version__, "(pip, needed on Humble for setuptools>=71)")'; }
echo "now: $(sv)"
colcon build --symlink-install >/tmp/h2.log 2>&1; r=$?; echo "[rebuild --symlink-install, no clean]"; summ /tmp/h2.log $r; runnode; [ $r -ne 0 ] && tail -6 /tmp/h2.log
colcon build >/tmp/h3.log 2>&1; r=$?; echo "[rebuild plain, no clean]"; summ /tmp/h3.log $r; runnode; [ $r -ne 0 ] && tail -6 /tmp/h3.log
rm -rf build install log
colcon build --symlink-install >/tmp/h4.log 2>&1; r=$?; echo "[after rm -rf build install log, --symlink-install]"; summ /tmp/h4.log $r; runnode
echo "symlink_check: $(find install/stl_pkg \( -name '*.egg-link' -o -name '__editable__*' -o -type l \) 2>/dev/null | sed 's#.*/##' | sort | head -4 | tr '\n' ' ')"
grep -h "falling back" log/latest_build/logger_all.log log/latest_build/stl_pkg/*.log 2>/dev/null | head -2
cleanst; python3 -m pip uninstall -y packaging >/dev/null 2>&1
;; esac
case "${1:-I}" in *I*)
echo; echo "======== I. older colcon-core 0.15.2, message-based and _distutils.cmd filters"
python3 -m pip install -q --ignore-installed --no-deps colcon-core==0.15.2 >/tmp/pip.log 2>&1 || tail -3 /tmp/pip.log
hash -r; python3 -c 'import colcon_core; print("colcon-core", colcon_core.__version__)'
for pw in "ignore:setup.py install is deprecated,ignore:easy_install command is deprecated" \
          "ignore:::setuptools._distutils.cmd,ignore:::setuptools.command.develop"; do
  PYTHONWARNINGS="$pw" cas old-colcon-pw2
done
python3 -m pip uninstall -y colcon-core >/dev/null 2>&1; hash -r
python3 -c 'import colcon_core; print("colcon-core", colcon_core.__version__)'
;; esac
echo "dpkg -V python3-setuptools (empty = unmodified): [$(dpkg -V python3-setuptools)]"
echo "=== done $ROS_DISTRO"
