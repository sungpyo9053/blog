#!/usr/bin/env python3
"""Observation-buffer reuse in a Gym-style robot env fed by ROS 2 joint-angle messages.

A simulated arm node publishes one joint angle per step (std_msgs/Float64). A Gym-style
env (no gymnasium in the image, so a minimal class) receives it in a rclpy subscription
callback and returns an observation according to one of several return policies.
Several consumers store the returned observations. Everything printed is computed at
run time; nothing below is a pre-written result.
"""
import json
import platform
import sys
import time
from collections import deque

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Float64

STEPS = 4            # buffer length / steps per episode
DT = 0.125           # nominal step interval [s] used for finite-difference velocity
INCREMENTS = (0.25, 0.0)  # moving joint, and the "joint does not move" counterexample
TOPIC = "/arm/joint_angle"
POLICIES = ("reuse", "view", "asarray", "copy", "np_array", "rebind")


def emit(**record):
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)


class ArmSim(Node):
    """Publishes the joint angle the arm reaches after each step command."""

    def __init__(self):
        super().__init__("arm_sim")
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        self.pub = self.create_publisher(Float64, TOPIC, qos)
        self.angle = 0.0

    def reset(self):
        self.angle = 0.0

    def advance(self, increment):
        self.angle += increment
        msg = Float64()
        msg.data = self.angle
        self.pub.publish(msg)
        return self.angle


class GymStyleArmEnv(Node):
    """Gym-style env: subscription callback writes the latest angle into self._q."""

    def __init__(self, policy):
        super().__init__(f"arm_env_{policy}")
        self.policy = policy
        self._q = np.zeros(1, dtype=np.float64)
        self.received = 0
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        self.sub = self.create_subscription(Float64, TOPIC, self._on_angle, qos)

    def _on_angle(self, msg):
        if self.policy == "rebind":
            self._q = np.array([msg.data], dtype=np.float64)   # new array, old one untouched
        else:
            self._q[0] = msg.data                              # in-place mutation
        self.received += 1

    def _obs(self):
        if self.policy in ("reuse", "rebind"):
            return self._q
        if self.policy == "view":
            return self._q[:]
        if self.policy == "asarray":
            return np.asarray(self._q)
        if self.policy == "copy":
            return self._q.copy()
        if self.policy == "np_array":
            return np.array(self._q)
        raise ValueError(self.policy)

    def reset(self):
        if self.policy == "rebind":
            self._q = np.zeros(1, dtype=np.float64)
        else:
            self._q[0] = 0.0
        return self._obs(), {}

    def step(self, sim, executor, increment):
        before = self.received
        t0 = time.perf_counter()
        sim.advance(increment)
        deadline = time.monotonic() + 5.0
        while self.received == before and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if self.received == before:
            raise RuntimeError(f"no joint-angle message within 5 s (policy={self.policy})")
        return self._obs(), 0.0, False, False, {}, latency_ms


class CopyingBuffer:
    """Preallocated storage that copies on add (the Stable-Baselines3 ReplayBuffer pattern)."""

    def __init__(self, size):
        self.data = np.zeros((size, 1), dtype=np.float64)
        self.pos = 0

    def append(self, obs):
        self.data[self.pos] = np.array(obs)
        self.pos += 1

    def values(self):
        return [float(v) for v in self.data[:self.pos, 0]]


def velocities(values):
    return [(values[i + 1] - values[i]) / DT for i in range(len(values) - 1)]


def shares(a, b):
    return bool(np.shares_memory(a, b))


def wait_for_match(sim, env, executor):
    deadline = time.monotonic() + 10.0
    while sim.pub.get_subscription_count() < 1 and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
    if sim.pub.get_subscription_count() < 1:
        raise RuntimeError("subscription never matched")
    for _ in range(5):
        executor.spin_once(timeout_sec=0.02)


def run_episode(policy, increment):
    sim = ArmSim()
    env = GymStyleArmEnv(policy)
    executor = SingleThreadedExecutor()
    executor.add_node(sim)
    executor.add_node(env)
    try:
        wait_for_match(sim, env, executor)
        sim.reset()
        reset_obs, _ = env.reset()
        returned, snapshot, latencies = [], [], []
        list_buf, deque_buf, copy_buf = [], deque(maxlen=STEPS), CopyingBuffer(STEPS)
        stack_refs, stack_outputs = deque(maxlen=STEPS), []
        published = []
        for _ in range(STEPS):
            obs, _r, _term, _trunc, _info, latency = env.step(sim, executor, increment)
            published.append(sim.angle)
            snapshot.append(float(obs[0]))          # value at the moment step() returned
            returned.append(obs)
            latencies.append(latency)
            list_buf.append(obs)
            deque_buf.append(obs)
            copy_buf.append(obs)
            stack_refs.append(obs)                   # frame-stack mimic: deque of references
            stack_outputs.append(np.stack(list(stack_refs)).copy())  # new stacked array every step
        received = env.received
        # Read every consumer after the episode, before any reset.
        consumers = {
            "list_append": [float(o[0]) for o in list_buf],
            "deque_maxlen4": [float(o[0]) for o in deque_buf],
            "copy_on_add": copy_buf.values(),
            "frame_stack_last_output": [float(v) for v in stack_outputs[-1][:, 0]],
        }
        # check_env-style sequence in Gymnasium 1.4.0: reset -> step -> step -> reset.
        reset_end_obs, _ = env.reset()
        list_after_reset = [float(o[0]) for o in list_buf]
        checked = [("reset0", reset_obs), ("step1", returned[0]), ("step2", returned[1]),
                   ("reset_end", reset_end_obs)]
        pair_shares = {f"{a}~{b}": shares(x, y)
                       for i, (a, x) in enumerate(checked) for (b, y) in checked[i + 1:]}
        return {
            "published_rad": published, "snapshot_rad": snapshot, "received_msgs": received,
            "consumers": consumers, "list_after_reset_rad": list_after_reset,
            "consecutive_is": [returned[i] is returned[i + 1] for i in range(STEPS - 1)],
            "consecutive_shares_memory": [shares(returned[i], returned[i + 1]) for i in range(STEPS - 1)],
            "reset_step1_shares_memory": shares(reset_obs, returned[0]),
            "checkenv_style_pairs": pair_shares,
            "latency_ms": latencies,
        }
    finally:
        executor.remove_node(env)
        executor.remove_node(sim)
        env.destroy_node()
        sim.destroy_node()
        executor.shutdown()


