#!/usr/bin/env python3
"""매 에피소드 reset(seed=42) vs 한 번만 seed vs seed 목록: 서로 다른 시작 수와 성공률 추정 분산.

Gymnasium·MuJoCo·Fetch를 실행하지 않는다. Gymnasium 1.4.0의 시딩 경로
(seeding.np_random: SeedSequence -> PCG64 -> Generator, reset에서 seed가 정수면 PRNG 교체)를
numpy로 그대로 따라 한 장난감 2차원 '목표 도달(reach)' 환경이다. 목표 위치는 reset에서
np_random.uniform으로 뽑고(Fetch의 _sample_goal과 같은 방식), 성공은 목표 거리 < 임계값이다.
에피소드 시작 관측값은 ROS 2 토픽(std_msgs/Float64MultiArray)으로 발행하고, 별도 평가 노드가
받은 메시지만으로 서로 다른 시작 수를 센다. 모든 수치는 실행 중에 계산해 JSON 줄로 출력한다.
"""
import json
import math
import platform
import statistics
import time

import numpy as np
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import Float64MultiArray

EPISODES = 20          # 독자 질문의 평가 에피소드 수
TARGET_RANGE = 0.15    # 목표 위치 범위 [-0.15, 0.15]^2 (m)
THRESHOLD = 0.05       # 성공 판정 거리 (m)
HARD_STEPS = 8         # 어려운 조건: 시간 제한 8 step
EASY_STEPS = 20        # 쉬운 조건: 모든 목표에 도달 가능
REPS = 1000            # 평가(20 에피소드) 반복 횟수
REF_EPISODES = 20000   # 성공 확률 p 기준값을 잴 독립 에피소드 수


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def np_random(seed=None):
    """Gymnasium utils/seeding.np_random와 같은 생성 경로."""
    seed_seq = np.random.SeedSequence(seed)
    return np.random.Generator(np.random.PCG64(seed_seq)), seed_seq.entropy


class ToyReachEnv:
    """그리퍼는 원점에서 출발해 목표로 이동한다. slip>0이면 step에서도 np_random을 쓴다."""

    def __init__(self, max_steps, slip=0.0):
        self.max_steps = max_steps
        self.slip = slip
        self._np_random = None
        self.np_random_seed = None

    def reset(self, *, seed=None):
        # Gymnasium Env.reset: 정수 seed면 PRNG가 이미 있어도 새로 만든다. None이면 그대로 둔다.
        if seed is not None:
            self._np_random, self.np_random_seed = np_random(seed)
        elif self._np_random is None:
            self._np_random, self.np_random_seed = np_random(None)
        gx, gy = self._np_random.uniform(-TARGET_RANGE, TARGET_RANGE, size=2)
        self.goal = (float(gx), float(gy))
        self.grip = [0.0, 0.0]
        return (0.0, 0.0, self.goal[0], self.goal[1])

    def step(self, action):
        ax, ay = action
        if self.slip > 0.0:  # FrozenLake 미끄러짐처럼 step에서 같은 PRNG를 소비
            nx, ny = self._np_random.normal(0.0, self.slip, size=2)
            ax, ay = ax + float(nx), ay + float(ny)
        self.grip[0] += ax
        self.grip[1] += ay
        dist = math.hypot(self.goal[0] - self.grip[0], self.goal[1] - self.grip[1])
        return dist < THRESHOLD


def policy(env, speed):
    """결정적 정책: 목표 방향으로 최대 speed만큼 이동."""
    dx, dy = env.goal[0] - env.grip[0], env.goal[1] - env.grip[1]
    d = math.hypot(dx, dy)
    if d == 0.0:
        return (0.0, 0.0)
    s = min(d, speed) / d
    return (dx * s, dy * s)


def run_episode(env, obs, speed=0.01):
    if math.hypot(obs[2], obs[3]) < THRESHOLD:
        return True, 0
    for t in range(1, env.max_steps + 1):
        if env.step(policy(env, speed)):
            return True, t  # 성공하면 에피소드 종료(이후 step의 PRNG 소비 없음)
    return False, env.max_steps


