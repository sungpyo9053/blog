# 경쟁 글 대비 차별점: rclpy-rate-sleep-timer-executor-loop-period

검색(2026-10-10, 영어·한국어)에서 같은 질문으로 노출된 문서 중 이 실행 환경에서 원문을 직접 읽은 글만 비교한다.
한국어 검색은 이 질문을 직접 다루는 한국어 글을 찾지 못했다(검색 결과는 같은 영어 문서·Q&A로 채워짐).
Robotics Stack Exchange 96684·103990과 ROS Answers 아카이브(358343, 414785, 404442)는 403/봇 차단 페이지로 열리지 않아
원문을 읽지 못했으므로 비교 대상과 근거에서 제외한다.

1. https://github.com/mikeferguson/ros2_cookbook/blob/main/rclpy/time.md (ROS 2 Cookbook, rclpy: Time — Rates 절)
   - 그 글이 다루는 것: "Due to implementation details, we need to spin() or the sleep() function will block" 한 문장과,
     `rclpy.spin`을 데몬 스레드로 돌리고 10 Hz Rate로 `while rclpy.ok()` 루프를 도는 스니펫.
   - 빠졌거나 틀린 것: 왜 블록되는지(타이머 콜백 = `Event.set`, executor 필요)를 설명하지 않는다. 콜백 안 호출,
     MultiThreadedExecutor·Reentrant 그룹, 작업이 주기보다 길 때의 동작, 실제 주기 측정이 없다.
   - 이 글이 더할 것: 소스 줄 근거로 멈춤 원리 설명 + 같은 데몬 스레드 패턴을 Jazzy 컨테이너에서 5회 실행해 실제 간격·반복 수를 측정.
2. https://www.yahboom.net/public/upload/upload-html/1770206436/15.ROS2%20time%20related%20API.html (Yahboom, 15. ROS2 time related API)
   - 그 글이 다루는 것: create_rate 소개, Rate와 Timer 비교표, 루프를 별도 스레드에서 돌리고 메인에서 `rclpy.spin(node)`하는 2 Hz 예제,
     "Rate should generally not be used directly in the main thread" 경고.
   - 빠졌거나 틀린 것: 동작 원리를 "각 루프 시작 시각을 기록 → 실제 소요와 목표 간격의 차이를 계산해 그만큼 잔다 → 시작 간격이 목표와
     strictly equals"로 설명한다. 이는 rospy식 모델이며, Jazzy rclpy Rate는 시간을 직접 계산하지 않고 타이머 이벤트를 기다린다
     (timer.py L133, L175). 작업이 주기보다 길면 간격을 지킬 수 없다는 점도 빠졌다. 측정 결과가 없다.
   - 이 글이 더할 것: 잘못된 시간 계산 모델 대신 이벤트 대기 모델을 소스로 보이고, 작업 0.25 s(및 0.15 s) 케이스를 실측해 실효 주기가 작업 시간을 따르는지 확인.
3. https://www.learnros2.com/ros/tutorials/executor-and-spin-explained (Introduction to ROS2 and Robotics, Executor and Spin Explained — Humble 기준)
   - 그 글이 다루는 것: spin_once / spin_some / spin_until_future_complete / spin 차이를 구독 콜백 실험으로 설명, "기본적으로 노드의 콜백은
     상호 배타적으로 하나씩 실행" 설명.
   - 빠졌거나 틀린 것: Rate를 다루지 않는다. 기본 그룹 설명만 있어, rclpy가 Rate 타이머를 별도 ReentrantCallbackGroup(`_rate_group`)에 넣는다는
     예외가 빠져 있다. 저자 스스로 공식 문서 부족으로 정확성을 보장하지 않는다고 밝힌다. Humble 기준이다.
   - 이 글이 더할 것: Jazzy 소스로 Rate 전용 Reentrant 그룹을 확인하고, SingleThreadedExecutor 대 MultiThreadedExecutor(num_threads=2)
     콜백 안 `rate.sleep()`을 실측으로 대조.
