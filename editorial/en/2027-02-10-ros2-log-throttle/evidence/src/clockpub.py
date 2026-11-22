#!/usr/bin/env python3
# Publishes /clock at 100 Hz, advancing sim time by STEP seconds per tick (0.1 -> 10x real time).
import sys, time
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock

step = float(sys.argv[1])
rclpy.init()
n = Node('clockpub')
p = n.create_publisher(Clock, '/clock', 10)
t = 100.0
while rclpy.ok():
    m = Clock()
    m.clock.sec = int(t)
    m.clock.nanosec = int((t - int(t)) * 1e9)
    p.publish(m)
    t += step
    time.sleep(0.01)
