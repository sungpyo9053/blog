#!/usr/bin/env python3
# Compare quaternion <-> Euler conversions in ROS 2 Python:
# tf_transformations, transforms3d, SciPy and a hand-written formula.
# Usage: python3 compare.py   (needs tf_transformations, transforms3d, scipy installed)
import math, sys, time, subprocess, json

D = math.degrees
R = math.radians


def hand_euler_from_quat(x, y, z, w):
    # common copy-paste formula (roll about x, pitch about y, yaw about z)
    t0 = 2.0 * (w * x + y * z)
    t1 = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(t0, t1)
    t2 = 2.0 * (w * y - z * x)
    t2 = max(-1.0, min(1.0, t2))
    pitch = math.asin(t2)
    t3 = 2.0 * (w * z + x * y)
    t4 = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(t3, t4)
    return roll, pitch, yaw


def hand_quat_from_euler(r, p, y):
    cr, sr = math.cos(r / 2), math.sin(r / 2)
    cp, sp = math.cos(p / 2), math.sin(p / 2)
    cy, sy = math.cos(y / 2), math.sin(y / 2)
    return (sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy)


def fmt(v, n=4):
    return '[' + ', '.join(f'{a:.{n}f}' for a in v) + ']'


def import_time(mod):
    code = f"import time;t=time.perf_counter();import {mod};print(time.perf_counter()-t)"
    best = []
    for _ in range(3):
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
        if out.returncode != 0:
            return 'FAIL ' + out.stderr.strip().splitlines()[-1]
        best.append(float(out.stdout))
    return f'{min(best)*1000:.1f} ms (min of 3; runs {", ".join(f"{b*1000:.1f}" for b in best)})'


print('python', sys.version.split()[0])
import numpy
print('numpy', numpy.__version__)
import tf_transformations as tft
import transforms3d
from transforms3d import euler as t3e
import scipy
from scipy.spatial.transform import Rotation
print('tf_transformations file', tft.__file__)
print('transforms3d', transforms3d.__version__, 'scipy', scipy.__version__)

print('\n## import time (fresh interpreter)')
for m in ['tf_transformations', 'transforms3d', 'scipy.spatial.transform', 'math']:
    print(f'{m}: {import_time(m)}')

cases = [(0, 0, 90), (10, 20, 30), (-45, 30, 170), (180, 0, 0), (0, 89.9, 0), (0, 90, 0), (30, 90, 40)]
print('\n## quaternion_from_euler for the same roll, pitch, yaw (degrees)')
for c in cases:
    r, p, y = map(R, c)
    a = tft.quaternion_from_euler(r, p, y)
    b = t3e.euler2quat(r, p, y)
    s = Rotation.from_euler('xyz', [r, p, y]).as_quat()
    h = hand_quat_from_euler(r, p, y)
    print(f'rpy={c}: tft(x,y,z,w)={fmt(a)} t3d(w,x,y,z)={fmt(b)} scipy(x,y,z,w)={fmt(s)} hand(x,y,z,w)={fmt(h)}')

print('\n## euler_from_quaternion round trip, result in degrees')
for c in cases:
    r, p, y = map(R, c)
    q = tft.quaternion_from_euler(r, p, y)  # x, y, z, w
    x, yy, z, w = q
    a = [D(v) for v in tft.euler_from_quaternion([x, yy, z, w])]
    b = [D(v) for v in t3e.quat2euler([w, x, yy, z])]
    s = [D(v) for v in Rotation.from_quat([x, yy, z, w]).as_euler('xyz')]
    S = [D(v) for v in Rotation.from_quat([x, yy, z, w]).as_euler('XYZ')]
    h = [D(v) for v in hand_euler_from_quat(x, yy, z, w)]
    print(f'rpy={c}: tft={fmt(a,3)} t3d={fmt(b,3)} scipy_xyz={fmt(s,3)} scipy_XYZ(intrinsic)={fmt(S,3)} hand={fmt(h,3)}')

print('\n## same rotation? (angle between rotations from each library\'s Euler output, degrees)')
for c in cases:
    r, p, y = map(R, c)
    q = tft.quaternion_from_euler(r, p, y)
    ref = Rotation.from_quat(q)
    outs = {
        'tft': tft.euler_from_quaternion(q),
        't3d': t3e.quat2euler([q[3], q[0], q[1], q[2]]),
        'scipy': Rotation.from_quat(q).as_euler('xyz'),
        'hand': hand_euler_from_quat(*q),
    }
    errs = {k: D((Rotation.from_euler('xyz', v) * ref.inv()).magnitude()) for k, v in outs.items()}
    print(f'rpy={c}: ' + ' '.join(f'{k}={v:.2e}' for k, v in errs.items()))

