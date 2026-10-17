# 실험 계획: ros2-apt-source가 바꾸는 것과 키 변경 때 사람 손이 가는 횟수

## 질문

1. `ros:jazzy-ros-base` 이미지의 공식 `ros2-apt-source`가 실제로 소유하는 파일은 무엇일까?
   그 파일 안의 키 ID와 만료일은 무엇일까?
2. 옛 튜토리얼의 `ros2.list`를 남겨 두면 apt는 어떤 출력과 종료 코드를 낼까?
3. 저장소 키의 만료일만 늘리는 변경(2021·2025년 F42ED6FBAB17C654와 같은 방식)이 k번 일어날 때를 보자.
   기계 n대가 다시 정상으로 `apt update`를 하려면 사람이 몇 번 손대야 할까?
   수동 방식 A(손으로 만든 .list와 키 파일)와 패키지 방식 B(키를 담은 .deb가 sources 파일을 소유)를 비교한다.
4. 만료된 키로 `apt update`를 하면 종료 코드는 몇일까? 이 출력만 보고 실패를 알아챌 수 있을까?

## research.md 기준 예측값

- 수작업 모델은 A = n×k, B = n×1(이행 1회)이다. n=6, k=2이면 A=12, B=6이 된다(verification.json 사례).
- 옛 `ros2.list`와 패키지의 `ros2.sources`가 함께 있을 때를 보자.
  Signed-By 값이 다르면 `E: Conflicting values set for option Signed-By`와 `E: The list of sources could not be read.`가 나온다(Tiryoh#72 재현 출력).
- 키 ID는 연장 전후에 같다. 만료일만 바뀐다(2021 사고 보고, RSE 수락 답변).
- Noble용 `ros2.sources`에는 키 블록이 내장돼 있다(rules L26-L37). 키 ID는 F42ED6FBAB17C654다.
  공개 키 메타데이터의 만료일은 2030-06-01이다.
- B의 "변경당 0회"는 만료 전에 업그레이드를 받은 기계에만 성립한다.
  그 기간에 꺼져 있던 기계는 변경 때마다 수동 부트스트랩이 필요하다(편집자 해석).
  그래서 오프라인 기계 한 대의 예측은 1+k회다.
- 만료 키 상태에서 `apt update`의 종료 코드는 research.md에서 미검증이다.
  apt-get(8)은 "오류는 100"이라고 적는다.

## 무엇을 어떻게 재는가

환경은 하네스의 `ros:jazzy-ros-base` 컨테이너다(네트워크 없음, 1 CPU, 1 GiB, root).
이미지에 있는 apt 2.8, gpg/gpgv, dpkg, dpkg-deb와 Python 표준 라이브러리만 쓴다. 외부 패키지는 설치하지 않는다.

### 1부: 실제 이미지(읽기와 컨테이너 내부 임시 변경)

- `dpkg-query`/`dpkg -L ros2-apt-source`로 버전과 소유 파일을 읽는다.
  `/etc/apt/sources.list.d/ros2.sources`의 심볼릭 링크 대상과 Types·URIs·Suites를 읽는다.
- `ros2.sources`에 내장된 키 블록과 `/usr/share/keyrings/ros2-archive-keyring.gpg`를 `gpg --show-keys`로 연다.
  키 ID, 지문, 생성일, 만료일, 두 키의 지문이 같은지를 잰다.
- `/etc/apt/sources.list.d/ros2.list`에 세 가지 옛 형식을 하나씩 쓴다.
  ① 옛 튜토리얼 키링 경로, ② 패키지 키링 경로를 가리키는 signed-by, ③ signed-by 없는 apt-key 시절 형식이다.
  그 뒤 `apt-cache policy`의 종료 코드와 E/W 줄을 기록한다.
  apt-cache는 sources를 파싱하지만 네트워크는 쓰지 않는다. 마지막으로 파일을 지운 뒤에도 같은 항목을 잰다.

### 2부: 로컬 서명 저장소 시뮬레이션(실제 apt·gpgv 판정)

- gpg로 수명이 몇 초인 ed25519 서명 키를 만든다.
  `/tmp`에 `file:` 저장소(InRelease 서명, Packages 색인)를 만들고 키 패키지 `huntlab-apt-source`를 배포한다.
  이 패키지는 ros2-apt-source를 흉내 낸다. sources 파일에 키 블록을 내장하고, 키링을 넣고, `etc/apt/sources.list.d` 링크를 둔다.
- 기계 13대는 각자 독립된 apt 설정·색인·dpkg DB 디렉터리를 갖는다(`-o Dir::...`).
  구성은 A 6대, B 6대, 업그레이드 기간에 꺼져 있는 B 1대다. 모두 옛 튜토리얼 방식으로 설정한 상태에서 시작한다.
  이 초기 설정은 세지 않는다.
- 이행: B 7대에 .deb를 `dpkg -i`로 설치한다. 옛 .list를 지우기 전 `apt-get update` 결과(충돌 여부)를 기록한다.
  그다음 옛 .list와 키 파일을 지운다. 이 묶음을 사람 작업 1회로 센다.
- 변경 1회의 순서는 다음과 같다.
  ① 운영자가 키 만료일을 연장하고 새 공개 키와 새 버전 패키지를 배포한 뒤 저장소를 다시 서명한다.
  ② 켜져 있는 B 6대가 무인으로 `apt-get update` → `apt-get download` → `dpkg -i`를 수행한다. 이 작업은 사람 작업으로 세지 않는다.
  ③ 옛 키 사본의 만료 시각이 실제로 지날 때까지 기다린다.
  ④ 저장소를 다시 서명한다.
  ⑤ 13대 모두 `apt-get update`를 실행한다.
  ⑥ 출력에 EXPKEYSIG·NO_PUBKEY·"is not signed"가 있거나 종료 코드가 0이 아니면 사람 작업 1회로 센다.
  A는 새 공개 키를 같은 경로에 덮어쓴다. 꺼져 있던 B는 릴리스 .deb를 `dpkg -i`로 다시 설치한다.
  그 뒤 재시도가 통과하는지 확인한다.
- 각 변경에서 함께 잰다: 연장 전후 키 ID·지문의 동일 여부, 만료일 증가량, 켜진 B가 만료 전에 업그레이드를 마쳤는지, 실패한 기계가 고치기 전·후에 apt가 아는 후보 버전(`apt-cache policy`의 Candidate).
  또 색인이 전혀 없는 새 기계를 연장 전 키 파일로 설정했을 때의 종료 코드와 출력도 잰다.
- 마지막 줄 `result`에는 A·B·오프라인 B의 사람 작업 합계, 최종 update 통과 여부, 전체 소요 시간을 담는다.
- 만료 시각은 같은 실행에서 잰 apt update·이행 소요 시간에 여유 배수를 곱해 정한다.
  순서가 지켜졌는지는 `online_b_upgrade_finished_before_old_expiry`로 출력한다.
  출력하는 수치는 모두 실행 중에 측정한 값이다.

### 한계

- 실제 `packages.ros.org`와 실제 F42ED6FBAB17C654 서명은 쓰지 않는다. 네트워크가 없기 때문이다.
  만료 현상은 같은 방식(같은 키 ID로 만료일만 연장)으로 만든 자체 키로 재현한다.
- B의 무인 업그레이드는 `apt-get download` + `dpkg --root -i`로 구현했다. `apt upgrade` 자체는 아니다.
  다만 패키지가 서명 검증을 거친 저장소에서 내려온다는 조건은 같다.
- 시뮬레이션 패키지의 sources.list.d 링크는 상대 경로다(실제 ros2-apt-source는 절대 경로).
  기계별 루트를 /tmp 아래에 나눠 두기 위해서다.
- "사람 작업 1회"는 작업 종류와 관계없이 기계 한 대에서 하는 수정 한 번이다. 시간과 실수 위험은 재지 않는다.
- 하드웨어·로봇 동작과 무관한 저장소 설정 실험이다.

## 시행착오(시험 실행에서 실제로 겪은 것)

1. 첫 시험 스크립트에서 `run()`에 `text=`를 두 번 넘겼다. 그래서 바이너리 키를 export할 때 TypeError가 날 구조였다.
   실행 전에 `text`를 인자로 받도록 고쳤다.
2. 두 번째 시험 실행에서 사람 작업 판정을 `apt-get update` 종료 코드(≠0)로만 했다.
   그랬더니 A 기계가 모두 EXPKEYSIG를 출력하고도 수작업이 0회로 집계됐다.
   이전에 색인을 받아 둔 기계는 apt가 "The repository is not updated and the previous index files will be used" 경고만 낸다.
   그리고 종료 코드 0으로 끝난다.
   판정을 "종료 코드 ≠0 또는 출력에 EXPKEYSIG/NO_PUBKEY/is not signed"로 바꿨다.
   종료 코드와 옛 색인 사용 여부는 별도 항목으로 기록하게 했다.
   이 차이를 확인하려고 색인이 없는 새 기계 측정과 후보 버전(Candidate) 측정을 추가했다.
3. 후보 버전을 처음에는 `apt-get install --simulate`의 Inst 줄로 읽었다.
   이미 최신인 기계는 Inst 줄이 없어 "none"으로 찍혔다. `apt-cache policy`의 Candidate로 바꿨다.
4. 첫 만료 대기 여유가 실제 필요 시간보다 길어 실행 시간이 길었다. 첫 만료 창을 줄였다.
   이후 만료 시각은 측정한 소요 시간 기반으로 정한다. 시험 실행은 60초 안에 끝났다.
