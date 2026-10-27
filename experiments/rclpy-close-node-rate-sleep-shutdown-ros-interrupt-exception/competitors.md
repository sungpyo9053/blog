# 경쟁 글 대비 차별점: rclpy-close-node-rate-sleep-shutdown-ros-interrupt-exception

확인 방법: GitHub·docs 페이지는 직접 열었다. Robotics Stack Exchange 페이지는 이 runner에서 HTML 403이라 Stack Exchange 공개 API 2.3(`api.stackexchange.com`, 인증 없음)으로 질문·답변 본문을 읽었다. 이 때문에 RSE URL은 본문의 근거 링크로 쓰지 않는다(아래 "글 작성 시 주의할 점").

1. https://robotics.stackexchange.com/questions/96684/rate-and-sleep-function-in-rclpy-library-for-ros2 (2020-07-30, 채택 답변 jacobperron)
   - 다루는 것: `rospy.is_shutdown()` → `rclpy.ok()` 대응. Rate는 ROS 타이머 콜백을 쓰므로 spin이 필요하다는 이유. spin 데몬 스레드 + `while rclpy.ok(): rate.sleep()` + `except KeyboardInterrupt: pass` + `rclpy.shutdown()` + `thread.join()` 예제.
   - 빠졌거나 틀린 것: `ROSInterruptException`을 언급하지 않는다. 명시적 셧다운으로 깨어나는 원리가 없다. 예제는 `KeyboardInterrupt`를 잡은 뒤 `rclpy.shutdown()`을 무조건 부른다. 소스상 Ctrl+C가 이미 `rcl_shutdown()`을 했다면 Jazzy에서 `RCLError`가 날 수 있는 형태다(2020년 답변이라 당시 rclpy 시그널 처리와 다를 수 있다. 현재 Jazzy 기준 평가이며 실측 전 추론).
   - 이 글이 더할 것: 명시적 셧다운 → `ROSInterruptException`의 소스 경로와 Ctrl+C 경로의 차이. `try_shutdown` 교체 이유. 실측으로 A·E 케이스의 예외 종류와 지연을 나란히 보여 준다.
2. https://github.com/mikeferguson/ros2_cookbook/blob/main/rclpy/time.md (Rates 절)
   - 다루는 것: spin을 daemon 스레드로 돌리고("so we don't have to join it to exit") `while rclpy.ok(): rate.sleep()`으로 10 Hz 출력.
   - 빠진 것: 종료 처리 전무. 예외, Ctrl+C, 셧다운 시점, daemon 스레드가 종료 때 갑자기 멈춘다는 Python 경고 모두 없다.
   - 이 글이 더할 것: 같은 구조에서 종료할 때 무슨 예외가 어디서 나는지. 지연 계산과 실측.
3. https://robotics.stackexchange.com/questions/113602/actual-good-way-to-close-nodes (2024-11-05, 독자 질문 원문, 채택 답변 2024-11-06)
   - 다루는 것: Jazzy demo_nodes_py는 `destroy_node()`/`rclpy.shutdown()`을 쓰는데 rolling은 쓰지 않는 이유. 채택 답변은 rolling의 `with rclpy.init(args=args):` 컨텍스트 매니저와 기본 SIGINT/SIGTERM 핸들러가 정리를 맡는다고 설명한다. 답변자 스스로 일부는 "not tested"라고 밝힌다.
   - 빠진 것: Jazzy에서 Rate 루프를 쓸 때의 종료 동작, 예외 종류, `try_shutdown`, Ctrl+C 때 `on_shutdown` 미호출(이슈 #532)을 다루지 않는다.
   - 이 글이 더할 것: 질문의 "typical usecase of sending SIGINT"를 Jazzy Rate 루프에 적용했을 때 명시적 셧다운과 무엇이 다른지를 소스와 실측으로 보인다. Rolling 컨텍스트 매니저는 범위 밖으로 명시한다.
4. https://robotics.stackexchange.com/questions/103990/how-to-use-the-rate-sleep-function-properly (2023-09-07)
   - 다루는 것: 구독 콜백 안에서 `create_rate`·`sleep`을 쓰는 turtlesim 예제. 답변은 타이머 콜백 구조로 바꾸라고 권한다.
   - 빠진 것: 종료·셧다운 처리 없음. `main`이 `rclpy.spin(node); rclpy.shutdown()`뿐이다.
   - 이 글이 더할 것: 콜백 안 sleep 문제는 기존 공개 글로 넘기고, 루프를 끝내는 쪽을 다룬다.
5. HuntLab 공개 글 https://huntlab.app/rclpy-rate-sleep-timer-executor-loop-period/ (post 923, 2026-10-15 공개) — 경쟁 글이 아니라 중복 검토 대상
   - 다루는 것: Rate의 이벤트 구조, spin 스레드·MultiThreadedExecutor·create_timer 선택, 8 Hz 루프 주기 계산과 8가지 구성 실측. 셧다운은 "Rate는 destroy나 rclpy.shutdown() 때 깃발을 올려 기다리던 스레드를 풀어 준다"는 한 문장뿐이다. 인벤토리 본문 검색 결과 `ROSInterruptException`, `KeyboardInterrupt`, `SIGINT`, `try_shutdown`, `ExternalShutdownException`은 나오지 않는다.
   - 판단: 검색 의도가 다르다(멈춤·주기 vs 종료·예외). 새 글이 타당하다. 다만 Rate 내부 구조는 그 글에 맡기고 짧게 요약하며 링크한다. 같은 실측 수치를 재사용하지 않는다.

결론: 이 글이 더할 것이 있다 → INSUFFICIENT 아님.
