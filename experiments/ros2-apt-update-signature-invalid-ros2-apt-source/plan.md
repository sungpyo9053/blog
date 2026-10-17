# 실험 계획: ROS 2 저장소 키 만료와 ros2-apt-source 전달 경로

## 질문

`apt update`의 `EXPKEYSIG F42ED6FBAB17C654` 오류는 같은 키의 만료일이 연장될 때마다 되풀이된다.
공식 문서의 `ros2-apt-source` 단계가 바꾸는 것은 키가 아니라 "키·소스 설정이 기계까지 오는 길"이라는
research.md의 결론이 실제 apt 동작에서도 성립하는가? 구체적으로 세 가지를 확인한다.

1. ros:jazzy-ros-base 이미지에 실제로 깔린 ROS 키와 소스 설정은 무엇이고, 만료일은 언제인가?
2. 예전 수동 파일(`ros2.list` + 별도 키링)을 지우지 않고 새 `ros2.sources`와 함께 두면 apt 2.8.x는 실제로 어떻게 반응하는가?
3. 같은 키의 만료일만 늘리는 사건이 k번 일어날 때, 기계 n대에서 사람이 손을 대야 하는 횟수는
   방식 A(기계마다 키 파일 수동 관리)와 방식 B(키·소스를 담은 설정 패키지 + 자동 갱신)에서 각각 몇 번인가?
   그리고 B의 전제("키가 유효할 때 갱신을 받아야 한다")가 깨지면 무슨 일이 생기는가?

## research.md 기준 예측값(실행 전에 적은 값)

- 이미지 키링 `/usr/share/keyrings/ros2-archive-keyring.gpg`: 지문 `C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654`,
  긴 키 ID `F42ED6FBAB17C654`, 키 생성 2019-05-30, 자기서명 2025-04-30, 만료 2030-06-01 12:39:34 UTC,
  크기 1,167 bytes(research는 1.0.0~1.3.0 키링 바이트가 모두 같다고 확인했으므로 이미지의 패키지 버전과 관계없이 같아야 한다).
  `ros2.sources`의 `Signed-By` 내장 키도 같은 지문이어야 한다. `/etc/apt/sources.list.d/ros2.sources`는
  `/usr/share/ros-apt-source/ros2.sources`를 가리키는 심볼릭 링크이고 dpkg 소유자는 `ros2-apt-source`.
  이미지 안의 패키지 버전은 research에 예측이 없다(1.3.0이 최신이지만 이미지 빌드 시점에 따라 다를 수 있음).
- research 6번 점검 명령 `grep -rl "packages.ros.org" … /etc/apt/sources.list.d/`: research는 ROS가 설정된
  기계의 결과를 확인하지 않았다. 예측: `-r`은 하위 디렉터리를 돌 때 심볼릭 링크를 따라가지 않으므로,
  ros2-apt-source가 설치된 기계에서 `ros2.sources`(링크)를 놓칠 수 있다. `-R`이면 찾아야 한다.
- 예전 `ros2.list` + 새 `ros2.sources` 공존: apt 2.8.2 소스 코드대로
  `E: Conflicting values set for option Signed-By regarding source …` 오류, 0이 아닌 종료 코드.
  예전 줄이 패키지의 키링 경로(`ros2-archive-keyring.gpg`)를 가리켜도 값(경로 vs 내장 키 블록)이 달라 충돌할 것으로 예측.
  같은 키 경로의 예전 줄 두 개는 충돌이 아니라 중복 경고만 나올 것으로 예측.
- 산술 모델(n=3, k=2): A = n×k = 6회, B = n×1 = 3회(이전 작업만), 차이 A−B = n×(k−1) = 3회.
  1회차 갱신 때 꺼져 있던 B 기계 1대는 이전 1회 + 복구 1회 = 2회.
- `EXPKEYSIG` 때 `apt-get update` 종료 코드: research는 미확인(2021 출력의 `E: … is not signed`와 2025 출력의
  `W: … previous index files will be used`가 다르다고만 기록). 예측: 이전 색인이 있는 기계는 `W:`만 나오고
  종료 코드 0일 수 있다. 색인이 없는 새 기계는 `E:`와 0이 아닌 종료 코드.
