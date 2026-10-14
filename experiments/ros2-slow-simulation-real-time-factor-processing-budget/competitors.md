# 경쟁 글 대비 차별점: ros2-slow-simulation-real-time-factor-processing-budget

한국어 검색(“가제보 real time factor 시뮬레이션 느리게”, “use_sim_time /clock 가제보 시뮬레이션 시간”, “keep last depth 1 느린 콜백 프레임 드롭” 등)에서 이 질문을 직접 다루는 한국어 글은 찾지 못했다. 아래는 직접 열어 읽은 영어 상위 자료다.

1. [Robotics Stack Exchange 질문 22917과 답변](https://api.stackexchange.com/2.3/questions/22917/answers?site=robotics&filter=withbody&sort=votes) (원 페이지 https://robotics.stackexchange.com/questions/22917/ros-how-to-slow-down-in-order-to-wait-for-my-results 는 runner에서 HTTP 403이라 API로 확인)
   - 다루는 것: `real_time_factor`로 Gazebo를 느리게 할 수 있다는 방향, 실물에서는 데이터를 버려 최신을 유지하라는 조언.
   - 빠졌거나 틀린 것: 얼마나 낮춰야 하는지 계산 없음. classic에서 실제 상한은 `max_step_size × real_time_update_rate`라는 공식 튜토리얼 설명과 어긋나는 부분이 있음. RTF가 노드를 기다리지 않는다는 점, 손실 프레임 수, 벽시계 비용 없음.
   - 이 글이 더할 것: 상한·손실 비율·벽시계 비용 식과 검산 예제, Harmonic 기준 설정 위치, 하네스 실측으로 예측과 처리 수 비교.
2. [Gazebo classic — Physics Parameters 튜토리얼](https://classic.gazebosim.org/tutorials?tut=physics_params&cat=physics)
   - 다루는 것: `max_step_size`, `real_time_update_rate`와 RTF 상한의 관계, 0이면 최대 속도.
   - 빠졌거나 틀린 것: 2025년 1월 EOL 버전. ROS 노드 처리 시간·센서 주기·QoS와의 연결 없음. 현재 권장 Harmonic의 `real_time_factor` 직접 사용과 다름.
   - 이 글이 더할 것: Harmonic 코드 기준 동작, 노드 쪽 계산과의 연결.
3. [CTU MRS — Run Simulation Faster than Real-time](https://ctu-mrs.github.io/docs/simulations/gazebo/simulation_speed/)
   - 다루는 것: PX4 SITL에서 `PX4_SIM_SPEED_FACTOR`, 느리게 돌릴 때는 `gz physics -u 125`(250 = RTF 1.0)를 쓰라는 실무 지침.
   - 빠졌거나 틀린 것: PX4·classic 전용 설정. 어떤 RTF가 필요한지 판단 기준, 센서 프레임·처리 시간·큐 이야기 없음.
   - 이 글이 더할 것: 처리 시간으로 RTF를 고르는 기준과 손실·지연 계산.
4. [Isaac Sim 5.1.0 — ROS 2 Publish Real Time Factor](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/ros2_tutorials/tutorial_ros2_rtf.html)
   - 다루는 것: RTF = simulated_elapsed_time / real_elapsed_time 정의와 RTF를 ROS 2 토픽으로 발행하는 방법.
   - 빠졌거나 틀린 것: 지원 종료 표시된 버전 문서. RTF를 어떻게 정할지, 느린 노드와의 관계 없음.
   - 이 글이 더할 것: RTF를 측정만 하는 것이 아니라 노드 처리 시간으로 목표값을 정하는 방법.
5. [O3DE — Simulation Time for ROS2 Gem](https://docs.o3de.org/docs/user-guide/interactivity/robotics/simulation-time/)
   - 다루는 것: realtime/simulation/ros2 시계 종류, `/clock`과 `use_sim_time`.
   - 빠졌거나 틀린 것: 시간 소스 설정 설명뿐이며 처리 지연·손실 계산 없음.
   - 이 글이 더할 것: 시간 소스 개념 위에서 실제 RTF 수치 결정.

판정: 경쟁 자료는 정의·설정 방법에서 멈춘다. 이 글은 계산 식·검산 예제·Harmonic 코드 근거·depth 효과 모델을 더하고, 후속 하네스 실험이 예측 대비 실측 처리 수를 더할 수 있다. 차별점이 있으므로 INSUFFICIENT 사유가 아니다.
