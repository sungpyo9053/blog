#!/bin/bash
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y wget >/dev/null 2>&1
source /opt/ros/jazzy/setup.bash
cd /tmp && wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O mc.sh && bash mc.sh -b -p /mc >/dev/null 2>&1
/mc/bin/conda create -q -y -n env --override-channels -c conda-forge python=3.12 >/dev/null 2>&1
/mc/envs/env/bin/python3 -c "import rclpy" 2>&1 | tail -3
/mc/envs/env/bin/python3 -m pip install -q pyyaml 2>/dev/null; echo "after pip install pyyaml:"; /mc/envs/env/bin/python3 -c "import rclpy; print('rclpy OK')" 2>&1 | tail -2
