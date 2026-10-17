# 경쟁 글 대비 차별점: ros2-apt-update-signature-invalid-ros2-apt-source

같은 질문으로 검색되는 상위 글을 직접 열어 확인했다(2026-10-17).

1. [TechOverflow — How to fix APT EXPKEYSIG F42ED6FBAB17C654 Open Robotics](https://techoverflow.net/2025/06/09/how-to-fix-expkeysig-f42ed6fbab17c654-open-robotics/) (영어, 2025-06-09)
   - 다루는 것: EXPKEYSIG 오류 출력, `sudo curl -sSL …/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg` 후 `sudo apt update`.
   - 빠진 것: 만료 원인과 반복 이력, `ros2-apt-source`, 옛 `ros2.list` 처리, 충돌 오류, 키 파일 경로가 환경마다 다를 수 있다는 점(Docker 이미지는 `ros2-latest-archive-keyring.gpg` — Discourse #23·#32), 이후 확인 기준이 없다. 다음 만료 때 똑같은 수작업을 반복해야 한다는 점도 말하지 않는다.
   - 이 글이 더할 것: 수동 갱신(이 글의 방식 A)과 패키지 이행(방식 B)의 수작업 비교식과 검산 사례. 이행 시 충돌 판정과 지울 파일.
2. [Hybridego — ROS2 apt update key 문제](https://hybridego.net/2366) (한국어, 2021-05-31)
   - 다루는 것: `NO_PUBKEY F42ED6FBAB17C654` 출력, `apt-key list`, `sudo apt-key del F42ED6FBAB17C654`, `curl http://repo.ros2.org/repos.key | sudo apt-key add -`.
   - 빠지거나 틀린 것: 2021 공식 처방(`/usr/share/keyrings/ros-archive-keyring.gpg`에 저장)과 다른 `apt-key` 경로를 쓴다. `apt-key`는 Debian/Ubuntu 매뉴얼에서 deprecated다("Debian 11과 Ubuntu 22.04에서 마지막으로 제공"). 키를 HTTP로 내려받는다(RSE에서 gvdhoorn이 비슷한 HTTP 명령의 보안 문제를 지적). 원인 설명, 이행 후 확인, ros2-apt-source가 없다(2021년 글이라 당연하다).
   - 이 글이 더할 것: 한국어 독자에게 EXPKEYSIG/NO_PUBKEY/Signed-By 충돌을 구분하는 표. 2025년 이후 공식 경로와 지금 남아 있는 옛 파일의 처리.
3. [Zenn (Tiryoh) — 2025年6月以降ROS環境でapt-get updateするときにGPG errorが発生する場合の対処方法](https://zenn.dev/tiryoh/articles/2025-06-02-ros-noetic-apt-get-update) (일본어, 2025-06-02 작성·06-10 갱신)
   - 다루는 것: 2019년부터 쓰던 공개 키가 2025-06-01에 만료됐다는 설명, apt-key 방식과 Signed-By 방식별 갱신 명령, Docker 이미지의 `ros2.sources`와 충돌 사례, Dockerfile 예, `gpg --show-keys` 확인과 2030년까지 유효하다는 언급.
   - 빠진 것: 여러 대를 관리할 때 수동 갱신과 패키지 이행 중 무엇이 수작업이 적은지 판단하는 기준. 패키지 방식의 "자동 갱신"이 만료 전 업그레이드를 전제한다는 조건. 이 글은 일본어이며 한국어 동급 자료는 확인하지 못했다.
   - 이 글이 더할 것: n×k 대 n×1 비교식과 경계·반례 사례(검산 기록 있음). 오프라인 로봇 PC 같은 예외를 독자가 직접 셀 수 있게 하는 조건 명시. 패키지 정의 파일(rules L26-L37)로 22.04 이상에서 키가 내장되는 이유를 직접 확인시키는 설명.
4. (참고, 제외) iThome 글 「apt update噴錯誤？ROS GPG 金鑰過期解決方法」(ithelp.ithome.com.tw, 링크 생략) — 검색 상위였으나 403으로 원문을 읽지 못해 대조·인용하지 않는다.

판정: 경쟁 글 3개는 모두 "지금 오류를 푸는 명령"에서 끝난다. 이 글은 실측 apt 결과를 더하지 않는다(미실행). 대신 검산된 산술 모델과 1차 자료로 고정한 "반복 이력·관리 주체·이행 시 충돌·자동 갱신의 전제"를 더한다. foundation_concept 계약의 고유 가치로 충분하다고 판단한다(READY). 단, 본문이 이 차별점을 "HuntLab이 apt로 확인했다"로 바꿔 쓰면 근거가 사라진다.
