#!/usr/bin/env python3
# Publishes N sensor_msgs/Image messages at a fixed rate; the sequence number goes in header.frame_id.
import os, sys, time, json, argparse, rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
ap = argparse.ArgumentParser()
ap.add_argument('--topic', default='/cam'); ap.add_argument('--size', type=int, default=921600)
ap.add_argument('--rate', type=float, default=30.0); ap.add_argument('--n', type=int, default=300)
ap.add_argument('--rel', default='reliable'); ap.add_argument('--depth', type=int, default=10)
ap.add_argument('--wait-subs', type=int, default=1); ap.add_argument('--data', default='random')
a = ap.parse_args()
rclpy.init(); node = rclpy.create_node('cam_pub')
qos = QoSProfile(depth=a.depth, history=HistoryPolicy.KEEP_LAST,
                 reliability=ReliabilityPolicy.RELIABLE if a.rel == 'reliable' else ReliabilityPolicy.BEST_EFFORT)
pub = node.create_publisher(Image, a.topic, qos)
t0 = time.time()
while pub.get_subscription_count() < a.wait_subs and time.time() - t0 < 30: time.sleep(0.05)
time.sleep(1.0)
msg = Image(); msg.height = 1; msg.width = a.size; msg.encoding = 'mono8'; msg.step = a.size
msg.data = os.urandom(a.size) if a.data == 'random' else bytes(a.size)  # random = incompressible, like noisy camera data
period = 1.0 / a.rate if a.rate > 0 else 0.0
start = time.monotonic(); late = 0
for i in range(a.n):
    target = start + i * period
    now = time.monotonic()
    if now < target: time.sleep(target - now)
    elif period and now - target > period: late += 1
    msg.header.frame_id = str(i); msg.header.stamp = node.get_clock().now().to_msg()
    pub.publish(msg)
el = time.monotonic() - start
time.sleep(2.0)
print(json.dumps({'published': a.n, 'size': a.size, 'rate_set': a.rate, 'rate_achieved': round(a.n / el, 1),
                  'seconds': round(el, 2), 'late_over_one_period': late, 'rel': a.rel, 'depth': a.depth, 'data': a.data}), flush=True)
node.destroy_node(); rclpy.shutdown()
