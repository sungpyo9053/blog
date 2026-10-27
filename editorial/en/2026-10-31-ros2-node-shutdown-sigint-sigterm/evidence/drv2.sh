#!/bin/bash
set -m
D=$1; source /opt/ros/$D/setup.bash; cd /sd
export SLOW=14
lrun(){ label=$1; shift; s=$(date +%s.%N); ros2 launch /sd/l.py "$@" > lo2.txt 2>&1 & p=$!; sleep 4; kill -INT $p; ( sleep 60; kill -9 $p 2>/dev/null ) & wait $p; rc=$?; e=$(date +%s.%N); echo "[launch14 $label] launch exit=$rc took $(python3 -c "print(round($e-$s-4,1))")s after Ctrl+C"; grep -E "finally|cleanup|escalat|failed to terminate|exited|caught|ERROR" lo2.txt | sed -E 's/^\[[^]]*\] //' | sed 's/^/    /' | head -8; }
lrun default
lrun cli_arg sigterm_timeout:=20
KW=1 lrun action_kwarg_15
