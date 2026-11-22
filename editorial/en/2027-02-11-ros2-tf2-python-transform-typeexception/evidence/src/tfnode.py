# A node with a TransformListener that calls buffer.transform() from a 10 Hz timer for 3 s.
# argv[1]: "noimport" or "import" (import tf2_geometry_msgs or not)
import sys, time, collections
import rclpy
from rclpy.node import Node
import tf2_ros
from geometry_msgs.msg import PoseStamped

if sys.argv[1] == 'import':
    import tf2_geometry_msgs  # noqa: F401


class N(Node):
    def __init__(self):
        super().__init__('pose_tf_test')
        self.buf = tf2_ros.Buffer()
        self.lis = tf2_ros.TransformListener(self.buf, self)
        self.t0 = time.monotonic()
        self.counts = collections.Counter()
        self.first = {}
        self.create_timer(0.1, self.cb)

    def cb(self):
        ps = PoseStamped()
        ps.header.frame_id = 'child'
        ps.pose.orientation.w = 1.0
        try:
            out = self.buf.transform(ps, 'world')
            k = 'OK'
            msg = f'({out.pose.position.x:.2f},{out.pose.position.y:.2f})'
        except Exception as e:
            k = type(e).__name__
            msg = str(e)
        self.counts[k] += 1
        if k not in self.first:
            self.first[k] = f'{time.monotonic()-self.t0:.2f}s {msg}'
            self.get_logger().info(f'first {k} at {self.first[k]}')


rclpy.init()
n = N()
end = time.monotonic() + 3.0
while time.monotonic() < end:
    rclpy.spin_once(n, timeout_sec=0.05)
print('RESULT', sys.argv[1], dict(n.counts))
n.destroy_node()
rclpy.shutdown()
