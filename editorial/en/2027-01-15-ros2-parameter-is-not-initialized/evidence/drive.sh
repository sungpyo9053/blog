#!/bin/bash
# usage: drive.sh <distro>   (runs on the runner, one distro at a time)
set -u; D=$1; cd /tmp/en-pick47; ulimit -c 0
uptime
L=$(cut -d' ' -f1 /proc/loadavg); awk -v l=$L 'BEGIN{exit !(l<4)}' || { echo "load $L too high"; exit 1; }
if [ "$D" = humble ]; then E="-e ROS_LOCALHOST_ONLY=1"; else E="-e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST"; fi
if [ "$D" != jazzy ]; then timeout 600 docker pull -q ros:$D-ros-base; fi
docker image inspect ros:$D-ros-base --format "ros:$D-ros-base id={{.Id}} digest={{index .RepoDigests 0}} created={{.Created}}" >> digests_img.txt
timeout 1500 docker run --rm --name pk37-$D --ulimit core=0 --pids-limit 256 --cpus 1.5 -e ROS_DOMAIN_ID=88 $E \
  -v /tmp/en-pick47:/w ros:$D-ros-base bash /w/repro.sh > out_$D.txt 2>&1
echo "run exit=$?"; uptime
