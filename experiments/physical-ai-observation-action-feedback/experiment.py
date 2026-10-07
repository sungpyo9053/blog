#!/usr/bin/env python3
"""관측·행동·피드백 폐루프를 ROS 2 노드 세 개로 돌려 글의 계산이 실제 루프에서도 맞는지 잰다.

  plant  : 실제 위치 x를 갖는다. x를 TF(world -> robot_<시나리오>)로 방송하고 tick을 발행한다.
           /action을 받으면 x <- x + a로 갱신하고 다음 단계로 넘어간다.
  sensor : tick을 받으면 tf2 Buffer에서 위치를 조회해 bias를 더한 관측 o를 발행한다.
           delay=1이면 한 단계 전 stamp의 TF를 조회한다(tf2 이력 조회).
  policy : a = clamp(gain * (target - o), -limit, +limit)를 발행한다. gain·limit은 ROS 파라미터다.

시나리오(입력값만 정하고 결과는 정하지 않는다)
  exact     : x0=0,   bias=0,   delay=0  (글의 표)
  bias      : x0=0,   bias=0.1, delay=0  (항상 0.1 m 크게 읽는 센서로 처음부터 이동)
  bias_at_09: x0=0.9, bias=0.1, delay=0  (글의 오차 사례: 0.9 m에서 1 m로 읽힘)
  delay1    : x0=0,   bias=0,   delay=1  (글이 '고려해야 한다'고만 한 시간 지연)

각 단계의 실제 위치·관측·행동·루프 왕복 시간을 실행 중에 기록하고, 같은 규칙을 분수(Fraction)로
계산한 기준 궤적과 비교한다. 시나리오마다 JSON 한 줄, 마지막에 요약 한 줄을 출력한다.
"""
import json
import statistics
import threading
import time
from fractions import Fraction

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.duration import Duration
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from rclpy.utilities import get_rmw_implementation_identifier
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Float64MultiArray, UInt32
from tf2_ros import Buffer, TransformBroadcaster, TransformListener

TARGET = 1.0
GAIN = 0.5
LIMIT = 0.2
TOLERANCE = 0.025          # 글의 성공 기준: |목표 - 실제 위치| <= 0.025 m
ARTICLE_UPDATES = 7        # 글: "7번 갱신한 뒤 ... 기준을 충족한다"
STAMP_STEP_NS = 100_000_000
SCENARIOS = [
    # name, x0, bias, delay, updates
    ("exact", "0", "0", 0, 12),
    ("bias", "0", "0.1", 0, 12),
    ("bias_at_09", "0.9", "0.1", 0, 3),
    ("delay1", "0", "0", 1, 20),
]
QOS = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)


def stamp_of(step):
    return Time(nanoseconds=(step + 1) * STAMP_STEP_NS)


class Plant:
    def __init__(self, name, x0, updates):
        self.node = rclpy.create_node(f"plant_{name}")
        self.frame = f"robot_{name}"
        self.x = x0
        self.updates = updates
        self.step = 0
        self.positions = [x0]          # positions[n] = n번 갱신한 뒤의 실제 위치
        self.tick_ns = {}
        self.latency_ms = []
        self.done = threading.Event()
        self.tf = TransformBroadcaster(self.node, qos=QOS)
        self.tick = self.node.create_publisher(UInt32, f"/tick_{name}", QOS)
        self.node.create_subscription(Float64MultiArray, f"/action_{name}", self.on_action, QOS)

    def emit(self):
        t = TransformStamped()
        t.header.stamp = stamp_of(self.step).to_msg()
        t.header.frame_id = "world"
        t.child_frame_id = self.frame
        t.transform.translation.x = self.x
        t.transform.rotation.w = 1.0
        self.tf.sendTransform(t)
        self.tick_ns[self.step] = time.monotonic_ns()
        self.tick.publish(UInt32(data=self.step))

    def on_action(self, msg):
        k, a = int(msg.data[0]), msg.data[1]
        if k != self.step:
            return
        self.latency_ms.append((time.monotonic_ns() - self.tick_ns[k]) / 1e6)
        self.x = self.x + a
        self.positions.append(self.x)
        self.step += 1
        if self.step >= self.updates:
            self.done.set()
        else:
            self.emit()


