#!/usr/bin/env python3
"""rclpy Rate.sleep() 동작 실측: executor 구성별 멈춤 여부와 작업 시간별 실효 루프 주기.

모든 값은 실행 중 time.monotonic()으로 잰다. 멈추는 구성은 워치독이 node.destroy_rate(rate)로
Rate의 이벤트를 세워(timer.py destroy -> _event.set) sleep()을 깨워서 실행이 끝나게 한다.
각 케이스는 JSON 한 줄을 출력한다.
"""
import json
import os
import statistics
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor

RATE_HZ = 8.0                # 목표 주기 1/8 s
WATCHDOG_S = 2.0             # 멈춤 판정 대기 시간
HARD_DEADLINE_S = 55.0       # 어떤 경우에도 60초 안에 종료


def emit(record):
    print(json.dumps(record, ensure_ascii=False), flush=True)


def r4(value):
    return None if value is None else round(value, 4)


def ms3(value):
    """sleep() 대기처럼 0에 가까운 값은 밀리초(소수 셋째 자리 = 1 µs)로 남긴다."""
    return None if value is None else round(value * 1000.0, 3)


def interval_stats(starts):
    """루프 본문 시작 시각 목록 -> 첫 간격(위상 차 포함)과 나머지 간격 통계."""
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    if not gaps:
        return {"first_interval_s": None, "n_intervals": 0}
    rest = gaps[1:]
    out = {"first_interval_s": r4(gaps[0]), "n_intervals": len(rest)}
    if rest:
        mean = statistics.fmean(rest)
        out.update({"mean_interval_s": r4(mean), "median_interval_s": r4(statistics.median(rest)),
                    "min_interval_s": r4(min(rest)), "max_interval_s": r4(max(rest)),
                    "stdev_interval_s": r4(statistics.pstdev(rest)),
                    "effective_hz": r4(1.0 / mean)})
    return out


def start_spin(executor):
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    return thread


def stop_spin(executor, node, thread):
    executor.shutdown(timeout_sec=2.0)
    thread.join(timeout=2.0)
    node.destroy_node()
    return not thread.is_alive()


def case_a_no_spin():
    """A: spin 없음. 메인 스레드 while 루프 + 8 Hz Rate."""
    node = rclpy.create_node("case_a_no_spin")
    rate = node.create_rate(RATE_HZ)
    woke = threading.Event()

    def watchdog():
        woke.set()
        node.destroy_rate(rate)

    timer = threading.Timer(WATCHDOG_S, watchdog)
    t0 = time.monotonic()
    timer.start()
    bodies = 0
    returns_before_watchdog = 0
    blocked_s = None
    error = None
    while True:
        bodies += 1
        s = time.monotonic()
        try:
            rate.sleep()
        except Exception as exc:  # noqa: BLE001 - 어떤 예외인지 기록한다
            error = type(exc).__name__
            break
        if woke.is_set():
            blocked_s = time.monotonic() - s
            break
        returns_before_watchdog += 1
    timer.cancel()
    node.destroy_node()
    emit({"case": "A_no_spin_main_loop", "rate_hz": RATE_HZ, "watchdog_s": WATCHDOG_S,
          "loop_bodies_run": bodies, "sleep_returns_before_watchdog": returns_before_watchdog,
          "last_sleep_blocked_s": r4(blocked_s), "elapsed_s": r4(time.monotonic() - t0), "error": error})


