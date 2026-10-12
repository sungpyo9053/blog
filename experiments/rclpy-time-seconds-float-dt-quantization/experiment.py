#!/usr/bin/env python3
"""rclpy now().nanoseconds: dt를 float 초끼리 빼서 구할 때와 정수 나노초로 먼저 뺄 때 비교.

ROS 2 Jazzy rclpy 노드 하나에서 실제 시각을 기록하고, 그 정수 나노초로 두 가지 dt를 계산한다.
모든 숫자는 실행 중 측정·계산한 값이며 미리 적어 둔 결과가 없다. 출력은 JSON 줄이다.
"""
import json
import math
import statistics
import sys
import time
from fractions import Fraction

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time

TIMER_PERIOD_S = 0.001      # 1 ms 타이머 콜백
TIMER_SAMPLES = 2000        # 타이머 콜백에서 기록할 시각 개수
TIGHT_SAMPLES = 20000       # 연속 now() 호출로 기록할 시각 개수(µs 규모 간격)
NOMINAL_NS = 1_000_000      # 실측 시작 시각 + 정확히 1 ms 를 붙여 보는 결정적 검사
SIM_LIKE_START_NS = 125 * 10**9  # 같은 간격을 0 근처(시뮬레이션 시계 규모)로 옮겨 보는 기준


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def dt_float_first(a, b):
    return b / 1e9 - a / 1e9          # 각 시각을 float 초로 바꾼 뒤 빼기


def dt_int_first(a, b):
    return (b - a) / 1e9              # 정수 나노초로 먼저 빼고 마지막에 초로


def is_multiple(x, step):
    return (Fraction(x) / Fraction(step)).denominator == 1


def compare(label, stamps, unit_ulp):
    pairs = list(zip(stamps, stamps[1:]))
    f = [dt_float_first(a, b) for a, b in pairs]
    i = [dt_int_first(a, b) for a, b in pairs]
    err_ns = [(x - y) * 1e9 for x, y in zip(f, i)]
    rel = [abs(x - y) / y for x, y in zip(f, i) if y > 0]
    int_ns = [b - a for a, b in pairs]
    emit("interval_compare", label=label,
         intervals=len(pairs),
         start_seconds_float=stamps[0] / 1e9,
         ulp_at_start_s=math.ulp(stamps[0] / 1e9),
         ulp_log2=math.log2(math.ulp(stamps[0] / 1e9)),
         int_dt_ns_min=min(int_ns), int_dt_ns_median=statistics.median(int_ns), int_dt_ns_max=max(int_ns),
         float_first_all_multiple_of_ulp=all(is_multiple(x, unit_ulp) for x in f),
         float_first_multiple_count=sum(is_multiple(x, unit_ulp) for x in f),
         int_first_multiple_count=sum(is_multiple(x, unit_ulp) for x in i),
         distinct_float_first=len(set(f)), distinct_int_first=len(set(i)),
         abs_err_ns_max=max(abs(e) for e in err_ns),
         abs_err_ns_mean=statistics.fmean(abs(e) for e in err_ns),
         rel_err_max=max(rel) if rel else None,
         rel_err_mean=statistics.fmean(rel) if rel else None,
         sum_float_first_s=math.fsum(f), sum_int_first_s=math.fsum(i),
         total_exact_s=(stamps[-1] - stamps[0]) / 1e9)
    return f, i


class Recorder(Node):
    def __init__(self):
        super().__init__("dt_quantization_probe")
        self.stamps = []
        self.timer = self.create_timer(TIMER_PERIOD_S, self.on_timer)

    def on_timer(self):
        if len(self.stamps) < TIMER_SAMPLES:
            self.stamps.append(self.get_clock().now().nanoseconds)