class Sensor:
    def __init__(self, name, bias, delay, frame):
        self.node = rclpy.create_node(f"sensor_{name}")
        self.node.declare_parameter("bias", bias)
        self.delay = delay
        self.frame = frame
        self.buffer = Buffer(node=self.node)
        self.listener = TransformListener(self.buffer, self.node, qos=QOS)
        self.lookups = []            # (step, 조회한 stamp의 단계, 읽은 위치)
        self.pub = self.node.create_publisher(Float64MultiArray, f"/obs_{name}", QOS)
        self.node.create_subscription(UInt32, f"/tick_{name}", self.on_tick, QOS,
                                      callback_group=MutuallyExclusiveCallbackGroup())

    def on_tick(self, msg):
        k = msg.data
        src = max(0, k - self.delay)
        t0 = time.monotonic_ns()
        ready = self.buffer.can_transform_core("world", self.frame, stamp_of(src))[0]
        tf = self.buffer.lookup_transform("world", self.frame, stamp_of(src),
                                          timeout=Duration(seconds=2.0))
        read = tf.transform.translation.x
        self.lookups.append((k, src, read, ready, (time.monotonic_ns() - t0) / 1e6))
        bias = self.node.get_parameter("bias").value
        self.pub.publish(Float64MultiArray(data=[float(k), read + bias]))


class Policy:
    def __init__(self, name):
        self.node = rclpy.create_node(f"policy_{name}")
        self.node.declare_parameter("gain", GAIN)
        self.node.declare_parameter("limit", LIMIT)
        self.node.declare_parameter("target", TARGET)
        self.log = []                # (step, 관측, 행동, 그 순간 읽은 gain, limit)
        self.pub = self.node.create_publisher(Float64MultiArray, f"/action_{name}", QOS)
        self.node.create_subscription(Float64MultiArray, f"/obs_{name}", self.on_obs, QOS)

    def on_obs(self, msg):
        k, o = int(msg.data[0]), msg.data[1]
        gain = self.node.get_parameter("gain").value
        limit = self.node.get_parameter("limit").value
        target = self.node.get_parameter("target").value
        a = max(-limit, min(limit, gain * (target - o)))
        self.log.append((k, o, a, gain, limit))
        self.pub.publish(Float64MultiArray(data=[float(k), a]))


def exact_reference(x0, bias, delay, updates):
    """같은 규칙을 분수로 계산한 기준 궤적(글의 Fraction 검산과 같은 방식)."""
    target, gain, limit = Fraction(str(TARGET)), Fraction(str(GAIN)), Fraction(str(LIMIT))
    xs = [Fraction(x0)]
    for k in range(updates):
        o = xs[max(0, k - delay)] + Fraction(bias)
        a = max(-limit, min(limit, gain * (target - o)))
        xs.append(xs[-1] + a)
    return xs


def first_success(gaps, tol=TOLERANCE):
    return next((n for n, g in enumerate(gaps) if g <= tol), None)


def settled(gaps, tol=TOLERANCE):
    """이 갱신 이후 기록 끝까지 계속 허용 오차 안에 머무는 첫 갱신 번호."""
    n = len(gaps)
    while n > 0 and gaps[n - 1] <= tol:
        n -= 1
    return n if n < len(gaps) else None


def r12(v):
    return None if v is None else round(v, 12)


