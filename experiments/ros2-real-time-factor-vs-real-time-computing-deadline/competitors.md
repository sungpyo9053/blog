# 경쟁 글 대비 차별점: ros2-real-time-factor-vs-real-time-computing-deadline

1. https://robotics.stackexchange.com/questions/22252/why-does-ros2-claim-to-be-real-time (EN, Robotics Stack Exchange, 2021-06-04; runner 직접 접근은 403이라 공개 Stack Exchange API로 질문·답변 원문을 읽음)
   - 그 글이 다루는 것: DDS의 "real-time systems" 문구를 보고 범용 OS에서 어떻게 실시간이 가능하냐는 질문. 채택 답변은 ROS가 말하는 실시간은 대개 소프트 실시간이고 하드 실시간과 구분된다고 설명.
   - 빠졌거나 틀린 것: 시뮬레이터 RTF·`use_sim_time`의 'real time'과의 혼동은 다루지 않음. 공식 설계 문서의 정의 인용, 수치 예, 측정 방법이 없음. "로봇 제어에 하드 실시간이 꼭 필요하지 않다"는 일반화는 근거 문서 없이 제시됨.
   - 이 글이 더할 것: 공식 설계 문서 두 개의 줄 단위 정의로 두 'real time'을 가르고, RTF 1.0과 마감 초과를 같은 실행에서 나란히 계산·실측한다(ROS 2 Jazzy 컨테이너 5회 실행 결과).
2. https://physicalailab.io/ros2-real-time-control/ (KO, 피지컬 AI Lab, 2026-07-25 작성·2026-08-01 수정)
   - 그 글이 다루는 것: 실시간 제어는 평균 속도가 아니라 마감 문제라는 정의, 하드/펌/소프트 구분, 관절 루프와 비실시간 노드 분리, 단조 시계로 예정·실제 시작·완료를 기록하고 최대값·높은 백분위를 보라는 측정 원칙, "평균 100µs여도 드물게 2ms" 같은 서술형 예.
   - 빠졌거나 틀린 것: RTF·`use_sim_time`·Gazebo 언급이 없어 이 글의 출발 질문(시뮬레이터 RTF와 실시간 혼동)에 답하지 않음. 수치 예는 측정이나 출처 없는 서술이고 자체 실측 데이터가 없음. ROS 2 타이머가 놓친 주기를 건너뛴다는 동작은 설명하지 않음.
   - 이 글이 더할 것: RTF와 마감을 하나의 계산 틀로 묶고, rcl 타이머의 고정 격자·건너뛰기 소스로 평균이 최댓값을 가리는 이유를 보인 뒤, 컨테이너 실측으로 평균·최대·건너뛴 주기를 함께 제시한다.
3. https://physicalailab.io/en/ros2-real-time-control-guide/ (EN, 피지컬 AI Lab, 2026-07-29 작성·2026-08-01 수정)
   - 그 글이 다루는 것: 마감·유계 지터 정의, soft/firm/hard 분류, 하드웨어 read-update-write 루프, CPU affinity·IRQ·메모리 사전 할당·트레이싱·RT 커널 필요성 평가.
   - 빠졌거나 틀린 것: 시뮬레이션 RTF·sim time 언급 없음. 평균 대비 최대를 수치로 비교하지 않고 자체 측정도 없음. 일부 판단(비RT 구성에서도 마감을 만족할 수 있다)은 근거 인용이 없음.
   - 이 글이 더할 것: 입문자가 시뮬레이터 화면의 RTF 수치에서 출발해 자기 노드의 마감 초과를 직접 세는 최소 실습과 실측 결과.
4. https://xilinx.github.io/KRS/sphinx/build/html/docs/features/realtime_ros2.html (EN, AMD/Xilinx KRS 1.0 문서, 2024-01-02 갱신)
   - 그 글이 다루는 것: 실시간을 로봇 시스템의 종단 간 특성으로 정의하고, 링크 계층·네트워크 스택·커널·캐시·미들웨어·ROS 2 계층·애플리케이션 7개 비결정성 원인과 TSN·PREEMPT_RT 등 대응책을 정리.
   - 빠졌거나 틀린 것: 하드/소프트 구분, 시뮬레이션 RTF, 평균 대비 최악값 수치가 없음. 특정 하드웨어(KRS) 맥락이라 입문자의 Gazebo/ROS 2 질문과 거리가 있음.
   - 이 글이 더할 것: 하드웨어 가속 없이 표준 ROS 2 Jazzy 컨테이너에서 독자가 그대로 재현할 수 있는 측정 절차와 판정 기준.
5. https://classic.gazebosim.org/tutorials?cat=tools_utilities&tut=performance_metrics (EN, Gazebo Classic 9·11 공식 튜토리얼)
   - 그 글이 다루는 것: 성능 지표로서의 real_time_factor, lockstep을 켜면 센서 갱신률을 지키느라 RTF가 1.0보다 낮아질 수 있다는 관찰.
   - 빠졌거나 틀린 것: RTF 계산 방식(평활·표본 주기)을 설명하지 않고, 제어 마감·실시간 컴퓨팅과의 관계를 다루지 않음. Gazebo Classic 기준이라 현재 Gazebo Sim과 다름.
   - 이 글이 더할 것: 현재 Gazebo Sim·gz-gui 소스로 RTF가 어떻게 계산·평활·표본화되는지 확인하고, 그 수치가 내 노드 콜백 지연과 다른 양임을 실측으로 보인다.
6. https://docs.isaacsim.omniverse.nvidia.com/5.1.0/ros2_tutorials/tutorial_ros2_rtf.html (EN, NVIDIA Isaac Sim 5.1.0 공식 문서)
   - 그 글이 다루는 것: RTF를 프레임마다 simulated_elapsed_time / real_elapsed_time로 계산해 ROS 2 Float32 토픽으로 발행하는 방법.
   - 빠졌거나 틀린 것: RTF가 무엇을 보장하지 않는지(제어 마감) 언급이 없음.
   - 이 글이 더할 것: 발행된 RTF를 읽는 독자가 그 값과 별도로 자기 콜백의 최대 간격·마감 초과를 재야 하는 이유와 방법.

판정: 상위 글들은 실시간 컴퓨팅 일반론과 RTF 설정·모니터링을 각각 다룰 뿐, 둘을 한 질문으로 묶어 숫자와 실측으로 구분하지 않는다. 이 글이 더할 실측(하네스 실험)과 소스 기반 설명이 있으므로 INSUFFICIENT 사유가 아니다.
