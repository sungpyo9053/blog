# Usage: python3 loop_subs.py <variant>
import sys, time, functools, inspect
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

TOPICS = ['/robot1/pose', '/robot2/pose', '/robot3/pose']
N = 20
variant = sys.argv[1]

class Sub(Node):
    def __init__(self):
        super().__init__('loop_sub')
        self.got = []
        self.subs = []
        if variant == 'factory':
            def make_cb(t):
                return lambda msg: self.cb(msg, t)
        for topic in TOPICS:
            if variant == 'lambda':
                cb = lambda msg: self.cb(msg, topic)
            elif variant == 'default_arg':
                cb = lambda msg, t=topic: self.cb(msg, t)
            elif variant == 'kwonly_default':
                cb = lambda msg, *, t=topic: self.cb(msg, t)
            elif variant == 'partial':
                cb = functools.partial(self.cb, topic=topic)
            elif variant == 'factory':
                cb = make_cb(topic)
            elif variant == 'not_stored':
                cb = functools.partial(self.cb, topic=topic)
            if variant == 'not_stored':
                self.create_subscription(String, topic, cb, 10)
            else:
                self.subs.append(self.create_subscription(String, topic, cb, 10))

    def cb(self, msg, topic):
        self.got.append((msg.data, topic if isinstance(topic, str) else type(topic).__name__))

class Pub(Node):
    def __init__(self):
        super().__init__('loop_pub')
        self.pubs = {t: self.create_publisher(String, t, 10) for t in TOPICS}
        self.sent = 0
    def wait_matched(self, timeout=5.0):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            if all(p.get_subscription_count() > 0 for p in self.pubs.values()):
                return time.monotonic() - t0
            time.sleep(0.01)
        return None
    def tick(self):
        for t, p in self.pubs.items():
            p.publish(String(data=t))
        self.sent += 1

rclpy.init()
sub, pub = Sub(), Pub()
ex = SingleThreadedExecutor(); ex.add_node(sub); ex.add_node(pub)
print('variant', variant)
print('matched_after_s', pub.wait_matched())
for _ in range(N):
    pub.tick()
    t_end = time.monotonic() + 0.05
    while time.monotonic() < t_end:
        ex.spin_once(timeout_sec=0.01)
for _ in range(50):
    ex.spin_once(timeout_sec=0.01)
right = sum(1 for d, t in sub.got if d == t)
wrong = len(sub.got) - right
from collections import Counter
print('sent_per_topic', N, 'received', len(sub.got), 'label_matches_source', right, 'label_wrong', wrong)
print('labels_seen', dict(Counter(t for d, t in sub.got)))
if variant in ('default_arg', 'kwonly_default', 'partial', 'factory', 'lambda'):
    print('callback_params', list(inspect.signature(sub.subs[0].callback).parameters) if sub.subs else 'n/a')
rclpy.shutdown()
