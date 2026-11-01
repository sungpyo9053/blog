#!/bin/bash
# Stale / missing entries in `ros2 node list` and the ros2 daemon cache.
# Host:  bash repro.sh host <distro>      (creates dmn-<distro>-* containers, runs everything, removes them)
# Inner: bash repro.sh inner <test>       (runs inside the container, called by host mode)
# Files live in /tmp/en-daemon on the host, mounted read-only at /r in every container.
set -u
MODE=${1:-}; shift || true

if [ "$MODE" = host ]; then
  D=$1; IMG=ros:$D-ros-base; NET=dmn-net-$D; A=dmn-$D-a
  RUN="--ulimit core=0 --pids-limit 128 --cpus 1.5 --network $NET -v /tmp/en-daemon:/r:ro"
  echo "=== HOST distro=$D image=$IMG $(date -u +%FT%TZ)"; uptime
  docker network create $NET >/dev/null
  docker run -d --name $A $RUN $IMG sleep infinity >/dev/null
  X() { docker exec "$@"; }
  X $A bash /r/repro.sh inner versions
  echo "=== install rmw_cyclonedds_cpp (apt)"; uptime
  X $A bash -c "apt-get update -qq >/dev/null 2>&1 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ros-$D-rmw-cyclonedds-cpp >/dev/null 2>&1 && echo CYCLONE_INSTALLED || echo CYCLONE_INSTALL_FAILED"
  X $A bash /r/repro.sh inner versions_cyclone
  for T in startup appear_and_signals domain fixes; do
    echo; echo "########## TEST $T (fastdds)"; uptime
    X $A bash /r/repro.sh inner $T
  done
  # remote container: talker as PID 1 in a second container
  echo; echo "########## TEST remote_container (fastdds)"; uptime
  X $A bash /r/repro.sh inner daemon_fresh
  B=dmn-$D-b
  T0=$(date +%s.%N)
  docker run -d --name $B $RUN $IMG bash -c "source /opt/ros/$D/setup.bash; exec python3 /r/talker.py talker_remote" >/dev/null
  X $A bash /r/repro.sh inner poll_appear talker_remote $T0
  echo "--- docker stop $B (sends SIGTERM to PID 1, SIGKILL after 10 s)"
  T0=$(date +%s.%N); docker stop $B >/dev/null
  echo "docker stop returned after $(python3 -c "import time;print(round(time.time()-$T0,2))") s"
  X $A bash /r/repro.sh inner poll_gone talker_remote $T0
  docker rm $B >/dev/null
  B=dmn-$D-c
  docker run -d --name $B $RUN $IMG bash -c "source /opt/ros/$D/setup.bash; exec python3 /r/talker.py talker_remote2" >/dev/null
  X $A bash /r/repro.sh inner poll_appear talker_remote2 $(date +%s.%N) >/dev/null
  echo "--- docker kill $B (SIGKILL)"
  T0=$(date +%s.%N); docker kill $B >/dev/null
  X $A bash /r/repro.sh inner poll_gone talker_remote2 $T0
  docker rm $B >/dev/null
  if X $A bash -c "test -e /opt/ros/$D/lib/librmw_cyclonedds_cpp.so"; then
    echo; echo "########## TEST appear_and_signals (cyclonedds)"; uptime
    X -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp $A bash /r/repro.sh inner appear_and_signals
    echo; echo "########## TEST rmw_mismatch"; uptime
    X $A bash /r/repro.sh inner rmw_mismatch
  else
    echo "rmw_cyclonedds_cpp not available: cyclone tests skipped"
  fi
  docker rm -f $A >/dev/null; docker network rm $NET >/dev/null
  echo "=== HOST done $(date -u +%FT%TZ)"; uptime
  exit 0
fi

