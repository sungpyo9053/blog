#!/usr/bin/env python3
"""평균 100 Hz 토픽이 15 ms deadline QoS를 지키는지 실제 ROS 2 이벤트로 확인한다.

시나리오 세 개를 한 프로세스에서 차례로 실행한다.
  uniform : 10 ms 간격으로 발행, 발행자·구독자 deadline 15 ms
  jitter  : 8,8,8,8,25,8,8,9,9,9 ms 간격(합 100 ms)을 반복, deadline 15 ms
  widened : jitter 간격 그대로, 발행자 deadline 30 ms
            구독자 A는 15 ms 요청(비호환 예상), 구독자 B는 30 ms 요청(호환 예상)
측정값(실제 발행 간격, 수신 간격, QoS 이벤트 횟수, 수신 개수)은 실행 중에 재서
시나리오마다 JSON 한 줄로 출력한다.
"""
import json
import statistics
import threading
import time

import rclpy
from rclpy.duration import Duration
from rclpy.event_handler import PublisherEventCallbacks, SubscriptionEventCallbacks
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.utilities import get_rmw_implementation_identifier
from std_msgs.msg import UInt32

UNIFORM = [10] * 10
JITTER = [8, 8, 8, 8, 25, 8, 8, 9, 9, 9]
CYCLES = 50          # 한 시나리오 = 50주기 x 10간격 = 500간격(약 5초)
MATCH_TIMEOUT = 5.0


def qos(deadline_ms):
    return QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                      deadline=Duration(nanoseconds=int(deadline_ms * 1_000_000)))


class EventLog:
    """QoS 이벤트 콜백이 불린 시각(monotonic)과 total_count를 기록한다."""

    def __init__(self):
        self.lock = threading.Lock()
        self.events = []      # (t_ns, total_count_change, total_count)
        self.policy = None

    def deadline(self, info):
        with self.lock:
            self.events.append((time.monotonic_ns(), info.total_count_change, info.total_count))

    def incompatible(self, info):
        with self.lock:
            self.events.append((time.monotonic_ns(), info.total_count_change, info.total_count))
            self.policy = str(info.last_policy_kind)

    def count_between(self, start_ns, end_ns):
        with self.lock:
            return sum(c for t, c, _ in self.events if start_ns <= t <= end_ns)

    def count_after(self, t_ns):
        with self.lock:
            return sum(c for t, c, _ in self.events if t > t_ns)

    def total(self):
        with self.lock:
            return self.events[-1][2] if self.events else 0


def interval_stats(stamps_ns, deadline_ms):
    """ros2 topic hz와 같은 방식(mean, 1/mean, min, max, 모표준편차)으로 간격을 요약한다."""
    gaps = [(b - a) / 1e6 for a, b in zip(stamps_ns, stamps_ns[1:])]
    if not gaps:
        return {"intervals": 0}
    mean = sum(gaps) / len(gaps)
    return {
        "intervals": len(gaps),
        "mean_ms": round(mean, 3),
        "average_rate_hz": round(1000.0 / mean, 3),
        "min_ms": round(min(gaps), 3),
        "max_ms": round(max(gaps), 3),
        "std_dev_ms": round(statistics.pstdev(gaps), 3),
        "gaps_over_deadline": sum(g > deadline_ms for g in gaps),
        "p99_ms": round(sorted(gaps)[int(len(gaps) * 0.99) - 1], 3),
    }


class Receiver:
    def __init__(self, node, topic, deadline_ms, name):
        self.name = name
        self.deadline_ms = deadline_ms
        self.stamps = []
        self.seqs = []
        self.missed = EventLog()
        self.incompat = EventLog()
        callbacks = SubscriptionEventCallbacks(deadline=self.missed.deadline,
                                               incompatible_qos=self.incompat.incompatible)
        self.sub = node.create_subscription(UInt32, topic, self.on_msg, qos(deadline_ms),
                                            event_callbacks=callbacks)

    def on_msg(self, msg):
        self.stamps.append(time.monotonic_ns())
        self.seqs.append(msg.data)


