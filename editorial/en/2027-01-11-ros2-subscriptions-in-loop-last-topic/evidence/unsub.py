# destroy_subscription: messages after destroy, and publisher matched count timeline
import time, rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String
rclpy.init()
sub = Node('unsub_sub'); pub = Node('unsub_pub')
got = {'before': 0, 'after': 0}
state = {'destroyed': False}
def cb(msg):
    got['after' if state['destroyed'] else 'before'] += 1
s = sub.create_subscription(String, '/unsub_topic', cb, 10)
p = pub.create_publisher(String, '/unsub_topic', 10)
ex = SingleThreadedExecutor(); ex.add_node(sub); ex.add_node(pub)
t0 = time.monotonic()
while p.get_subscription_count() == 0 and time.monotonic() - t0 < 5: time.sleep(0.01)
def run(sec):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        p.publish(String(data='x')); 
        e2 = time.monotonic() + 0.02
        while time.monotonic() < e2: ex.spin_once(timeout_sec=0.005)
run(1.0)
print('subs_count_before', p.get_subscription_count(), 'count_subscribers', pub.count_subscribers('/unsub_topic'))
r = sub.destroy_subscription(s); state['destroyed'] = True
td = time.monotonic()
print('destroy_subscription returned', r)
drop = None
while time.monotonic() - td < 5:
    if p.get_subscription_count() == 0 and drop is None:
        drop = time.monotonic() - td
    run(0.02)
print('publisher_matched_count_zero_after_s', None if drop is None else round(drop, 4))
print('count_subscribers_graph_after_5s', pub.count_subscribers('/unsub_topic'))
print('msgs_before', got['before'], 'msgs_after_destroy', got['after'])
rclpy.shutdown()
