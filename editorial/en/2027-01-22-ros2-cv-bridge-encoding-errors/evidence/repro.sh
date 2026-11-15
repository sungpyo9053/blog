#!/bin/bash
# cv_bridge encoding errors: "[16UC1] is not a color format. but [bgr8] is",
# "encoding specified as bgr8, but image has incompatible type 8UC1" and friends.
# Runs inside ros:<distro>-ros-base as: bash /w/repro.sh <distro>
# Host side (runner), one distro at a time:
#   docker run -d --name pk44-$D -v /tmp/en-pick54:/w ros:$D-ros-base sleep infinity
#   docker exec pk44-$D bash -c 'apt-get update -qq && apt-get install -y -qq --no-install-recommends ros-'$D'-cv-bridge'
#   docker network disconnect bridge pk44-$D        # no network for the tests
#   docker exec pk44-$D bash /w/repro.sh $D > out_$D.txt 2>&1
set +e
ulimit -c 0
D=$1
export ROS_DOMAIN_ID=88 PYTHONUNBUFFERED=1 RCUTILS_COLORIZED_OUTPUT=0
if [ "$D" = humble ]; then export ROS_LOCALHOST_ONLY=1; else export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST; fi
source /opt/ros/$D/setup.bash
echo "##### network interfaces: $(ls /sys/class/net | tr '\n' ' ')"
echo "##### versions"
dpkg-query -W -f='${Package} ${Version}\n' ros-$D-cv-bridge ros-$D-rclpy ros-$D-rclcpp ros-$D-ros2cli ros-$D-rmw ros-$D-sensor-msgs python3-opencv python3-numpy 'libopencv-core4*' 'libopencv-core*' 2>/dev/null | sort -u
python3 -c "import cv2, numpy; print('cv2', cv2.__version__, 'numpy', numpy.__version__)"
python3 --version

cat > /tmp/t.py <<'PY'
import time
import numpy as np, cv2
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
b = CvBridge()
H, W = 4, 6

def short(e):
    return '%s: %s' % (type(e).__name__, str(e).replace('\n', ' ')[:160])

def desc(a):
    return 'dtype=%s shape=%s px=%s' % (a.dtype, a.shape, a[0, 0].tolist())

# ---------- source images (made with cv2_to_imgmsg, which validates them) ----------
c3 = np.zeros((H, W, 3), np.uint8); c3[:] = (10, 20, 30)
c4 = np.zeros((H, W, 4), np.uint8); c4[:] = (10, 20, 30, 255)
srcs = {
    '16UC1': np.full((H, W), 1500, np.uint16),
    'mono16': np.full((H, W), 1500, np.uint16),
    '32FC1': np.full((H, W), 1.5, np.float32),
    '8UC1': np.full((H, W), 100, np.uint8),
    'mono8': np.full((H, W), 100, np.uint8),
    '8UC3': c3.copy(),
    'bgr8': c3.copy(),
    'rgb8': c3.copy(),
    'bgra8': c4.copy(),
    'bayer_rggb8': np.full((H, W), 100, np.uint8),
    'yuv422': np.full((H, W, 2), 128, np.uint8),
}
targets = ['passthrough', 'bgr8', 'rgb8', 'mono8', 'mono16', 'bgra8', '8UC1', '8UC3', '16UC1', '32FC1']
print('##### A. imgmsg_to_cv2(msg, desired_encoding=T): source encoding -> target')
for s, arr in srcs.items():
    try:
        m = b.cv2_to_imgmsg(arr, encoding=s)
    except Exception as e:
        print('A %-12s make-msg %s' % (s, short(e))); continue
    for t in targets:
        try:
            print('A %-12s -> %-12s OK  %s' % (s, t, desc(b.imgmsg_to_cv2(m, desired_encoding=t))))
        except Exception as e:
            print('A %-12s -> %-12s ERR %s' % (s, t, short(e)))

