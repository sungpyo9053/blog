# 경쟁 글 대비 차별점: ros2-bag-jazzy-to-humble-readability-convert-vs-upgrade

1. https://robotics.stackexchange.com/questions/114246/convert-ros2-bags-from-jazzy-to-humble-arm-to-x86 (Stack Exchange API로 2026-11-19 확인, 원문 페이지는 runner에서 403)
   - 그 글이 다루는 것: RPi5 Jazzy MCAP → Humble x86에서 `bad conversion`. 답변 3개: NeonVector 변환기 링크(점수 0), Humble 컨테이너에서 다시 녹화(점수 1), Jazzy에서 sqlite3로 convert하면 info는 되고 재생은 실패(점수 1). 채택 답 없음.
   - 빠졌거나 틀린 것: 원인(QoS 필드 형식)을 설명한 답이 없다. "sqlite3로 convert하면 info가 고쳐진다"는 답은 소스와 맞지 않는다(convert 출력도 버전 9 시퀀스). 다시 녹화 방법은 실시간 재생이 필요해 시간이 bag 길이만큼 든다. 2026-11 Humble 수정·EOL 언급 없음.
   - 이 글이 더할 것: Jazzy 컨테이너에서 convert 전후 4칸의 metadata 버전·QoS 형식을 실측해 "convert로는 안 고쳐진다"를 파일로 보여 주고, 원인 한 줄과 경로별(폴더/파일, info/play) 결과를 정리한다.
2. https://github.com/NeonVector/rosbag_converter_jazzy2humble (README 커밋 db18570 확인, 2025-10-01 생성, 마지막 푸시 2026-05-12, Apache-2.0)
   - 그 글이 다루는 것: Jazzy와 Humble metadata.yaml의 차이 4가지(QoS 표기, custom_data·ros_distro, type_description_hash, 중복 QoS 블록)와 이를 고치는 C++ 프로그램. 15개 bag 성공 보고.
   - 빠졌거나 틀린 것: "sqlite3든 mcap이든 어떤 Jazzy bag도 Humble에서 읽을 수 없다"고 쓰지만 PR #2553 표에서는 저장 파일을 직접 `info`하면 성공한다. 차이가 생기는 이유(어느 코드 줄이 문자열·정수를 요구하는지)를 설명하지 않는다. `custom_data`·`ros_distro`·`type_description_hash`는 Humble 디코더가 조회하지 않는 키라 삭제가 필수인지 근거가 없다(코드 읽기 기준). 공식 수정(PR #2553)과 EOL 언급 없음.
   - 이 글이 더할 것: 핵심 원인이 QoS 필드 2단계(문자열 기대, 정수 기대)라는 것을 Humble 0.15.17 코드 줄로 짚고, Jazzy 파일에서 그 두 조건을 실측 판정한다. `transient_local` 정보가 우회법별로 남는지 비교한다.
3. https://github.com/ros2/rosbag2/issues/1895 (2025-01-13 개설, 2026-11-19 open)
   - 그 글이 다루는 것: 배포판 간 bag 변환 기능 요청. 유지보수자가 하위 호환만 보장된다고 답하고 `reindex`·`offered_qos_profiles: ""` 우회를 제시. 사용자 성공 보고, rosbags 도구 언급.
   - 빠졌거나 틀린 것: 스레드가 길고 우회법의 대가(`transient_local` 손실)는 스레드 안에서 언급되지 않는다(PR #2553에서 처음 명시). 2026-11 병합된 수정과 배포 상태가 반영되지 않았다.
   - 이 글이 더할 것: 스레드의 결론을 한국어로 정리하고, 우회법이 파일에서 무엇을 지우는지 실측, 수정의 배포 상태(apt 0.15.17)를 2026-11-19 기준으로 확인해 덧붙인다.
4. https://github.com/ros2/rosbag2/pull/2553 (2026-11-05 humble 병합)
   - 그 글이 다루는 것: 원인 두 가지, 부분 역이식, Humble에서 폴더·파일 × info·play 전후 표(가장 정확한 1차 실행 기록).
   - 빠졌거나 틀린 것: 개발자 대상 PR이라 사용자가 지금 apt로 받을 수 있는지, Humble EOL까지 남은 기간과 업그레이드 판단은 다루지 않는다.
   - 이 글이 더할 것: 이 표를 독자용 판단 기준으로 옮기고, 수정이 아직 apt에 없다는 확인, Jazzy 쪽 파일 형식 실측, EOL 기반 선택지 비교를 더한다.
