# Is TypeException a TransformException? Does it escape rclpy.spin()?
import sys
import rclpy
from rclpy.node import Node
import tf2_ros
from tf2_ros import TransformException
from tf2_ros.buffer_interface import TypeException
from geometry_msgs.msg import PoseStamped, TransformStamped

print('TypeException MRO:', [c.__module__ + '.' + c.__name__ for c in TypeException.__mro__])
print('issubclass(TypeException, TransformException):', issubclass(TypeException, TransformException))
print('tf2_ros exports TypeException:', hasattr(tf2_ros, 'TypeException'))
print('TransformException MRO:', [c.__module__ + '.' + c.__name__ for c in TransformException.__mro__])


class N(Node):
    def __init__(self):
        super().__init__('catch_test')
        self.buf = tf2_ros.Buffer()
        t = TransformStamped()
        t.header.frame_id = 'world'
        t.child_frame_id = 'child'
        t.transform.rotation.w = 1.0
        self.buf.set_transform_static(t, 'test')
        self.n = 0
        self.create_timer(0.1, self.cb)

    def cb(self):
        self.n += 1
        ps = PoseStamped()
        ps.header.frame_id = 'child'
        ps.pose.orientation.w = 1.0
        try:
            self.buf.transform(ps, 'world')
        except TransformException as e:
            self.get_logger().error(f'caught by except TransformException: {e}')
        if self.n >= 3:
            raise SystemExit(0)


rclpy.init()
node = N()
try:
    rclpy.spin(node)
except SystemExit:
    print('spin ended normally after 3 callbacks: TypeException was caught')
except BaseException as e:
    print(f'EXCEPTION ESCAPED rclpy.spin after callback {node.n}: {type(e).__name__}: {e}')
    sys.exit(3)
