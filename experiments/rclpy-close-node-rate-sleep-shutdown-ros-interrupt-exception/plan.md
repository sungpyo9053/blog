# 실험 계획: rate.sleep() 루프는 rclpy.shutdown()과 Ctrl+C(SIGINT)에 어떻게 끝나는가

## 질문

`while rclpy.ok(): rate.sleep()` 루프를 돌리는 rclpy 노드(ROS 2 Jazzy)를 끝낼 때,

1. 다른 스레드가 `rclpy.shutdown()`을 부르면 잠든 `rate.sleep()`은 다음 틱까지 기다리는가, 바로 깨어나는가? 어떤 예외로 깨어나는가?
2. 셧다운 뒤 `rate.sleep()`을 한 번 더 부르면 기다리는가?
3. Ctrl+C(SIGINT)로 끝내면 같은 경로를 타는가? 루프가 메인 스레드일 때와 워커 스레드일 때 무엇이 다른가?
4. 끝난 뒤 `rclpy.shutdown()`을 다시 부르면 실패하고 `rclpy.try_shutdown()`은 조용히 지나가는가?

## research.md 기준 예측값 (실행 전 작성)

예측의 근거는 research.md의 소스 읽기(timer.py, context.py, signal_handler.cpp)와 자체 산술 예제다. 아래 수치는 산술 예측이며 실측이 아니다.

| 케이스 | 구성 | 예측 |
| --- | --- | --- |
| A | 10 Hz(주기 100 ms), 루프=메인 스레드, spin=별도 스레드, 2350 ms에 다른 스레드가 `rclpy.shutdown()` | 정상 반환 23회(마지막 정상 틱 2300 ms). 루프는 `ROSInterruptException`(메시지 `rclpy.shutdown() has been called`)으로 끝남. 셧다운 호출→예외 지연은 0 ms보다 크지만 "다음 틱까지 기다린다" 반례 가정의 50 ms보다 훨씬 작음(구체 수치 예측 없음). 예외 직후 `rclpy.ok()`는 False |
| C (A 프로세스 안) | A에서 예외를 받은 뒤 `rate.sleep()` 재호출 | `_presleep`에서 즉시 `ROSInterruptException`. 대기 거의 0, 워치독 미발동 |
| B | 1 Hz(주기 1000 ms), 나머지 A와 같음 | 정상 반환 2회(1000, 2000 ms). 지연이 반례 가정 650 ms보다 훨씬 작음 |
| D | 10 Hz, 셧다운 2400 ms(틱 경계) | 정상 반환 23 또는 24회. 5회 반복 사이 달라질 수 있음. 루프가 `rclpy.ok()==False`로 끝날 수도 있음 |
| E | 10 Hz, 루프=메인 스레드, 2350 ms에 `os.kill(os.getpid(), SIGINT)` | 루프는 `KeyboardInterrupt`로 끝남(`ROSInterruptException` 아님). `rclpy.ok()`는 곧 False. 재호출한 `sleep()`은 예외 없이 막혀 있다가 1000 ms 워치독(`destroy_rate`)이 깨움. 두 번째 `rclpy.shutdown()`은 `RCLError`(rcl_shutdown already called), `try_shutdown()`은 정상. spin 스레드는 `ExternalShutdownException` 가능 |
| F | 10 Hz, 루프=워커 스레드, 2350 ms에 SIGINT | 메인 스레드는 `KeyboardInterrupt`. 워커의 `sleep()`은 2000 ms 안에 깨어나지 않음(종료 콜백 미호출 + spin 정지로 틱 없음). 워치독 `destroy_rate` 뒤에 깨어나 루프 종료 |
| G | 10 Hz, 루프=워커 스레드, 2350 ms에 `rclpy.shutdown()` (F 대조군) | 워커가 `ROSInterruptException`으로 즉시 끝남. 워치독 불필요 |

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 실행. 표준 라이브러리 + `rclpy`(+ 버전 확인용 `ament_index_python`)만 사용.
- 격리: 부모 프로세스가 케이스마다 `python3 experiment.py <케이스>`로 새 프로세스를 띄운다. 시그널 핸들러·컨텍스트가 케이스끼리 섞이지 않게 하기 위해서다. 케이스당 제한 15초, 전체 예상 30초 안팎.
- 시각: `time.monotonic()`, 기준 t0은 `node.create_rate()` 직후(research 한계 항목의 권고대로 타이머 생성 시점을 0으로 둔다). spin 스레드는 t0 뒤에 시작한다.
- 기록 항목(케이스별 JSON 한 줄):
  - `return_times_ms`, `normal_returns`: 트리거 호출 전에 루프의 `rate.sleep()`이 정상 반환한 시각과 횟수. 트리거 뒤의 반환(예: 워치독이 깨운 반환)은 `returns_after_trigger_ms`에 따로 기록
  - `max_abs_tick_error_ms`: 정상 반환 시각과 이상적 틱(주기 × n)의 최대 차이
  - `trigger.t_call_ms`: 실제로 `rclpy.shutdown()`/`os.kill`을 부른 시각(`time.sleep` 오차 때문에 목표 시각과 다를 수 있어 실제 값을 남긴다)
  - `loop_end`: 루프가 끝난 이유(예외 클래스 이름·메시지 또는 `rclpy.ok()==False`)와 시각, `trigger_to_loop_end_ms` = 루프 종료 시각 − 트리거 호출 시각
  - `ok_right_after_loop_end`, `ok_false_at_ms`: 루프가 끝난 직후의 `rclpy.ok()`와 False가 된 시각(1초까지 1 ms 간격 폴링)
  - `resleep_after_end`(메인 스레드 케이스, research의 케이스 C): 끝난 뒤 `rate.sleep()` 재호출의 결과, 막힌 시간, 1000 ms 워치독(`node.destroy_rate`) 발동 여부
  - `main_thread`, `worker_finished_within_wait`, `watchdog_destroy_rate.worker_finished_after`(워커 스레드 케이스): 메인 스레드가 받은 것, 2000 ms 안에 워커 루프가 스스로 끝났는지, 워치독 `destroy_rate` 뒤 1000 ms 안에 끝났는지(워커가 직접 set하는 Event로 판정)
  - `second_shutdown`, `try_shutdown`: 끝난 뒤 `rclpy.shutdown()` 재호출과 `rclpy.try_shutdown()`의 결과
  - `spin_thread`: `rclpy.spin()`이 끝난 방식(반환/예외 클래스)과 `trigger_to_spin_end_ms`
  - `child_stderr_traceback`: 자식 프로세스 stderr에 트레이스백이 찍혔는지
