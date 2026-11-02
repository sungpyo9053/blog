# One case per process: assign a value, then serialize+deserialize it (or publish it).
# Run per process because a wrong type that reaches the C conversion aborts the interpreter.
import sys
import numpy as np
from rclpy.serialization import serialize_message, deserialize_message
from rclpy.clock import Clock
from rclpy.duration import Duration
from std_msgs.msg import Float64, Float32, Int32, UInt8, Bool, String, Header, Float64MultiArray
from geometry_msgs.msg import Wrench
from sensor_msgs.msg import Imu
from trajectory_msgs.msg import JointTrajectoryPoint
import time
cases = {
    "f64_int": (Float64, "data", lambda: 1),
    "f64_np_float32": (Float64, "data", lambda: np.float32(1.5)),
    "f64_np_int64": (Float64, "data", lambda: np.int64(1)),
    "f64_str": (Float64, "data", lambda: "1.0"),
    "f64_none": (Float64, "data", lambda: None),
    "f32_1e39": (Float32, "data", lambda: 1e39),
    "i32_float": (Int32, "data", lambda: 1.7),
    "i32_np_int64": (Int32, "data", lambda: np.int64(5)),
    "i32_2pow31": (Int32, "data", lambda: 2**31),
    "u8_256": (UInt8, "data", lambda: 256),
    "u8_neg1": (UInt8, "data", lambda: -1),
    "bool_int": (Bool, "data", lambda: 1),
    "str_int": (String, "data", lambda: 5),
    "str_bytes": (String, "data", lambda: b"abc"),
    "frame_id_none": (Header, "frame_id", lambda: None),
    "stamp_time_time": (Header, "stamp", lambda: time.time()),
    "stamp_clock_now": (Header, "stamp", lambda: Clock().now()),
    "jtp_rclpy_duration": (JointTrajectoryPoint, "time_from_start", lambda: Duration(seconds=1)),
    "wrench_force_list": (Wrench, "force", lambda: [1.0, 2.0, 3.0]),
    "f64ma_ints": (Float64MultiArray, "data", lambda: [1, 2]),
    "f64ma_numpy": (Float64MultiArray, "data", lambda: np.array([1.0, 2.0])),
    "imu_cov_len8": (Imu, "orientation_covariance", lambda: [0.0] * 8),
    "imu_cov_ints": (Imu, "orientation_covariance", lambda: [0] * 9),
    "imu_eye": (Imu, "orientation_covariance", lambda: np.eye(3)),
}
name = sys.argv[1]
cls, field, make = cases[name]
m = cls()
try:
    setattr(m, field, make())
except Exception as e:
    print("assign: %s: %s" % (type(e).__name__, str(e)[:160])); sys.exit(0)
v = getattr(m, field)
print("assign: OK, stored as %s %s" % (type(v).__name__, repr(v).replace("\n", "")[:80]), flush=True)
if len(sys.argv) > 2 and sys.argv[2] == "publish":
    import rclpy
    import rclpy.node
    rclpy.init(); node = rclpy.node.Node("pk2_pub")
    pub = node.create_publisher(cls, "pk2_topic", 10)
    try:
        pub.publish(m); print("publish: returned normally", flush=True)
    except Exception as e:
        print("publish: %s: %s" % (type(e).__name__, str(e)[:160]))
    sys.exit(0)
try:
    out = deserialize_message(serialize_message(m), cls)
    v = getattr(out, field)
    if isinstance(v, np.ndarray):
        print("serialize+deserialize: OK, received ndarray len=%d values=%s" % (len(v), v.tolist()))
    else:
        print("serialize+deserialize: OK, received %s %s" % (type(v).__name__, repr(v).replace("\n", "")[:80]))
except Exception as e:
    print("serialize: %s: %s" % (type(e).__name__, str(e)[:160]))
