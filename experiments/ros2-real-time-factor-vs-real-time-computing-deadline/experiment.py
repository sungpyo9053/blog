#!/usr/bin/env python3
"""RTF 1.0 and deadline keeping are different measurements: show both in one ROS 2 Jazzy run.

A 100 Hz rclpy timer (period = deadline = 10 ms) runs in five phases:

  wall_baseline         steady-clock timer, nothing injected
  wall_injected         steady-clock timer, a 22 ms sleep in every 50th callback (deliberate control)
  sim_rtf1              use_sim_time timer, /clock from a separate process paced at target RTF 1.0
  sim_rtf1_injected     same as sim_rtf1 plus the 22 ms injection
  sim_rtf05             use_sim_time timer, /clock paced at target RTF 0.5

The /clock publisher is a separate OS process (like a simulator), so the injected sleep in the
control node cannot stall it. Every number printed is measured at run time; each phase prints
one JSON line.
"""
import json
import os
import statistics
import subprocess
import sys
import time

PERIOD_MS = 10.0          # timer period; implicit deadline = period
DEADLINE_MS = PERIOD_MS
INJECT_MS = 22.0          # deliberate overrun, longer than one period
INJECT_EVERY = 50         # inject in callback #25, #75, #125, ...
PHASE_S = 5.0             # measured wall seconds per phase
CLOCK_STEP_MS = 1.0       # simulated time added per /clock message
WALL_BUDGET_MS = 25.0     # illustrative wall budget from the arithmetic contract example
JITTER_PCT = 5.0          # allowable jitter assumed in the official real-time tutorial (5 % of period)
STATS_WINDOW_MS = 100.0   # publisher-side RTF window (Gazebo Sim sends stats at most 10/s)
STOP_FILE = "/tmp/stop_clock"


def clock_main(rtf: float) -> None:
    """Simulator stand-in: advance sim time by fixed steps, paced to a target RTF."""
    import rclpy
    from rosgraph_msgs.msg import Clock

    rclpy.init()
    node = rclpy.create_node("sim_clock")
    pub = node.create_publisher(Clock, "/clock", 10)
    step_ns = int(CLOCK_STEP_MS * 1e6)
    wall_step_ns = int(step_ns / rtf)
    sim_ns = 1_000_000_000  # start at sim 1 s so "no /clock yet" (0) is distinguishable
    msg = Clock()
    samples = []
    target = time.monotonic_ns()
    next_sample = target
    while True:
        msg.clock.sec, msg.clock.nanosec = divmod(sim_ns, 1_000_000_000)
        pub.publish(msg)
        now = time.monotonic_ns()
        if now >= next_sample:
            samples.append((now, sim_ns))
            next_sample = now + int(STATS_WINDOW_MS * 1e6)
            if os.path.exists(STOP_FILE):
                break
        sim_ns += step_ns
        target += wall_step_ns
        if now > target + wall_step_ns:
            target = now  # fell behind: lost wall time stays lost, so RTF drops (no catch-up burst)
        delay = target - time.monotonic_ns()
        if delay > 0:
            time.sleep(delay / 1e9)
    print(json.dumps({"samples": samples}), flush=True)
    node.destroy_node()
    rclpy.shutdown()


def cpu_stat():
    """cgroup v2 CPU counters of this container (None outside a cgroup v2 container)."""
    try:
        with open("/sys/fs/cgroup/cpu.stat") as f:
            return {k: int(v) for k, v in (line.split() for line in f)}
    except (OSError, ValueError):
        return None


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q / 100 * (len(ordered) - 1))))]


def r(x, nd=3):
    return None if x is None else round(x, nd)


class Recorder:
    """Timer callback that records start/end in wall (monotonic) and timer clocks."""

    def __init__(self, clock, inject: bool):
        self.clock = clock
        self.inject = inject
        self.rows = []  # (wall_start, timer_start, wall_end, timer_end, injected)

    def __call__(self):
        wall_start = time.monotonic_ns()
        timer_start = self.clock.now().nanoseconds
        injected = self.inject and (len(self.rows) + 1) % INJECT_EVERY == INJECT_EVERY // 2
        if injected:
            time.sleep(INJECT_MS / 1000)
        self.rows.append((wall_start, timer_start, time.monotonic_ns(),
                          self.clock.now().nanoseconds, injected))


