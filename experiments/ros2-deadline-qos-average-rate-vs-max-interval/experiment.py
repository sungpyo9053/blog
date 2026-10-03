#!/usr/bin/env python3
"""평균 100 Hz 토픽이 15 ms deadline QoS를 지키는지 실제 ROS 2 이벤트로 확인한다.

시나리오 네 개를 한 프로세스에서 차례로 실행한다. 모든 간격 패턴은 합이 100 ms(평균 100 Hz)다.
  uniform : 10 ms 간격, 발행자·구독자 deadline 15 ms
  jitter  : 8,8,8,8,25,8,8,9,9,9 ms 간격 반복, deadline 15 ms
  long    : 7,7,7,7,37,7,7,7,7,7 ms 간격 반복, deadline 15 ms
            (긴 간격이 deadline의 2배를 넘을 때 miss가 몇 번 세지는지 본다)
  widened : jitter 간격 그대로, 발행자 deadline 30 ms
            구독자 A는 15 ms 요청(비호환 예상), 구독자 B는 30 ms 요청(호환 예상)
측정값(실제 발행 간격, 수신 간격, QoS 이벤트 횟수와 그 이벤트가 난 간격, 수신 개수)은
실행 중에 재서 시나리오마다 JSON 한 줄로 출력한다.
"""
import bisect
import json
import statistics
import threading
import time
from collections import Counter

import rclpy
from rclpy.duration import Duration
from rclpy.event_handler import PublisherEventCallbacks, SubscriptionEventCallbacks
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.utilities import get_rmw_implementation_identifier
from std_msgs.msg import UInt32

UNIFORM = [10] * 10
JITTER = [8, 8, 8, 8, 25, 8, 8, 9, 9, 9]
LONG = [7, 7, 7, 7, 37, 7, 7, 7, 7, 7]
CYCLES = 50          # 한 시나리오 = 50주기 x 10간격 = 500간격(약 5초)
MATCH_TIMEOUT = 5.0
TAIL_S = 0.3         # 마지막 발행 뒤 관찰 구간


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
            self.policy = str(info.last_policy_kind).rsplit(".", 1)[-1]

    def snapshot(self):
        with self.lock:
            return list(self.events)

    def total(self):
        with self.lock:
            return self.events[-1][2] if self.events else 0


def interval_stats(stamps_ns, deadline_ms):
    """ros2 topic hz와 같은 방식(mean, 1/mean, min, max, 모표준편차)으로 간격을 요약한다."""
    gaps = [(b - a) / 1e6 for a, b in zip(stamps_ns, stamps_ns[1:])]
    if not gaps:
        return {"n": 0}
    mean = sum(gaps) / len(gaps)
    return {
        "n": len(gaps),
        "mean_ms": round(mean, 3),
        "rate_hz": round(1000.0 / mean, 3),
        "min_ms": round(min(gaps), 3),
        "max_ms": round(max(gaps), 3),
        "std_ms": round(statistics.pstdev(gaps), 3),
        "over_deadline": sum(g > deadline_ms for g in gaps),
    }


def miss_summary(log, pub_stamps, deadline_ms):
    """deadline missed 이벤트를 발행 간격에 배정해 센다.

    이벤트 콜백 시각이 발행 i와 i+1 사이면 간격 i에서 난 것으로 본다. 첫 발행 전과
    마지막 발행 뒤의 이벤트는 판정에서 빼고 따로 센다(메시지가 끊긴 뒤에는 계속 나는 것이 정상).
    """
    first, last = pub_stamps[0], pub_stamps[-1]
    per_gap = Counter()
    before = after = during = 0
    for t, change, _ in log.snapshot():
        if t < first:
            before += change
        elif t > last:
            after += change
        else:
            during += change
            per_gap[bisect.bisect_right(pub_stamps, t) - 1] += change
    gaps = [(b - a) / 1e6 for a, b in zip(pub_stamps, pub_stamps[1:])]
    over = [i for i, g in enumerate(gaps) if g > deadline_ms]
    return {
        "during_run": during,
        "before_first_publish": before,
        "after_last_publish": after,
        "gaps_over_deadline": len(over),
        # 발행 간격이 deadline을 넘은 간격 하나당 miss 수의 분포 {miss 수: 간격 수}
        "per_over_gap_hist": dict(sorted(Counter(per_gap[i] for i in over).items())),
        "in_gaps_within_deadline": sum(c for i, c in per_gap.items() if gaps[i] <= deadline_ms),
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
    time.sleep(TAIL_S)   # 마지막 메시지 수신과 이벤트 콜백 전달을 기다린다.

    record = {
        "scenario": name,
        "rmw": get_rmw_implementation_identifier(),
        "pattern_ms": pattern,
        "planned": {
            "n": len(gaps),
            "mean_ms": round(sum(gaps) / len(gaps), 3),
            "rate_hz": round(1000.0 / (sum(gaps) / len(gaps)), 3),
            "max_ms": max(gaps),
            "over_pub_deadline": sum(g > pub_deadline_ms for g in gaps),
        },
        "matched": matched,
        "discovery_s": round(discovery_s, 3),
        "pub": {
            "deadline_ms": pub_deadline_ms,
            "published": len(pub_stamps),
            "subs_matched": pub.get_subscription_count(),
            "intervals": interval_stats(pub_stamps, pub_deadline_ms),
            "offered_missed": miss_summary(offered_missed, pub_stamps, pub_deadline_ms),
            "incompatible_total": offered_incompat.total(),
            "incompatible_policy": offered_incompat.policy,
        },
        "subs": [],
    }
    for r in receivers:
        record["subs"].append({
            "name": r.name,
            "deadline_ms": r.deadline_ms,
            "received": len(r.stamps),
            "lost": len(pub_stamps) - len(set(r.seqs)),
            "intervals": interval_stats(r.stamps, r.deadline_ms),
            # 구독자 miss도 발행 간격 기준으로 배정한다(같은 프로세스·같은 monotonic 시계).
            "requested_missed": miss_summary(r.missed, pub_stamps, r.deadline_ms),
            "incompatible_total": r.incompat.total(),
            "incompatible_policy": r.incompat.policy,
        })

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
            ("long", LONG, 15, [("req15", 15)]),
            ("widened", JITTER, 30, [("req15", 15), ("req30", 30)]),
        ]:
            print(json.dumps(run_scenario(executor, name, pattern, pub_deadline, subs),
                             ensure_ascii=False, separators=(",", ":")), flush=True)
        print(json.dumps({"summary": "done", "elapsed_s": round(time.monotonic() - started, 2)}),
              flush=True)
    finally:
        # 스핀 스레드를 먼저 멈추고 합류시킨 뒤 rclpy를 내린다(종료 순서가 틀리면 SIGSEGV).
        executor.shutdown(timeout_sec=2.0)
        spinner.join(timeout=2.0)
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
