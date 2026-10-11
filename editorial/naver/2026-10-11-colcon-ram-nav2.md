제목: ROS 2 colcon 빌드, RAM 몇 GB면 될까 — Nav2를 16·8·4GB에서 직접 빌드해 봤습니다

colcon build 중에 노트북이 멈추거나 "c++: fatal error: Killed signal terminated program cc1plus"가 뜬다면 원인은 대개 RAM입니다. 감으로 답하지 않고 Nav2(Jazzy, 45개 패키지)를 메모리 상한을 바꿔 가며 다섯 번 빌드해 쟀습니다.

■ 결과 (4 vCPU 리눅스, Docker 메모리 상한, 스왑 끔)
- 기본 설정 16GB : 성공, 최대 8.1GiB
- 기본 설정 8GB : 성공, 최대 7.8GiB (상한 근처까지 참)
- 기본 설정 4GB : 실패 (cc1plus Killed, 8개 패키지 후 중단)
- 순차 빌드 16GB : 성공, 최대 2.7GiB
- 순차 빌드 4GB : 성공, 최대 2.7GiB

■ 결론
- 기본 설정으로 편하게 빌드하려면 RAM 16GB가 안전선입니다. 실제 노트북은 OS·브라우저·IDE가 3~4GB를 더 씁니다.
- 8GB 노트북이라면 순차 빌드로 돌리면 됩니다.
  MAKEFLAGS="-j1" colcon build --parallel-workers 1
- 너무 느리면 -j2, -j3처럼 하나씩 올려 보며 멈추지 않는 선을 찾으면 됩니다.

■ 주의
- 최대 메모리 값에는 파일 캐시도 들어갑니다. 그래서 "꼭 필요한 양"은 4GiB와 8GiB 사이 어딘가입니다.
- 코어가 많을수록 기본 설정에서 동시에 도는 컴파일러가 늘어 RAM을 더 씁니다.
- 측정 서버의 CPU 속도가 중간에 묶여서 빌드 시간은 비교하지 않았습니다.

측정 스크립트, 조건별 빌드 로그, RAM 업그레이드 기준은 원문에 정리했습니다.
원문: https://huntlab.app/ros2-colcon-build-ram-how-many-gb-nav2-measured/

#ROS2 #colcon #Nav2 #노트북RAM #메모리부족 #로봇개발 #우분투