def wait_until(predicate, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def run_scenario(executor, name, pattern, pub_deadline_ms, sub_deadlines):
    pub_node = rclpy.create_node(f"pub_{name}")
    sub_node = rclpy.create_node(f"sub_{name}")
    executor.add_node(pub_node)
    executor.add_node(sub_node)
    topic = f"/sensor_{name}"

    offered_missed, offered_incompat = EventLog(), EventLog()
    pub = pub_node.create_publisher(
        UInt32, topic, qos(pub_deadline_ms),
        event_callbacks=PublisherEventCallbacks(deadline=offered_missed.deadline,
                                                incompatible_qos=offered_incompat.incompatible))
    receivers = [Receiver(sub_node, topic, d, label) for label, d in sub_deadlines]

    expect_match = sum(d >= pub_deadline_ms for _, d in sub_deadlines)
    expect_incompat = len(sub_deadlines) - expect_match
    t0 = time.monotonic()
    matched = wait_until(lambda: pub.get_subscription_count() >= expect_match and
                         offered_incompat.total() >= expect_incompat, MATCH_TIMEOUT)
    discovery_s = time.monotonic() - t0
    time.sleep(0.2)

    # 발행: 메인 스레드가 절대 목표 시각까지 잠든 뒤 발행한다. 늦게 깨면 다음 목표가
    # 이미 지나 있어 곧바로 발행하므로(따라잡기) 평균 주기는 계획대로 유지된다.
    gaps = pattern * CYCLES
    pub_stamps = []
    target = time.monotonic_ns()
    seq = 0
    pub.publish(UInt32(data=seq))
    pub_stamps.append(time.monotonic_ns())
    for gap in gaps:
        target += gap * 1_000_000
        remaining = target - time.monotonic_ns()
        if remaining > 0:
            time.sleep(remaining / 1e9)
        seq += 1
        pub.publish(UInt32(data=seq))
        pub_stamps.append(time.monotonic_ns())
    first_ns, last_ns = pub_stamps[0], pub_stamps[-1]
    time.sleep(0.3)   # 마지막 메시지 수신과 이벤트 콜백 전달을 기다린다.
    after_ns = time.monotonic_ns()

    planned = gaps
    record = {
        "scenario": name,
        "rmw": get_rmw_implementation_identifier(),
        "pattern_ms": pattern,
        "cycles": CYCLES,
        "planned": {
            "intervals": len(planned),
            "mean_ms": round(sum(planned) / len(planned), 3),
            "average_rate_hz": round(1000.0 / (sum(planned) / len(planned)), 3),
            "max_ms": max(planned),
            "gaps_over_pub_deadline": sum(g > pub_deadline_ms for g in planned),
        },
        "discovery_matched": matched,
        "discovery_s": round(discovery_s, 3),
        "publisher": {
            "offered_deadline_ms": pub_deadline_ms,
            "published": len(pub_stamps),
            "matched_subscriptions": pub.get_subscription_count(),
            "publish_intervals": interval_stats(pub_stamps, pub_deadline_ms),
            "offered_deadline_missed_during_run": offered_missed.count_between(first_ns, last_ns),
            "offered_deadline_missed_after_last_publish": offered_missed.count_after(last_ns),
            "offered_incompatible_qos_total": offered_incompat.total(),
            "offered_incompatible_policy": offered_incompat.policy,
        },
        "subscribers": [],
    }
    for r in receivers:
        record["subscribers"].append({
            "name": r.name,
            "requested_deadline_ms": r.deadline_ms,
            "received": len(r.stamps),
            "lost": (len(pub_stamps) - len(set(r.seqs))),
            "receive_intervals": interval_stats(r.stamps, r.deadline_ms),
            "requested_deadline_missed_during_run": r.missed.count_between(first_ns, last_ns),
            "requested_deadline_missed_after_last_publish": r.missed.count_after(last_ns),
            "requested_incompatible_qos_total": r.incompat.total(),
            "requested_incompatible_policy": r.incompat.policy,
        })
    record["observation_end_after_last_publish_ms"] = round((after_ns - last_ns) / 1e6, 1)

    executor.remove_node(pub_node)
    executor.remove_node(sub_node)
    pub_node.destroy_node()
    sub_node.destroy_node()
    return record


def main():
    rclpy.init()
    executor = SingleThreadedExecutor()
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    started = time.monotonic()
    try:
        for name, pattern, pub_deadline, subs in [
            ("uniform", UNIFORM, 15, [("req15", 15)]),
            ("jitter", JITTER, 15, [("req15", 15)]),
            ("widened", JITTER, 30, [("req15", 15), ("req30", 30)]),
        ]:
            print(json.dumps(run_scenario(executor, name, pattern, pub_deadline, subs),
                             ensure_ascii=False), flush=True)
        print(json.dumps({"summary": "done", "elapsed_s": round(time.monotonic() - started, 2)}),
              flush=True)
    finally:
        # 스핀 스레드를 먼저 멈추고 합류시킨 뒤 rclpy를 내린다(종료 순서가 틀리면 SIGSEGV).
        executor.shutdown(timeout_sec=2.0)
        spinner.join(timeout=2.0)
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