def evaluate(env, loop, base_seed, n=EPISODES, speed=0.01, sink=None):
    """loop A: 매번 reset(seed=base). B: 처음만 reset(seed=base), 이후 reset(). C: reset(seed=base+i)."""
    starts, successes = [], []
    for i in range(n):
        if loop == "A":
            obs = env.reset(seed=base_seed)
        elif loop == "B":
            obs = env.reset(seed=base_seed) if i == 0 else env.reset()
        else:
            obs = env.reset(seed=base_seed + i)
        ok, _ = run_episode(env, obs, speed)
        starts.append(obs)
        successes.append(1 if ok else 0)
        if sink is not None:
            sink(i, obs, ok)
    return starts, successes


class StartPublisher(Node):
    def __init__(self, qos):
        super().__init__("toy_reach_env")
        self.pub = self.create_publisher(Float64MultiArray, "episode_start", qos)


class StartCounter(Node):
    """에피소드별 첫 관측값을 토픽으로만 받아 기록하는 평가 노드."""

    def __init__(self, qos):
        super().__init__("start_counter")
        self.received = []
        self.create_subscription(Float64MultiArray, "episode_start", self.on_msg, qos)

    def on_msg(self, msg):
        self.received.append(tuple(msg.data))


def ros_single_eval(executor, pub_node, counter, env, loop, condition):
    counter.received.clear()

    def sink(i, obs, ok):
        msg = Float64MultiArray()
        msg.data = [float(i), obs[2], obs[3], 1.0 if ok else 0.0]
        pub_node.pub.publish(msg)
        deadline = time.monotonic() + 2.0
        while len(counter.received) < i + 1 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)

    starts, successes = evaluate(env, loop, 42, sink=sink)
    received_starts = {(r[1], r[2]) for r in counter.received}
    emit(measure="single_eval", condition=condition, loop=loop, base_seed=42, episodes=EPISODES,
         messages_received=len(counter.received),
         distinct_starts_local=len({(s[2], s[3]) for s in starts}),
         distinct_starts_via_ros=len(received_starts),
         successes=sum(successes), success_rate=sum(successes) / EPISODES,
         np_random_seed_after=int(env.np_random_seed),
         first_goal=[round(starts[0][2], 6), round(starts[0][3], 6)])


def repeated(env, loop, reps, p_ref):
    rates = []
    for r in range(reps):
        if loop == "A":
            base = 1000 + r                  # 반복마다 다른 seed를 매 에피소드 재사용
        elif loop == "B":
            base = 1000 + r                  # 반복마다 다른 seed를 처음에 한 번
        else:
            base = 10_000_000 + r * EPISODES  # 반복끼리 겹치지 않는 seed 목록
        _, s = evaluate(env, loop, base)
        rates.append(sum(s) / EPISODES)
    var = statistics.variance(rates)
    return {
        "loop": loop, "reps": reps, "mean_rate": round(statistics.fmean(rates), 6),
        "sample_variance": round(var, 6), "sample_sd": round(math.sqrt(var), 6),
        "share_rate_0_or_1": round(sum(x in (0.0, 1.0) for x in rates) / reps, 6),
        "distinct_rate_values": len(set(rates)),
        "predicted_var_n20": round(p_ref * (1 - p_ref) / EPISODES, 6),
        "predicted_var_n1": round(p_ref * (1 - p_ref), 6),
    }, var


