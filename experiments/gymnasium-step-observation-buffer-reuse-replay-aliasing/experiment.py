#!/usr/bin/env python3
"""관측 배열을 제자리 수정해 돌려주는 환경을 복사 없이 쌓으면 버퍼에 무엇이 남는가.

ros:jazzy-ros-base 컨테이너(네트워크 없음)에서 실행한다. gymnasium은 이미지에 없으므로
Gymnasium Env의 reset()/step() 반환 계약만 흉내 낸 설명용 환경을 쓴다(check_env는 측정하지 않는다).
모든 숫자는 실행 중 계산해 JSON 한 줄씩 출력한다.

측정 1: 반환 방식 4종 x 버퍼 3종(list·copy_on_store는 4 step, deque(maxlen=4)는 6 step)을 쌓고 평균, 가장 오래된/최신 원소 오차, 차분 속도를 잰다.
측정 2: 같은 버그에서 버퍼 길이(step 수)를 늘리면 가장 오래된 원소 오차가 어떻게 변하는지 잰다.
측정 3: 마지막 원소만 보는 테스트와 가장 오래된 원소를 보는 테스트가 각각 버그를 잡는지 잰다.
측정 4: ROS 2 sensor_msgs/JointState 메시지 객체 하나를 재사용할 때, 발행 노드 안의 list와
        토픽을 건너 받은 구독 쪽 list에 남는 값을 잰다.
측정 5: 7관절 float64 관측의 .copy()와 np.array() 1회 비용을 잰다.
"""
import json
import platform
import statistics
import sys
import time
from collections import deque

import numpy as np

STEP_RAD = 0.25   # 설명용: 매 step 관절이 움직이는 양
DT = 0.125        # 설명용: step 간격(s)
N_STEPS = 4


