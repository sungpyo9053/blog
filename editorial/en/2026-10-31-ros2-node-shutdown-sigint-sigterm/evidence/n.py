import sys, time, rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
mode = sys.argv[1]; slow = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
t0 = time.monotonic()
def log(m): print(f"[{mode} +{time.monotonic()-t0:.1f}s] {m}", flush=True)

def body(n):
    if not __import__("os").environ.get("NOTIMER"): n.create_timer(0.1, lambda: None)
    try:
        rclpy.spin(n)
        log("spin returned normally")
    except KeyboardInterrupt:
        log("caught KeyboardInterrupt")
    except ExternalShutdownException:
        log("caught ExternalShutdownException")
    finally:
        log("finally reached")
        if slow:
            time.sleep(slow); log(f"cleanup of {slow:.0f}s done")

if mode in ("classic", "try_shutdown"):
    rclpy.init(); n = Node("sd_node"); body(n); n.destroy_node()
    try:
        rclpy.shutdown() if mode == "classic" else rclpy.try_shutdown()
        log(f"{'shutdown' if mode=='classic' else 'try_shutdown'} ok")
    except Exception as e:
        log(f"shutdown raised {type(e).__name__}: {str(e).splitlines()[0][:90]}")
elif mode == "ctx":
    try:
        with rclpy.init():
            n = Node("sd_node"); body(n)
        log("context exited cleanly")
    except Exception as e:
        log(f"ctx raised {type(e).__name__}: {str(e).splitlines()[0][:90]}")
log("exiting")