print('##### B. cv2_to_imgmsg(array, encoding=E)')
cases = [
    ('uint8 HxW', np.zeros((H, W), np.uint8), 'bgr8'),
    ('uint8 HxW', np.zeros((H, W), np.uint8), 'mono8'),
    ('uint8 HxW', np.zeros((H, W), np.uint8), 'passthrough'),
    ('uint8 HxWx3', c3.copy(), 'mono8'),
    ('uint8 HxWx3', c3.copy(), 'bgr8'),
    ('uint8 HxWx3', c3.copy(), 'passthrough'),
    ('uint8 HxWx4', c4.copy(), 'bgr8'),
    ('uint16 HxW', np.zeros((H, W), np.uint16), 'passthrough'),
    ('uint16 HxW', np.zeros((H, W), np.uint16), 'mono16'),
    ('uint16 HxW', np.zeros((H, W), np.uint16), 'mono8'),
    ('float32 HxW', np.zeros((H, W), np.float32), 'passthrough'),
    ('float32 HxW', np.zeros((H, W), np.float32), '16UC1'),
    ('float64 HxW', np.zeros((H, W), np.float64), '32FC1'),
    ('float64 HxW', np.zeros((H, W), np.float64), 'passthrough'),
    ('int64 HxW', np.zeros((H, W), np.int64), 'passthrough'),
    ('int64 HxW', np.zeros((H, W), np.int64), 'mono16'),
    ('bool HxW', np.zeros((H, W), bool), 'passthrough'),
    ('python list', [[0, 0], [0, 0]], 'mono8'),
    ('uint8 HxWx3', c3.copy(), 'BGR8'),
]
for name, arr, enc in cases:
    try:
        m = b.cv2_to_imgmsg(arr, encoding=enc)
        print('B %-12s enc=%-12s OK  msg.encoding=%s step=%d' % (name, enc, m.encoding, m.step))
    except Exception as e:
        print('B %-12s enc=%-12s ERR %s' % (name, enc, short(e)))

print('##### C. the passthrough chain: cv2_to_imgmsg(bgr array) without encoding, then ask for bgr8')
m = b.cv2_to_imgmsg(c3.copy())
print('C default encoding of a uint8 HxWx3 array:', m.encoding)
try:
    b.imgmsg_to_cv2(m, 'bgr8'); print('C then imgmsg_to_cv2(bgr8): OK')
except Exception as e:
    print('C then imgmsg_to_cv2(bgr8): ERR', short(e))
m2 = b.cv2_to_imgmsg(c3.copy(), encoding='rgb8')
print('C rgb8 msg (10,20,30) read as bgr8 ->', b.imgmsg_to_cv2(m2, 'bgr8')[0, 0].tolist(),
      ' read as passthrough ->', b.imgmsg_to_cv2(m2)[0, 0].tolist())

print('##### D. broken or odd messages')
def raw(enc, data, step, h=H, w=W, big=0):
    m = Image(); m.height = h; m.width = w; m.encoding = enc; m.step = step
    m.is_bigendian = big; m.data = bytes(data); return m
