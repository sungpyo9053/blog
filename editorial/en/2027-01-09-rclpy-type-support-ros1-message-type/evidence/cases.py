# Each case builds one rclpy entity with a "type" that is not a ROS 2 interface class.
# Usage: python3 cases.py <case>   (one process per case, see repro.sh)
import sys, time, traceback
import rclpy
from rclpy.node import Node


def describe(t):
    return f"{t!r} type(t)={type(t).__name__}"


def case_ok_publisher(n):
    from std_msgs.msg import String
    print("  ", describe(String))
    n.create_publisher(String, 'chatter', 10)


def case_ros1_shadow_sub(n):
    # PYTHONPATH puts a fake ROS 1 style std_msgs (plain classes) first; see repro.sh
    from std_msgs.msg import String
    print("   String from", String.__module__, sys.modules['std_msgs'].__file__)
    n.create_subscription(String, 'voice_cmd', lambda m: None, 10)


def case_ros1_shadow_pub(n):
    from std_msgs.msg import String
    n.create_publisher(String, 'chatter', 10)


def case_pil_shadow(n):
    from sensor_msgs.msg import Image
    from PIL import Image  # noqa: F811  rebinds the name to the PIL module
    print("  ", describe(Image))
    n.create_subscription(Image, 'image', lambda m: None, 10)


def case_pil_alias_fix(n):
    from sensor_msgs.msg import Image
    from PIL import Image as PILImage  # noqa: F401
    print("  ", describe(Image))
    n.create_subscription(Image, 'image', lambda m: None, 10)


def case_class_shadow_srv(n):
    from example_interfaces.srv import AddTwoInts

    class AddTwoInts(Node):  # noqa: F811  node class named like the service
        pass
    print("  ", describe(AddTwoInts))
    n.create_service(AddTwoInts, 'add', lambda req, res: res)


def case_string_name_pub(n):
    n.create_publisher('std_msgs/msg/String', 'chatter', 10)


def case_string_name_action(n):
    from rclpy.action import ActionClient
    ActionClient(n, 'example_interfaces/action/Fibonacci', 'fibonacci')


def case_instance_pub(n):
    from std_msgs.msg import String
    p = n.create_publisher(String(), 'chatter', 10)
    print("   created:", p.msg_type)
    p.publish(String(data='x'))


def case_module_pub(n):
    from std_msgs import msg
    n.create_publisher(msg, 'chatter', 10)


def case_plain_class_action(n):
    from rclpy.action import ActionServer

    class MotorsGoal:
        def __init__(self, target_pwm=0):
            self.target_pwm = target_pwm
    ActionServer(n, MotorsGoal, 'motors', lambda gh: None)


def case_srv_as_pub(n):
    from example_interfaces.srv import AddTwoInts
    n.create_publisher(AddTwoInts, 'chatter', 10)


def case_msg_as_service(n):
    from std_msgs.msg import String
    n.create_service(String, 'add', lambda req, res: res)


def case_action_as_client(n):
    from example_interfaces.action import Fibonacci
    n.create_client(Fibonacci, 'fib')


def case_msg_as_action(n):
    from rclpy.action import ActionClient
    from std_msgs.msg import String
    ActionClient(n, String, 'fib')


def case_srv_request_as_pub(n):
    from example_interfaces.srv import AddTwoInts
    p = n.create_publisher(AddTwoInts.Request, 'req', 10)
    print("   created:", p.msg_type)


def case_wrong_msg_publish(n):
    from std_msgs.msg import String, Int32
    p = n.create_publisher(String, 'chatter', 10)
    p.publish(Int32(data=1))


def case_check_helper(n):
    # a quick check you can paste: ROS 2 classes have a Metaclass_* metaclass
    from std_msgs.msg import String
    from sensor_msgs.msg import Image
    for t in (String, Image, String(), 'std_msgs/msg/String'):
        print("   ", repr(t)[:60], "->", type(t).__name__, hasattr(type(t), '_TYPE_SUPPORT'))


def main():
    name = sys.argv[1]
    rclpy.init()
    n = Node('type_check_' + name)
    t0 = time.perf_counter()
    try:
        globals()['case_' + name](n)
        print(f"RESULT {name}: OK")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        last = tb[-1]
        print(f"RESULT {name}: {type(e).__module__}.{type(e).__name__}: {e}")
        print(f"   raised at {last.filename.split('site-packages/')[-1]}:{last.lineno} in {last.name}")
        print("   frames:", " > ".join(f.name for f in tb[1:]))
    print(f"   elapsed_ms={(time.perf_counter()-t0)*1000:.1f}")
    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