print('\n## wrong component order (rpy=(10,20,30) deg)')
r, p, y = map(R, (10, 20, 30))
x, yy, z, w = tft.quaternion_from_euler(r, p, y)
print('tft euler_from_quaternion([w,x,y,z]) ->', fmt([D(v) for v in tft.euler_from_quaternion([w, x, yy, z])], 3))
print('t3d quat2euler([x,y,z,w]) ->', fmt([D(v) for v in t3e.quat2euler([x, yy, z, w])], 3))
print('scipy from_quat([w,x,y,z]) xyz ->', fmt([D(v) for v in Rotation.from_quat([w, x, yy, z]).as_euler('xyz')], 3))
print('identity quaternion read as [w,x,y,z] by tft: euler_from_quaternion([1,0,0,0]) ->',
      fmt([D(v) for v in tft.euler_from_quaternion([1, 0, 0, 0])], 3))

print('\n## passing a geometry_msgs Quaternion directly')
from geometry_msgs.msg import Quaternion
qm = Quaternion(x=x, y=yy, z=z, w=w)
for name, fn in [('tft.euler_from_quaternion(msg)', lambda: tft.euler_from_quaternion(qm)),
                 ('t3d.quat2euler(msg)', lambda: t3e.quat2euler(qm)),
                 ('Rotation.from_quat(msg)', lambda: Rotation.from_quat(qm))]:
    try:
        print(name, '->', fn())
    except Exception as e:
        print(name, '->', type(e).__name__ + ':', str(e).splitlines()[0][:200])
print('tft.euler_from_quaternion([msg.x, msg.y, msg.z, msg.w]) ->',
      fmt([D(v) for v in tft.euler_from_quaternion([qm.x, qm.y, qm.z, qm.w])], 3))
try:
    q2 = tft.quaternion_from_euler(r, p, y)
    Quaternion(x=q2[0], y=q2[1], z=q2[2], w=q2[3])
    print('Quaternion(x=q[0],...) from numpy floats: ok, type', type(q2[0]).__name__)
except Exception as e:
    print('Quaternion from numpy floats ->', type(e).__name__, e)

print('\n## unnormalized quaternion [0, 0, 1, 1] (x,y,z,w), expected yaw 90')
u = [0.0, 0.0, 1.0, 1.0]
print('tft ->', fmt([D(v) for v in tft.euler_from_quaternion(u)], 3))
print('t3d ->', fmt([D(v) for v in t3e.quat2euler([u[3], u[0], u[1], u[2]])], 3))
print('scipy ->', fmt([D(v) for v in Rotation.from_quat(u).as_euler('xyz')], 3))
print('hand ->', fmt([D(v) for v in hand_euler_from_quat(*u)], 3))
u = [0.0, 0.0, 2.0, 2.0 * math.sqrt(3)]  # yaw 60 scaled by 4
print('scaled [0,0,2,3.464] (yaw 60 x4): tft ->', fmt([D(v) for v in tft.euler_from_quaternion(u)], 3),
      'hand ->', fmt([D(v) for v in hand_euler_from_quat(*u)], 3))

print('\n## time per euler_from_quaternion call (20000 calls, best of 3), microseconds')
q = list(tft.quaternion_from_euler(r, p, y))
qw = [q[3], q[0], q[1], q[2]]
funcs = {
    'tf_transformations': lambda: tft.euler_from_quaternion(q),
    'transforms3d': lambda: t3e.quat2euler(qw),
    'scipy (one Rotation per call)': lambda: Rotation.from_quat(q).as_euler('xyz'),
    'hand-written math': lambda: hand_euler_from_quat(*q),
}
N = 20000
for k, f in funcs.items():
    best = 1e9
    for _ in range(3):
        t = time.perf_counter()
        for _ in range(N):
            f()
        best = min(best, time.perf_counter() - t)
    print(f'{k}: {best / N * 1e6:.2f} us')
qs = numpy.tile(q, (N, 1))
best = 1e9
for _ in range(3):
    t = time.perf_counter()
    Rotation.from_quat(qs).as_euler('xyz')
    best = min(best, time.perf_counter() - t)
print(f'scipy vectorized, {N} quaternions in one call: {best / N * 1e6:.3f} us each ({best*1000:.2f} ms total)')

print('\n## tf_transformations functions available:', len([n for n in dir(tft) if not n.startswith('_')]))
print('has euler_from_quaternion/quaternion_from_euler/quaternion_multiply/euler_matrix:',
      all(hasattr(tft, n) for n in ['euler_from_quaternion', 'quaternion_from_euler', 'quaternion_multiply', 'euler_matrix']))
