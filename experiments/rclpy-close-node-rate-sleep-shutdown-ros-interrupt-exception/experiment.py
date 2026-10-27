#!/usr/bin/env python3
"""rate.sleep() 루프는 rclpy.shutdown()과 Ctrl+C(SIGINT)에 각각 어떻게 끝나는가.

각 케이스를 새 Python 프로세스에서 한 번씩 실행해 시그널 핸들러와 컨텍스트 상태가
서로 섞이지 않게 한다. 모든 시각은 time.monotonic()으로 실행 중에 재며,
기준 t0은 node.create_rate() 직후다. 케이스마다 JSON 한 줄을 출력한다.

  A: 10 Hz, 루프=메인 스레드, 2350 ms에 다른 스레드가 rclpy.shutdown()
     (셧다운 뒤 rate.sleep() 재호출 = research의 케이스 C도 같은 프로세스에서 잰다)
  B: 1 Hz, 나머지 A와 같음
  D: 10 Hz, 셧다운을 틱 경계 2400 ms에
  E: 10 Hz, 루프=메인 스레드, 2350 ms에 os.kill(os.getpid(), SIGINT) (Ctrl+C 흉내)
  F: 10 Hz, 루프=워커 스레드, 2350 ms에 SIGINT, 2000 ms 기다린 뒤 워치독이 destroy_rate
  G: 10 Hz, 루프=워커 스레드, 2350 ms에 rclpy.shutdown() (F의 대조군)
"""
import json
import os
import platform
import signal
import subprocess
import sys
import threading
import time

CASES = {
    "A": {"hz": 10, "at_ms": 2350, "action": "shutdown", "loop_thread": "main"},
    "B": {"hz": 1, "at_ms": 2350, "action": "shutdown", "loop_thread": "main"},
    "D": {"hz": 10, "at_ms": 2400, "action": "shutdown", "loop_thread": "main"},
    "E": {"hz": 10, "at_ms": 2350, "action": "sigint", "loop_thread": "main"},
    "F": {"hz": 10, "at_ms": 2350, "action": "sigint", "loop_thread": "worker"},
    "G": {"hz": 10, "at_ms": 2350, "action": "shutdown", "loop_thread": "worker"},
}
RESLEEP_WATCHDOG_S = 1.0   # 셧다운/시그널 뒤 재호출한 sleep()이 이보다 오래 막히면 destroy_rate로 깨운다
WORKER_WAIT_S = 2.0        # F/G: 시그널·셧다운 뒤 워커 루프가 스스로 끝나기를 기다리는 시간
CHILD_TIMEOUT_S = 15


def _err(exc):
    return {"type": type(exc).__name__, "msg": str(exc)[:160]}