- 판정: 예측표와 다른 값은 그대로 기록하고 글은 실측을 따른다. 결과 숫자를 코드에 미리 적지 않는다(코드의 숫자는 주기·트리거 시각·제한 시간 같은 입력뿐이다).
- 한계: SIGINT는 터미널 Ctrl+C 대신 같은 프로세스 안에서 `os.kill(os.getpid(), SIGINT)`로 보낸다(프로세스 대상 시그널이라는 점은 같지만 터미널 프로세스 그룹 전송과 완전히 같다고 주장하지 않는다). 컨테이너 1 CPU 결과이며 실물 로봇·시뮬레이터 검증이 아니다.

## 시행착오

`--try` 시험 실행 3회. 실행 결과 수치는 하네스의 정식 `results.json`만 근거로 하며, 여기에는 무엇을 고쳤는지만 적는다.

1. **워커 스레드 케이스(F)가 잘못된 "워커 종료"를 보고함 → 측정 방법 수정.** 첫 시험에서 F는 `worker.is_alive()`가 False인데 워커 루프의 종료 기록(`loop_end`)은 비어 있었다. 루프가 끝났다면 반드시 남는 기록이므로 모순이다. 원인은 측정 코드였다. 메인 스레드가 `worker.join(0.05)` 안에서 SIGINT로 `KeyboardInterrupt`를 받으면, Python 3.12.3 `threading.Thread._wait_for_tstate_lock()`의 예외 처리(bpo-45274 대응 코드: `if lock.locked(): lock.release(); self._stop()`)가 **아직 살아 있는 워커의 tstate 잠금을 풀고 스레드를 멈춘 것으로 표시**한다(호스트의 같은 버전 3.12.3 `/usr/lib/python3.12/threading.py`에서 코드 확인. 컨테이너 Python도 3.12.3). 그래서 `join()`/`is_alive()`로는 워커 생존을 판정할 수 없었다. 수정: 워커 루프가 `finally`에서 직접 set하는 `threading.Event`(`loop_done`)로 종료를 판정하고, 메인 스레드는 `join` 대신 `time.sleep(0.01)` 폴링으로 기다린다. 수정 뒤 F는 워커가 대기 시간(2000 ms) 안에 끝나지 않고 워치독 `destroy_rate` 뒤에야 끝나는 것으로 기록됐다. (이것은 rclpy가 아니라 Python 표준 라이브러리 동작이다. Ctrl+C 처리에서 `thread.join()`으로 워커 생존을 확인하는 코드에도 같은 함정이 있을 수 있다는 점만 글에서 짧게 언급할 수 있다.)
2. **`rclpy.ok()` False 시각이 워치독 대기만큼 늦게 찍힘 → 측정 순서 수정.** 첫 시험의 E는 `ok()` 폴링을 셧다운 뒤 `sleep()` 재호출(워치독 1000 ms) 다음에 해서, False가 된 시각이 그만큼 늦게 기록됐다. 폴링을 루프 종료 직후(메인 스레드 케이스)와 메인 스레드가 시그널/워커 종료를 받은 직후(워커 케이스)로 옮겼다.
3. **워치독이 깨운 반환이 정상 틱으로 집계됨 → 집계 분리.** 2차 시험의 F에서 워치독 `destroy_rate`로 깨어난 `sleep()` 반환(예외 없이 반환)이 정상 반환 횟수와 틱 오차 계산에 섞였다. 트리거 호출 시각 이전 반환만 `normal_returns`·`return_times_ms`·`max_abs_tick_error_ms`에 넣고, 이후 반환은 `returns_after_trigger_ms`에 따로 남기도록 고쳤다.
4. 첫 시험에서는 `ros:jazzy-ros-base` 이미지가 없어 하네스가 받아 왔다(실행 실패 아님). 이미지 다이제스트는 하네스가 `results.json`의 environment에 기록한다.
5. 예측과 실측의 차이는 측정 코드를 고칠 이유로 쓰지 않았다. 위 1–3은 모두 측정값이 서로 모순되거나(1) 측정 순서·집계가 질문과 맞지 않아서(2, 3) 고친 것이다. 셧다운 뒤 `rclpy.shutdown()` 재호출의 예외 종류처럼 예측과 다르게 나온 값은 코드를 바꾸지 않고 그대로 기록한다. 글은 정식 5회 `results.json`의 값을 따른다.
