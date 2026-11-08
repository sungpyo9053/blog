# Cross-process: role 'pub' prints its matched subscription count timeline; role 'sub' subscribes, destroys after 2 s.
import sys, time, rclpy
from rclpy.node import Node
from std_msgs.msg import String
role = sys.argv[1]
rclpy.init()
n = Node('xproc_' + role)
if role == 'pub':
    p = n.create_publisher(String, '/xproc_topic', 10)
    t0 = time.monotonic(); last = None
    while time.monotonic() - t0 < 12:
        c = p.get_subscription_count()
        if c != last:
            print(f'pub wall {time.time():.3f} t={time.monotonic()-t0:.3f}s matched={c} graph={n.count_subscribers("/xproc_topic")}', flush=True); last = c
        p.publish(String(data='x')); time.sleep(0.01)
else:
    got = [0, 0]; st = {'d': False}
    s = n.create_subscription(String, '/xproc_topic', lambda m: got.__setitem__(1 if st['d'] else 0, got[1 if st['d'] else 0] + 1), 10)
    end = time.monotonic() + 3
    while time.monotonic() < end: rclpy.spin_once(n, timeout_sec=0.01)
    n.destroy_subscription(s); st['d'] = True
    print(f'sub destroy_subscription at wall {time.time():.3f}', flush=True)
    end = time.monotonic() + 3
    while time.monotonic() < end: rclpy.spin_once(n, timeout_sec=0.01)
    print('sub msgs_before', got[0], 'msgs_after', got[1], flush=True)
rclpy.shutdown()
