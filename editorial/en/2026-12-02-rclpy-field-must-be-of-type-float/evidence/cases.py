# Each case assigns one value to one message field and prints OK (stored type/value) or the exception.
import sys, time, array, math, inspect, timeit
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.serialization import serialize_message, deserialize_message
from std_msgs.msg import Float64, Float32, Int32, UInt8, String, Header, Float64MultiArray, Bool
from geometry_msgs.msg import Vector3, Wrench, Point
from sensor_msgs.msg import Imu
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Time as TimeMsg, Duration as DurationMsg
from rclpy.duration import Duration

import os
print("python", sys.version.split()[0], "numpy", np.__version__, "asserts_enabled", __debug__, "ROS_PYTHON_CHECK_FIELDS=%r" % os.environ.get("ROS_PYTHON_CHECK_FIELDS"))
rclpy.init()
node = Node("pk2_cases")

def show(v):
    if isinstance(v, (array.array,)): return "array.array('%s') len=%d first=%r" % (v.typecode, len(v), v[0] if len(v) else None)
    if isinstance(v, np.ndarray): return "numpy.ndarray dtype=%s len=%d" % (v.dtype, len(v))
    return "%s %r" % (type(v).__name__, v)

def case(label, fn):
    try:
        r = fn()
        print("CASE %-48s OK  %s" % (label, show(r)))
    except Exception as e:
        print("CASE %-48s ERR %s: %s" % (label, type(e).__name__, str(e).replace("\n", " | ")))

def setf(msgcls, field, value):
    m = msgcls(); setattr(m, field, value); return getattr(m, field)

case("Float64.data = 1", lambda: setf(Float64, "data", 1))
case("Float64.data = 1.0", lambda: setf(Float64, "data", 1.0))
case("Float64.data = float(1)", lambda: setf(Float64, "data", float(1)))
case("Float64.data = True", lambda: setf(Float64, "data", True))
case("Float64.data = '1.0'", lambda: setf(Float64, "data", "1.0"))
case("Float64.data = None", lambda: setf(Float64, "data", None))
case("Float64.data = np.float64(1.5)", lambda: setf(Float64, "data", np.float64(1.5)))
case("Float64.data = np.float32(1.5)", lambda: setf(Float64, "data", np.float32(1.5)))
case("Float64.data = float(np.float32(1.5))", lambda: setf(Float64, "data", float(np.float32(1.5))))
case("Float64.data = np.array([1.5])[0]", lambda: setf(Float64, "data", np.array([1.5])[0]))
case("Float64.data = np.int64(1)", lambda: setf(Float64, "data", np.int64(1)))
case("Float64.data = 1e309 (inf)", lambda: setf(Float64, "data", 1e309))
case("Float64.data = nan", lambda: setf(Float64, "data", float("nan")))
case("Float32.data = 1.5", lambda: setf(Float32, "data", 1.5))
case("Float32.data = 1e39", lambda: setf(Float32, "data", 1e39))
case("Float32.data = inf", lambda: setf(Float32, "data", float("inf")))
case("Float32.data = nan", lambda: setf(Float32, "data", float("nan")))
case("Float32(data=2) constructor", lambda: Float32(data=2).data)
case("Int32.data = 1.0", lambda: setf(Int32, "data", 1.0))
case("Int32.data = 2**31", lambda: setf(Int32, "data", 2**31))
case("Int32.data = np.int64(5)", lambda: setf(Int32, "data", np.int64(5)))
case("Int32.data = int(np.int64(5))", lambda: setf(Int32, "data", int(np.int64(5))))
case("Int32.data = True", lambda: setf(Int32, "data", True))
case("UInt8.data = 256", lambda: setf(UInt8, "data", 256))
case("UInt8.data = -1", lambda: setf(UInt8, "data", -1))
case("Bool.data = 1", lambda: setf(Bool, "data", 1))
case("String.data = 5", lambda: setf(String, "data", 5))
case("String.data = b'abc'", lambda: setf(String, "data", b"abc"))
case("Vector3(x=1, y=2.0, z=3.0)", lambda: Vector3(x=1, y=2.0, z=3.0).x)
case("Vector3(x=1.0, y=2.0, z=3.0)", lambda: Vector3(x=1.0, y=2.0, z=3.0).x)
case("Wrench.force = [1.0, 2.0, 3.0]", lambda: setf(Wrench, "force", [1.0, 2.0, 3.0]))
case("Point(x=np.float64(1.0))", lambda: Point(x=np.float64(1.0)).x)
# sub-message fields
case("Header.stamp = time.time()", lambda: setf(Header, "stamp", time.time()))
case("Header.stamp = clock.now()", lambda: setf(Header, "stamp", node.get_clock().now()))
case("Header.stamp = clock.now().to_msg()", lambda: setf(Header, "stamp", node.get_clock().now().to_msg()))
case("Header.stamp = Time msg(sec=1, nanosec=5)", lambda: setf(Header, "stamp", TimeMsg(sec=1, nanosec=5)))
case("Header.frame_id = None", lambda: setf(Header, "frame_id", None))
case("JTP.time_from_start = Duration(seconds=1)", lambda: setf(JointTrajectoryPoint, "time_from_start", Duration(seconds=1)))
case("JTP.time_from_start = Duration(...).to_msg()", lambda: setf(JointTrajectoryPoint, "time_from_start", Duration(seconds=1).to_msg()))
case("JTP.time_from_start = DurationMsg(sec=1)", lambda: setf(JointTrajectoryPoint, "time_from_start", DurationMsg(sec=1)))
case("JTP.time_from_start = 1.0", lambda: setf(JointTrajectoryPoint, "time_from_start", 1.0))
# sequences (float64[] unbounded)
case("F64MA.data = [1, 2, 3]", lambda: setf(Float64MultiArray, "data", [1, 2, 3]))
case("F64MA.data = [1.0, 2, 3.0]", lambda: setf(Float64MultiArray, "data", [1.0, 2, 3.0]))
case("F64MA.data = [1.0, 2.0, 3.0]", lambda: setf(Float64MultiArray, "data", [1.0, 2.0, 3.0]))
case("F64MA.data = (1.0, 2.0)", lambda: setf(Float64MultiArray, "data", (1.0, 2.0)))
case("F64MA.data = np.array([1.,2.]) float64", lambda: setf(Float64MultiArray, "data", np.array([1.0, 2.0])))
case("F64MA.data = np.array([1.,2.], float32)", lambda: setf(Float64MultiArray, "data", np.array([1.0, 2.0], dtype=np.float32)))
case("F64MA.data = np.array([1, 2]) int64", lambda: setf(Float64MultiArray, "data", np.array([1, 2])))
case("F64MA.data = np.zeros((2,2)) 2-D", lambda: setf(Float64MultiArray, "data", np.zeros((2, 2))))
case("F64MA.data = np.zeros((2,2)).ravel()", lambda: setf(Float64MultiArray, "data", np.zeros((2, 2)).ravel()))
case("F64MA.data = arr.tolist() float64", lambda: setf(Float64MultiArray, "data", np.array([1.0, 2.0]).tolist()))
case("F64MA.data = np.array(int).astype(float).tolist()", lambda: setf(Float64MultiArray, "data", np.array([1, 2]).astype(float).tolist()))
case("F64MA.data = array.array('d', [1, 2])", lambda: setf(Float64MultiArray, "data", array.array("d", [1, 2])))
case("F64MA.data = array.array('f', [1, 2])", lambda: setf(Float64MultiArray, "data", array.array("f", [1, 2])))
case("F64MA.data = (x for x in [1.0, 2.0]) generator", lambda: setf(Float64MultiArray, "data", (x for x in [1.0, 2.0])))
case("F64MA.data = [nested list]", lambda: setf(Float64MultiArray, "data", [[1.0, 2.0], [3.0, 4.0]]))
case("F64MA.data = 1.0 (scalar)", lambda: setf(Float64MultiArray, "data", 1.0))
def append_int():
    m = Float64MultiArray(); m.data = [1.0]; m.data.append(2); return m.data