def analyse(rows, period_ns):
    """Mirror rcl_timer_call's fixed grid (next = expected + period, skip missed periods)."""
    rows = rows[1:]  # drop the first callback: its interval has no predecessor in this phase
    lateness, response, intervals_wall, intervals_timer = [], [], [], []
    expected = rows[0][1]
    skipped = 0
    for i, (ws, ts, we, te, _inj) in enumerate(rows):
        if i:
            intervals_wall.append((ws - rows[i - 1][0]) / 1e6)
            intervals_timer.append((ts - rows[i - 1][1]) / 1e6)
        late_ms = (ts - expected) / 1e6
        lateness.append(late_ms)
        response.append(late_ms + (we - ws) / 1e6)  # start delay on the grid + execution (wall)
        nxt = expected + period_ns
        if nxt <= ts:
            ahead = 1 + (ts - nxt) // period_ns
            skipped += ahead
            nxt += ahead * period_ns
        expected = nxt
    span_ms = (rows[-1][1] - rows[0][1]) / 1e6
    return {
        "callbacks": len(rows),
        "grid_periods_spanned": int(round(span_ms / PERIOD_MS)),
        "skipped_periods": skipped,
        "injected": sum(1 for row in rows if row[4]),
        "interval_wall_ms": {"mean": r(statistics.fmean(intervals_wall)), "min": r(min(intervals_wall)),
                             "p99": r(percentile(intervals_wall, 99)), "max": r(max(intervals_wall))},
        "max_wall_interval_at_s": r((rows[intervals_wall.index(max(intervals_wall)) + 1][0] - rows[0][0]) / 1e9),
        "interval_timer_clock_ms": {"mean": r(statistics.fmean(intervals_timer)),
                                    "max": r(max(intervals_timer))},
        "start_lateness_ms": {"mean": r(statistics.fmean(lateness)), "max": r(max(lateness))},
        "response_ms_max": r(max(response)),
        "deadline_ms": DEADLINE_MS,
        "deadline_misses": sum(1 for x in response if x > DEADLINE_MS),
        "wall_intervals_over_period": sum(1 for x in intervals_wall if x > PERIOD_MS),
        "wall_intervals_over_period_plus_jitter": sum(
            1 for x in intervals_wall if x > PERIOD_MS * (1 + JITTER_PCT / 100)),
        "jitter_tolerance_ms": PERIOD_MS * JITTER_PCT / 100,
        "max_wall_interval_minus_deadline_ms": r(max(intervals_wall) - DEADLINE_MS),
        "wall_intervals_over_budget": sum(1 for x in intervals_wall if x > WALL_BUDGET_MS),
        "wall_budget_ms": WALL_BUDGET_MS,
        "exec_timer_clock_ms_max_injected": r(max(((te - ts) / 1e6 for _, ts, _, te, inj in rows if inj),
                                                   default=None)),
        "exec_wall_ms_max_injected": r(max(((we - ws) / 1e6 for ws, _, we, _, inj in rows if inj),
                                            default=None)),
    }


def run_phase(name, sim_rtf, inject):
    import rclpy
    from rclpy.clock import Clock, ClockType
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.parameter import Parameter

    clock_proc = None
    if sim_rtf is not None:
        if os.path.exists(STOP_FILE):
            os.remove(STOP_FILE)
        clock_proc = subprocess.Popen([sys.executable, __file__, "--clock", str(sim_rtf)],
                                      stdout=subprocess.PIPE, text=True)
        node = rclpy.create_node(f"control_{name}",
                                 parameter_overrides=[Parameter("use_sim_time", value=True)])
        timer_clock = node.get_clock()
    else:
        node = rclpy.create_node(f"control_{name}")
        timer_clock = Clock(clock_type=ClockType.STEADY_TIME)
    executor = SingleThreadedExecutor()
    executor.add_node(node)

    waited_s = None
    if clock_proc is not None:
        t0 = time.monotonic()
        while node.get_clock().now().nanoseconds == 0:
            executor.spin_once(timeout_sec=0.05)
            if time.monotonic() - t0 > 15:
                clock_proc.kill()
                raise RuntimeError(f"{name}: no /clock received within 15 s")
        waited_s = round(time.monotonic() - t0, 3)

    cpu_before = cpu_stat()
    rec = Recorder(timer_clock, inject)
    timer = node.create_timer(PERIOD_MS / 1000, rec, clock=timer_clock)
    start = time.monotonic_ns()
    end = start + int(PHASE_S * 1e9)
    while time.monotonic_ns() < end:
        executor.spin_once(timeout_sec=0.05)
    node.destroy_timer(timer)
    cpu_after = cpu_stat()
    result = {"phase": name, "timer_clock": "ros_time(use_sim_time)" if sim_rtf else "steady",
              "target_rtf": sim_rtf, "inject_ms": INJECT_MS if inject else 0,
              "inject_every": INJECT_EVERY if inject else None, "period_ms": PERIOD_MS}
    result.update(analyse(rec.rows, int(PERIOD_MS * 1e6)))
    if cpu_before and cpu_after:
        result["cgroup_cpu_delta"] = {k: cpu_after[k] - cpu_before[k]
                                      for k in ("nr_periods", "nr_throttled", "throttled_usec", "usage_usec")
                                      if k in cpu_before and k in cpu_after}

    if clock_proc is not None:
        with open(STOP_FILE, "w"):
            pass
        out, _ = clock_proc.communicate(timeout=20)
        samples = json.loads(out.strip().splitlines()[-1])["samples"]
        first, last = rec.rows[1], rec.rows[-1]
        node_rtf = (last[1] - first[1]) / (last[0] - first[0])
        inside = [s for s in samples if first[0] <= s[0] <= last[0]]
        windows = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(inside, inside[1:])]
        result.update({
            "first_clock_wait_s": waited_s,
            "rtf_seen_by_control_node": r(node_rtf, 4),
            "rtf_clock_publisher": r((inside[-1][1] - inside[0][1]) / (inside[-1][0] - inside[0][0]), 4),
            "rtf_clock_publisher_100ms_min": r(min(windows), 4),
            "rtf_clock_publisher_100ms_max": r(max(windows), 4),
            "rtf_windows": len(windows),
        })
    executor.remove_node(node)
    node.destroy_node()
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--clock":
        clock_main(float(sys.argv[2]))
        return
    import rclpy

    started = time.monotonic()
    rclpy.init()
    print(json.dumps({"phase": "environment", "kernel": os.uname().release, "kernel_version": os.uname().version,
                      "python": sys.version.split()[0], "cpus_visible": os.cpu_count(),
                      "rmw": os.environ.get("RMW_IMPLEMENTATION", "default"),
                      "discovery_range": os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE", "unset")}), flush=True)
    run_phase("wall_baseline", None, False)
    run_phase("wall_injected", None, True)
    run_phase("sim_rtf1", 1.0, False)
    run_phase("sim_rtf1_injected", 1.0, True)
    run_phase("sim_rtf05", 0.5, False)
    rclpy.shutdown()
    print(json.dumps({"phase": "done", "total_wall_s": round(time.monotonic() - started, 2)}), flush=True)


if __name__ == "__main__":
    main()
