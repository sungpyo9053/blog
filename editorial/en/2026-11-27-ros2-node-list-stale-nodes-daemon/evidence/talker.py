#!/usr/bin/env python3
# Minimal rclpy talker: node <name>, publishes std_msgs/String on /chatter_<name> at 2 Hz.
# Tutorial-style shutdown: KeyboardInterrupt -> destroy_node -> try_shutdown.
import os, sys, rclpy
from rclpy.node import Node
from std_msgs.msg import String
name = sys.argv[1]
rclpy.init()
n = Node(name)
pub = n.create_publisher(String, 'chatter_' + name, 10)
n.create_timer(0.5, lambda: pub.publish(String(data='hi')))
print(f'started {name} domain={os.environ.get("ROS_DOMAIN_ID", "unset")} rmw={os.environ.get("RMW_IMPLEMENTATION", "default")}', flush=True)
try:
    rclpy.spin(n)
except KeyboardInterrupt:
    print('KeyboardInterrupt', flush=True)
except BaseException as e:
    print('exception', type(e).__name__, e, flush=True)
finally:
    n.destroy_node()
    rclpy.try_shutdown()
    print('clean exit', flush=True)