def main():
    t0 = time.monotonic()
    emit(measure="environment", numpy=np.__version__, python=platform.python_version(),
         episodes=EPISODES, target_range=TARGET_RANGE, threshold=THRESHOLD,
         hard_steps=HARD_STEPS, easy_steps=EASY_STEPS, reps=REPS)

    # 1) 시딩 규칙 확인: 정수 seed는 PRNG를 다시 만들고, None은 이어서 쓴다.
    env = ToyReachEnv(HARD_STEPS)
    a = env.reset(seed=42)
    b = env.reset()
    c = env.reset(seed=42)
    fresh = ToyReachEnv(HARD_STEPS).reset(seed=42)
    emit(measure="seeding_rule", same_after_reseed=a == c, same_as_fresh_env=a == fresh,
         reset_none_differs=a != b)

    # 2) 성공 확률 기준값 p: 한 번만 seed를 준 긴 독립 스트림
    p_ref = {}
    for condition, steps in (("hard", HARD_STEPS), ("easy", EASY_STEPS)):
        _, ref = evaluate(ToyReachEnv(steps), "B", 7, n=REF_EPISODES)
        p = p_ref[condition] = sum(ref) / REF_EPISODES
        emit(measure="p_reference", condition=condition, episodes=REF_EPISODES, p_hat=round(p, 6),
             se=round(math.sqrt(p * (1 - p) / REF_EPISODES), 6))

    # 3) seed 42로 20 에피소드 한 번 평가: 시작 관측값은 ROS 2 토픽으로 전달해 센다.
    rclpy.init()
    qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
    pub_node, counter = StartPublisher(qos), StartCounter(qos)
    executor = SingleThreadedExecutor()
    executor.add_node(pub_node)
    executor.add_node(counter)
    deadline = time.monotonic() + 10.0
    while pub_node.pub.get_subscription_count() == 0 and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
    emit(measure="ros_link", matched_subscriptions=pub_node.pub.get_subscription_count(),
         wait_seconds=round(time.monotonic() - (deadline - 10.0), 3))
    for condition, steps in (("hard", HARD_STEPS), ("easy", EASY_STEPS)):
        for loop in ("A", "B", "C"):
            ros_single_eval(executor, pub_node, counter, ToyReachEnv(steps), loop, condition)
    executor.shutdown()
    pub_node.destroy_node()
    counter.destroy_node()
    rclpy.shutdown()

    # 4) 같은 seed 42로 평가 전체를 5번 다시 실행: 재현성(숫자가 같은가)
    for loop in ("A", "B"):
        rates = [sum(evaluate(ToyReachEnv(HARD_STEPS), loop, 42)[1]) / EPISODES for _ in range(5)]
        emit(measure="rerun_same_seed", loop=loop, reruns=5, rates=rates,
             variance=round(statistics.pvariance(rates), 6))

    # 5) 평가를 REPS번 반복했을 때 성공률 추정값의 흩어짐
    out = {}
    for condition, steps in (("hard", HARD_STEPS), ("easy", EASY_STEPS)):
        for loop in ("A", "B", "C"):
            rec, var = repeated(ToyReachEnv(steps), loop, REPS, p_ref[condition])
            out[(condition, loop)] = var
            emit(measure="repeated_eval", condition=condition, **rec)
    vb = out[("hard", "B")]
    emit(measure="variance_ratio", condition="hard",
         a_over_b=round(out[("hard", "A")] / vb, 4) if vb else None,
         c_over_b=round(out[("hard", "C")] / vb, 4) if vb else None)

    # 6) 루프 B의 주의점: step에서도 PRNG를 쓰면 정책이 바뀔 때 이후 시작 순서가 바뀐다.
    for slip in (0.0, 0.004):
        for loop in ("B", "C"):
            s1, _ = evaluate(ToyReachEnv(25, slip=slip), loop, 42, speed=0.010)
            s2, _ = evaluate(ToyReachEnv(25, slip=slip), loop, 42, speed=0.007)
            same = sum(x == y for x, y in zip(s1, s2))
            first_diff = next((i for i, (x, y) in enumerate(zip(s1, s2)) if x != y), None)
            emit(measure="policy_change_start_order", slip=slip, loop=loop, episodes=EPISODES,
                 same_starts_between_policies=same, first_different_episode=first_diff)

    emit(measure="runtime", seconds=round(time.monotonic() - t0, 3))


if __name__ == "__main__":
    main()
