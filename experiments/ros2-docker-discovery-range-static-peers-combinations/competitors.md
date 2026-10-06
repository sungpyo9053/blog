# 경쟁 글 대비 차별점: ros2-docker-discovery-range-static-peers-combinations

모두 2026-10-06에 원문을 직접 열어 읽었다. (markaicode.com의 "Fix ROS 2 Discovery Issues in Docker in 15 Minutes"는 검색 상위였으나 403/Cloudflare로 열리지 않아 비교에서 제외했다.)

1. https://robotics.stackexchange.com/questions/98161/ros2-foxy-nodes-cant-communicate-through-docker-container-border (영어, 2021-01 질문, 채택 답변 2021-02; 러너에서 403이라 [Stack Exchange API 답변 엔드포인트](https://api.stackexchange.com/2.3/questions/98161/answers?site=robotics&filter=withbody)로 본문 확인)
   - 그 글이 다루는 것: Foxy, 호스트(데비안 패키지)와 `--net host` 컨테이너(소스 빌드) 사이 minimal publisher/subscriber 미수신. 채택 답변은 Fast DDS가 같은 기계로 판단해 SHM을 쓰려다 실패한다고 설명하고 (1) XML로 UDPv4만 사용 (2) `/dev/shm` 공유 + 같은 UID를 제시. 후속 답변은 `--ipc=host --pid=host`, `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`, rootless Docker를 언급.
   - 빠졌거나 틀린 것: 2021년 글이라 Iron 이후의 `ROS_AUTOMATIC_DISCOVERY_RANGE`/`ROS_STATIC_PEERS`가 없다. "발견은 됐는데 데이터가 안 온다"는 증상 구분이 질문 본문에만 있고 일반 점검 순서로 정리되지 않았다.
   - 이 글이 더할 것: 이 질문을 "목록엔 보이는데 데이터가 안 오는" 갈래의 예로 정확히 분류하고, "아예 안 보이는" 갈래는 공식 표 두 줄 규칙으로 판정하는 분기 점검표.
2. https://velog.io/@jk01019/%EB%8F%84%EC%BB%A4-%EC%BB%A8%ED%85%8C%EC%9D%B4%EB%84%88-%EB%81%BC%EB%A6%AC-ros2-%ED%86%B5%EC%8B%A0 (한국어, 2024-09-10, "도커 컨테이너 끼리 ros2 통신")
   - 그 글이 다루는 것: `osrf/ros:foxy-desktop` 기반 이미지, `docker network create ros2_network` 후 두 컨테이너를 같은 사용자 네트워크에 붙여 talker/listener 실행, `ROS_DOMAIN_ID` 통일, docker-compose 예.
   - 빠졌거나 틀린 것: "각 컨테이너는 동일한 네트워크에 있어야 한다"를 근거 없이 단정한다. 발견 범위·정적 피어·`ROS_LOCALHOST_ONLY` 언급이 없고, 실제 실행 출력이 없다. Foxy 기준이라 현재 배포판 변수와 연결되지 않는다.
   - 이 글이 더할 것: 같은 네트워크에 두어도 한쪽이 OFF거나 피어 없는 LOCALHOST면 왜 안 보이는지를 표와 코드로 설명하고, Iron 이후 배포판에서 확인할 변수 두 개와 판정 규칙을 제공.
3. https://husarnet.com/docs/ros2/ros-static-peers-env (영어, 상용 VPN 업체 문서, 작성일 표기 없음)
   - 그 글이 다루는 것: Jazzy + `rmw_cyclonedds_cpp` + IPv6(Husarnet) 환경에서 각 호스트에 `ROS_STATIC_PEERS=talker-host;listener-host`와 (선택) `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`를 똑같이 설정하는 절차, 호스트·Docker 양쪽 예.
   - 빠졌거나 틀린 것: 공식 표나 OFF의 동작을 설명하지 않는다. 양쪽에 같은 피어 목록을 넣는 처방만 있어 "한쪽만으로 충분한가"라는 질문에 답하지 않는다. 특정 RMW·VPN 전제라 일반 Docker 브리지 상황에 바로 대입하기 어렵다.
   - 이 글이 더할 것: 공식 표상 양쪽이 OFF만 아니면 한쪽 정적 피어로 O라는 최소 조건, 그리고 OFF와 정적 피어 조합은 rcl이 피어를 무시한다는 코드 근거.
4. https://github.com/michaelchi08/ros2_docker_examples (영어, DominikN/ros2_docker_examples의 포크, 2021, Foxy)
   - 그 글이 다루는 것: 단일 기계·단일 컨테이너·두 컨테이너(docker-compose)·서로 다른 네트워크 두 기계(VPN + Cyclone DDS XML `<Peers>`) 네 시나리오를 같은 코드로 보여 준다.
   - 빠졌거나 틀린 것: 다른 네트워크 시나리오에서 한쪽에만 피어를 넣었을 때 동작하지 않아 양쪽에 넣었다고 적지만, 이는 Foxy·Cyclone XML·VPN 조건의 관측이며 Iron 이후 환경변수 표와는 다른 메커니즘이다. 발견 범위 변수는 다루지 않는다.
   - 이 글이 더할 것: Iron 이후 표준 환경변수 기준의 판정표와, 이 저장소의 "양쪽 필요" 관측이 공식 표의 "한쪽 충분"과 왜 단순 비교되면 안 되는지(다른 RMW·설정 방식·NAT/VPN 조건) 경계를 밝힘.
5. https://github.com/eProsima/Fast-DDS/issues/5396 (영어 이슈 스레드, 2024-11, Humble, Fast DDS 2.6.8)
   - 그 글이 다루는 것: 다른 컨테이너의 토픽이 `ros2 topic list`에는 보이지만 `ros2 topic echo`는 아무것도 받지 못하는 증상. 메인테이너 답변: `--net=host --ipc=host`에서 SHM을 쓰려다 `/dev/shm` 권한(root vs 사용자) 문제로 실패, 해결책은 같은 사용자·root 실행·`FASTDDS_BUILTIN_TRANSPORTS=UDPv4`·두 옵션 미사용. 다른 사용자는 compose에 `ipc: host`가 빠져 있었던 것이 원인.
   - 빠졌거나 틀린 것: 이슈 스레드라 발견 범위 문제와의 구분, 공식 표와의 관계를 정리하지 않는다.
   - 이 글이 더할 것: "보이는데 안 온다 → 전송 계층(SHM) 의심" / "안 보인다 → 발견 범위 표"라는 분기의 앞 갈래 근거로 사용.

- 실측으로 더할 것: 하네스 실험은 단일 컨테이너·`--network none` 환경이므로 **같은 호스트 표의 판정과 rcl 경고 문구**만 실측할 수 있다(아래 `## 실험 설계 시 주의`). 다른 호스트 표·컨테이너 간 동작은 실측하지 않으며, 본문에서 실측처럼 쓰지 않는다.
