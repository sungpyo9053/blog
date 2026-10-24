# 실험 계획: 갱신 전후 `E: Failed to fetch` 개수로 "목록이 낡았다" 가설 판정

## 질문

packages.ros.org의 `pool/…/*.deb`에서 `E: Failed to fetch … 404`가 날 때 `apt update`를 다시 하면
풀릴까? 풀린다면 어떤 조건에서이고, `apt update`를 했는데도 그대로인 조건은 무엇이며
출력의 어느 줄로 둘을 가를 수 있을까?

## 모델(통제 조건) — packages.ros.org 측정이 아님

- 하네스 컨테이너(`ros:jazzy-ros-base`, `--network none`) 안에서 Python 표준 라이브러리
  `http.server`를 `127.0.0.1`에 띄우고, 그 위에 flat apt 저장소(`deb [trusted=yes] http://127.0.0.1:<port>/<시나리오>/ ./`)를 만든다.
- 패키지는 `dpkg-deb --build`로 만든 빈 더미 `.deb`(Architecture: all, 의존성 없음)다. 시나리오마다
  이름 접두어가 다르다(`hla-01`…`hla-20`, `hlb-…` 등). 경로는 packages.ros.org처럼 `pool/main/<첫글자>/<이름>/`이다.
- 서버 쪽 "sync"는 ROS snapshot 문서의 설명을 흉내 낸다. 5개 패키지를 새 버전으로 바꾸고 **옛 `.deb`를 지운다**.
  색인은 `dpkg-scanpackages`로 `Packages`/`Packages.gz`를 만들고, `Release`(SHA256 목록·Date)는 스크립트가 직접 쓴다.
  `Release`의 mtime과 Date는 세대마다 10초씩 늘린다. 같은 초 안에 다시 쓴 파일이 `304`(Hit)로 잘못 응답되는 것을 막기 위해서다.
- apt는 시나리오 전용 sources·lists·cache만 보게 한다(`Dir::Etc::sourcelist`, `Dir::Etc::sourceparts`,
  `Dir::State::Lists`, `Dir::Cache`). 이미지에 있는 Ubuntu/ROS 소스는 네트워크가 없어 오류를 내므로 격리한다.
  `Acquire::Languages=none`, `APT::Sandbox::User=root`(tmpfs 디렉터리 권한 문제 회피)를 쓴다. 명령은 스크립트 안정성을 위해
  `apt-get`이며 `DEBIAN_FRONTEND=noninteractive`, `LC_ALL=C`를 준다. dpkg 상태 DB는 컨테이너의 실제 DB를 쓴다(실행 후 컨테이너는 폐기).
- 설정값: 패키지 N=20개, sync로 교체 k=5개. 실험자가 고른 값이며 실제 ROS 저장소를 대표하지 않는다.
- 이 실험은 패키지 관리 실험이다. 로봇·시뮬레이터·ROS 노드를 실행하지 않는다. ROS Python 라이브러리(rclpy 등)는
  질문과 관계가 없어 쓰지 않았고, 이미지에 이미 있는 apt-get·dpkg-deb·dpkg-scanpackages·dpkg-query와 Python 표준 라이브러리만 쓴다.

## 시나리오와 예측값(research.md의 산술 예제·공식 소스 기준, 실행 전에 적음)

| 시나리오 | 절차 | 예측 |
|---|---|---|
| A 목록만 낡음(가설 지지) | update → sync(5개 1.0→2.0, 1.0 삭제) → 갱신 없이 install 20개 → update → install 20개 | 갱신 전 `E: Failed to fetch` 5, 설치 0(하나라도 못 받으면 설치 단계 전체 중단, private-install.cc), 종료 코드 100. update의 저장소 Release 줄 `Get`. 갱신 후 실패 0, 설치 20. 설명된 실패 비율 (5−0)/5 = 1 |
| B upgrade를 update보다 먼저(원 질문 형태) | 출발 상태: 20개 1.0 설치. 서버 5개 1.1 게시 → update(목록이 1.1을 앎) → 다음 sync로 1.1→1.2, 1.1 삭제 → 갱신 없이 upgrade → update → upgrade | 갱신 전 upgrade 실패 5, 업그레이드 0(20개 모두 1.0 유지), 종료 코드 100. 갱신 후 실패 0, 5개 1.2·15개 1.0. 비율 1 |
| C update가 색인을 못 받음(기각) | A와 같되 두 번째 update 때 서버가 `Packages`·`Packages.gz`만 404로 응답 | update 종료 코드 100, update 출력에 `Failed to fetch …/Packages` 1줄 이상과 "old ones used instead". 갱신 후 install 실패 5 그대로, 비율 (5−5)/5 = 0 |
| D 서버 색인이 그대로(Hit, 기각) | pool만 sync하고 색인은 옛 것을 계속 제공 → update | update의 Release 줄 `Hit`(서버 304), 종료 코드 0. 갱신 후 install 실패 5 그대로, 비율 0 |
| E 경계(sync 없음) | update → install | 실패 0, 설치 20 |
| F `--fix-missing`(갱신 없이) | A의 갱신 전 상태에서 `install --fix-missing` | research.md 기준: 못 받은 5개를 보류하고 15개를 처리할 것. 설치 15로 예측. 종료 코드는 문서로 예측하지 못함 |

