# CPU cost of rclpy spin patterns. One case per process.
# usage: python3 cpu.py <entity> <mode>
#   entity: idle | timer:<hz> | sub | pub:<hz> | coro
#   mode:   spin | once0 | once10ms | onceNone | once0_sleep1ms | steonce | mte | ee
# Prints: RESULT ... cpu_pct=<process CPU time / wall time * 100> events_per_s=<callbacks per second>
import os, sys, time, threading
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

WARM = float(os.environ.get('WARM', '2'))
DUR = float(os.environ.get('DUR', '8'))
TAIL = float(os.environ.get('TAIL', '0'))
count = [0]


def os_threads():
    with open('/proc/self/status') as f:
        for line in f:
            if line.startswith('Threads:'):
                return int(line.split()[1])
    return -1


def measure(label):
    time.sleep(WARM)
    c0 = count[0]
    p0 = time.process_time(); w0 = time.monotonic()
    time.sleep(DUR)
    p1 = time.process_time(); w1 = time.monotonic()
    c1 = count[0]
    print('RESULT %-34s cpu_pct=%6.1f events_per_s=%7.1f os_threads=%d total_events=%d' % (
        label, 100.0 * (p1 - p0) / (w1 - w0), (c1 - c0) / (w1 - w0), os_threads(), c1), flush=True)
    time.sleep(TAIL)
    os._exit(0)


def cb(*_):
    count[0] += 1


def main():
    entity, mode = sys.argv[1], sys.argv[2]
    if mode == 'ee':
        try:
            from rclpy.experimental import EventsExecutor  # noqa: F401
        except Exception as e:
            print('RESULT %s %s ee UNAVAILABLE %s: %s' % (
                os.environ.get('RMW_IMPLEMENTATION', 'default'), entity, type(e).__name__, e), flush=True)
            return
    rclpy.init()
    node = Node('cpu_probe_%d' % os.getpid())
    if entity.startswith('timer:'):
        node.create_timer(1.0 / float(entity.split(':')[1]), cb)
    elif entity == 'coro':  # rclpy issue 1405: async timer callback awaiting a Future that never completes
        from rclpy.task import Future

        async def coro():
            count[0] += 1
            await Future()
        node.create_timer(1.0, coro)
    elif entity == 'sub':
        node.create_subscription(String, '/cpu_test', cb, 10)
    elif entity.startswith('pub:'):
        pub = node.create_publisher(String, '/cpu_test', 10)
        msg = String(); msg.data = 'x' * 16

        def tick():
            pub.publish(msg); count[0] += 1
        node.create_timer(1.0 / float(entity.split(':')[1]), tick)

    def run():
        if mode == 'spin':
            rclpy.spin(node)
        elif mode == 'once0':
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0)
        elif mode == 'once10ms':
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.01)
        elif mode == 'onceNone':
            while rclpy.ok():
                rclpy.spin_once(node)
        elif mode == 'once0_sleep1ms':
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0)
                time.sleep(0.001)
        elif mode == 'steonce':
            from rclpy.executors import SingleThreadedExecutor
            ex = SingleThreadedExecutor(); ex.add_node(node)
            while rclpy.ok():
                ex.spin_once()
        elif mode == 'mte':
            from rclpy.executors import MultiThreadedExecutor
            ex = MultiThreadedExecutor(); ex.add_node(node); ex.spin()
        elif mode == 'ee':
            from rclpy.experimental import EventsExecutor
            ex = EventsExecutor(); ex.add_node(node); ex.spin()
    threading.Thread(target=run, daemon=True).start()
    measure('%s %s %s' % (os.environ.get('RMW_IMPLEMENTATION', 'default'), entity, mode))


if __name__ == '__main__':
    main()
