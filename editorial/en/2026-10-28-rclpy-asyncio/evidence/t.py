"""rclpy + asyncio experiments. Usage: python3 t.py A|B|C|D"""
import asyncio, sys, threading, time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

mode = sys.argv[1]
rclpy.init()
node = Node("t_" + mode)
log = lambda *a: print(f"[{mode} {time.monotonic():.2f}]", *a, flush=True)


def handle(req, res):
    res.success = True
    return res


if mode == "A":
    # asyncio awaitable inside an rclpy async callback
    async def cb():
        log("cb start")
        try:
            await asyncio.sleep(0.1)
            log("after asyncio.sleep")
        except BaseException as e:
            log("EXC", type(e).__name__, e)
    node.create_timer(0.5, cb)
    end = time.monotonic() + 2
    try:
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
    except BaseException as e:
        log("SPIN EXC", type(e).__name__, e)

elif mode == "A2":
    # asyncio.run inside a plain sync callback
    def cb():
        t0 = time.monotonic()
        asyncio.run(asyncio.sleep(0.1))
        log("asyncio.run ok after %.2fs" % (time.monotonic() - t0))
    node.create_timer(0.5, cb)
    end = time.monotonic() + 1.2
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

elif mode in ("B", "B2", "B3", "B4"):
    # rclpy future (service call) awaited inside an rclpy async callback
    # B: all default group; B2: timer in ReentrantCallbackGroup; B3: server on a second node
    from rclpy.callback_groups import ReentrantCallbackGroup
    from rclpy.executors import SingleThreadedExecutor
    ex = SingleThreadedExecutor(); ex.add_node(node)
    if mode == "B3":
        srv_node = Node("srv"); ex.add_node(srv_node)
        srv_node.create_service(Trigger, "trig", handle)
    else:
        node.create_service(Trigger, "trig", handle)
    from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
    # B4: timer stays in the default group, only the client gets its own group
    cli = node.create_client(Trigger, "trig", callback_group=MutuallyExclusiveCallbackGroup() if mode == "B4" else None)
    group = ReentrantCallbackGroup() if mode == "B2" else None
    done = []
    async def cb():
        if done:
            return
        log("cb start")
        res = await cli.call_async(Trigger.Request())
        log("got response success=", res.success)
        done.append(1)
    node.create_timer(0.5, cb, callback_group=group)
    end = time.monotonic() + 3
    while time.monotonic() < end and not done:
        ex.spin_once(timeout_sec=0.1)
    log("done" if done else "TIMEOUT no response")

elif mode == "C":
    # rclpy spins in a thread, asyncio owns the main thread
    from std_msgs.msg import String
    async def main():
        loop = asyncio.get_running_loop()
        q = asyncio.Queue()
        node.create_subscription(String, "chat", lambda m: loop.call_soon_threadsafe(q.put_nowait, m.data), 10)
        pub = node.create_publisher(String, "chat", 10)
        threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()
        await asyncio.sleep(0.5)
        for i in range(5):
            pub.publish(String(data=f"msg{i}"))
            await asyncio.sleep(0.1)
        got = []
        try:
            while True:
                got.append(await asyncio.wait_for(q.get(), 1.0))
        except asyncio.TimeoutError:
            pass
        log("received", len(got), got)
    asyncio.run(main())

elif mode == "D":
    # spin_until_future_complete inside a callback (sync style)
    node.create_service(Trigger, "trig", handle)
    cli = node.create_client(Trigger, "trig")
    def cb():
        log("cb start")
        f = cli.call_async(Trigger.Request())
        t0 = time.monotonic()
        try:
            rclpy.spin_until_future_complete(node, f, timeout_sec=2.0)
            log("future done=", f.done(), "after %.2fs" % (time.monotonic() - t0))
        except BaseException as e:
            log("EXC", type(e).__name__, e)
        raise SystemExit
    node.create_timer(0.5, cb)
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    except BaseException as e:
        log("SPIN EXC", type(e).__name__, e)

log("exit")