CONSUMER_KEYS = {"list_append": "list", "deque_maxlen4": "deque", "copy_on_add": "copy_buf",
                 "frame_stack_last_output": "stack"}


def main():
    # The harness keeps only the last 8000 stdout characters, so each episode is one compact line.
    started = time.monotonic()
    rclpy.init()
    emit(kind="env", python=platform.python_version(), numpy=np.__version__,
         ros_distro=__import__("os").environ.get("ROS_DISTRO", ""), steps=STEPS, dt_s=DT)
    summary = []
    all_latency = []
    all_received = 0
    try:
        for increment in INCREMENTS:
            for policy in POLICIES:
                ep = run_episode(policy, increment)
                truth = ep["snapshot_rad"]
                stored, mean, oldest_err, vel, bad = {}, {}, {}, {}, {}
                for consumer, values in ep["consumers"].items():
                    key = CONSUMER_KEYS[consumer]
                    errors = [s - t for s, t in zip(values, truth)]
                    tests = {
                        "last_slot_value": values[-1] != truth[-1],
                        "oldest_slot_value": values[0] != truth[0],
                        "shares_memory_between_steps": any(ep["consecutive_shares_memory"]),
                        "checkenv_style_any_pair": any(ep["checkenv_style_pairs"].values()),
                    }
                    stored[key] = values
                    mean[key] = float(np.mean(values))
                    oldest_err[key] = errors[0]
                    vel[key] = velocities(values)
                    bad[key] = any(e != 0 for e in errors)
                    summary.append((policy, key, increment, bad[key], tests,
                                    float(np.mean(values)) - float(np.mean(truth)), errors))
                # Derived numbers for the reference-keeping list buffer; other consumers are
                # summarised by their stored values and the corrupted flag.
                emit(kind="ep", p=policy, inc=increment, msgs=ep["received_msgs"], true=truth,
                     stored=stored, bad=[k for k, v in bad.items() if v],
                     list_mean=mean["list"], true_mean=float(np.mean(truth)),
                     list_oldest_err=oldest_err["list"], list_vel=vel["list"], true_vel=velocities(truth),
                     is_=ep["consecutive_is"], shares=ep["consecutive_shares_memory"],
                     ck_pairs=sum(ep["checkenv_style_pairs"].values()),
                     list_after_reset=ep["list_after_reset_rad"])
                all_latency.extend(ep["latency_ms"])
                all_received += ep["received_msgs"]
    finally:
        rclpy.shutdown()

    corrupted = [s for s in summary if s[3]]
    sharing = [s for s in summary if s[4]["shares_memory_between_steps"]]
    worst = max(corrupted, key=lambda s: abs(s[6][0]), default=None)
    emit(kind="summary",
         cases=len(summary),
         corrupted_cases=len(corrupted),
         corrupted=[f"{p}/{c}/{i}" for p, c, i, *_ in corrupted],
         max_abs_mean_error=max((abs(s[5]) for s in corrupted), default=0.0),
         worst_per_slot_error=worst[6] if worst else [],
         last_slot_error_max=max(abs(s[6][-1]) for s in summary),
         caught_by_last_slot=sum(s[4]["last_slot_value"] for s in corrupted),
         caught_by_oldest_slot=sum(s[4]["oldest_slot_value"] for s in corrupted),
         caught_by_shares_memory=sum(s[4]["shares_memory_between_steps"] for s in corrupted),
         caught_by_checkenv_style=sum(s[4]["checkenv_style_any_pair"] for s in corrupted),
         sharing_cases=len(sharing),
         sharing_but_values_ok=len([s for s in sharing if not s[3]]),
         oldest_slot_misses_sharing=sum(not s[4]["oldest_slot_value"] for s in sharing),
         false_alarm_shares_memory=sum(s[4]["shares_memory_between_steps"] for s in summary
                                       if s[0] in ("copy", "np_array", "rebind")),
         ros_msgs_received=all_received, ros_msgs_published=len(INCREMENTS) * len(POLICIES) * STEPS,
         ros_step_latency_ms_median=round(float(np.median(all_latency)), 3),
         ros_step_latency_ms_max=round(float(np.max(all_latency)), 3),
         wall_seconds=round(time.monotonic() - started, 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
