# Buffer-only tests: no DDS, no spinning. Prints one line per case.
import sys, time, traceback
import rclpy
from rclpy.duration import Duration
from rclpy.time import Time
import tf2_ros
from tf2_ros.buffer_interface import TransformRegistration
from geometry_msgs.msg import (TransformStamped, PoseStamped, Pose, PointStamped, Point,
                               Vector3Stamped, PoseWithCovarianceStamped, PoseArray,
                               TwistStamped, Vector3, Quaternion)
from nav_msgs.msg import Odometry


def reg_keys():
    m = TransformRegistration._TransformRegistration__type_map
    return sorted(k.__module__.split('.')[0] + '/' + k.__name__ for k in m)


def err(e):
    return f'{type(e).__module__}.{type(e).__name__}: {e}'


def case(name, fn):
    try:
        r = fn()
        print(f'CASE {name}: OK {r}')
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f'CASE {name}: EXC {err(e)}  [raised at {tb.filename.split("site-packages/")[-1]}:{tb.lineno} in {tb.name}]')


def tf_world_child():
    t = TransformStamped()
    t.header.frame_id = 'world'
    t.child_frame_id = 'child'
    t.transform.translation.x = 1.0
    t.transform.translation.y = 2.0
    # 90 deg about z
    t.transform.rotation.z = 0.7071067811865476
    t.transform.rotation.w = 0.7071067811865476
    return t


def pose_child():
    ps = PoseStamped()
    ps.header.frame_id = 'child'
    ps.pose.position.x = 1.0
    ps.pose.orientation.w = 1.0
    return ps


def fmt_pose(p):
    return f'pos=({p.position.x:.3f},{p.position.y:.3f},{p.position.z:.3f}) q=({p.orientation.x:.3f},{p.orientation.y:.3f},{p.orientation.z:.3f},{p.orientation.w:.3f})'


rclpy.init()
buf = tf2_ros.Buffer()
buf.set_transform_static(tf_world_child(), 'test')

print('tf2_geometry_msgs in sys.modules after import tf2_ros:', 'tf2_geometry_msgs' in sys.modules)
print('registry before import:', reg_keys())

case('A1 buffer.transform(PoseStamped) without import tf2_geometry_msgs',
     lambda: fmt_pose(buf.transform(pose_child(), 'world').pose))
case('A2 buffer.transform(PointStamped) without import',
     lambda: buf.transform(PointStamped(header=pose_child().header), 'world').point)

import tf2_geometry_msgs  # noqa: E402  registers conversions as a side effect
print('tf2_geometry_msgs file:', tf2_geometry_msgs.__file__)
print('registry after import tf2_geometry_msgs:', reg_keys())

case('B1 buffer.transform(PoseStamped) after import',
     lambda: (type(buf.transform(pose_child(), 'world')).__name__, fmt_pose(buf.transform(pose_child(), 'world').pose)))
case('B2 buffer.transform(PoseStamped, timeout=1s) after import',
     lambda: fmt_pose(buf.transform(pose_child(), 'world', timeout=Duration(seconds=1.0)).pose))
case('B3 buffer.transform(bare Pose)', lambda: buf.transform(pose_child().pose, 'world'))
case('B4 buffer.transform(PointStamped)',
     lambda: buf.transform(PointStamped(header=pose_child().header, point=Point(x=1.0)), 'world').point)
case('B5 buffer.transform(Vector3Stamped)',
     lambda: buf.transform(Vector3Stamped(header=pose_child().header, vector=Vector3(x=1.0)), 'world').vector)
pwc = PoseWithCovarianceStamped()
pwc.header.frame_id = 'child'
pwc.pose.pose.orientation.w = 1.0
case('B6 buffer.transform(PoseWithCovarianceStamped)', lambda: fmt_pose(buf.transform(pwc, 'world').pose.pose))
pa = PoseArray()
pa.header.frame_id = 'child'
pa.poses = [pose_child().pose]
case('B7 buffer.transform(PoseArray)', lambda: buf.transform(pa, 'world'))
od = Odometry()
od.header.frame_id = 'child'
case('B8 buffer.transform(Odometry)', lambda: buf.transform(od, 'world'))
tw = TwistStamped()
tw.header.frame_id = 'child'
case('B9 buffer.transform(TwistStamped)', lambda: buf.transform(tw, 'world'))
case('B10 buffer.transform(PoseStamped, new_type=PointStamped)',
     lambda: buf.transform(pose_child(), 'world', new_type=PointStamped))

from tf2_geometry_msgs import do_transform_pose  # noqa: E402
t = buf.lookup_transform('world', 'child', Time())
print('lookup_transform result:', type(t).__name__, t.header.frame_id, '->', t.child_frame_id)
case('C1 do_transform_pose(PoseStamped, t)', lambda: do_transform_pose(pose_child(), t))
case('C2 do_transform_pose(Pose, t)', lambda: (type(do_transform_pose(pose_child().pose, t)).__name__, fmt_pose(do_transform_pose(pose_child().pose, t))))
case('C3 do_transform_pose_stamped exists', lambda: hasattr(tf2_geometry_msgs, 'do_transform_pose_stamped'))
if hasattr(tf2_geometry_msgs, 'do_transform_pose_stamped'):
    case('C4 do_transform_pose_stamped(PoseStamped, t)',
         lambda: (type(tf2_geometry_msgs.do_transform_pose_stamped(pose_child(), t)).__name__,
                  tf2_geometry_msgs.do_transform_pose_stamped(pose_child(), t).header.frame_id,
                  fmt_pose(tf2_geometry_msgs.do_transform_pose_stamped(pose_child(), t).pose)))
    case('C5 do_transform_pose_stamped(Pose, t)', lambda: tf2_geometry_msgs.do_transform_pose_stamped(pose_child().pose, t))
case('C6 do_transform_pose(Pose, t.transform)', lambda: do_transform_pose(pose_child().pose, t.transform))
case('C7 do_transform_point(PointStamped, t)',
     lambda: tf2_geometry_msgs.do_transform_point(PointStamped(header=pose_child().header, point=Point(x=1.0)), t).point)
case('C8 do_transform_point(Point, t)', lambda: tf2_geometry_msgs.do_transform_point(Point(x=1.0), t))
case('C9 do_transform_vector3(Vector3Stamped, t)',
     lambda: tf2_geometry_msgs.do_transform_vector3(Vector3Stamped(header=pose_child().header, vector=Vector3(x=1.0)), t).vector)
print('functions in tf2_geometry_msgs:', sorted(n for n in dir(tf2_geometry_msgs) if n.startswith('do_transform')))

# cost per call
N = 20000
ps0 = pose_child()
t0 = time.perf_counter()
for _ in range(N):
    buf.transform(ps0, 'world')
t1 = time.perf_counter()
for _ in range(N):
    tt = buf.lookup_transform('world', 'child', Time())
    do_transform_pose(ps0.pose, tt)
t2 = time.perf_counter()
for _ in range(N):
    do_transform_pose(ps0.pose, t)
t3 = time.perf_counter()
print(f'TIMING N={N} buffer.transform={1e6*(t1-t0)/N:.1f}us lookup+do_transform_pose={1e6*(t2-t1)/N:.1f}us do_transform_pose_only={1e6*(t3-t2)/N:.1f}us')
rclpy.shutdown()