def main():
    wall_start = time.monotonic()
    rclpy.init()
    node = Recorder()
    clock = node.get_clock()
    t_a, t_b = clock.now(), clock.now()
    d = t_b - t_a
    emit("api_surface",
         python=sys.version.split()[0],
         clock_type=getattr(clock.clock_type, "name", str(clock.clock_type)),
         ros_time_is_active=getattr(clock, "ros_time_is_active", None),
         use_sim_time=node.get_parameter("use_sim_time").value,
         nanoseconds_type=type(t_a.nanoseconds).__name__,
         time_has_seconds=hasattr(Time, "seconds"),
         duration_has_seconds=hasattr(Duration, "seconds"),
         time_has_seconds_nanoseconds=hasattr(Time, "seconds_nanoseconds"),
         time_minus_time_type=type(d).__name__,
         duration_nanoseconds_type=type(d.nanoseconds).__name__,
         now_ns_above_2pow53=t_a.nanoseconds > 2**53)

    # 1) 1 ms 타이머 콜백에서 실제 시각 기록
    deadline = time.monotonic() + 30.0
    while len(node.stamps) < TIMER_SAMPLES and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.01)
    timer_stamps = list(node.stamps)

    # 2) 연속 now() 호출: µs 규모의 짧은 구간
    tight = [clock.now().nanoseconds for _ in range(TIGHT_SAMPLES)]

    node.destroy_node()
    rclpy.shutdown()

    unit = math.ulp(timer_stamps[0] / 1e9)
    f, i = compare("timer_1ms_system_clock", timer_stamps, unit)
    compare("tight_now_calls_system_clock", tight, math.ulp(tight[0] / 1e9))

    # 3) 같은 실측 간격을 125 s 근처로 옮겨(시뮬레이션 시계 크기) 같은 계산
    base = timer_stamps[0]
    rebased = [s - base + SIM_LIKE_START_NS for s in timer_stamps]
    compare("timer_1ms_rebased_to_125s", rebased, math.ulp(rebased[0] / 1e9))
    rebased_tight = [s - tight[0] + SIM_LIKE_START_NS for s in tight]
    compare("tight_now_calls_rebased_to_125s", rebased_tight, math.ulp(rebased_tight[0] / 1e9))

    # 4) 실측 시작 시각마다 정확히 1 ms(1,000,000 ns)를 더해 float 선변환 결과 분포 확인
    starts = timer_stamps + tight
    one_ms_div_float = [dt_float_first(s, s + NOMINAL_NS) for s in starts]
    one_ms_div_int = [(s + NOMINAL_NS) / 10**9 - s / 10**9 for s in starts]
    one_us_div_float = [dt_float_first(s, s + 1000) for s in starts]

    def hist(values):
        out = {}
        for v in values:
            key = repr(v)
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: float(kv[0])))

    emit("fixed_interval_from_real_starts", starts=len(starts),
         ulp_s=unit,
         one_ms_ns_div_1e9_values=hist(one_ms_div_float),
         one_ms_ns_div_1e9_in_ulp=sorted({round(v / unit) for v in one_ms_div_float}),
         one_ms_ns_div_10pow9_values=hist(one_ms_div_int),
         one_ms_int_first=dt_int_first(starts[0], starts[0] + NOMINAL_NS),
         one_us_ns_div_1e9_values=hist(one_us_div_float),
         one_us_int_first=dt_int_first(starts[0], starts[0] + 1000),
         starts_where_div_1e9_differs_from_div_10pow9=sum(
             s / 1e9 != s / 10**9 for s in starts))

    # 5) 등속 0.5 m/s 물체의 차분 속도: 위치는 정수 나노초로 정확히 계산, dt만 두 방식
    v_true = 0.5
    v_float = [v_true * y / x for x, y in zip(f, i) if x > 0]
    v_int = [v_true * y / y for y in i if y > 0]
    emit("finite_difference_velocity", true_mps=v_true, samples=len(v_float),
         float_first_min=min(v_float), float_first_max=max(v_float),
         float_first_stdev=statistics.pstdev(v_float),
         int_first_min=min(v_int), int_first_max=max(v_int))

    emit("run_info", timer_samples=len(timer_stamps), tight_samples=len(tight),
         wall_seconds=round(time.monotonic() - wall_start, 3))


if __name__ == "__main__":
    main()
