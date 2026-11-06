#!/bin/bash
# "ros2: error: argument Call `ros2 <command> -h` ...: invalid choice" and
# "Failed to load entry point" repro. Runs INSIDE ros:<distro>-ros-base as root.
# Host side (one distro at a time):
#   docker run --rm --name pk20-$D --cpus 1.5 --pids-limit 256 -v /tmp/en-pick30:/w \
#     ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
ulimit -c 0
export DEBIAN_FRONTEND=noninteractive
D=$ROS_DISTRO
source /opt/ros/$D/setup.bash

sec(){ echo; echo "=================== $*"; }
# run CMD: print command, merged output (first 40 lines), exit code, wall ms
run(){
  echo "\$ $*"
  local s=$(date +%s%N)
  timeout 60 bash -c "$*" > /tmp/o.txt 2>&1; local rc=$?
  local ms=$(( ($(date +%s%N)-s)/1000000 ))
  head -n 40 /tmp/o.txt; local n=$(wc -l < /tmp/o.txt); [ "$n" -gt 40 ] && echo "... ($n lines total)"
  echo "[exit=$rc wall=${ms}ms]"
}

sec "0 versions"
cat /etc/os-release | grep PRETTY
python3 --version
dpkg-query -W -f '${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-rmw-implementation ros-$D-rosbag2 2>&1
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-<unset>}"
echo "LD_LIBRARY_PATH=$LD_LIBRARY_PATH"

sec "1 the command list in this image"
run "ros2 --help | sed -n '/^Commands:/,/^\s*Call/p'"
run "ros2 extension_points"
run "ros2 extensions | grep -c ."

echo "--- start the daemon in its own run so a later timeout cannot kill it"
run "ros2 daemon start"
run "ros2 topic list"

sec "2 verbs that are not installed"
run "timeout 15 ros2 control list_controllers"
run "ros2 plugin list"

sec "3 typos"
run "ros2 topics list"
run "ros2 Topic list"
run "ros2 topic lst"
run "ros2 bag recrod /chatter"

sec "4 which apt package provides a missing verb"
run "apt-get update -qq"
run "apt-cache policy ros-$D-ros2controlcli | head -4"
run "apt-cache search --names-only '^ros-$D-ros2[a-z]' | grep -v dbgsym | sort"
echo "--- which installed package registers each ros2 command"
run "python3 -c \"from importlib.metadata import distributions as d; [print(e.name, '->', x.metadata['Name']) for x in d() for e in x.entry_points if e.group == 'ros2cli.command']\" | sort"

sec "5 install ros2controlcli, same shell, no re-source"
run "apt-get install -y --no-install-recommends ros-$D-ros2controlcli 2>&1 | grep -E 'newly installed|Need to get|^E:'"
run "ros2 control -h | head -20"
run "timeout 15 ros2 control list_controllers"
run "ros2 daemon status"
echo "--- fresh shell after install"
run "bash -c 'source /opt/ros/$D/setup.bash; ros2 control -h | head -3'"

sec "6 your own ros2cli command from a workspace"
mkdir -p /ws/src/my_cli/my_cli/command /ws/src/my_cli/resource
touch /ws/src/my_cli/resource/my_cli /ws/src/my_cli/my_cli/__init__.py /ws/src/my_cli/my_cli/command/__init__.py
cat > /ws/src/my_cli/package.xml <<'EOF'
<?xml version="1.0"?>
<package format="3">
  <name>my_cli</name><version>0.0.1</version><description>demo verb</description>
  <maintainer email="a@b.c">a</maintainer><license>Apache-2.0</license>
  <exec_depend>ros2cli</exec_depend>
  <export><build_type>ament_python</build_type></export>
</package>
EOF
cat > /ws/src/my_cli/setup.py <<'EOF'
from setuptools import setup
setup(name='my_cli', version='0.0.1', packages=['my_cli', 'my_cli.command'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/my_cli']),
                  ('share/my_cli', ['package.xml'])],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'ros2cli.command': ['hello = my_cli.command.hello:HelloCommand']})
EOF
cat > /ws/src/my_cli/my_cli/command/hello.py <<'EOF'
from ros2cli.command import CommandExtension
class HelloCommand(CommandExtension):
    """Say hello."""
    def main(self, *, parser, args):
        print('hello from my_cli')
        return 0
EOF
run "cd /ws && colcon build 2>&1 | tail -3"
echo "--- control: ros2 topic list on a healthy install (daemon start, then reuse)"
run "ros2 topic list"
run "ros2 topic list"
echo "--- 6a built, workspace NOT sourced"
run "ros2 hello"
echo "--- 6b workspace sourced"
run "source /ws/install/setup.bash && ros2 hello"
run "source /ws/install/setup.bash && ros2 --help | grep -E '^\s+hello'"
echo "--- 6c broken import inside the verb module"
sed -i '1i import this_module_does_not_exist' /ws/src/my_cli/my_cli/command/hello.py
run "cd /ws && colcon build 2>&1 | tail -2"
run "source /ws/install/setup.bash && ros2 hello"
run "source /ws/install/setup.bash && ros2 topic list"
run "source /ws/install/setup.bash && ros2 topic list --no-daemon"
run "source /ws/install/setup.bash && ros2 node list"
run "source /ws/install/setup.bash && ros2 --help | grep -E '^\s+hello'"
echo "--- 6d entry point string points at a class name that does not exist"
sed -i '1d' /ws/src/my_cli/my_cli/command/hello.py
sed -i 's/hello:HelloCommand/hello:HeloCommand/' /ws/src/my_cli/setup.py
run "cd /ws && colcon build 2>&1 | tail -2"
run "source /ws/install/setup.bash && ros2 hello"

sec "7 LD_LIBRARY_PATH and PYTHONPATH missing (sudo, cron, IDE run configs)"
t(){ echo "\$ $1   (last 2 lines shown)"; local s=$(date +%s%N); timeout 60 bash -c "$1" > /tmp/o.txt 2>&1; local rc=$?; tail -n 2 /tmp/o.txt; echo "[exit=$rc wall=$(( ($(date +%s%N)-s)/1000000 ))ms lines=$(wc -l < /tmp/o.txt)]"; }
t "env -u LD_LIBRARY_PATH ros2 bag record -h"
t "env -u LD_LIBRARY_PATH ros2 topic list"
t "env -u LD_LIBRARY_PATH ros2 --help"
t "env -u PYTHONPATH ros2 topic list"
t "env -u AMENT_PREFIX_PATH ros2 topic list"
t "env -u AMENT_PREFIX_PATH ros2 --help"
run "apt-get install -y --no-install-recommends sudo 2>&1 | grep -E 'newly installed|^E:'"
run "sudo -E bash -c 'echo PATH=\$PATH; echo LD_LIBRARY_PATH=\$LD_LIBRARY_PATH; echo PYTHONPATH=\$PYTHONPATH; echo AMENT_PREFIX_PATH=\$AMENT_PREFIX_PATH'"
t "sudo -E ros2 topic list"
t "sudo env PATH=\$PATH ros2 topic list"
t "sudo -E env PATH=\$PATH ros2 topic list"
t "sudo -E env PATH=\$PATH LD_LIBRARY_PATH=\$LD_LIBRARY_PATH PYTHONPATH=\$PYTHONPATH ros2 topic list"
t "sudo bash -c 'source /opt/ros/$D/setup.bash && ros2 topic list'"

sec "8 timing of ros2 --help (5 runs each)"
for i in 1 2 3 4 5; do run "ros2 --help > /dev/null"; done
for i in 1 2 3 4 5; do run "ros2 nosuchverb > /dev/null"; done
echo DONE
