# 경쟁 글 대비 차별점: rclpy-time-seconds-float-dt-quantization

1. [ROS Answers archive 415959 — Is there a more elegant way to get the time in seconds in a ROS 2 node?](https://answers.ros.org/question/415959/) (Robotics SE 111251의 보관 사본, 2023-05)
   - 다루는 것: rclpy에 `.seconds()`가 없다는 사실, rclcpp issue #482, Humble `dir(Duration)` 출력.
   - 빠진 것: 질문자 코드의 순서(정수 선감산)가 왜 맞는지, float 선변환을 하면 무엇이 깨지는지, 정밀도 수치.
   - 이 글이 더할 것: 2⁻²²초 간격 계산, 1 µs·1 ms 결과 비교, 시뮬레이션 대 시스템 시계 차이.
2. [mikeferguson/ros2_cookbook — rclpy/time.md](https://github.com/mikeferguson/ros2_cookbook/blob/main/rclpy/time.md)
   - 다루는 것: int·float·rclpy·msg 4형식 변환표(rclpy→float는 `t.nanoseconds / 1e9`), "혼합 타입끼리 비교·연산 불가".
   - 빠진 것: dt 계산 순서, 정밀도 언급이 전혀 없다. float→rclpy 칸의 `Time(int(sec), int(nano * 1e9))`는 위치 인자 호출인데, Jazzy Time 생성자는 키워드 전용이다([time.py L43-L47](https://github.com/ros2/rclpy/blob/4e607c09d624debc39a4ae5405680c06d87fac35/rclpy/rclpy/time.py#L43-L47)). 실행으로 확인하지 않았으므로 "소스상 키워드 전용"이라고만 쓴다.
   - 이 글이 더할 것: 변환표의 `/ 1e9`를 시각에 적용할 때와 차이에 적용할 때의 결과 차이를 숫자로 제시한다.
3. [velog @jk01019 — [ros2] rclpy.time.Time](https://velog.io/@jk01019/ros2-rclpy.time.Time) (2024-04-28)
   - 다루는 것: Time·msg 비교, float 변환 예시.
   - 틀린 것(소스 대조):
     - "내부적으로 초와 나노초 두 부분으로 저장"이라고 하지만 실제로는 정수 nanoseconds 하나다.
     - `seconds()` 메서드가 있다고 하지만 Jazzy·Rolling에 없다.
     - 예시 코드가 `time_obj.nanoseconds() / 1e9`인데, `nanoseconds`는 프로퍼티라 호출하면 int 호출 오류가 날 것으로 보인다. 실행하지 않았으므로 Writer는 "소스상 프로퍼티"라고만 쓴다.
   - 이 글이 더할 것: 정확한 API 표면, dt 순서 기준.
4. [velog @hy_k — [ROS2] ROS2의 단위, 좌표, 시간](https://velog.io/@hy_k/ROS2-ROS2%EC%9D%98-%EB%8B%A8%EC%9C%84-%EC%A2%8C%ED%91%9C-%EC%8B%9C%EA%B0%84) (2024-09-18)
   - 다루는 것: rclcpp/rclpy 시간 예제, `(now-past).nanoseconds * 1e-9 > 5`처럼 정수 선감산 사용, "nanosecond가 더 정확함" 한 줄.
   - 빠진 것: 왜 더 정확한지, 얼마나 차이 나는지, 언제 문제가 되는지.
   - 이 글이 더할 것: 그 "더 정확함"의 크기를 시간 값 크기별 ulp로 계산하고, 판단 조건(차분·짧은 구간·시스템 시계)을 제시한다.

판정: 상위 문서 4건 모두 변환 한 줄에서 멈춘다. 이 글은 공식 소스 대조, 자체 산술 검산, 판단 기준을 더하므로 차별점이 충분하다.
