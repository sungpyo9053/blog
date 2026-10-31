#!/bin/bash
# Run inside ros:<distro>-ros-base as root. Reproduces colcon test failures
# (test_copyright / test_flake8 / test_pep257) on a fresh ament_python package.
set +e
export DEBIAN_FRONTEND=noninteractive
source /opt/ros/$ROS_DISTRO/setup.bash
echo "=== distro=$ROS_DISTRO $(. /etc/os-release; echo $PRETTY_NAME) python=$(python3 -V)"

step(){ echo; echo "################ $*"; }
# run_test PKG [extra colcon test args...]
run_test(){
  local P=$1; shift
  cd /ws
  colcon build --packages-select $P --event-handlers console_direct- >/tmp/b.log 2>&1 || { echo "BUILD FAILED"; tail -20 /tmp/b.log; }
  echo "\$ colcon test --packages-select $P $*"
  colcon test --packages-select $P "$@"; echo "EXIT colcon test = $?"
  echo "--- pytest output (log/latest_test/$P/stdout_stderr.log):"
  grep -v -e '^\s*$' -e '^plugins:' -e '^cachedir:' log/latest_test/$P/stdout_stderr.log 2>/dev/null | head -90
  echo "\$ colcon test-result --test-result-base build/$P --all --verbose"
  colcon test-result --test-result-base build/$P --all --verbose; echo "EXIT colcon test-result = $?"
}
pyver(){ python3 -c 'import flake8,pycodestyle,pyflakes;print("flake8",flake8.__version__,flake8.__file__);print("pycodestyle",pycodestyle.__version__,pycodestyle.__file__);print("pyflakes",pyflakes.__version__,pyflakes.__file__)'; }
bad_talker(){ cat > $1 <<'X'
import os
import rclpy
from rclpy.node import Node

def main():
    rclpy.init()
    node = Node("talker")
    node.get_logger().info("hello from talker, this line is longer than ninety-nine characters on purpose")
    rclpy.shutdown()
X
}
good_talker(){ cat > $1 <<'X'
# Copyright 2026 Example
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Minimal talker node."""

import rclpy
from rclpy.node import Node


def main():
    """Log one message and exit."""
    rclpy.init()
    node = Node('talker')
    node.get_logger().info(
        'hello from talker, this line is longer than ninety-nine characters on purpose')
    rclpy.shutdown()
X
}
unskip_copyright(){ sed -i '/^@pytest.mark.skip/d; /^# Remove the `skip` decorator/d' $1/test/test_copyright.py; }

step "0. setup"
apt-get update -qq >/dev/null 2>&1
apt-get install -y -qq python3-pip >/dev/null 2>&1; echo "apt python3-pip rc=$?"
rosdep update --rosdistro $ROS_DISTRO >/dev/null 2>&1; echo "rosdep update rc=$?"

mkdir -p /ws/src && cd /ws/src
step "1a. ros2 pkg create --build-type ament_python nolic_pkg   (no --license)"
ros2 pkg create --build-type ament_python nolic_pkg 2>&1 | grep -iv '^creating' ; echo "rc=${PIPESTATUS[0]}"
step "1b. ros2 pkg create --build-type ament_python --license Apache-2.0 apache_pkg"
ros2 pkg create --build-type ament_python --license Apache-2.0 apache_pkg 2>&1 | grep -iv '^creating'; echo "rc=${PIPESTATUS[0]}"
step "1c. ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name my_node gen_pkg"
ros2 pkg create --build-type ament_python --license Apache-2.0 --node-name my_node gen_pkg 2>&1 | grep -iv '^creating'; echo "rc=${PIPESTATUS[0]}"
for p in nolic_pkg apache_pkg; do echo "--- $p license line:"; grep '<license>' $p/package.xml; ls $p $p/test; done
echo "--- nolic_pkg/test/test_copyright.py:"; cat nolic_pkg/test/test_copyright.py
echo "--- diff nolic_pkg vs apache_pkg test/:"; diff -r nolic_pkg/test apache_pkg/test && echo "identical"
echo "--- apache_pkg/test/test_flake8.py:"; cat apache_pkg/test/test_flake8.py
echo "--- apache_pkg/test/test_pep257.py:"; cat apache_pkg/test/test_pep257.py
echo "--- gen_pkg/gen_pkg/my_node.py:"; cat gen_pkg/gen_pkg/my_node.py

step "deps via rosdep"
cd /ws && rosdep install --from-paths src --ignore-src -y -q >/tmp/rosdep.log 2>&1; echo "rosdep install rc=$?"; tail -3 /tmp/rosdep.log
dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2pkg ros-$ROS_DISTRO-rmw ros-$ROS_DISTRO-rmw-implementation ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-ament-flake8 ros-$ROS_DISTRO-ament-pep257 ros-$ROS_DISTRO-ament-copyright python3-flake8 python3-pycodestyle python3-pyflakes python3-pydocstyle python3-flake8-quotes python3-flake8-import-order python3-pytest python3-colcon-core 2>&1
echo "flake8 --version: $(python3 -m flake8 --version 2>&1 | head -1)"

step "2a. fresh nolic_pkg"
run_test nolic_pkg
step "2b. fresh apache_pkg"
run_test apache_pkg
step "2c. fresh gen_pkg (--node-name generated file)"
run_test gen_pkg

step "2d. remove the skip decorator from test_copyright (fresh packages)"
unskip_copyright /ws/src/nolic_pkg; unskip_copyright /ws/src/apache_pkg; unskip_copyright /ws/src/gen_pkg
grep -n -A3 '^from ament_copyright' /ws/src/nolic_pkg/test/test_copyright.py
run_test nolic_pkg
run_test apache_pkg
run_test gen_pkg

step "3. add a minimal node with lint problems (no header) to apache_pkg and nolic_pkg"
bad_talker /ws/src/apache_pkg/apache_pkg/talker.py; bad_talker /ws/src/nolic_pkg/nolic_pkg/talker.py
cat /ws/src/apache_pkg/apache_pkg/talker.py
run_test apache_pkg
run_test nolic_pkg
step "3b. same, with --return-code-on-test-failure"
run_test apache_pkg --return-code-on-test-failure
step "3c. ament_flake8 / ament_pep257 / ament_copyright run directly on apache_pkg"
cd /ws/src/apache_pkg
ament_flake8 apache_pkg; echo "rc=$?"
ament_pep257 apache_pkg; echo "rc=$?"
ament_copyright apache_pkg; echo "rc=$?"

step "3d. docstrings that ament_pep257 rejects (gen_pkg/my_node.py, header kept)"
{ printf '# Copyright 2026 Example\n#\n'; sed -n '/Licensed under/,/limitations under/p' /ws/src/apache_pkg/test/test_flake8.py; echo; } > /tmp/h0.txt
cat /tmp/h0.txt - > /ws/src/gen_pkg/gen_pkg/my_node.py <<'X'
"""my node module"""


def main():
    '''Print a greeting.'''
    print('Hi from gen_pkg.')


def helper():
    """
    Return one.
    """
    return 1


if __name__ == '__main__':
    main()
X
cd /ws/src/gen_pkg; ament_pep257 gen_pkg; echo "rc=$?"
run_test gen_pkg

step "4a. fix option: --pytest-args -k 'not flake8 and not pep257 and not copyright'"
run_test apache_pkg --pytest-args -k "not flake8 and not pep257 and not copyright"
step "4b. fix option: --ctest-args -E flake8 (ament_python package)"
run_test apache_pkg --ctest-args -E flake8
step "4c. fix option: setup.cfg [flake8] max-line-length = 200, extend-ignore = E501,F401,E302"
cp /ws/src/apache_pkg/setup.cfg /tmp/setup.cfg.bak
printf '[flake8]\nmax-line-length = 200\nextend-ignore = E501,F401,E302\n' >> /ws/src/apache_pkg/setup.cfg
run_test apache_pkg
cp /tmp/setup.cfg.bak /ws/src/apache_pkg/setup.cfg
step "4d. fix option: test_flake8.py argv=['--linelength', '200']"
cp -r /ws/src/apache_pkg/test /tmp/test.bak
sed -i "s/main_with_errors(argv=\[\])/main_with_errors(argv=['--linelength', '200'])/" /ws/src/apache_pkg/test/test_flake8.py
grep -n main_with_errors /ws/src/apache_pkg/test/test_flake8.py
run_test apache_pkg
cp /tmp/test.bak/* /ws/src/apache_pkg/test/
step "4e. fix option: @pytest.mark.skip on all three tests"
for t in copyright flake8 pep257; do sed -i "s/^@pytest.mark.$t\$/@pytest.mark.skip(reason='lint off')\n@pytest.mark.$t/" /ws/src/apache_pkg/test/test_$t.py; done
grep -n -B2 '^def test' /ws/src/apache_pkg/test/test_*.py
run_test apache_pkg
cp /tmp/test.bak/* /ws/src/apache_pkg/test/
step "4f. fix option: add license header only"
{ printf '# Copyright 2026 Example\n#\n'; sed -n '/Licensed under/,/limitations under/p' /ws/src/apache_pkg/test/test_flake8.py; echo; cat /ws/src/apache_pkg/apache_pkg/talker.py; } > /tmp/t.py && mv /tmp/t.py /ws/src/apache_pkg/apache_pkg/talker.py
head -16 /ws/src/apache_pkg/apache_pkg/talker.py
run_test apache_pkg
step "4g. fix option: header + lint fixed (apache_pkg and nolic_pkg)"
good_talker /ws/src/apache_pkg/apache_pkg/talker.py; good_talker /ws/src/nolic_pkg/nolic_pkg/talker.py
run_test nolic_pkg
run_test apache_pkg

step "5. where results live"
cd /ws; find build/apache_pkg -maxdepth 3 -name '*.xml'; ls log/latest_test/apache_pkg
grep -o '<testsuite [^>]*>' build/apache_pkg/pytest.xml

step "6. pip install -U flake8 (newest), rosdep-installed deps only"
pip install -U flake8 2>&1 | tail -3; echo "pip rc=${PIPESTATUS[0]}"
if ! python3 -c 'import sys,flake8; sys.exit(0 if flake8.__file__.startswith("/usr/local") else 1)' 2>/dev/null; then
  echo "--- retry with --break-system-packages"
  pip install -U --break-system-packages flake8 2>&1 | grep -v '^WARNING: Running pip' | tail -8; echo "pip rc=${PIPESTATUS[0]}"
fi
if ! python3 -c 'import sys,flake8; sys.exit(0 if flake8.__file__.startswith("/usr/local") else 1)' 2>/dev/null; then
  echo "--- retry with --break-system-packages --ignore-installed"
  pip install -U --break-system-packages --ignore-installed flake8 2>&1 | grep -v '^WARNING: Running pip' | tail -3; echo "pip rc=${PIPESTATUS[0]}"
fi
pyver
run_test apache_pkg
BSP=""; pip uninstall --help 2>/dev/null | grep -q break-system && BSP=--break-system-packages
step "6b. recover attempt: pip uninstall -y flake8 only"
pip uninstall -y $BSP flake8 2>&1 | tail -1
pyver
run_test apache_pkg
step "6c. recover: also pip uninstall pycodestyle pyflakes mccabe"
pip uninstall -y $BSP pycodestyle pyflakes mccabe 2>&1 | grep -i success
pyver
run_test apache_pkg

step "7. apt install the flake8 plugins listed in the ROS 2 source-build setup"
for p in python3-flake8-blind-except python3-flake8-builtins python3-flake8-class-newline python3-flake8-comprehensions python3-flake8-deprecated python3-flake8-docstrings python3-flake8-import-order python3-flake8-quotes; do
  apt-get install -y -qq $p >/dev/null 2>&1; echo "apt $p rc=$?"; done
dpkg-query -W -f='${db:Status-Abbrev} ${Package} ${Version}\n' 'python3-flake8*' 2>/dev/null | grep '^ii'
echo "flake8 --version: $(python3 -m flake8 --version 2>&1 | head -1)"
step "7a. good talker with plugins"
run_test apache_pkg
step "7b. bad talker (with header) with plugins"
{ printf '# Copyright 2026 Example\n#\n'; sed -n '/Licensed under/,/limitations under/p' /ws/src/apache_pkg/test/test_flake8.py; echo; } > /tmp/h.txt
bad_talker /tmp/bt.py; cat /tmp/h.txt /tmp/bt.py > /ws/src/apache_pkg/apache_pkg/talker.py
run_test apache_pkg
good_talker /ws/src/apache_pkg/apache_pkg/talker.py

step "8. pip install -U flake8 with plugins installed"
pip install -U $BSP flake8 2>&1 | grep -v '^WARNING: Running pip' | tail -3; echo "pip rc=${PIPESTATUS[0]}"
if ! python3 -c 'import sys,flake8; sys.exit(0 if flake8.__file__.startswith("/usr/local") else 1)' 2>/dev/null; then
  echo "--- retry with --ignore-installed"
  pip install -U $BSP --ignore-installed flake8 2>&1 | grep -v '^WARNING: Running pip' | tail -3; echo "pip rc=${PIPESTATUS[0]}"
fi
pyver
run_test apache_pkg
step "8b. recover: pip uninstall -y flake8 pycodestyle pyflakes mccabe"
pip uninstall -y $BSP flake8 pycodestyle pyflakes mccabe 2>&1 | grep -i success
pyver
run_test apache_pkg
step "9. recover: apt-get install --reinstall python3-flake8 python3-pycodestyle python3-pyflakes"
apt-get install -y -qq --reinstall python3-flake8 python3-pycodestyle python3-pyflakes >/dev/null 2>&1; echo "apt reinstall rc=$?"
pyver
run_test apache_pkg
echo "=== done $ROS_DISTRO"
