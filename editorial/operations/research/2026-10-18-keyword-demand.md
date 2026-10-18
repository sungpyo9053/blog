# 검색 수요 조사 (2026-10-18)

데이터: GSC 전체 기간(07-27~10-17) 실측 + 구글 자동완성(ko·en)·네이버 자동완성. 네이버 검색광고 월간 검색수는 키가 없어 못 씀 → 자동완성 개수를 수요 대리 지표로만 쓴다(검색량 숫자 아님).

## GSC 실측 (사이트 전체)
- 노출 상위는 전부 410 처리된 옛 생활 글: 멜론 이용권 1,095(7.7위)·유가 315·등본 231·KBO 214·청약 209. 새 도메인이어도 대중 검색어는 1페이지(6~10위)에 붙었다.
- 지금 살아 있는 글 최고: EN ros2 command not found 51노출. KO ROS 글은 거의 0.
- 결론: 문제는 색인이 아니라 주제 수요. 10/13 결정(영어 검색 유입)대로 EN을 지표로 유지.

## 자동완성 (제안 수, 최대 10)
| 시드 | 구글 ko | 네이버 | 구글 en | 실측 가능 |
|---|---|---|---|---|
| 로컬 llm 사양 / ollama 사양 | 10 / 6 | 1 / 0 | ollama ram requirements 10, how much ram for local llm 10 | **이미 실측(#975·#976)** |
| 맥미니 m4 llm | 10 | 0 | — | 불가(기기 없음, 리뷰 금지) |
| 개발용 노트북 추천 | 10 | 0 | — | 불가(실측 아님) |
| 도커 램 | 5 | 0 | docker desktop ram usage 10 | 가능(리눅스 엔진·스택별 메모리) |
| 라즈베리파이 5 8gb | 4 | 3 | — | 불가(기기 없음) |
| 노트북 램 16gb 32gb / 개발자 16 vs 32 | 2 / 2 | 0 | 16gb vs 32gb programming 3 | 기존 실측 모음(허브) |
| 안드로이드 스튜디오 램 | 2 | 0 | is 16gb ram enough for android studio 4 | 가능(Gradle 빌드만, IDE 제외) |
| colcon build out of memory | — | — | 1 | 이미 실측 |

## 결정
- 5번 블록: 로컬 LLM 글 제목·첫 문단을 "로컬 LLM 사양 / Ollama 최소 사양"(KO), "Ollama RAM requirements: how much RAM for a local LLM"(EN)에 맞춘다.
- 다음 장비 글 3개(이 순서):
  1. **Docker 메모리 사용량 실측** — 엔진 자체 + Postgres·Redis·Node 개발 스택을 컨테이너별 memory.peak로. EN "docker ram usage" 수요가 가장 큼.
  2. **개발용 RAM 16GB vs 32GB 실측표(허브)** — LLM·MoveIt 2·Nav2·Docker·Gradle 결과를 한 표로. 5-b 허브와 같은 글.
  3. **Android Gradle 빌드 RAM — 16GB면 충분한가** — 샘플 앱 빌드를 4/8/16GB 상한으로. IDE 메모리는 측정 범위 밖이라고 명시.
- 정보 이득 게이트(각 글): 상위 결과는 공식 최소 사양·추정치뿐 → 우리 것은 메모리 상한별 성공/OOM 실측. 착수 전 상위 3개를 읽고 한 문장으로 재확인.
