#!/bin/bash
# Run inside ros:<distro>-ros-base as root:
#   docker run --rm --name np2-$D -v /tmp/en-np2:/w ros:$D-ros-base bash /w/repro.sh
# Shows which apt-built ROS 2 Python pieces break when pip puts NumPy 2.x on top of
# the apt NumPy, and which fixes bring them back.
export DEBIAN_FRONTEND=noninteractive PIP_ROOT_USER_ACTION=ignore PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_ONLY_BINARY=:all:   # wheels only, never build numpy from source
D=$ROS_DISTRO
echo "=== distro=$D"
apt-get update -qq >/dev/null
apt-get install -y -qq python3-pip python3-venv ros-$D-cv-bridge ros-$D-sensor-msgs-py >/dev/null 2>&1 \
  || echo "APT INSTALL FAILED (base set)"
apt-get install -y -qq ros-$D-tf-transformations >/dev/null 2>&1 || echo "ros-$D-tf-transformations: not installable"
. /etc/os-release; echo "os: $PRETTY_NAME"
python3 --version; pip3 --version
dpkg-query -W -f='${Package} ${Version}\n' python3-numpy python3-opencv ros-$D-cv-bridge ros-$D-sensor-msgs-py \
  ros-$D-tf-transformations python3-transforms3d ros-$D-rclpy libopencv-core-dev 2>/dev/null
echo "--- cv_bridge boost module links:"
ls /opt/ros/$D/local/lib/python3*/dist-packages/cv_bridge/boost/ 2>/dev/null || find /opt/ros/$D -path '*cv_bridge/boost*' -name '*.so'
source /opt/ros/$D/setup.bash

cat > /tmp/tests.py <<'PY'
import sys
t = sys.argv[1]
if t == 'numpy':
    import numpy; print(numpy.__version__, numpy.__file__)
elif t == 'cv2':
    import cv2; print(cv2.__version__, cv2.__file__, 'CV_8UC3=', cv2.CV_8UC3)
elif t == 'import_cv_bridge':
    import cv_bridge; from cv_bridge import CvBridge
    print('import ok; boost getCvType loaded:', hasattr(cv_bridge, 'getCvType'))
elif t == 'cv_bridge_roundtrip':
    import numpy as np
    from cv_bridge import CvBridge
    b = CvBridge()
    a = np.random.randint(0, 255, (48, 64, 3), np.uint8)
    m = b.cv2_to_imgmsg(a, 'bgr8')
    r = b.imgmsg_to_cv2(m, 'bgr8'); print('bgr8', r.shape, bool((r == a).all()))
    g = b.imgmsg_to_cv2(m, 'mono8'); print('bgr8->mono8', g.shape)
    d = np.arange(12, dtype=np.uint16).reshape(3, 4)
    print('16UC1', b.imgmsg_to_cv2(b.cv2_to_imgmsg(d, '16UC1')).dtype)
elif t == 'pc2_read_points_numpy':
    from sensor_msgs_py import point_cloud2 as pc2
    from std_msgs.msg import Header
    c = pc2.create_cloud_xyz32(Header(frame_id='map'), [[1, 2, 3], [4, 5, 6]])
    print(pc2.read_points_numpy(c).tolist())
elif t == 'msg_float64_fixed':   # sensor_msgs/Imu float64[9]
    from sensor_msgs.msg import Imu
    from rclpy.serialization import serialize_message, deserialize_message
    m = Imu(); m.orientation_covariance = [0.5] * 9
    r = deserialize_message(serialize_message(m), Imu)
    print(type(r.orientation_covariance).__name__, r.orientation_covariance[0])
elif t == 'msg_float64_seq':     # sensor_msgs/JointState float64[]
    import numpy as np
    from sensor_msgs.msg import JointState
    from rclpy.serialization import serialize_message, deserialize_message
    m = JointState(); m.position = np.array([1.0, 2.0]).tolist()
    r = deserialize_message(serialize_message(m), JointState)
    print(type(r.position).__name__, list(r.position))
elif t == 'tf_transformations':
    import tf_transformations as tt
    print(tt.quaternion_from_euler(0, 0, 1.5707963))
PY

run_tests() {  # $1=python $2=label
  echo; echo "##### SCENARIO: $2  (python=$1)"
  for t in numpy cv2 import_cv_bridge cv_bridge_roundtrip pc2_read_points_numpy msg_float64_fixed msg_float64_seq tf_transformations; do
    out=$(timeout 60 "$1" /tmp/tests.py $t 2>&1); rc=$?
    echo "--- $t rc=$rc"; echo "$out" | head -40
  done
}
pipi() { echo "\$ $*"; "$@" 2>&1 | grep -vE '^\s*(Downloading|Using cached|Collecting|Requirement already satisfied: (pip|setuptools|wheel))' | tail -15; }