def wait_until(predicate, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def run_scenario(executor, name, x0_s, bias_s, delay, updates):
    plant = Plant(name, float(x0_s), updates)
    sensor = Sensor(name, float(bias_s), delay, plant.frame)
    policy = Policy(name)
    nodes = [plant.node, sensor.node, policy.node]
    for n in nodes:
        executor.add_node(n)

    t0 = time.monotonic()
    matched = wait_until(lambda: plant.tick.get_subscription_count() >= 1
                         and sensor.pub.get_subscription_count() >= 1
                         and policy.pub.get_subscription_count() >= 1
                         and plant.node.count_subscribers("/tf") >= 1, 10.0)
    discovery_s = time.monotonic() - t0
    time.sleep(0.3)

    started = time.monotonic()
    plant.emit()
    finished = plant.done.wait(20.0)
    loop_s = time.monotonic() - started

    xs = plant.positions
    true_gaps = [abs(TARGET - x) for x in xs]
    by_step = {k: (o, a) for k, o, a, _, _ in policy.log}
    obs = [by_step.get(k, (None, None))[0] for k in range(len(xs) - 1)]
    acts = [by_step.get(k, (None, None))[1] for k in range(len(xs) - 1)]

    # 센서가 돌려준 값이 '실제 위치(지연 반영) + bias'와 얼마나 다른지 실행 기록으로 확인한다.
    readout_err = max((abs(read - xs[src]) for _, src, read, _, _ in sensor.lookups), default=None)
    waits = [w for *_, w in sensor.lookups]
    obs_minus_true = [o - xs[k] for k, o, *_ in policy.log]

    ref = exact_reference(x0_s, bias_s, delay, updates)
    tol = Fraction(str(TOLERANCE))
    ref_gaps = [abs(Fraction(str(TARGET)) - x) for x in ref]
    obs_ok = [k for k, o, *_ in policy.log if abs(TARGET - o) <= TOLERANCE]
    first_obs_ok = obs_ok[0] if obs_ok else None
    nonzero = [a for a in acts if a]
    lat = plant.latency_ms
    n7 = ARTICLE_UPDATES

    record = {
        "scenario": name,
        "inputs": {"x0": x0_s, "bias": bias_s, "delay_steps": delay, "updates": updates},
        "matched": matched,
        "discovery_s": round(discovery_s, 3),
        "finished": finished,
        "updates_done": len(xs) - 1,
        # 궤적은 12자리로 반올림해 싣는다. 판정 값은 아래에서 반올림 없이 싣는다.
        "x": [r12(v) for v in xs],
        "obs": [r12(v) for v in obs],
        "action": [r12(v) for v in acts],
        "final_true_gap": true_gaps[-1],
        # 글의 주장: 7번 갱신 뒤 차이 0.025 m로 성공 기준 충족
        "after_7": None if len(xs) <= n7 else {
            "x": xs[n7], "true_gap": true_gaps[n7],
            "gap_minus_tol": true_gaps[n7] - TOLERANCE, "meets_tol": true_gaps[n7] <= TOLERANCE},
        "first_success": first_success(true_gaps),
        "settled_from": settled(true_gaps),
        "overshoot": max(xs) - TARGET,
        "action_sign_changes": sum(1 for a1, a2 in zip(nonzero, nonzero[1:]) if a1 * a2 < 0),
        "zero_actions": sum(1 for a in acts if a == 0.0),
        "obs_check": {
            "first_obs_within_tol": first_obs_ok,
            "true_gap_then": None if first_obs_ok is None else true_gaps[first_obs_ok],
            "obs_minus_true": [min(obs_minus_true, default=None), max(obs_minus_true, default=None)],
            "tf_readout_max_err": readout_err,
        },
        "policy_params_seen": {
            "gain": sorted({g for *_, g, _ in policy.log}),
            "limit": sorted({lim for *_, lim in policy.log}),
            "distinct_abs_actions": len({abs(a) for a in acts if a is not None}),
        },
        "exact": {
            "gap_after_7": None if len(ref) <= n7 else str(ref_gaps[n7]),
            "first_success": first_success(ref_gaps, tol),
            "settled_from": settled(ref_gaps, tol),
            "max_abs_diff_vs_ros": float(max(abs(Fraction(x) - r) for x, r in zip(xs, ref))),
            "tol_verdict_differs_at": [
                n for n, (g, rg) in enumerate(zip(true_gaps, ref_gaps)) if (g <= TOLERANCE) != (rg <= tol)],
        },
        "timing_ms": None if not lat else {
            "loop_median": round(statistics.median(lat), 2), "loop_max": round(max(lat), 2),
            "tf_ready_on_tick": sum(1 for *_, ready, _ in sensor.lookups if ready),
            "tf_wait_median": round(statistics.median(waits), 2)},
    }

    for n in nodes:
        executor.remove_node(n)
        n.destroy_node()
    return record


def main():
    t_start = time.monotonic()
    rclpy.init()
    executor = MultiThreadedExecutor(num_threads=4)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    records = []
    try:
        for spec in SCENARIOS:
            rec = run_scenario(executor, *spec)
            records.append(rec)
            print(json.dumps(rec, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        executor.shutdown()
        rclpy.shutdown()
    summary = {
        "summary": True,
        "rmw": get_rmw_implementation_identifier(),
        "target": TARGET, "gain": GAIN, "limit": LIMIT, "tolerance": TOLERANCE,
        "all_finished": all(r["finished"] for r in records),
        "total_s": round(time.monotonic() - t_start, 3),
    }
    print(json.dumps(summary, separators=(",", ":")), flush=True)
    return 0 if summary["all_finished"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