def emit(**record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


class OneJointEnv:
    """Gymnasium Env의 reset/step 반환 형태만 흉내 낸 관절 1개 설명용 환경."""

    def __init__(self, mode, n_joints=1):
        self.mode = mode
        self._q = np.zeros(n_joints, dtype=np.float64)

    def _get_obs(self):
        if self.mode == "reuse":
            return self._q
        if self.mode == "view":
            return self._q[:]
        if self.mode == "asarray":
            return np.asarray(self._q, dtype=np.float64)
        return self._q.copy()

    def reset(self):
        self._q[:] = 0.0  # 제자리 수정
        return self._get_obs(), {}

    def step(self, action=None):
        self._q += STEP_RAD  # 제자리 수정: 새 배열을 만들지 않는다
        return self._get_obs(), 0.0, False, False, {}


def fill(env_mode, buffer_kind, n_steps):
    env = OneJointEnv(env_mode)
    env.reset()
    expected = []
    if buffer_kind == "deque4":
        buf = deque(maxlen=4)
    else:
        buf = []
    for _ in range(n_steps):
        obs, *_ = env.step()
        expected.append(float(env._q[0]))  # 그 순간의 참값을 숫자로 따로 기록
        if buffer_kind == "copy_on_store":
            buf.append(np.array(obs))  # SB3 ReplayBuffer.add()처럼 저장할 때 복사
        else:
            buf.append(obs)  # 복사 없이 참조만 쌓음
    stored = [float(o[0]) for o in buf]
    expected = expected[-len(stored):]
    return buf, stored, expected


def summarize(env_mode, buffer_kind, n_steps):
    buf, stored, expected = fill(env_mode, buffer_kind, n_steps)
    vel_stored = [(b - a) / DT for a, b in zip(stored, stored[1:])]
    vel_expected = [(b - a) / DT for a, b in zip(expected, expected[1:])]
    return {
        "env": env_mode,
        "buffer": buffer_kind,
        "steps": n_steps,
        "stored_rad": stored,
        "expected_rad": expected,
        "mean_stored": statistics.fmean(stored),
        "mean_expected": statistics.fmean(expected),
        "mean_err": statistics.fmean(stored) - statistics.fmean(expected),
        "oldest_err": stored[0] - expected[0],
        "newest_err": stored[-1] - expected[-1],
        "fd_vel_stored": vel_stored[0],
        "fd_vel_expected": vel_expected[0],
        "distinct_ids": len({id(o) for o in buf}),
        "oldest_shares_mem_newest": bool(np.shares_memory(buf[0], buf[-1])),
    }


def measure_buffers():
    # list는 4 step, deque(maxlen=4)는 6 step을 넣어 최근 4칸 창이 밀려나는 경우까지 본다.
    for mode in ("reuse", "view", "asarray", "copy"):
        for kind, n in (("list", N_STEPS), ("deque4", N_STEPS + 2), ("copy_on_store", N_STEPS)):
            emit(m="buffer", **summarize(mode, kind, n))


def measure_length_growth():
    for n in (2, 4, 8, 16, 64):
        s = summarize("reuse", "list", n)
        emit(m="reuse_length", steps=n, oldest_err=s["oldest_err"], mean_err=s["mean_err"],
             newest_err=s["newest_err"])


def measure_tests():
    for mode in ("reuse", "view", "asarray", "copy"):
        _, stored, expected = fill(mode, "list", N_STEPS)
        emit(m="unit_test", env=mode, last_only_pass=stored[-1] == expected[-1],
             oldest_pass=stored[0] == expected[0], all_pass=stored == expected)


def measure_ros():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import JointState

    rclpy.init()
    node = Node("obs_reuse_probe")
    qos = QoSProfile(depth=16, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
    received = []
    node.create_subscription(JointState, "joint_obs", received.append, qos)  # 받은 메시지를 그대로 append
    pub = node.create_publisher(JointState, "joint_obs", qos)

    deadline = time.monotonic() + 10.0
    while pub.get_subscription_count() < 1 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
    matched = pub.get_subscription_count()

    msg = JointState()  # 메시지 객체 하나를 계속 재사용
    msg.name = ["joint1"]
    msg.position = [0.0]
    local_log = []
    expected = []
    for _ in range(N_STEPS):
        msg.position[0] += STEP_RAD  # 제자리 수정
        expected.append(msg.position[0])
        pub.publish(msg)
        local_log.append(msg)  # 발행 노드 안에서 복사 없이 기록
        rclpy.spin_once(node, timeout_sec=0.0)

    deadline = time.monotonic() + 10.0
    while len(received) < N_STEPS and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)

    local_vals = [float(m.position[0]) for m in local_log]
    recv_vals = [float(m.position[0]) for m in received]
    emit(m="ros2_jointstate", position_type=type(msg.position).__name__, matched=matched,
         expected_rad=expected, pub_local_rad=local_vals,
         pub_local_ids=len({id(x) for x in local_log}), pub_local_oldest_err=local_vals[0] - expected[0],
         sub_count=len(recv_vals), sub_rad=recv_vals, sub_ids=len({id(x) for x in received}),
         sub_oldest_err=(recv_vals[0] - expected[0]) if recv_vals else None,
         sub_matches=recv_vals == expected)
    node.destroy_node()
    rclpy.shutdown()


def measure_copy_cost():
    q = np.linspace(-1.0, 1.0, 7)  # 7관절 float64 관측
    reps = 20000
    for name, fn in (("ndarray.copy", lambda: q.copy()), ("np.array", lambda: np.array(q)),
                     ("return_reference", lambda: q)):
        samples = []
        for _ in range(7):
            t0 = time.perf_counter_ns()
            for _ in range(reps):
                fn()
            samples.append((time.perf_counter_ns() - t0) / reps)
        emit(m="cost_7joint", op=name, reps=reps, samples=len(samples),
             median_ns=round(statistics.median(samples), 1), min_ns=round(min(samples), 1))


def main():
    started = time.monotonic()
    emit(m="env", python=platform.python_version(), numpy=np.__version__,
         machine=platform.machine(), step_rad=STEP_RAD, dt_s=DT, n_steps=N_STEPS)
    measure_buffers()
    measure_length_growth()
    measure_tests()
    measure_ros()
    measure_copy_cost()
    emit(m="done", elapsed_s=round(time.monotonic() - started, 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