if [ "$EXTRA" = 1 ]; then   # second pass, Jazzy: force a pip NumPy 2 next to the Debian one
  B=--break-system-packages
  echo "##### EXTRA: does pip uninstall --break-system-packages remove a Debian package's files?"
  python3 -c "import transforms3d; print('transforms3d', transforms3d.__version__, transforms3d.__file__)"
  pipi pip3 uninstall -y $B transforms3d
  python3 -c "import transforms3d" 2>&1 | tail -1; dpkg-query -W -f='dpkg still lists: ${Package} ${Version} ${Status}\n' python3-transforms3d
  apt-get install -y -qq --reinstall python3-transforms3d >/dev/null 2>&1; echo "apt reinstalled python3-transforms3d"
  pipi pip3 install $B --ignore-installed numpy
  run_tests python3 "X1 pip --ignore-installed numpy (latest) next to apt 1.26"
  pipi pip3 uninstall -y $B numpy
  run_tests python3 "X2 pip numpy uninstalled again (apt fallback)"
  pipi pip3 install $B --ignore-installed opencv-python
  run_tests python3 "X3 pip --ignore-installed opencv-python (latest)"
  pipi pip3 uninstall -y $B numpy
  run_tests python3 "X4 opencv-python latest, pip numpy removed (apt numpy 1.26)"
  pipi pip3 uninstall -y $B opencv-python
  pipi pip3 install $B --ignore-installed "opencv-python<5"
  run_tests python3 "X5 pip --ignore-installed opencv-python<5"
  pipi pip3 uninstall -y $B opencv-python numpy
  run_tests python3 "X6 both removed (apt only)"
  echo "=== done extra $D"; exit 0
fi
BSP=""
run_tests python3 "S0 apt only"

echo; echo "##### pip install numpy (no flags)"
pipi pip3 install numpy
if pip3 install numpy 2>&1 | grep -q externally-managed; then BSP=--break-system-packages; echo "PEP 668 active -> using $BSP"; fi
if [ -n "$BSP" ]; then pipi pip3 install $BSP numpy; fi
echo "numpy now:"; python3 -c "import numpy; print(numpy.__version__, numpy.__file__)"

pipi pip3 install $BSP -U numpy
run_tests python3 "S1 pip install -U numpy (latest) on top of apt"

pipi pip3 install $BSP "numpy<2"
run_tests python3 "S2 pip install numpy<2"

pipi pip3 install $BSP "numpy<1.24"
run_tests python3 "S2b pip install numpy<1.24"

pipi pip3 install $BSP -U numpy transforms3d
run_tests python3 "S2c pip install -U numpy transforms3d"
pipi pip3 uninstall -y $BSP transforms3d

pipi pip3 uninstall -y $BSP numpy
run_tests python3 "S3 pip numpy uninstalled (apt fallback)"

pipi pip3 install $BSP opencv-python
run_tests python3 "S4 pip install opencv-python (latest)"

pipi pip3 install $BSP "numpy<2"
run_tests python3 "S5 opencv-python latest + numpy<2"

pipi pip3 uninstall -y $BSP opencv-python
pipi pip3 install $BSP "opencv-python<5"
run_tests python3 "S5b opencv-python<5 (numpy unpinned)"
pipi pip3 uninstall -y $BSP opencv-python

pipi pip3 install $BSP "opencv-python-headless<4.12" "numpy<2"
run_tests python3 "S6 opencv-python-headless<4.12 + numpy<2"
pipi pip3 uninstall -y $BSP opencv-python-headless numpy
echo "after cleanup:"; python3 -c "import numpy; print(numpy.__version__, numpy.__file__)"

echo; echo "##### venv --system-site-packages"
python3 -m venv --system-site-packages /v_sys
run_tests /v_sys/bin/python "S7 venv --system-site-packages, no pip numpy"
pipi /v_sys/bin/pip install -U numpy
run_tests /v_sys/bin/python "S8 venv --system-site-packages + pip install -U numpy"
pipi /v_sys/bin/pip install "numpy<2"
run_tests /v_sys/bin/python "S9 venv --system-site-packages + numpy<2"

echo; echo "##### isolated venv"
python3 -m venv /v_iso
run_tests /v_iso/bin/python "S10 isolated venv, nothing installed"
pipi /v_iso/bin/pip install numpy
run_tests /v_iso/bin/python "S11 isolated venv + pip numpy latest"
pipi /v_iso/bin/pip install "numpy<2"
run_tests /v_iso/bin/python "S12 isolated venv + numpy<2"
pipi /v_iso/bin/pip install "numpy<2" "opencv-python-headless<4.12" transforms3d
run_tests /v_iso/bin/python "S13 isolated venv + numpy<2 + opencv-python-headless<4.12 + transforms3d"

echo; echo "##### RESOLUTION (dry run, venv --system-site-packages, upgraded pip): which numpy pip would install"
python3 -m venv --system-site-packages /v_dry
/v_dry/bin/pip install -q -U pip 2>&1 | tail -2; /v_dry/bin/pip --version
for spec in "opencv-python" "opencv-python-headless" "opencv-python==4.10.0.84" "opencv-python==4.11.0.86" \
            "opencv-python==4.12.0.88" "opencv-python<5" "opencv-python-headless<4.12" "ultralytics" "torch" "opencv-python numpy<2"; do
  echo "--- dry-run: $spec"
  PIP_ONLY_BINARY= timeout 300 /v_dry/bin/pip install --dry-run --quiet --report /tmp/r.json $spec >/tmp/dry.log 2>&1; rc=$?
  if [ $rc -ne 0 ]; then echo "rc=$rc"; tail -8 /tmp/dry.log; continue; fi
  /v_dry/bin/python - <<'PY'
import json
r = json.load(open('/tmp/r.json'))
for i in r['install']:
    md = i['metadata']; n = md['name'].lower()
    if n in ('numpy', 'opencv-python', 'opencv-python-headless', 'ultralytics', 'torch'):
        req = [x for x in md.get('requires_dist', []) if x.lower().startswith('numpy')]
        print(f"  would install {md['name']}=={md['version']}  numpy reqs: {req}")
if not any(i['metadata']['name'].lower() == 'numpy' for i in r['install']):
    print('  numpy: not installed (existing numpy satisfies)')
PY
done
echo "=== done $D"