- 모든 키 버전의 지문은 하나(같은 키의 만료 연장)여야 한다.

## 무엇을 어떻게 재는가

환경: 하네스가 `ros:jazzy-ros-base`(네트워크 없음, 1 CPU, 1 GiB)에서 실행한다. 이미지에 있는 apt 2.8.x,
gpg/gpgv 2.4.x, dpkg/dpkg-deb, Python 3.12 표준 라이브러리만 쓴다. 이 질문은 apt 저장소 설정에 관한 것이라
ROS 노드(rclpy·tf2_ros)는 실행하지 않는다. 시스템 apt 설정은 읽기만 하고, 쓰기는 모두 `/tmp/lab` 아래에서 한다.

1부 `image`(읽기 전용): `dpkg-query`로 `ros2-apt-source` 버전, `/etc/apt/sources.list.d/*ros*`의 링크 여부·대상·dpkg 소유자,
키링 바이트 수를 잰다. 키링과 `ros2.sources`의 `Signed-By` 내장 키를 표준 라이브러리 OpenPGP 파서(공개키 패킷 SHA-1 지문,
자기서명 서브패킷 2·9)로 읽고 `gpg --show-keys --with-colons`로 교차 확인한다. 실행 시각 기준 만료까지 남은 일수를 계산한다.
예전 방식 파일(`ros-archive-keyring.gpg`, `ros2.list`, `ros2-latest.list`) 존재 여부, `grep -rl`과 `grep -Rl`의 종료 코드와 일치 파일을 비교한다.

2부 `conflict`: 격리된 apt 디렉터리(`Dir::Etc::SourceParts` 등을 `/tmp` 아래로 지정)에 이미지의 실제 `ros2.sources` 본문과
예전 공식 문서 형식의 `ros2.list` 한 줄을 조합해 넣고 `apt-cache policy`를 실행한다(소스 목록 해석 단계라 네트워크가 필요 없다).
경우 5개: 새 파일만 / 예전 파일만 / 둘 다 / 예전 줄이 패키지 키링 경로를 가리키는 경우 + 새 파일 / 같은 키의 예전 줄 두 개.
종료 코드, `Conflicting values` 문구, 중복 경고, 첫 오류 줄을 기록한다.

3부 `lab`: 실험용 ed25519 서명 키를 gpg로 만들고 `file:` 저장소(Packages·Release를 Python으로 작성, InRelease는 `gpg --clearsign`)를 연다.
기계는 apt 디렉터리를 따로 가진 루트 7개로 흉내 낸다: A 3대, B 3대, B 오프라인 1대. 모두 예전 수동 방식(키 파일 + 한 줄 `.list`)으로 시작한다.
B 그룹은 이전 작업 1회(사람)를 한다: 예전 `.list`·키링 삭제 → 설정 패키지 `lab-apt-source 1.0` 설치(`dpkg --root`) → `apt-get update` 확인.
설정 패키지는 ros2-apt-source와 같은 구조다(키링 파일 + `Signed-By` 키 내장 deb822 소스 + `/etc/apt/sources.list.d`의 심볼릭 링크).
그다음 k=2번의 "같은 키 만료 연장" 사건을 실제 시계로 일으킨다(만료 간격은 수 초로 압축).

- 만료 전: 운영자가 `gpg --quick-set-expire`로 같은 키의 만료일을 늘리고, 새 공개키(`lab.key`, 예전 방식이 손으로 받는 `ros.key` 역할)와
  새 설정 패키지 버전(1.1, 1.2)을 저장소에 올린 뒤 InRelease를 다시 서명한다. B 그룹 중 켜져 있는 기계는 사람 없이
  `apt-get update` → `apt-cache policy` 후보 확인 → `apt-get download`(서명 검사된 색인의 해시로 검증) → `dpkg --root -i`를 돈다.
  B 오프라인 기계는 1회차에만 이 단계를 건너뛴다. 예전 만료 시각까지 남은 초(`seconds_left_before_old_expiry`)를 재서 순서가 지켜졌는지 기록한다.
