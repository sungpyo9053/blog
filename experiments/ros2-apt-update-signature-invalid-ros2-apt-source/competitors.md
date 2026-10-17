# 경쟁 글 대비 차별점: ros2-apt-update-signature-invalid-ros2-apt-source

1. https://techoverflow.net/2025/06/09/how-to-fix-expkeysig-f42ed6fbab17c654-open-robotics/ (Uli Köhler, 2025-06-09, EN)
   - 다루는 것: `EXPKEYSIG F42ED6FBAB17C654 Open Robotics` 출력, `ros.key`를 `/usr/share/keyrings/ros-archive-keyring.gpg`로 다시 받는 명령, `sudo apt update`.
   - 빠진 것: 원인 설명이 없다. ros2-apt-source가 이미 공식 절차가 된 뒤(2025-05-28)의 글인데 언급하지 않는다. 키 ID가 그대로라는 점, 다음 만료일, 여러 기계 운용, 이전 시 옛 파일 충돌도 없다. 이 방식대로면 2030-06-01에 같은 작업을 반복한다.
   - 이 글이 더할 것: 키 이력(2021/2025/2030) 파싱 결과, 패키지가 소유하는 파일 목록, n·k·m 수작업 계산. Experiment 단계의 오프라인 apt 측정(충돌 출력과 종료 코드, 만료 재현 시 종료 코드)도 더한다.
2. https://varhowto.com/fix-ros-package-repo-signature-verification-error/ (VarHowto Editor, 2021-06-03, EN)
   - 다루는 것: 2021년 5월 만료, 키 생성 도구의 기본 2년 만료라는 설명, ROS 1 `apt-key add`와 ROS 2 `ros.key` 재다운로드, `sudo apt update` 확인.
   - 빠지거나 낡은 것: ROS 1용으로 이제 권장되지 않는 `apt-key add`를 경고 없이 제시한다. 2025년 이후 패키지 방식이 없다. 만료일 연장이 반복된다는 사실(2025, 2030)도 없다.
   - 이 글이 더할 것: 현재 공식 절차와 옛 절차의 파일 단위 비교, 재발 조건 계산, 측정된 충돌·만료 출력.
3. https://hybridego.net/2366 (2021-05-31, KO)
   - 다루는 것: `NO_PUBKEY F42ED6FBAB17C654` 한국어 출력, `apt-key list`, `apt-key del F42ED6FBAB17C654`, `curl http://repo.ros2.org/repos.key | sudo apt-key add -`.
   - 빠지거나 틀린 것: EXPKEYSIG와 NO_PUBKEY를 구분하지 않는다. HTTP로 키를 받는다(RSE에서 gvdhoorn이 "not a secure way"라고 지적한 방식). 전역 `apt-key` 키링에 넣기 때문에 `signed-by` 방식과 섞인다. ros2-apt-source가 없다.
   - 이 글이 더할 것: 두 메시지의 원인 구분, HTTPS·`Signed-By` 기반 현재 절차, 이전 후 확인 순서.
4. https://velog.io/@gaebalsebal/ROS2-Humble-%EC%84%A4%EC%B9%98-%EB%B0%8F-%EC%84%A4%EC%B9%98-%ED%99%95%EC%9D%B8-%EC%82%AD%EC%A0%9C (2024-06-04, KO)
   - 다루는 것: Humble 설치 시 옛 방식(`ros.key` → `ros-archive-keyring.gpg`, `ros2.list` echo)과 삭제 시 `ros2.list` 제거.
   - 빠진 것: 키 만료에 대한 언급이 없다. 이 절차로 설치한 기계는 2025-06-01에 만료 오류를 겪는 구성이었다. 삭제 시 옛 키 파일 제거도 언급하지 않는다.
   - 이 글이 더할 것: 이런 튜토리얼로 설치한 독자가 지금 남아 있는 파일(`ros2.list`, `ros-archive-keyring.gpg`)을 어떻게 정리하고 패키지 방식으로 옮기는지, 그 이득을 언제 얻는지.
5. Robotics Stack Exchange 99143 수락 답변(gvdhoorn, 2021-05-29, EN; 원문 확인은 [API](https://api.stackexchange.com/2.3/questions/99143?site=robotics&filter=withbody))
   - 다루는 것: 정확한 오류 출력, Discourse 사고 보고 인용, ROS 1/ROS 2 명령, Docker 캐시 주의.
   - 빠진 것: 2021년 시점 답이라 패키지 방식과 2025·2030 만료를 다루지 않는다. 일반 독자를 위한 서명·만료 원리 설명이 없다.
   - 이 글이 더할 것: 같은 오류가 4년 주기로 반복된 이력과, 반복을 줄이는 현재 공식 단계의 조건부 이득 계산.

판정: 경쟁 글은 모두 "지금 한 번 고치는 명령"에 머문다. 이 글은 원리(같은 키 ID, 만료일 연장)와 공식 단계가 바꾸는 소유 관계, 기계 대수 기반 판단, 이전 시 충돌 위험을 더할 수 있다. 실측은 Experiment 단계 결과로 보강된다. 더할 것이 있으므로 INSUFFICIENT가 아니다.