# ---------------- inner (inside container) ----------------
set +u; source /opt/ros/$ROS_DISTRO/setup.bash
ulimit -c 0
now() { date +%s.%N; }
# PID 1 here is `sleep infinity`, which never reaps, so a dead talker stays a zombie: treat state Z as dead
alive() { [ -r /proc/$1/stat ] && [ "$(awk '{print $3}' /proc/$1/stat)" != Z ]; }
el() { python3 -c "print(f'{$(now)-$1:.2f}')"; }
# run a command, print "<elapsed_since_T0> <duration> <present|absent>"
probe() { # name t0 cmd...
  local n=$1 t0=$2; shift 2; local s=$(now); local out; out=$(timeout 30 "$@" 2>&1)
  local d=$(python3 -c "print(f'{$(now)-$s:.2f}')")
  if echo "$out" | grep -qx "/$n"; then echo "present $(el $t0) dur=$d"; else echo "absent $(el $t0) dur=$d"; fi
}
start_talker() { # name [extra env]  -> pid
  setsid python3 /r/talker.py "$1" >/tmp/$1.log 2>&1 < /dev/null &
  echo $!
}
poll_appear() { # name t0 : until visible in both, max 30 s
  local n=$1 t0=$2 gd= gn=
  for i in $(seq 1 30); do
    [ -z "$gd" ] && { r=$(probe $n $t0 ros2 node list); echo "  daemon    $r"; case $r in present*) gd=1;; esac; }
    [ -z "$gn" ] && { r=$(probe $n $t0 ros2 node list --no-daemon); echo "  no-daemon $r"; case $r in present*) gn=1;; esac; }
    [ -n "$gd" ] && [ -n "$gn" ] && break; sleep 0.5
  done
}
poll_gone() { # name t0 : until gone from both, max ~60 s; also topic list via daemon
  local n=$1 t0=$2 gd= gn= gt=
  while :; do
    e=$(el $t0); python3 -c "import sys;sys.exit(0 if $e<62 else 1)" || { echo "  STILL LISTED at $e s: daemon=${gd:-yes} nodaemon=${gn:-yes}"; break; }
    [ -z "$gd" ] && { r=$(probe $n $t0 ros2 node list); echo "  daemon    $r"; case $r in absent*) gd=gone;; esac; }
    [ -z "$gn" ] && { r=$(probe $n $t0 ros2 node list --no-daemon); echo "  no-daemon $r"; case $r in absent*) gn=gone;; esac; }
    [ -z "$gt" ] && { o=$(timeout 30 ros2 topic list -v 2>&1 | grep -A0 "/chatter_$n " ); echo "  topic(daemon) $(el $t0) ${o:-'/chatter_'$n' not listed'}"; [ -z "$o" ] && gt=gone; }
    [ -n "$gd" ] && [ -n "$gn" ] && [ -n "$gt" ] && break
    sleep 1
  done
}
daemon_fresh() { ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 1; }

case $1 in
versions|versions_cyclone)
  echo "=== distro=$ROS_DISTRO rmw_default=$(ros2 doctor --report 2>/dev/null | grep -m1 'middleware name' | awk '{print $NF}')"
  dpkg-query -W -f='${Package} ${Version}\n' ros-$ROS_DISTRO-rclpy ros-$ROS_DISTRO-rclcpp ros-$ROS_DISTRO-ros2cli ros-$ROS_DISTRO-ros2node ros-$ROS_DISTRO-rmw-fastrtps-cpp ros-$ROS_DISTRO-fastrtps ros-$ROS_DISTRO-fastdds ros-$ROS_DISTRO-rmw-cyclonedds-cpp ros-$ROS_DISTRO-cyclonedds 2>/dev/null
  python3 --version ;;
poll_appear) poll_appear $2 $3 ;;
poll_gone) poll_gone $2 $3 ;;
daemon_fresh) daemon_fresh ;;
startup)
  echo "--- daemon cost: no daemon running, no nodes"
  ros2 daemon stop; ros2 daemon status; echo "status exit=$?"
  for k in 1 2 3; do s=$(now); ros2 node list >/dev/null 2>&1; echo "node list call $k (daemon): $(el $s) s"; done
  ros2 daemon status; echo "status exit=$?"
  for k in 1 2; do s=$(now); ros2 node list --no-daemon >/dev/null 2>&1; echo "node list --no-daemon call $k: $(el $s) s"; done
  echo "--- talker already running, daemon stopped, first call starts daemon"
  P=$(start_talker talker_pre); sleep 4
  for rep in 1 2; do
    ros2 daemon stop; T0=$(now)
    for k in $(seq 1 12); do s=$(now); o=$(ros2 node list 2>&1 | tr '\n' ' '); echo "rep $rep call $k at +$(el $T0) s after daemon stop, took $(el $s) s -> [${o}]"; sleep 0.5; done
  done
  for k in 1 2 3 4 5; do s=$(now); o=$(ros2 node list --no-daemon 2>&1 | tr '\n' ' '); echo "--no-daemon call $k: $(el $s) s -> [${o}]"; done
  for st in 0 1 3; do s=$(now); ros2 daemon stop >/dev/null; o=$(ros2 node list --spin-time $st 2>&1 | tr '\n' ' '); echo "daemon stopped, ros2 node list --spin-time $st: $(el $s) s -> [${o}]"; done
  kill -INT $P; sleep 2 ;;