def child(case):
    import rclpy
    from rclpy.exceptions import ROSInterruptException

    cfg = CASES[case]
    rec = {"case": case, **cfg}
    rclpy.init()
    node = rclpy.create_node(f"shutdown_exp_{case.lower()}")
    rate = node.create_rate(cfg["hz"])
    t0 = time.monotonic()

    def ms():
        return round((time.monotonic() - t0) * 1000, 3)

    spin_info = {}

    def spin():
        try:
            rclpy.spin(node)
            spin_info["end"] = "returned"
        except BaseException as exc:  # 어떤 예외로 spin이 끝나는지 기록
            spin_info["end"] = type(exc).__name__
        spin_info["t_ms"] = ms()

    trig = {}

    def trigger():
        time.sleep(max(0.0, t0 + cfg["at_ms"] / 1000 - time.monotonic()))
        trig["t_call_ms"] = ms()
        if cfg["action"] == "shutdown":
            rclpy.shutdown()
        else:
            os.kill(os.getpid(), signal.SIGINT)
        trig["t_return_ms"] = ms()

    returns = []
    loop_end = {}
    loop_done = threading.Event()  # Thread.is_alive() 대신 쓴다(plan.md 시행착오 참고)

    def loop():
        try:
            while rclpy.ok():
                rate.sleep()
                returns.append(ms())
            loop_end["how"] = "rclpy.ok()==False"
        except (ROSInterruptException, KeyboardInterrupt) as exc:
            loop_end.update(how=type(exc).__name__, msg=str(exc)[:160])
        except BaseException as exc:
            loop_end.update(how=type(exc).__name__, msg=str(exc)[:160], unexpected=True)
        finally:
            loop_end["t_ms"] = ms()
            loop_done.set()

    def poll_ok_false():
        # ok()가 False가 되는 시각(시그널 경로는 별도 스레드가 rcl_shutdown을 하므로 늦을 수 있다)
        deadline = time.monotonic() + 1.0
        while rclpy.ok() and time.monotonic() < deadline:
            time.sleep(0.001)
        rec["ok_false_at_ms"] = None if rclpy.ok() else ms()

    spin_thread = threading.Thread(target=spin, daemon=True)
    spin_thread.start()
    threading.Thread(target=trigger, daemon=True).start()

    if cfg["loop_thread"] == "main":
        loop()
        rec["ok_right_after_loop_end"] = rclpy.ok()
        poll_ok_false()
        # 케이스 C: 셧다운/시그널 뒤 sleep()을 한 번 더 부르면 기다리는가
        done = threading.Event()
        watchdog = {"fired": False}

        def wake():
            if not done.wait(RESLEEP_WATCHDOG_S):
                watchdog["fired"] = True
                try:
                    node.destroy_rate(rate)
                except BaseException as exc:
                    watchdog["destroy_rate_error"] = _err(exc)
                    rate.destroy()

        threading.Thread(target=wake, daemon=True).start()
        started = time.monotonic()
        try:
            rate.sleep()
            resleep = {"result": "returned"}
        except BaseException as exc:
            resleep = {"result": type(exc).__name__, "msg": str(exc)[:160]}
        done.set()
        resleep["blocked_ms"] = round((time.monotonic() - started) * 1000, 3)
        resleep["watchdog_fired"] = watchdog["fired"]
        if "destroy_rate_error" in watchdog:
            resleep["destroy_rate_error"] = watchdog["destroy_rate_error"]
        rec["resleep_after_end"] = resleep
    else:
        worker = threading.Thread(target=loop, daemon=True)
        worker.start()
        main = {}
        try:
            deadline = time.monotonic() + 10
            while not loop_done.is_set() and time.monotonic() < deadline:
                time.sleep(0.01)
            main["how"] = "worker_finished" if loop_done.is_set() else "deadline"
        except KeyboardInterrupt:
            main["how"] = "KeyboardInterrupt"
        main["t_ms"] = ms()
        rec["main_thread"] = main
        poll_ok_false()
        rec["worker_finished_within_wait"] = loop_done.wait(WORKER_WAIT_S)
        rec["worker_wait_ms"] = WORKER_WAIT_S * 1000
        if not loop_done.is_set():
            wd = {"t_ms": ms()}
            try:
                node.destroy_rate(rate)
            except BaseException as exc:
                wd["destroy_rate_error"] = _err(exc)
                rate.destroy()
            wd["worker_finished_after"] = loop_done.wait(1.0)
            rec["watchdog_destroy_rate"] = wd

    try:
        rclpy.shutdown()
        rec["second_shutdown"] = {"result": "ok"}
    except BaseException as exc:
        rec["second_shutdown"] = {"result": "raised", **_err(exc)}
    try:
        rec["try_shutdown"] = {"result": "ok", "returned": repr(rclpy.try_shutdown())}
    except BaseException as exc:
        rec["try_shutdown"] = {"result": "raised", **_err(exc)}

    spin_thread.join(2.0)
    rec["spin_thread"] = {"alive": spin_thread.is_alive(), **spin_info}

    t_call = trig.get("t_call_ms")
    rec["trigger"] = trig
    # 트리거 뒤의 반환(F의 워치독 기상 등)은 정상 틱이 아니므로 따로 센다
    before = [t for t in returns if t_call is None or t < t_call]
    rec["normal_returns"] = len(before)
    rec["return_times_ms"] = before
    rec["returns_after_trigger_ms"] = returns[len(before):]
    rec["loop_end"] = loop_end
    if t_call is not None and "t_ms" in loop_end:
        rec["trigger_to_loop_end_ms"] = round(loop_end["t_ms"] - t_call, 3)
    if t_call is not None and "t_ms" in spin_info:
        rec["trigger_to_spin_end_ms"] = round(spin_info["t_ms"] - t_call, 3)
    if before:
        period = 1000 / cfg["hz"]
        rec["max_abs_tick_error_ms"] = round(
            max(abs(t - period * (i + 1)) for i, t in enumerate(before)), 3)
    try:
        node.destroy_node()
    except BaseException as exc:
        rec["destroy_node_error"] = _err(exc)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    os._exit(0)  # 남은 daemon 스레드와 무관하게 측정 프로세스를 끝낸다


def rclpy_version():
    try:
        import re
        from ament_index_python.packages import get_package_share_directory
        xml = open(os.path.join(get_package_share_directory("rclpy"), "package.xml")).read()
        return re.search(r"<version>([^<]+)</version>", xml).group(1)
    except Exception as exc:  # 버전 확인 실패는 측정 실패가 아니다
        return f"unknown ({type(exc).__name__})"


def main():
    print(json.dumps({"env": {"python": platform.python_version(),
                              "ros_distro": os.environ.get("ROS_DISTRO"),
                              "rclpy": rclpy_version(),
                              "rmw": os.environ.get("RMW_IMPLEMENTATION", "default")}}), flush=True)
    failures = 0
    for case in CASES:
        started = time.monotonic()
        try:
            done = subprocess.run([sys.executable, os.path.abspath(__file__), case],
                                  capture_output=True, text=True, timeout=CHILD_TIMEOUT_S)
            code, out, err = done.returncode, done.stdout, done.stderr
        except subprocess.TimeoutExpired as exc:
            code, out, err = "timeout", exc.stdout or "", exc.stderr or ""
            out = out.decode() if isinstance(out, bytes) else out
            err = err.decode() if isinstance(err, bytes) else err
        lines = [ln for ln in out.splitlines() if ln.startswith("{")]
        try:
            rec = json.loads(lines[-1])
        except (IndexError, json.JSONDecodeError):
            rec = {"case": case, "error": "no_json_output"}
            failures += 1
        rec["child_exit"] = code
        rec["child_wall_ms"] = round((time.monotonic() - started) * 1000, 1)
        rec["child_stderr_traceback"] = "Traceback" in err
        if err.strip():
            rec["child_stderr_tail"] = err.strip()[-400:]
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in CASES:
        child(sys.argv[1])
    else:
        sys.exit(main())
