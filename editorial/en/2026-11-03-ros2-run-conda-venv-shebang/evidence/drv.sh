#!/bin/bash
D=$1; PYV=$2
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y python3-venv wget >/dev/null 2>&1
source /opt/ros/$D/setup.bash
echo "## $D system python $(/usr/bin/python3 -V 2>&1 | cut -d' ' -f2), tqdm in system: $(/usr/bin/python3 -c 'import tqdm' 2>/dev/null && echo yes || echo no)"
mkdir -p /ws/src && cd /ws/src && ros2 pkg create --build-type ament_python demo --node-name n >/dev/null 2>&1
cat > /ws/src/demo/demo/n.py <<'P'
import sys
def main():
    print("python:", sys.executable)
    try:
        import tqdm; print("tqdm OK", tqdm.__version__)
    except Exception as e: print("ERR", type(e).__name__, e)
    import rclpy; print("rclpy OK")
P
build(){ cd /ws; colcon build >/tmp/b.log 2>&1 || { echo "   build failed: $(tail -2 /tmp/b.log)"; return; }; }
fresh(){ mv /ws/build /tmp/old_build_$RANDOM 2>/dev/null; mv /ws/install /tmp/old_install_$RANDOM 2>/dev/null; }
show(){ s=$(head -1 /ws/install/demo/lib/demo/n); r=$(cd /ws; source install/setup.bash; timeout 20 ros2 run demo n 2>&1 | tr '\n' ' ' | cut -c1-200); echo "[$1] shebang: $s | ros2 run: $r"; }
python3 -m venv --system-site-packages /venv && /venv/bin/pip install -q tqdm
source /venv/bin/activate
echo "   venv active: python3 -> $(command -v python3)"
fresh; build; show venv_default
printf '[build_scripts]\nexecutable = /usr/bin/env python3\n' >> /ws/src/demo/setup.cfg
fresh; build; show venv_setup_cfg_env_python3
sed -i '/\[build_scripts\]/,$d' /ws/src/demo/setup.cfg
fresh; build
r=$(cd /ws; source install/setup.bash; python3 install/demo/lib/demo/n 2>&1 | tr '\n' ' '); echo "[venv_run_with_venv_python] $r"
SP=$(python3 -c 'import site;print(site.getsitepackages()[0])')
r=$(cd /ws; source install/setup.bash; PYTHONPATH=$SP:$PYTHONPATH timeout 20 ros2 run demo n 2>&1 | tr '\n' ' '); echo "[venv_PYTHONPATH_site_packages] $r"
deactivate
cd /tmp && wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O mc.sh && bash mc.sh -b -p /mc >/dev/null 2>&1
/mc/bin/conda create -q -y -n env --override-channels -c conda-forge python=$PYV >/tmp/mcc.log 2>&1 || echo "   conda create failed: $(tail -2 /tmp/mcc.log)" && /mc/envs/env/bin/pip install -q tqdm
export PATH=/mc/envs/env/bin:$PATH
echo "   conda env python3 -> $(command -v python3) $(python3 -V | cut -d' ' -f2)"
fresh; build; show conda_default
printf '[build_scripts]\nexecutable = /usr/bin/env python3\n' >> /ws/src/demo/setup.cfg
fresh; build; show conda_setup_cfg_env_python3
