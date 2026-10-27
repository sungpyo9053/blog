import time, rclpy
from rclpy.node import Node
from rclpy.task import Future
from rclpy.executors import SingleThreadedExecutor
import rclpy.executors as ex

def sleep_cancel(node, sec):          # helper posted in the issue: cancel only
    fut = Future(); t = None
    def done():
        fut.set_result(None); t.cancel()
    t = node.create_timer(sec, done); return fut

def sleep_destroy(node, sec):         # same, but destroy the timer
    fut = Future(); t = None
    def done():
        fut.set_result(None); node.destroy_timer(t)
    t = node.create_timer(sec, done); return fut

async def run(node, helper, n, sec):
    errs = []
    t0 = time.monotonic()
    for _ in range(n):
        s = time.monotonic(); await helper(node, sec); errs.append(time.monotonic() - s - sec)
    return time.monotonic() - t0, max(errs), len(list(node.timers))

rclpy.init()
print("rclpy executors:", sorted(n for n in dir(ex) if "xecutor" in n))
for name, h in (("cancel", sleep_cancel), ("destroy", sleep_destroy)):
    node = Node("n_" + name); e = SingleThreadedExecutor(); e.add_node(node)
    # a 20 Hz timer keeps running to show the executor is not blocked while sleeping
    ticks = [0]; node.create_timer(0.05, lambda: ticks.__setitem__(0, ticks[0] + 1))
    task = e.create_task(run(node, h, 50, 0.02))
    e.spin_until_future_complete(task, timeout_sec=30)
    total, worst, ntimers = task.result()
    print("%s: 50 x 0.02s sleeps took %.2fs, worst overshoot %.1f ms, timers left on node %d (1 is the 20 Hz timer), other timer ticks %d"
          % (name, total, worst * 1000, ntimers, ticks[0]))
    e.shutdown(); node.destroy_node()
rclpy.shutdown()