appear_and_signals)
  echo "rmw=${RMW_IMPLEMENTATION:-default}"
  j=0
  for SIG in INT TERM KILL KILL; do
    j=$((j+1)); N=talker_sig$(echo $SIG | tr A-Z a-z)$j
    daemon_fresh
    echo "--- start $N (daemon running, started 1 s earlier)"
    T0=$(now); P=$(start_talker $N); poll_appear $N $T0
    sleep 3
    echo "--- kill -$SIG $N (pid $P)"
    T0=$(now); kill -$SIG $P
    for i in $(seq 1 50); do alive $P || break; sleep 0.1; done
    alive $P && echo "process still alive after 5 s" || echo "process exited after $(el $T0) s"
    echo "talker log tail: $(tail -2 /tmp/$N.log | tr '\n' '|')"
    poll_gone $N $T0
    kill -9 $P 2>/dev/null
  done ;;
domain)
  echo "--- daemon for domain 0 running; talker_d0 on domain 0"
  daemon_fresh; P=$(start_talker talker_d0); sleep 4
  echo "ROS_DOMAIN_ID unset: [$(ros2 node list | tr '\n' ' ')]"
  echo "ROS_DOMAIN_ID=5: [$(ROS_DOMAIN_ID=5 ros2 node list | tr '\n' ' ')]"
  echo "ROS_DOMAIN_ID=5 --no-daemon: [$(ROS_DOMAIN_ID=5 ros2 node list --no-daemon | tr '\n' ' ')]"
  echo "ros2 daemon status (domain unset): $(ros2 daemon status)"
  echo "ros2 daemon status (domain 5): $(ROS_DOMAIN_ID=5 ros2 daemon status)"
  echo "_ros2_daemon processes:"
  for p in /proc/[0-9]*; do c=$(tr '\0' ' ' < $p/cmdline 2>/dev/null); case $c in *daemon*) echo "  pid ${p#/proc/} domain=$(tr '\0' '\n' < $p/environ | grep '^ROS_DOMAIN_ID=' || echo unset) cmd=${c:0:160}";; esac; done
  echo "--- talker_d5 on domain 5, shell on domain 0"
  P5=$(ROS_DOMAIN_ID=5 start_talker talker_d5); sleep 4
  echo "domain unset: [$(ros2 node list | tr '\n' ' ')]"
  echo "domain 5: [$(ROS_DOMAIN_ID=5 ros2 node list | tr '\n' ' ')]"
  kill -INT $P $P5; sleep 2
  ROS_DOMAIN_ID=5 ros2 daemon stop ;;
fixes)
  for F in wait nodaemon restart spintime topic_nodaemon; do
    N=talker_fix_$F; daemon_fresh
    P=$(start_talker $N); T0=$(now); poll_appear $N $T0 >/dev/null; sleep 3
    T0=$(now); kill -KILL $P; sleep 0.5
    echo "--- SIGKILL $N, then fix=$F"
    case $F in
      wait) echo "  daemon list at +0.5 s: $(probe $N $T0 ros2 node list)";;
      nodaemon) echo "  $(probe $N $T0 ros2 node list --no-daemon)";;
      restart) s=$(now); ros2 daemon stop >/dev/null; ros2 daemon start >/dev/null; echo "  stop+start took $(el $s) s"
               for k in 1 2 3; do echo "  call $k: $(probe $N $T0 ros2 node list)"; done;;
      spintime) echo "  --spin-time 5 with daemon: $(probe $N $T0 ros2 node list --spin-time 5)";;
      topic_nodaemon) o=$(ros2 topic list --no-daemon | grep -x "/chatter_$N"); echo "  topic list --no-daemon at $(el $T0): ${o:-not listed}";;
    esac
  done ;;
rmw_mismatch)
  echo "--- daemon started with default rmw; talker_cyc and shell use rmw_cyclonedds_cpp"
  daemon_fresh
  P=$(RMW_IMPLEMENTATION=rmw_cyclonedds_cpp start_talker talker_cyc); sleep 4
  echo "shell cyclone, daemon list: [$(RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 node list 2>&1 | tr '\n' ' ')]"
  echo "shell cyclone, --no-daemon: [$(RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 node list --no-daemon 2>&1 | tr '\n' ' ')]"
  echo "shell default, daemon list: [$(ros2 node list 2>&1 | tr '\n' ' ')]"
  kill -INT $P; sleep 2 ;;
esac
