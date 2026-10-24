# 경쟁 글 대비 차별점: ros2-apt-failed-to-fetch-404-apt-update-before-after

같은 질문으로 검색되는 상위 문서를 직접 읽었다(영어 5, 한국어 1). 정리된 해설 글은 찾지 못했고 대부분 Q&A·이슈 스레드다.

1. https://robotics.stackexchange.com/questions/104189/failed-to-fetch-http-packages-ros-org-ros2-404-not-found (runner에서 403. 본문은 https://api.stackexchange.com/2.3/questions/104189?site=robotics&filter=withbody 와 answers API로 확인)
   - 다루는 것: Ubuntu 22.04 + Humble에서 `apt upgrade` 중 `ros-humble-rviz2_11.2.7-1jammy.20230814…deb 404`. 채택 답(점수 4)은 "apt update를 하라. 이 파일은 서버에 없고 더 늦은 빌드 날짜 20230822 버전이 있다". 질문자의 해결은 `sudo rm /var/lib/apt/lists/*`. 2024년 답변은 `rm /var/lib/apt/lists/*ros*` 후 update/upgrade를 권하고 "ROS는 최신 버전만 게시하는 듯"이라고 추측한다.
   - 빠졌거나 틀린 것: 질문자의 update 출력에서 packages.ros.org ros2 jammy InRelease 줄이 `Hit:9`로 찍혔는데, 채택 답은 이 점을 설명하지 않는다. "최신 버전만 게시"는 추측으로 남아 공식 근거가 없다. `apt clean`이 왜 효과 없었는지 설명이 없다. 원인을 "메타데이터 미게시"로 단정한 답은 근거가 없다.
   - 이 글이 더할 것: 공식 snapshot 문서의 "sync 때 옛 버전 삭제" 문장으로 추측을 근거로 바꾼다. apt 소스로 `Hit`의 뜻과 "old ones used instead" 경로를 설명한다. 하네스 실측으로 update가 실패 개수를 0으로 만드는 조건과 못 만드는 조건을 같은 오프라인 저장소에서 보여 준다.
2. https://github.com/ros-drivers/usb_cam/issues/334
   - 다루는 것: Iron에서 apt가 `ros-iron-usb-cam_0.8.0-1jammy.20240419…deb`를 요청했는데 서버에는 0.8.1만 있어 404가 났다. `Err:1 … 404  Not Found`와 `E: Failed to fetch …`, `E: Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?` 원문 로그가 있다.
   - 빠졌거나 틀린 것: 관리자가 "로컬 네트워크 문제 같다"며 닫았다. 버전 불일치(목록이 아는 버전 ≠ 서버 보유 버전)라는 로그상의 단서와 맞지 않는 결론이고 근거 제시가 없다. 목록 갱신 여부 확인 절차가 없다.
   - 이 글이 더할 것: 로그 속 버전 문자열과 서버 보유 버전의 차이를 "목록이 낡았다"는 가설의 관측 증거로 읽는 법, 그리고 갱신 전후 실패 개수로 그 가설을 판정하는 규칙.
3. https://github.com/ros/diagnostics/issues/151
   - 다루는 것: Foxy `ros-foxy-diagnostic-updater_2.0.2-1focal.20200624…deb` 404. 관리자가 공식 Docker 이미지에서 재현하지 못했고 "apt-get update를 해 봤나"라고 물은 뒤 닫았다.
   - 빠졌거나 틀린 것: 질문자가 update 했는지, 그 출력이 어땠는지 확인하지 않은 채 끝났다. "로컬 설정 문제"라고만 했다.
   - 이 글이 더할 것: "깨끗한 컨테이너에서는 된다"가 왜 캐시 가설과 맞는 관측인지 설명한다(새 컨테이너는 update부터 한다). 독자가 자기 기계에서 같은 판정을 하도록 개수 비교 절차를 준다.
4. https://robotics.stackexchange.com/questions/91952/apt-update-fails-cannot-install-pkgs-key-not-working (runner에서 403. 본문은 https://api.stackexchange.com/2.3/questions/91952?site=robotics&filter=withbody 와 answers API로 확인)
   - 다루는 것: 2019년 ROS 저장소 키 교체 때 `apt update`에서 `NO_PUBKEY F42ED6FBAB17C654`와 `W: Some index files failed to download. They have been ignored, or old ones used instead.`가 나고, 설치 때 `.deb` 404가 난 사례. 해결은 새 키 등록 후 `apt clean && apt update`.
   - 빠졌거나 틀린 것: 키 교체 대응 글이라 "update가 실패하면 옛 목록이 쓰여 설치 단계에서 404가 난다"는 연결 원리를 따로 설명하지 않는다. 2019년 `apt-key` 기반 절차는 현재 공식 순서(ros2-apt-source)와 다르다.
   - 이 글이 더할 것: 이 사례를 "update가 돌았지만 목록을 못 바꾼 기각 사례"의 실제 예로 쓴다. apt 소스의 "old ones used instead" 경로와 연결한다. 서명 문제 자체는 HuntLab 기존 글로 연결한다.
5. https://robotics.stackexchange.com/questions/93647/404-not-found-ip-when-try-to-install-any-ros-kinetic-package (answers API https://api.stackexchange.com/2.3/questions/93647/answers?site=robotics&filter=withbody 로 확인)
   - 다루는 것: Kinetic. 질문자는 "apt-get update를 해도 ROS 저장소가 갱신되지 않는다"고 썼다. 채택 답은 "update 했나? 2019-03 빌드를 찾고 있다"였고 실제 해결은 키 교체 글이었다. 다른 사용자는 "sudo apt update로 풀렸다"고 댓글을 남겼다.
   - 빠졌거나 틀린 것: 같은 증상에 원인이 둘(목록만 낡음 / update 실패)인데 구분하는 기준이 없다.
   - 이 글이 더할 것: update 출력의 해당 저장소 줄(Get/Hit/Err)과 `W:`/`E:` 줄을 먼저 보고, 갱신 후 실패 개수로 두 원인을 가르는 판정 표.
6. https://extrememanual.net/26688 (한국어, 2018-04-18)
   - 다루는 것: 지원이 끝난 우분투(zesty)에서 `apt-get update`가 `Release 404 Not Found`로 실패할 때 old-releases 저장소로 바꾸는 방법.
   - 빠졌거나 틀린 것: ROS와 무관하다. 404가 **update 단계의 Release 파일**에서 나는 증상이라 이 글의 질문(설치 단계의 `.deb` 404)과 다르다. 독자가 두 증상을 섞을 위험이 있다.
   - 이 글이 더할 것: "404가 어느 줄에서 났는가"(update의 `Release`/`InRelease` vs install의 `pool/…/*.deb`)로 증상을 먼저 가르는 기준. 앞의 경우는 코드네임·배포판 지원 문제 후보이고(예: SE 110750 mantic 사례), 뒤의 경우가 이 글의 캐시 가설 대상이다.
