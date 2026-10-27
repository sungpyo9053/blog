#!/bin/bash
D=$1; PYV=$2
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y python3-venv wget ca-certificates >/dev/null 2>&1
source /opt/ros/$D/setup.bash
echo "## $D"
python3 -m venv /venv >/dev/null && /venv/bin/python3 -c "import rclpy; print('venv(no system site) import rclpy OK')" 2>&1 | tail -2
python3 -m venv --system-site-packages /venv2 >/dev/null && /venv2/bin/python3 -c "import rclpy; print('venv --system-site-packages import rclpy OK')" 2>&1 | tail -2
cd /tmp && wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O mc.sh; echo "   mc.sh bytes: $(stat -c %s mc.sh 2>/dev/null)"
bash mc.sh -b -p /mc > /tmp/mci.log 2>&1; echo "   install rc=$? $(tail -1 /tmp/mci.log)"
/mc/bin/conda create -y -n env python=$PYV > /tmp/mcc.log 2>&1; echo "   create rc=$? $(grep -i -E "error|tos|terms" /tmp/mcc.log | head -3 | tr '\n' ' ')"
ls /mc/envs/env/bin/python3 2>&1
