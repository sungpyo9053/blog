# 경쟁 글 대비 차별점: ros2-apt-update-signature-invalid-ros2-apt-source

모두 2026-10-18에 원문을 직접 열어 확인했다.

| URL | 그 글이 다루는 것 | 빠졌거나 틀린 것 | 이 글이 실측·검산으로 더할 것 |
| --- | --- | --- | --- |
| [Robotics SE 99143 (API 원문)](https://api.stackexchange.com/2.3/questions/99143?site=robotics&filter=withbody) (영어, 2021-05-29; 사람용 페이지는 runner에서 403) | 2021 만료 당시 실제 `EXPKEYSIG` 출력, 채택 답: ROS 2는 `ros.key`를 `ros-archive-keyring.gpg`로 다시 받기, Docker 캐시 주의 | 2021 시점이라 ros2-apt-source가 없다. 점수 13의 답은 HTTP로 키를 받아 `apt-key add`(질문자가 비보안 지적) | 같은 키가 2025·2030으로 다시 연장된 이력, 현재 공식 파일과 예전 파일의 이름·형식 차이, 이전 손익의 n·k 계산 |
| [techoverflow 2025-06-09](https://techoverflow.net/2025/06/09/how-to-fix-expkeysig-f42ed6fbab17c654-open-robotics/) (영어) | 오류 문구와 `ros.key` 덮어쓰기 한 줄 + `apt update` | 원인 설명 없음. ros2-apt-source, 다음 만료일, 예전 파일 정리, 확인 절차 언급 없음 | 그 한 줄이 2030-06-01에 다시 필요해지는 이유(키 만료일 직접 판독), 반복을 패키지 경로로 바꾸는 조건과 이전 후 점검 |
| [VarHowto](https://varhowto.com/fix-ros-package-repo-signature-verification-error/) (영어, 2021-06-03) | 2021 만료, 경고 4줄, ROS 1(`apt-key add`)/ROS 2(`ros.key`) 분기 | "키 생성 소프트웨어가 기본으로 2년 만료를 설정한다"는 일반화 — 2021 공지는 보안 사고 대응으로 2년 만료 키를 배포했다고만 말함. 이후 이력·패키지 방식 없음 | 공지 원문으로 원인 교정, 실제 키 파일에서 읽은 3개 시점 만료일 |
| [hybridego 2366](https://hybridego.net/2366) (한국어, 2021-05-31) | 한국어 `NO_PUBKEY F42ED6FBAB17C654` 출력, `apt-key del` 후 `http://repo.ros2.org/repos.key`를 `apt-key add` | 증상이 EXPKEYSIG가 아닌 NO_PUBKEY. 폐기 예정인 `apt-key`와 HTTP 키 다운로드. 원인 설명 없음 | EXPKEYSIG와 NO_PUBKEY 구분, `Signed-By`로 저장소별 키를 묶는 현재 방식과 파일 위치, 한국어 독자용 이전·점검 순서 |
| [zenn Tiryoh 2025-06-02](https://zenn.dev/tiryoh/articles/2025-06-02-ros-noetic-apt-get-update) (일본어, 참고) | `gpg --show-keys`로 만료 전후(2025-06-01 → 2030-06-01) 비교, apt-key 방식과 Signed-By 방식 분리, Docker 예시 | 해법이 수동 `ros.key` 재다운로드 중심. 패키지 이전의 손익·조건, 패키지가 예전 파일을 지우지 않는다는 점은 다루지 않음 | 2021을 포함한 3개 시점 이력, 패키지 버전별 키링 동일성, n·k 판단, Signed-By 충돌 근거와 실측 |

판정: 한국어·영어 상위 글 4개(+일본어 참고 1개)를 직접 읽었다. 이 글이 더할 것은 위 표의 마지막 열이며, 공식 문서 재요약을 넘는 고유 결론(키 동일성 이력, 패키지 내용 확인, 충돌 근거, n·k 손익 조건, 점검 함정)이 있다. INSUFFICIENT 아님.
