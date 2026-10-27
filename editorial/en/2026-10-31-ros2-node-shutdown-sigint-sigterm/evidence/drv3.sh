#!/bin/bash
set -m
D=$1; source /opt/ros/$D/setup.bash; cd /sd
for t in timer notimer; do
  [ $t = notimer ] && export NOTIMER=1
  res=""
  for i in 1 2 3 4 5; do python3 -u n.py classic > r.txt 2>&1 & p=$!; sleep 2; kill -TERM $p; wait $p; rc=$?
    if grep -q ExternalShutdownException r.txt; then k=ESE; elif grep -q "failed to initialize wait set" r.txt; then k=WAITSET; else k=OTHER; fi
    res="$res $k/exit$rc"; done
  echo "[$D TERM x5 $t]$res"
  unset NOTIMER
done
bash /sd/drv2.sh $D
