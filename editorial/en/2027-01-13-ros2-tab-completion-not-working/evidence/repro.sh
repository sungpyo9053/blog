#!/bin/bash
# ros2 / colcon tab completion in bash and zsh, measured with real key presses in tmux
# and with the argcomplete protocol directly.
#
#   bash repro.sh host <distro>    on the Docker host: builds pk35img:<distro> (adds tmux, zsh,
#                                  a pip argcomplete in a separate user base), then runs the
#                                  test below in a --network none container.
#   bash repro.sh test             inside the container (called by host mode).
MODE=${1:-test}

if [ "$MODE" = host ]; then
  D=$2; W=/tmp/en-pick45
  if [ "$D" = humble ]; then RANGE="-e ROS_LOCALHOST_ONLY=1"; else RANGE="-e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"; fi
  docker rm -f pk35-build-$D >/dev/null 2>&1
  # Build step needs the network for apt and pip only. Nothing ROS runs here.
  timeout 600 docker run --name pk35-build-$D --ulimit core=0 ros:$D-ros-base bash -c '
    set -e; export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null
    apt-get install -y -qq --no-install-recommends tmux zsh python3-pip >/dev/null
    BSP=""; pip3 install --help | grep -q break-system-packages && BSP=--break-system-packages
    PYTHONUSERBASE=/opt/pipuser pip3 install -q --user --ignore-installed $BSP argcomplete
    rm -rf /var/lib/apt/lists/*'
  docker commit pk35-build-$D pk35img:$D >/dev/null && docker rm pk35-build-$D >/dev/null
  # Test step: no network, separate domain, localhost discovery, no core dumps.
  timeout 900 docker run --rm --name pk35-test-$D --network none --ulimit core=0 --pids-limit 256 \
    -e ROS_DOMAIN_ID=88 $RANGE -v $W:/w:ro pk35img:$D bash /w/repro.sh test
  exit $?
fi

ulimit -c 0
D=$ROS_DISTRO
echo "=== distro=$D  $(. /etc/os-release; echo $PRETTY_NAME)"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-ros2launch ros-$D-rmw \
  python3-argcomplete python3-colcon-argcomplete python3-colcon-core bash zsh tmux 2>/dev/null
echo "pip argcomplete in /opt/pipuser: $(PYTHONUSERBASE=/opt/pipuser python3 -c 'import argcomplete,importlib.metadata as m;print(m.version("argcomplete"), argcomplete.__file__)')"
echo "--- register scripts on PATH"
for c in register-python-argcomplete register-python-argcomplete3 activate-global-python-argcomplete; do printf '%s: %s\n' $c "$(command -v $c || echo missing)"; done
echo "--- colcon argcomplete hooks"; ls /usr/share/colcon_argcomplete/hook/ 2>&1
echo "--- ros2cli completion files"; ls /opt/ros/$D/share/ros2cli/environment/
echo "--- ros2-argcomplete.bash"; cat /opt/ros/$D/share/ros2cli/environment/ros2-argcomplete.bash
echo "--- ros2-argcomplete.zsh"; cat /opt/ros/$D/share/ros2cli/environment/ros2-argcomplete.zsh

# A fake installed package with launch files, registered in the ament index (no build needed).
P=/tmp/ws/install/my_bringup; mkdir -p $P/share/my_bringup/launch $P/share/ament_index/resource_index/packages
touch $P/share/ament_index/resource_index/packages/my_bringup
for f in robot.launch.py robot_launch.py robot.py view.launch.xml sim.launch.yaml bringup_launch.xml params.yaml; do
  echo "# $f" > $P/share/my_bringup/launch/$f; done
echo "# top" > $P/share/my_bringup/top.launch.py

# tmux driver: start a fresh login-less interactive shell with its own HOME, type text, press Tab.
tt() { # tt <case> <shell> <typed> <tabs>
  local c=$1 sh=$2 typed=$3 tabs=$4
  tmux kill-server 2>/dev/null
  tmux new-session -d -s t -x 160 -y 40 "env -i TERM=xterm-256color PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/h/$c ROS_DOMAIN_ID=$ROS_DOMAIN_ID ${ROS_LOCALHOST_ONLY:+ROS_LOCALHOST_ONLY=1} ${ROS_AUTOMATIC_DISCOVERY_RANGE:+ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST} ${EXTRA_ENV:-} $sh -i"
  sleep 4; tmux send-keys -t t "clear" Enter; sleep 1
  tmux send-keys -t t -l "$typed"
  for i in $(seq $tabs); do tmux send-keys -t t Tab; sleep 2.5; done
  sleep 1
  echo "### case=$c shell=$sh typed='$typed' tabs=$tabs"
  tmux capture-pane -t t -p | sed '/^$/d' | head -25
  tmux kill-server 2>/dev/null
}
mk() { mkdir -p /h/$1; cat > /h/$1/$2; }

RC="source /opt/ros/$D/setup.bash"
ZRC="source /opt/ros/$D/setup.zsh"
REG=$(command -v register-python-argcomplete || command -v register-python-argcomplete3)
REG=$(basename $REG)

echo "=== tmux tests"
# bash
mk bash_rc .bashrc <<<"$RC"
mk bash_none .bashrc </dev/null
mk bash_pip .bashrc <<<"$RC"
mk bash_colcon .bashrc <<<"$RC
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash"
for t in "ros2 ru|1" "ros2 run tf2_r|2" "ros2 launch my_bringup |2" "colcon bu|1"; do
  EXTRA_ENV="AMENT_PREFIX_PATH=$P" tt bash_rc bash "${t%|*}" "${t#*|}"; done
# Environment inherited from a parent that sourced setup.bash (like docker exec into an image whose
# entrypoint sourced it), but this shell did not source anything itself.
EXTRA_ENV="$(source /opt/ros/$D/setup.bash; echo PATH=$PATH AMENT_PREFIX_PATH=$AMENT_PREFIX_PATH PYTHONPATH=$PYTHONPATH LD_LIBRARY_PATH=$LD_LIBRARY_PATH ROS_DISTRO=$ROS_DISTRO ROS_VERSION=2 ROS_PYTHON_VERSION=3)"
EXTRA_ENV="$EXTRA_ENV" tt bash_none bash "ros2 ver" 1
EXTRA_ENV="$EXTRA_ENV" tt bash_none bash "ros2 run tf2_r" 2
EXTRA_ENV="PYTHONUSERBASE=/opt/pipuser" tt bash_pip bash "ros2 ru" 1
EXTRA_ENV="PYTHONUSERBASE=/opt/pipuser" tt bash_pip bash "ros2 run tf2_r" 2
tt bash_colcon bash "colcon bu" 1
# zsh
mk zsh_only .zshrc <<<"$ZRC"
mk zsh_compinit_after .zshrc <<<"$ZRC
autoload -Uz compinit && compinit"
mk zsh_compinit_before .zshrc <<<"autoload -Uz compinit && compinit
$ZRC"
mk zsh_fix .zshrc <<<"$ZRC
autoload -Uz compinit && compinit
eval \"\$($REG ros2)\""
mk zsh_fix_colcon .zshrc <<<"$ZRC
autoload -Uz compinit && compinit
eval \"\$($REG ros2)\"
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.zsh"
mk zsh_eval_only .zshrc <<<"$ZRC
eval \"\$($REG ros2)\""
mk zsh_compdef .zshrc <<<"$ZRC
compdef _ros2_argcomplete ros2"
mk zsh_complete_line .zshrc <<<"$ZRC
autoload -Uz compinit && compinit
complete -o nospace -o default -F _python_argcomplete ros2"
for c in zsh_only zsh_compinit_after zsh_compinit_before zsh_eval_only zsh_compdef zsh_fix zsh_complete_line; do
  tt $c zsh "ros2 ru" 1
  tt $c zsh "ros2 run tf2_r" 2
done
EXTRA_ENV="AMENT_PREFIX_PATH=$P:/opt/ros/$D" tt zsh_fix zsh "ros2 launch my_bringup " 2
tt zsh_fix zsh "colcon bu" 1
tt zsh_fix_colcon zsh "colcon bu" 1
EXTRA_ENV="PYTHONUSERBASE=/opt/pipuser" tt zsh_fix zsh "ros2 ru" 1
EXTRA_ENV="PYTHONUSERBASE=/opt/pipuser" tt zsh_fix zsh "ros2 run tf2_r" 2
echo "--- which completion files does each setup file source? (AMENT_TRACE_SETUP_FILES=1)"
env HOME=/h/zsh_only AMENT_TRACE_SETUP_FILES=1 zsh -c "source /opt/ros/$D/setup.zsh" 2>&1 | grep -i argcomplete | sed 's/^/zsh: /'
env AMENT_TRACE_SETUP_FILES=1 bash -c "source /opt/ros/$D/setup.bash" 2>&1 | grep -i argcomplete | sed 's/^/bash: /'
echo "--- zsh: after sourcing setup.zsh in an interactive zsh, which helper functions exist?"
env HOME=/h/zsh_only zsh -i -c 'for f in _python_argcomplete __python_argcomplete_run _ros2_argcomplete _bash_complete compdef complete; do print -r -- "$f: ${+functions[$f]}"; done' 2>&1
echo "--- rosidl-argcomplete.zsh (sourced right after ros2-argcomplete.zsh)"
grep -v '^#' /opt/ros/$D/share/rosidl_cli/environment/rosidl-argcomplete.zsh | sed '/^$/d'
echo "--- zsh: registrations right after sourcing only ros2-argcomplete.zsh, then after the full setup.zsh"
env HOME=/h/zsh_compinit_before zsh -i -c 'source /opt/ros/'$D'/share/ros2cli/environment/ros2-argcomplete.zsh; print -r -- "ros2-argcomplete.zsh alone: comps[ros2]=${_comps[ros2]:-<none>}"' 2>&1 | tail -1
env HOME=/h/zsh_only zsh -i -c 'print -r -- "setup.zsh: comps[ros2]=${_comps[ros2]:-<none>} comps[rosidl]=${_comps[rosidl]:-<none>}"' 2>&1 | tail -1
echo "--- ros2launch: which file names the launch completer accepts"
python3 -c "from ros2launch.api.api import is_launch_file; print('is_launch_file.extensions =', is_launch_file.extensions)" 2>&1
grep -rn "fnmatch\|endswith\|glob\|_launch\.\|\.launch" /opt/ros/$D/lib/python3*/site-packages/ros2launch/api/api.py | head -12
echo "--- zsh: is ros2 registered after each .zshrc? (non-interactive check with zsh -i -c)"
for c in zsh_only zsh_compinit_after zsh_compinit_before zsh_eval_only zsh_compdef zsh_fix zsh_complete_line; do
  printf '%-22s %s\n' $c "$(env HOME=/h/$c zsh -i -c 'print -r -- "comps[ros2]=${_comps[ros2]:-<none>}"' 2>&1 | tail -1)"; done