case("F64MA.data=[1.0] then .append(2)", append_int)
def append_str():
    m = Float64MultiArray(); m.data = [1.0]; m.data.append("x"); return m.data
case("F64MA.data=[1.0] then .append('x')", append_str)
# fixed-size float64[9]
case("Imu.orientation_covariance = [0.0]*8", lambda: setf(Imu, "orientation_covariance", [0.0] * 8))
case("Imu.orientation_covariance = [0]*9 ints", lambda: setf(Imu, "orientation_covariance", [0] * 9))
case("Imu.orientation_covariance = [0.0]*9", lambda: setf(Imu, "orientation_covariance", [0.0] * 9))
case("Imu.orientation_covariance = np.zeros(9)", lambda: setf(Imu, "orientation_covariance", np.zeros(9)))
case("Imu.orientation_covariance = np.zeros(9, f32)", lambda: setf(Imu, "orientation_covariance", np.zeros(9, dtype=np.float32)))
case("Imu.orientation_covariance = np.eye(3)", lambda: setf(Imu, "orientation_covariance", np.eye(3)))
case("Imu.orientation_covariance = np.eye(3).flatten()", lambda: setf(Imu, "orientation_covariance", np.eye(3).flatten()))
def cov_elem():
    m = Imu(); m.orientation_covariance[0] = 1; return m.orientation_covariance
case("Imu.orientation_covariance[0] = 1 (element)", cov_elem)

case("Float64(data=1, check_fields=True)", lambda: Float64(data=1, check_fields=True).data)
case("Float64(data=1.0, check_fields=True)", lambda: Float64(data=1.0, check_fields=True).data)

if "--src" in sys.argv:
    print("---- generated setter source: std_msgs Float64.data ----")
    print(inspect.getsource(Float64.data.fset))
    print("---- generated setter source: std_msgs Float64MultiArray.data ----")
    print(inspect.getsource(Float64MultiArray.data.fset))

if "--time" in sys.argv:
    N = 100000
    lst = [float(i) for i in range(N)]
    arr = np.arange(N, dtype=np.float64)
    def t(label, stmt, number=20):
        try:
            best = min(timeit.repeat(stmt, number=number, repeat=5)) / number
            print("TIME %-52s %.3f ms per assignment (N=%d)" % (label, best * 1000, N))
        except Exception as e:
            print("TIME %-52s ERR %s" % (label, type(e).__name__))
    m = Float64MultiArray()
    t("data = list of 100k Python floats", lambda: setattr(m, "data", lst))
    t("data = numpy float64 array (100k)", lambda: setattr(m, "data", arr))
    t("data = arr.tolist()  (incl. tolist)", lambda: setattr(m, "data", arr.tolist()))
    t("data = array.array('d', arr) (incl. conversion)", lambda: setattr(m, "data", array.array("d", arr)))
    t("data = [float(x) for x in arr] (incl. conversion)", lambda: setattr(m, "data", [float(x) for x in arr]), number=5)
    t("Float64.data = 1.0 (scalar, x1000)", lambda: [setattr(Float64(), "data", 1.0) for _ in range(1000)])

node.destroy_node()
rclpy.shutdown()
