import os, sys, time, json, threading, rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float64
depth, lifespan = int(sys.argv[1]), float(sys.argv[2])
HZ, LATE = 10.0, 3.0
def qos(life=None):
    q = QoSProfile(depth=depth, history=HistoryPolicy.KEEP_LAST, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
    if life: q.lifespan = Duration(seconds=life)
    return q
rclpy.init(); ex = MultiThreadedExecutor()
pn = Node("pub"); pub = pn.create_publisher(Float64, "state", qos(lifespan or None))
pn.create_timer(1.0 / HZ, lambda: pub.publish(Float64(data=time.monotonic())))
ex.add_node(pn); threading.Thread(target=ex.spin, daemon=True).start()
time.sleep(LATE)
rx = []; joined = time.monotonic()
sn = Node("late_sub"); sn.create_subscription(Float64, "state", lambda m: rx.append((time.monotonic(), m.data)), qos())
ex.add_node(sn); time.sleep(1.5)
history = [(r, s) for r, s in rx if s < joined]  # samples published before the subscriber existed
print(json.dumps({"depth": depth, "pub_lifespan_s": lifespan, "rmw": os.environ.get("RMW_IMPLEMENTATION", "rmw_fastrtps_cpp(default)"),
  "history_count": len(history),
  "oldest_age_at_join_s": round(joined - min(s for _, s in history), 3) if history else None,
  "history_arrival_after_join_s": round(min(r for r, _ in history) - joined, 3) if history else None}), flush=True)
os._exit(0)