tests = [
    ('encoding empty, passthrough', raw('', bytes(H * W), W), 'passthrough'),
    ('encoding empty, bgr8', raw('', bytes(H * W), W), 'bgr8'),
    ('encoding BGR8 (upper case)', raw('BGR8', bytes(H * W * 3), W * 3), 'passthrough'),
    ('desired BGR8 (upper case)', b.cv2_to_imgmsg(c3.copy(), 'bgr8'), 'BGR8'),
    ('desired bgr (typo)', b.cv2_to_imgmsg(c3.copy(), 'bgr8'), 'bgr'),
    ('data too short (half)', raw('bgr8', bytes(H * W * 3 // 2), W * 3), 'passthrough'),
    ('step padded (+2 bytes/row)', raw('mono8', bytes(H * (W + 2)), W + 2), 'passthrough'),
    ('16UC1 is_bigendian=1, value 1500', raw('16UC1', np.full((H, W), 1500, '>u2').tobytes(), W * 2, big=1), 'passthrough'),
    ('16UC1 is_bigendian=0, value 1500', raw('16UC1', np.full((H, W), 1500, '<u2').tobytes(), W * 2), 'passthrough'),
]
for name, m, t in tests:
    try:
        print('D %-36s OK  %s' % (name, desc(b.imgmsg_to_cv2(m, t))))
    except Exception as e:
        print('D %-36s ERR %s' % (name, short(e)))

print('##### E. value changes on conversions that succeed')
for s, v, t in [('16UC1', 1500, '32FC1'), ('mono16', 1500, 'mono8'), ('mono16', 1500, 'bgr8'),
                ('32FC1', 1.5, '16UC1'), ('32FC1', 1.5, 'mono8'), ('mono8', 100, 'mono16'), ('mono8', 100, 'bgr8')]:
    dt = np.float32 if s == '32FC1' else (np.uint16 if '16' in s else np.uint8)
    try:
        out = b.imgmsg_to_cv2(b.cv2_to_imgmsg(np.full((H, W), v, dt), s), t)
        print('E %-7s %-6s -> %-6s %s' % (s, v, t, desc(out)))
    except Exception as e:
        print('E %-7s %-6s -> %-6s ERR %s' % (s, v, t, short(e)))

print('##### F. fixes for showing a depth image (640x480 16UC1, values 500..4499 mm, one 0 hole)')
dep = (np.arange(480 * 640, dtype=np.int64) % 4000 + 500).astype(np.uint16).reshape(480, 640); dep[0, 0] = 0
dm = b.cv2_to_imgmsg(dep, '16UC1')
d = b.imgmsg_to_cv2(dm, 'passthrough')
f1 = cv2.convertScaleAbs(d, alpha=255.0 / 5000)
f2 = cv2.normalize(d, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
f3 = cv2.applyColorMap(f2, cv2.COLORMAP_JET)
f4 = (d.astype(np.float32) / 1000.0)
print('F passthrough            ', desc(d))
print('F convertScaleAbs 255/5000', desc(f1), 'max', int(f1.max()))
print('F normalize MINMAX CV_8U ', desc(f2), 'min', int(f2.min()), 'max', int(f2.max()))
print('F applyColorMap on that  ', desc(f3))
print('F float32 metres         ', desc(f4), 'px[1,0]=%.3f' % f4[1, 0])
print('F python CvBridge has cvtColorForDisplay:', hasattr(b, 'cvtColorForDisplay'))

print('##### G. timings, 640x480, mean of 300 calls (ms)')
def tm(fn, n=300):
    fn(); t0 = time.perf_counter()
    for _ in range(n): fn()
    return (time.perf_counter() - t0) * 1000 / n
bgr = np.random.default_rng(1).integers(0, 255, (480, 640, 3), dtype=np.uint8)
mb = b.cv2_to_imgmsg(bgr, 'bgr8'); mr = b.cv2_to_imgmsg(bgr, 'rgb8')
G = [
    ('bgr8 msg -> passthrough', lambda: b.imgmsg_to_cv2(mb)),
    ('bgr8 msg -> bgr8', lambda: b.imgmsg_to_cv2(mb, 'bgr8')),
    ('rgb8 msg -> bgr8', lambda: b.imgmsg_to_cv2(mr, 'bgr8')),
    ('rgb8 msg -> passthrough + cv2.cvtColor', lambda: cv2.cvtColor(b.imgmsg_to_cv2(mr), cv2.COLOR_RGB2BGR)),
    ('16UC1 msg -> passthrough', lambda: b.imgmsg_to_cv2(dm)),
    ('16UC1 msg -> 32FC1 (desired)', lambda: b.imgmsg_to_cv2(dm, '32FC1')),
    ('16UC1 passthrough + convertScaleAbs', lambda: cv2.convertScaleAbs(b.imgmsg_to_cv2(dm), alpha=255.0 / 5000)),
    ('16UC1 passthrough + normalize + colormap', lambda: cv2.applyColorMap(cv2.normalize(b.imgmsg_to_cv2(dm), None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U), cv2.COLORMAP_JET)),
    ('cv2_to_imgmsg bgr8', lambda: b.cv2_to_imgmsg(bgr, 'bgr8')),
]
for name, fn in G:
    print('G %-42s %.3f' % (name, tm(fn)))
PY
echo; timeout 300 python3 /tmp/t.py 2>&1

echo; echo "##### H. C++ cv_bridge (toCvCopy / cvtColorForDisplay)"
H=cv_bridge/cv_bridge.hpp; [ -f /opt/ros/$D/include/cv_bridge/cv_bridge/cv_bridge.hpp ] || [ -f /opt/ros/$D/include/cv_bridge/cv_bridge.hpp ] || H=cv_bridge/cv_bridge.h
echo "header used: $H"
cat > /tmp/t.cpp <<CPP
#include <$H>
#include <iostream>
int main() {
  sensor_msgs::msg::Image m; m.height = 4; m.width = 6; m.encoding = "16UC1"; m.step = 12;
  m.data.assign(48, 0); m.data[0] = 0xdc; m.data[1] = 0x05;   // first pixel 1500
  for (std::string t : {"bgr8", "mono8", "mono16", "8UC1", "32FC1", "passthrough", ""}) {
    try { auto c = cv_bridge::toCvCopy(m, t);
      std::cout << "toCvCopy 16UC1 -> [" << t << "] OK type=" << c->image.type() << " enc=" << c->encoding << std::endl;
    } catch (cv_bridge::Exception & e) { std::cout << "toCvCopy 16UC1 -> [" << t << "] ERR cv_bridge::Exception: " << e.what() << std::endl;
    } catch (std::exception & e) { std::cout << "toCvCopy 16UC1 -> [" << t << "] ERR std::exception (not cv_bridge::Exception): " << e.what() << std::endl; }
  }
  auto d = cv_bridge::cvtColorForDisplay(cv_bridge::toCvCopy(m), "bgr8");
  std::cout << "cvtColorForDisplay(16UC1, bgr8) enc=" << d->encoding << " type=" << d->image.type()
            << " px0=" << d->image.at<cv::Vec3b>(0, 0) << std::endl;
  cv_bridge::CvtColorForDisplayOptions o; o.do_dynamic_scaling = true;
  auto e = cv_bridge::cvtColorForDisplay(cv_bridge::toCvCopy(m), "bgr8", o);
  std::cout << "cvtColorForDisplay dynamic_scaling enc=" << e->encoding << " px0=" << e->image.at<cv::Vec3b>(0, 0)
            << " px1=" << e->image.at<cv::Vec3b>(0, 1) << std::endl;
  try { cv_bridge::cvtColorForDisplay(cv_bridge::toCvCopy(m), "16UC1"); std::cout << "cvtColorForDisplay -> 16UC1 OK" << std::endl; }
  catch (std::exception & x) { std::cout << "cvtColorForDisplay -> 16UC1 ERR " << x.what() << std::endl; }
}
CPP
INC=""; for d in /opt/ros/$D/include /opt/ros/$D/include/*/; do INC="$INC -I$d"; done
if timeout 300 g++ -std=c++17 -O0 /tmp/t.cpp -o /tmp/tcpp $INC -I/usr/include/opencv4 \
     -L/opt/ros/$D/lib -Wl,-rpath,/opt/ros/$D/lib -lcv_bridge -lopencv_core -lopencv_imgproc 2> /tmp/gpp.err; then
  timeout 60 /tmp/tcpp
else
  echo "C++ build failed:"; head -c 1500 /tmp/gpp.err
fi
echo "##### done"