def case_spin_thread(name, work_s, duration_s):
    """B/C/D/경계: spin을 별도 데몬 스레드(SingleThreadedExecutor), 메인 루프에서 작업 후 rate.sleep()."""
    node = rclpy.create_node(name.lower().replace(".", "_"))
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    thread = start_spin(executor)
    rate = node.create_rate(RATE_HZ)
    starts, waits = [], []
    t0 = time.monotonic()
    while True:
        now = time.monotonic()
        if now - t0 >= duration_s:
            break
        starts.append(now)
        time.sleep(work_s)                       # 루프 본문(작업) 대역
        s = time.monotonic()
        rate.sleep()
        waits.append(time.monotonic() - s)
    node.destroy_rate(rate)
    clean = stop_spin(executor, node, thread)
    later_waits = waits[1:]
    record = {"case": name, "rate_hz": RATE_HZ, "work_s": work_s, "window_s": duration_s,
              "loop_starts_in_window": len(starts),
              "first_sleep_wait_ms": ms3(waits[0]) if waits else None,
              "mean_sleep_wait_ms": ms3(statistics.fmean(later_waits)) if later_waits else None,
              "max_sleep_wait_ms": ms3(max(later_waits)) if later_waits else None,
              "spin_thread_stopped": clean}
    record.update(interval_stats(starts))
    emit(record)


def case_sleep_in_callback(name, executor, tries):
    """E/F: 노드 기본(상호 배타) 그룹 타이머 콜백 안에서 rate.sleep()을 tries번 시도."""
    node = rclpy.create_node(name.lower().replace(".", "_"))
    rate = node.create_rate(RATE_HZ)
    returns = []
    state = {"entered": None, "error": None, "done": threading.Event()}
    woke = threading.Event()

    def callback():
        trigger.cancel()
        if state["entered"] is not None:
            return
        state["entered"] = time.monotonic()
        try:
            for _ in range(tries):
                rate.sleep()
                if woke.is_set():
                    break
                returns.append(time.monotonic())
        except Exception as exc:  # noqa: BLE001
            state["error"] = type(exc).__name__
        state["done"].set()

    trigger = node.create_timer(0.05, callback)
    executor.add_node(node)
    thread = start_spin(executor)
    t0 = time.monotonic()
    finished_alone = state["done"].wait(timeout=WATCHDOG_S)
    if not finished_alone:
        woke.set()
        node.destroy_rate(rate)
        state["done"].wait(timeout=2.0)
    else:
        node.destroy_rate(rate)
    clean = stop_spin(executor, node, thread)
    entered = state["entered"]
    record = {"case": name, "rate_hz": RATE_HZ, "sleep_attempts": tries, "watchdog_s": WATCHDOG_S,
              "callback_entered": entered is not None,
              "sleep_returns_before_watchdog": len(returns),
              "finished_without_watchdog": finished_alone,
              "callback_exited": state["done"].is_set(),
              "elapsed_s": r4(time.monotonic() - t0), "error": state["error"],
              "spin_thread_stopped": clean}
    if entered is not None and returns:
        record.update(interval_stats([entered] + returns))
    emit(record)


def main():
    hard = threading.Timer(HARD_DEADLINE_S, lambda: os._exit(3))
    hard.daemon = True
    hard.start()
    t0 = time.monotonic()
    rclpy.init()
    emit({"case": "env", "sched_getaffinity_cpus": len(os.sched_getaffinity(0)), "os_cpu_count": os.cpu_count(),
          "rmw": os.environ.get("RMW_IMPLEMENTATION", "default"), "ros_distro": os.environ.get("ROS_DISTRO")})
    case_a_no_spin()
    case_spin_thread("B_spin_thread_work_0.0625", 0.0625, 5.0)
    case_spin_thread("Bound_spin_thread_work_0.125", 0.125, 3.0)
    case_spin_thread("D_spin_thread_work_0.15", 0.15, 3.0)
    case_spin_thread("C_spin_thread_work_0.25", 0.25, 3.0)
    case_sleep_in_callback("E_single_threaded_callback", SingleThreadedExecutor(), 8)
    case_sleep_in_callback("F1_multi_threaded_1_thread_callback", MultiThreadedExecutor(num_threads=1), 8)
    case_sleep_in_callback("F2_multi_threaded_2_threads_callback", MultiThreadedExecutor(num_threads=2), 8)
    rclpy.shutdown()
    emit({"case": "done", "total_elapsed_s": r4(time.monotonic() - t0)})


if __name__ == "__main__":
    main()