- 만료 후: 예전 만료 시각이 실제로 지나갈 때까지 기다리고 저장소를 다시 서명한 뒤 모든 기계에서 `apt-get update`를 실행한다.
  종료 코드, `EXPKEYSIG <긴 키 ID>`, `previous index files will be used`, `is not signed`, `W:`/`E:` 줄 수를 출력에서 센다.
  서명 검사가 실패한 기계만 사람 복구 1회로 센다(A: `lab.key`를 키링에 덮어씀, B: 최신 .deb를 저장소 밖 경로로 직접 `dpkg -i`).
  B 실패 기계는 복구 전에 자동 갱신으로 스스로 회복되는지(`self_heal`)를 먼저 시도해 기록한다. 복구 뒤 `apt-get update`를 다시 돌려 통과 여부를 잰다.
  1회차에는 예전 키만 가진 채 처음 `apt-get update`를 하는 새 기계(이전 색인 없음)의 결과도 따로 잰다.
- 요약: 그룹별 사람 작업 횟수(실측)와 위 산술 모델 예측값을 나란히 출력하고, 모든 키 버전과 기계의 지문 개수를 센다.

출력은 모두 JSON 한 줄씩이다. 하네스가 stdout의 마지막 8000자만 보관하므로 기계별 줄 대신 그룹별로 묶어 출력한다.
한 번 실행은 약 20초다(대부분 만료 시각을 기다리는 시간).

## 한계

- 기계는 한 컨테이너 안의 별도 apt 디렉터리로 흉내 낸 것이며 `apt upgrade` 대신 `apt-get download` + `dpkg --root -i`를 썼다.
  실제 `apt upgrade`·unattended-upgrades·재부팅·프록시·미러는 재현하지 않았다.
- 실험 키는 ed25519, 저장소는 `file:`이다. ROS의 실제 키(RSA)와 `http://packages.ros.org`에 접속하지 않았다(네트워크 없음).
  2부의 충돌은 소스 목록 해석 단계(`apt-cache policy`)에서 잰 것이며 네트워크가 있는 `apt update` 전체 출력은 아니다.
- 연 단위 만료 주기를 초 단위로 압축했다. 사람 작업 1회는 "기계 한 대에서 하는 설정 묶음 1회"이며 시간·실수 확률은 재지 않는다.
- 로봇·시뮬레이터·하드웨어 실행은 없다. 따라서 하드웨어 안전 조건과 중지 방법은 이 실험의 범위 밖이다.

## 시행착오(시험 실행에서 실제로 실패하거나 고친 점)

1. 첫 시험 실행은 이미지 조사용 탐색 스크립트였다. 이미지에 `ros2-apt-source`가 이미 설치돼 있고(버전은 1.3.0이 아니라 1.2.0~noble),
   gpg는 있으나 `apt-utils`(apt-ftparchive)는 없다는 것을 확인했다. 그래서 Packages·Release를 Python으로 직접 만들도록 설계했다.
   같은 실행에서 `grep -rl packages.ros.org /etc/apt/`가 아무것도 찾지 못했다. 원인이 심볼릭 링크라고 보고 `-r`/`-R` 비교를 1부에 넣었다.
2. 코드 검토 중 `installed_version()`의 `return res.stdout or None if … else None` 연산자 우선순위 오류를 발견해, 실행 전에 괄호로 고쳤다.
3. 두 번째·세 번째 시험 실행은 성공했다. 하지만 하네스가 stdout 마지막 8000자만 남겨 앞부분(env·image·conflict 줄)이 잘렸다.
   기계별 줄을 그룹별 요약으로 바꾸고 중복 메시지를 줄였다.
4. 처음 잡은 첫 만료 간격은 준비 작업 시간보다 훨씬 길어서 대부분 대기 시간이었다. 첫 만료 간격과 다음 만료 간격을 각각 9초로 줄였다.
   만료 전 여유 시간(`seconds_left_before_old_expiry`)과 `timing_ok`를 출력해, 하네스 실행에서 순서가 깨지면 결과에 그대로 드러나게 했다.
5. 마지막 시험 실행: 종료 코드 0, stdout이 8000자 안에 모두 들어왔다.
