#!/bin/bash
# Run on the measurement host. Usage: ./repro.sh humble|jazzy|lyrical [inner|extra]
# Expects ./src (tfpy.py, tfnode.py, extra.py, inner.sh, extra.sh) next to this script.
# out_<distro>.txt = "inner" output followed by "extra" output.
set -u
d=$1
docker run --rm --name pk74-$d --network none \
  -e ROS_DOMAIN_ID=88 -e ROS_LOCALHOST_ONLY=1 -e ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  -e PYTHONUNBUFFERED=1 -e RCUTILS_COLORIZED_OUTPUT=0 \
  --ulimit core=0 --pids-limit 128 --cpus 1.5 \
  -v "$PWD/src:/src:ro" ros:$d-ros-base bash /src/${2:-inner}.sh
