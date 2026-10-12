제목: ROS 2 노드가 Docker 너머에서 안 보일 때 — ROS_AUTOMATIC_DISCOVERY_RANGE 36칸 직접 돌려 봤습니다
같은 PC에서는 잘 되던 talker·listener가 Docker 컨테이너나 다른 PC로 나누면 ros2 topic list에서 사라질 때가 있습니다. Iron 이후 배포판이라면 먼저 볼 것은 ROS_AUTOMATIC_DISCOVERY_RANGE와 ROS_STATIC_PEERS 두 환경변수입니다.

■ 먼저 증상부터 가르기
- 상대 노드가 ros2 topic list --no-daemon에 아예 없다 → 발견 단계 문제 (이 글의 주제)
- 목록에는 있는데 echo가 조용하다 → 발견은 됐고 전송 문제 (Fast DDS 공유 메모리, --ipc=host 등)

■ 공식 표를 세어 보면
- 같은 호스트: 36칸 중 16칸 통신
- 다른 호스트: 13칸만 통신
- 빠지는 3칸에는 모두 "정적 피어 없는 LOCALHOST"가 끼어 있습니다
- 정리하면: 다른 호스트에서는 양쪽 다 OFF가 아니고, 한쪽이라도 상대 주소를 ROS_STATIC_PEERS에 넣었거나 양쪽 다 SUBNET이어야 합니다

■ Jazzy 컨테이너에서 같은 호스트 36칸을 5번 재현
- 5번 모두 16칸 통신, 공식 표와 칸 단위로 일치
- 통신되는 칸은 0.42초 안에 서로 발견·첫 메시지 수신

■ 실무 함정 두 가지 (실측으로 확인)
- OFF에 넣은 ROS_STATIC_PEERS는 경고 없이 버려집니다
- 값을 소문자 subnet으로 쓰면 LOCALHOST로 처리됩니다. 같은 PC에선 멀쩡해서 다른 PC로 나눌 때 처음 터집니다
- 오래된 .bashrc의 ROS_LOCALHOST_ONLY=1도 새 변수를 무시하게 만듭니다

Humble·Foxy에는 이 변수가 없습니다. 다른 호스트 표는 문서와 소스 코드로 판정했고, 재현 스크립트와 5회 원본 출력, 코드 근거는 원문에 정리했습니다.
원문: https://huntlab.app/ros2-docker-discovery-range-static-peers-combinations/

#ROS2 #Docker #DDS #FastDDS #로봇개발 #ROS2Jazzy #네트워크

<!-- 게시: 2026-10-13 https://blog.naver.com/sungpyo9053/224439765394 -->
