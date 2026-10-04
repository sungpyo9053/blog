# 경쟁 글 대비 차별점: ros2-distro-choice-iron-humble-remaining-support-months

같은 질문으로 검색되는 글을 직접 읽었다(2026-10-04). 한국어 검색에서는 이 질문(배포판을 지원 기간으로 고르기)을 직접 다룬 글을 찾지 못했다. 설치 튜토리얼과 중국어 글만 나왔다. 아래 4개는 영어 자료다.

1. **Robotics Stack Exchange — "Which ROS2 Distro? Iron or Humble?"** (2023-11-30, CC BY-SA 4.0). 원문 페이지는 이 runner에서 HTTP 403이어서 [Stack Exchange 공개 API](https://api.stackexchange.com/2.3/questions/105772?site=robotics&filter=withbody)로 질문과 답변 본문을 확인했다.
   - 다루는 것: Ubuntu 22.04 사용자의 Iron/Humble 선택. 채택 답변은 Humble이 LTS라 안정 패키지·지원이 더 많을 수 있다는 한 줄.
   - 빠진 것: 답이 시점에 따라 바뀐다는 점(2026년 10월에는 Humble도 7개월 남음), 프로젝트 기간과의 비교, 이후 배포판(Jazzy·Kilted·Lyrical), 배포판 간 통신 비보장, OS 업그레이드와의 연결.
   - 이 글이 더할 것: 같은 질문을 2026년 10월 날짜로 다시 계산한 표, Iron −22 반례, 판정 부등식.
   - 주의: 페이지가 runner에서 403이므로 본문 하이퍼링크로 넣지 말 것. 질문 제목과 작성 시점만 텍스트로 언급하고 문장을 복제하지 않는다.
2. **QuantaraCore — "ROS2 Jazzy vs Humble: Which Distro Should You Use?"** (2026-06-22, https://quantaracore.in/blog/ros2-jazzy-vs-humble)
   - 다루는 것: Humble/Jazzy 비교, "배포판과 OS를 분리해 고를 수 없다"는 Ubuntu 결합, 생태계 성숙도, 새 하드웨어면 Jazzy라는 결론.
   - 빠진 것/문제: Humble의 EOL 날짜를 "phasing out"으로만 적고 구체 날짜가 없다. Iron·Kilted·Lyrical·Rolling을 다루지 않는다. 배포판 간 통신 문제가 없다. 남은 개월 계산이 없다. 패키지 이식률·"새 하드웨어가 Jazzy 우선" 같은 주장에 출처가 없다.
   - 이 글이 더할 것: 다섯 배포판 + 예정 Makoa의 공식 날짜와 남은 개월, 프로젝트 기간으로 판정하는 식, 공식 문서의 통신 비보장 문장.
3. **IoT Digital Twin PLM — "ROS 2 Jazzy Jalisco: Migration Guide from Humble (2026)"** (2026-04-27, https://iotdigitaltwinplm.com/ros2-jazzy-jalisco-migration-guide-from-humble-2026/)
   - 다루는 것: Humble→Jazzy 마이그레이션 절차, DDS 선택, 단계별 롤아웃 일정, Iron을 건너뛰라는 조언.
   - 틀리거나 근거 없는 것: (a) "A robot deployed in Q4 2026 will have support until Q4 2029"라고 쓰지만, 같은 글이 밝힌 Jazzy EOL은 May 2029다. Q4 2026에서 May 2029까지는 약 31개월로, Q4 2029보다 짧다(우리 계산 31개월과 대조). (b) "Humble enters security-fix-only mode in May 2026"은 공식 Releases·REP 2000에서 확인되지 않는 단계 구분이며 출처가 없다. (c) "roughly 65% of production ROS 2 systems"에 출처가 없다. (d) Iron EOL을 "Nov 2024"로 적는데, 이는 REP 2000 표기와는 같지만 공식 Releases 표(2024-12-04)와 다르다. Kilted·Lyrical은 언급하지 않는다.
   - 이 글이 더할 것: 남은 개월 계산을 식과 검산으로 보여 그런 산술 오류를 독자가 직접 잡을 수 있게 한다. 근거 없는 지원 단계 주장을 쓰지 않는다.
   - 본문에서 이 글을 직접 비판·링크할 필요는 없다. 독자가 흔히 보게 될 오류 유형으로만 일반화해 언급하는 편이 낫다(작성자 판단).
4. **endoflife.date — ROS 2** (https://endoflife.date/ros-2)
   - 다루는 것: 배포판별 출시일·EOL 표. 저장소 정의 파일에 따르면 docs.ros.org Releases 표를 출처로 한다(자동 수집 비활성, 수동 갱신).
   - 빠진 것/주의: 공식 표가 월까지만 적은 EOL을 그 달의 마지막 날(Humble 2027-05-31, Jazzy 2029-05-31, Kilted 2026-12-31, Lyrical 2031-05-31)로 채운다. 공식 문서에 없는 일 단위 날짜다. 프로젝트 기간 판정, OS Tier 결합, 배포판 간 통신 문제는 다루지 않는다.
   - 이 글이 더할 것: 월 단위 근사의 한계를 명시하고, 날짜 표를 판단 절차로 바꾼다.

**판정:** 공식 표 기반의 남은 개월·판정식·OS Tier 결합·통신 통일 기준을 한 흐름으로 제공하는 글은 확인한 경쟁 글에 없다. 이 글이 더하는 것은 실측 실험이 아니라 **공식 날짜에 대한 검산된 산술과 출처 간 불일치 공개**다. 이 구분을 본문에서 정확히 밝히는 조건으로 READY다.
