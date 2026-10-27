#!/bin/bash
set -m  # background jobs must not inherit SIG_IGN for SIGINT
D=$1; source /opt/ros/$D/setup.bash; cd /sd
echo "## $D rclpy $(python3 -c 'import importlib.metadata as m;print(m.version("rclpy"))') launch $(python3 -c 'import importlib.metadata as m;print(m.version("launch"))' 2>/dev/null) init-ctx $(python3 -c 'import rclpy,inspect;print(hasattr(rclpy.init(),"__enter__"))' 2>/dev/null)"
run(){ m=$1; sig=$2; python3 -u n.py $m > o.txt 2>&1 & p=$!; sleep 3; kill -$sig $p; wait $p; rc=$?; echo "[$m $sig] exit=$rc"; grep -v "^\s*$" o.txt | grep -E "^\[|Error|error|Traceback" | sed 's/^/    /' | head -8; }
for m in classic try_shutdown ctx; do for s in INT TERM; do run $m $s; done; done
lrun(){ label=$1; shift; s=$(date +%s.%N); ros2 launch /sd/l.py "$@" > lo.txt 2>&1 & p=$!; sleep 4; kill -INT $p; ( sleep 60; kill -9 $p 2>/dev/null ) & g=$!; wait $p; e=$(date +%s.%N); echo "[launch $label] launch exit=$? took $(python3 -c "print(round($e-$s-4,1))")s after Ctrl+C"; grep -E "finally|cleanup|escalat|failed to terminate|exited|caught|ERROR" lo.txt | sed -E 's/^\[[^]]*\] //' | sed 's/^/    /' | head -8; }
lrun default
lrun cli_arg sigterm_timeout:=15
KW=1 lrun action_kwarg
python3 -u n.py classic > z.txt 2>&1 & p=$!; sleep 3; ros2 node list >/dev/null 2>&1; echo "    before kill (daemon): $(ros2 node list 2>/dev/null | tr '\n' ' ')"; kill -9 $p; wait $p 2>/dev/null
echo "    right after kill -9: no-daemon=[$(ros2 node list --no-daemon 2>/dev/null | tr '\n' ' ')] daemon=[$(ros2 node list 2>/dev/null | tr '\n' ' ')]"
s=$(date +%s); while ros2 node list 2>/dev/null | grep -q sd_node; do [ $(( $(date +%s)-s )) -gt 40 ] && break; sleep 1; done; echo "[zombie] killed node left daemon list after $(( $(date +%s)-s ))s (cap 40)"
ros2 daemon stop >/dev/null 2>&1; echo "    after daemon stop: [$(ros2 node list 2>/dev/null | tr '\n' ' ')]"