C는 2019년 키 교체처럼 "update가 실패해 옛 목록이 쓰이는" 상황의 **유사 모델**이다. 서명 오류 자체를 재현하지 않는다.
D는 원 질문처럼 update 출력에 `Hit`이 찍혔는데도 404가 남는 관측을 재현하는 모델이다. 실제 원인(프록시·미러)을 재현한 것은 아니다.

## 무엇을 어떻게 재는가(모두 실행 중 측정)

각 측정 단계마다 JSON 한 줄을 출력한다. 준비 단계(최초 update, B의 기준 설치, 1.1 갱신)는 종료 코드가 0이고 실패가 없으면 출력하지 않는다.

- `exit_code`: apt-get 종료 코드(매뉴얼상 오류 시 100).
- `failed_fetch_lines`: stdout+stderr 합친 출력에서 `E: Failed to fetch`로 시작하는 줄 수. **판정 기준 지표**.
- `err_lines`: 진행 줄 `Err:N` 수(같은 실패의 다른 표시이므로 합산하지 않음).
- `unable_to_fetch_msg`: "Unable to fetch some archives" 문구 유무. `old_ones_used_msg`: "old ones used instead" 문구 유무.
- `release_line`: update 출력에서 이 저장소 `./ Release` 줄의 접두어(Get/Hit/Ign/Err).
- 서버 쪽 교차 확인: 그 단계 동안 서버가 실제로 응답한 `.deb` 404 수(`srv_404_deb`), 색인 404 수(`srv_404_index`),
  `.deb` 200 수(`srv_200_deb`), 304 수(`srv_304`).
- `installed`/`versions`: 단계 직후 `dpkg-query`로 센 실제 설치(`ii`) 패키지 수와 버전별 개수.
- `seconds`: 그 apt-get 호출의 경과 시간.
- 마지막 두 줄: 단계별 첫 `E:`/`W:` 줄 예시(`diagnostic_samples`)와 시나리오별 요약(`summary`).
  요약의 `explained_ratio = (갱신 전 실패 − 갱신 후 실패) / 갱신 전 실패`는 측정된 개수로 실행 중에 계산한다.
- 환경 줄: apt·dpkg·Python 버전, uid, 이미지의 packages.ros.org 소스 줄, 이미지 `/var/lib/apt/lists` 파일 수
  (새 컨테이너가 목록 없이 시작하는지 확인용).

404 사유 문구는 CPython `http.server`의 "File not found"다. packages.ros.org의 "Not Found"와 다르므로 문구가 아니라
`E: Failed to fetch` 줄 수로 센다.

## 시행착오(시험 실행에서 실제로 겪고 고친 점)

1. 첫 시험 실행에서 C의 두 번째 update가 종료 코드 0으로 끝나고 실패가 0이 됐다. 서버 차단 조건이 요청 경로
   `/hlc/Packages`로 시작하는지만 봤는데, apt는 flat 저장소에서 `/hlc/./Packages.gz`처럼 `./`가 들어간 경로를 요청했다.
   요청 경로를 `posixpath.normpath`로 정규화한 뒤 비교하게 고쳤다. 고친 뒤 C는 의도대로 색인 404와 "old ones used instead"를 냈다.
2. 단계 기록의 `command` 필드가 첫 인자만 써서 `apt-get -y`로 찍혔다. 하위 명령(update/upgrade/install)과 `--` 옵션을 쓰도록 고쳤다.
3. 하네스는 stdout의 마지막 8000자만 보관한다. 첫 버전은 출력이 이보다 길어 환경 줄과 A 시나리오가 잘렸다.
   키 이름을 줄이고, 문제없는 준비 단계 출력을 생략하고, 오류 줄 예시를 단계별 1줄(C의 update만 2줄)로 줄였다.
4. 첫 실행에서 F(`--fix-missing`)는 예측대로 15개를 설치했지만 종료 코드는 100이었고 "Unable to fetch some archives" 문구는 나오지 않았다.
   이것은 고친 점이 아니라 관측이며, 정식 결과는 results.json으로만 말한다.