echo "=== argcomplete protocol: what ros2 returns and how long it takes"
source /opt/ros/$D/setup.bash
export AMENT_PREFIX_PATH=$P:$AMENT_PREFIX_PATH
ac() { # ac <line>  -> prints candidate count, wall ms, first candidates
  local line=$1 t0 t1 out
  t0=$(date +%s%N)
  out=$(COMP_LINE="$line" COMP_POINT=${#line} _ARGCOMPLETE=1 _ARGCOMPLETE_SHELL=bash _ARGCOMPLETE_IFS=$'\n' ros2 8>&1 9>/dev/null)
  t1=$(date +%s%N)
  printf '%-45s n=%-4s %5d ms  %s\n' "'$line'" "$(printf '%s' "$out" | grep -c .)" $(( (t1-t0)/1000000 )) "$(printf '%s' "$out" | head -8 | tr '\n' ' ')"
}
for i in 1 2 3; do ac "ros2 "; done
for i in 1 2 3; do ac "ros2 run "; done
for i in 1 2 3; do ac "ros2 run tf2_ros "; done
ac "ros2 launch my_bringup "
ac "ros2 launch my_bringup r"
ac "ros2 interface show std_msgs/msg/Str"
echo "--- message template completion (ros2 topic pub)"
line="ros2 topic pub /p geometry_msgs/msg/Point "
COMP_LINE="$line" COMP_POINT=${#line} _ARGCOMPLETE=1 _ARGCOMPLETE_SHELL=bash _ARGCOMPLETE_IFS=$'\n' ros2 8>&1 9>/dev/null | head -5 | cat -A | cut -c1-150
echo "--- topic name completion: needs the daemon"
ros2 daemon stop >/dev/null 2>&1
ros2 topic pub -r 5 /chatter std_msgs/msg/String "{data: hi}" >/dev/null 2>&1 &
PUB=$!; sleep 3
ac "ros2 topic echo /ch"
ac "ros2 topic echo /ch"
ac "ros2 topic echo /ch"
ros2 daemon stop >/dev/null 2>&1
ac "ros2 topic echo /ch"
kill $PUB; wait $PUB 2>/dev/null
ros2 daemon stop >/dev/null 2>&1
echo "--- pip argcomplete (PYTHONUSERBASE=/opt/pipuser) with the apt shell glue"
export PYTHONUSERBASE=/opt/pipuser
ac "ros2 run "
ac "ros2 run tf2_r"
echo "=== end $D"
