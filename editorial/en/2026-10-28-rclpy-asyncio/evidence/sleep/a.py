import asyncio, time, rclpy
from rclpy.experimental import AsyncNode

async def main():
    async with AsyncNode('sleeper') as node:
        ticks = [0]
        node.create_timer(0.05, lambda: ticks.__setitem__(0, ticks[0] + 1))
        clock = node.get_clock()
        errs = []; t0 = time.monotonic()
        for _ in range(50):
            s = time.monotonic(); await clock.sleep(0.02); errs.append(time.monotonic() - s - 0.02)
        print("AsyncClock.sleep: 50 x 0.02s took %.2fs, min %.1f ms, worst overshoot %.1f ms, other timer ticks %d"
              % (time.monotonic() - t0, min(errs) * 1000, max(errs) * 1000, ticks[0]))
        node.destroy_node()

rclpy.init(); asyncio.run(main()); rclpy.shutdown()
