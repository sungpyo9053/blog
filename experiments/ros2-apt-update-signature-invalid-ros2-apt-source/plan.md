# 실험 계획: ros2-apt-source는 무엇을 바꾸고, 키 만료일 연장 때 사람 손은 몇 번 필요한가

## 질문

1. `ros:jazzy-ros-base`에 설치된 ros2-apt-source는 어떤 파일을 소유하는가? 저장소 설정에 내장된 공개 키와 키링 파일은 같은 키(F42ED6FBAB17C654)이고 만료일도 같은가?
2. 옛 공식 절차의 한 줄 형식 `ros2.list`가 남아 있으면 apt는 어떻게 되는가? 옛 파일을 지우면 다시 정상으로 돌아오는가? `signed-by`가 어느 경로를 가리키는지, 또는 아예 없는지에 따라 결과가 달라지는가?
3. "같은 키 ID로 만료일만 연장"하는 변경이 일어날 때 갱신 창을 놓친 기계의 `apt-get update`는 어떻게 끝나는가(종료 코드, 출력)? 색인을 이미 받아 둔 기계와 색인이 없는 새 기계(예: 옛 키가 캐시에 남은 Docker 이미지)는 다르게 끝나는가? 이것으로 공식 첫 줄 `sudo apt update && ...`의 `&&`가 끊기는지 판단한다.
4. 기계 n대, 변경 k회, 갱신 창을 놓친 (기계, 변경) 쌍 m개에서 실제로 사람이 손댄 횟수가 research.md 모델 A=n×k, B=n+m과 같은가?

## research.md 기준 예측값

- 1: 소유 파일에 `/usr/share/keyrings/ros2-archive-keyring.gpg`, `/usr/share/ros-apt-source/ros2.sources`, `/etc/apt/sources.list.d/ros2.sources`(→ `/usr/share/ros-apt-source/ros2.sources` 링크)가 있다. Jammy 이후이므로 `Signed-By:`에 키 블록이 직접 들어 있다. 내장 키와 키링의 지문은 `C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654`, 생성일 2019-05-30, 만료일 2030-06-01로 같다.
- 2: 옛 키링 경로를 가리키는 `ros2.list`를 추가하면 `E: Conflicting values set for option Signed-By ...`, `E: The list of sources could not be read.`가 나온다(Tiryoh #72 외부 재현). 종료 코드는 0이 아니다. 옛 파일을 지우면 정상으로 돌아온다. `signed-by` 없는 줄, 새 키링 경로를 가리키는 줄은 research.md에 예측이 없다.
- 3: RSE 99143 출력처럼 `EXPKEYSIG`와 `E: The repository ... is not signed.`가 나오고 종료 코드는 0이 아니다. 그래서 `&&` 뒤는 실행되지 않는다(research.md는 미확인으로 남겼고, 이 예측은 인용 출력에 근거한다). 색인 유무에 따른 차이는 예측하지 않았다.
- 4: n=4, k=2, m=3(갱신 창을 한 번 놓친 기계 1대 + 두 번 모두 놓친 기계 1대)이면 A=n×k=8, B=n+m=4+3=7이다.

## 무엇을 어떻게 재는가

환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB). 모든 숫자는 실행 중에 측정해 JSON 줄로 출력한다.

### 1부: 패키지 소유 파일과 키

- `dpkg-query -W ros2-apt-source`로 버전을, `dpkg -L ros2-apt-source`로 소유 파일(일반 파일·링크만)을 센다. `/etc/apt/sources.list.d/ros2.sources`의 링크 대상을 읽는다.
- `/usr/share/ros-apt-source/ros2.sources`의 deb822 `Signed-By:` 연속 줄을 꺼낸다(` .`은 빈 줄). 이 블록을 키 파일로 저장한다. 이것과 `/usr/share/keyrings/ros2-archive-keyring.gpg`를 각각 `gpg --show-keys --with-colons`로 읽어 지문·생성일·만료일을 비교하고, 남은 일수를 계산한다.

### 2부: 옛 `ros2.list`와 Signed-By 충돌

- 실제 `/etc/apt/sources.list.d/`에 `ros2.list`를 쓰고 `apt-cache policy`(네트워크 없이 sources만 읽음)의 종료 코드와 `E:`/`W:` 줄을 기록한다. 경우는 다섯 가지다. 패키지만 있음, 옛 키링 경로 `signed-by`, 새 키링 경로 `signed-by`, `signed-by` 없음, 옛 파일 삭제 후.
- `dpkg -S`로 `ros2.list`가 어느 패키지에도 속하지 않는지 확인한다.
- 충돌 상태에서 `apt-get update`의 종료 코드를 재고, 네트워크 요청(`Get:`/`Err:` 등)을 하기 전에 멈추는지 본다. 멈추면 무관한 Ubuntu 저장소 갱신도 함께 막힌다는 뜻이다.

### 3부: 만료일 연장 재현(자체 키 + `file:` 저장소)

- 컨테이너 안에서 `gpg --quick-gen-key ... ed25519 sign seconds=6`으로 수명 6초 서명 키를 만든다. `file:` 저장소(Packages, Release, `gpg --clearsign`으로 서명한 InRelease)를 직접 만든다. 저장소에는 키링 패키지 `huntlab-apt-source`(ros2-apt-source 역할)를 올린다.
- 기계 8대를 각각 별도 apt 상태 디렉터리(`Dir::State::lists`, `Dir::Cache`, `Dir::Etc::sourceparts`, `Dir::State::status`)로 흉내 낸다. 모두 같은 저장소를 쓰고, deb822 `Signed-By:`가 각 기계의 키 파일을 가리킨다.
  - A(수동) 4대: 사람이 받아 둔 키 사본. 최초 사본은 이미 있다고 보고 세지 않는다.
  - B(패키지) 4대: 최초 이전 1회(공식 문서의 `dpkg -i` 대신 v1 .deb를 `dpkg-deb -x`로 풀기)를 사람 작업 1회로 센다.
  - 일정: on1, on2는 갱신 창을 놓치지 않는다. miss1은 변경 1만 놓친다. missall은 두 변경을 모두 놓친다. 그래서 방식별로 m=3이다.
- 변경 k=2회. 각 변경에서 만료 전에 `gpg --quick-set-expire`로 같은 키의 만료일을 늘리고(변경 1은 +10초, 변경 2는 +40초) 키링 패키지 새 버전을 저장소에 올린 뒤 재서명한다.
  - 갱신 창: 켜진 A 기계는 사람이 새 공개 키를 복사한다(1회). 켜진 B 기계는 사람 없이 `apt-get update` → `apt-get download huntlab-apt-source` → `dpkg-deb -x`로 키링을 갱신한다(apt upgrade 대용). 갱신 후 키링 만료일이 저장소의 현재 키와 같은지 확인한다.
  - 옛 만료 시각 + 1.5초까지 기다린다. 저장소를 다시 서명한 뒤 모든 기계에서 `apt-get update`를 실행해 종료 코드, 출력 속 `EXPKEYSIG`/`NO_PUBKEY`/`is not signed`, 이후 `apt-cache policy`의 Candidate(저장소 최신 버전을 보는지)를 기록한다.
  - 서명 실패(종료 코드 ≠ 0 또는 서명 오류 문자열)가 나온 기계는 사람이 새 공개 키를 같은 경로에 복사해 복구한다(+1회). 다시 update한 종료 코드와 Candidate를 기록한다. B는 복구 후 패키지 갱신을 이어서 한다.
- 변경 1 직후에는 색인이 없는 새 기계(C, 옛 v1 키 사본)도 같은 시점에 `apt-get update`를 실행해 색인이 있는 기계와 비교한다.
- 마지막에 방식별 사람 작업 합계와 기계별 횟수를 출력한다. 비교용으로 입력값 n, k, m에서 계산한 모델값(n×k, n+m)도 함께 출력한다.

### 한계

- 실제 packages.ros.org, 실제 F42ED6FBAB17C654 서명, 실제 `dpkg -i`/`apt upgrade`(maintainer script 실행)는 쓰지 않는다. 키링 패키지 갱신은 검증된 색인으로 .deb를 받고 파일을 푸는 것으로 대신한다.
- 키 수명은 초 단위로 줄였다. 실제 변경 간격(수년)과 사람의 작업 시간·실수는 재지 않는다. "사람 작업 1회"는 기계 한 대에서 키 복사(또는 이전) 한 번이다.
- 시뮬레이션이며 로봇 하드웨어나 실제 운영 기계에서 실행하지 않는다.

## 시행착오(시험 실행에서 실제로 실패하거나 고친 점)

1. 첫 시험은 도구 확인용이었다. 이미지에 `gpg`/`gpgv` 2.4.4, apt 2.8.3, `dpkg-deb`가 있고 `apt-ftparchive`는 없었다. 그래서 Packages/Release 파일은 Python에서 SHA256을 계산해 직접 쓰도록 바꿨다. 실행 사용자는 root였다.
2. 두 번째 시험에서 1부 키 비교가 실패했다(`gpg --show-keys` 종료 코드 2, 지문 빈 값). 원인은 3부에서야 만드는 GNUPGHOME을 1부가 먼저 썼기 때문이다. 키 조회 전용 homedir을 따로 만들어 고쳤다.
3. 같은 시험에서 예측과 다른 동작이 나왔다. 색인을 이미 받아 둔 기계는 키가 만료돼도 `apt-get update` 종료 코드가 0이었다. 출력에는 `EXPKEYSIG`와 "previous index files will be used" 경고만 있었다. 종료 코드 100과 `E: ... is not signed`는 색인이 없는 새 기계에서만 나왔다. 처음 코드는 "종료 코드 ≠ 0"만 실패로 봤으므로 복구 단계가 실행되지 않았고, 사람 작업 수가 모델과 어긋났다. 그래서 실패 판정을 "종료 코드 ≠ 0 또는 출력에 서명 오류 문자열"로 바꿨다. 실패 출력 예시도 색인 있음과 없음으로 나눠 따로 남겼다.
4. 같은 시험에서 A 방식의 최초 키 사본도 사람 작업으로 세는 바람에 A 합계가 모델(n×k, 이미 수동 설정된 기계 기준)보다 컸다. A의 최초 사본은 세지 않고, B의 최초 이전만 1회로 세도록 고쳤다.
5. 2부 오류 줄을 150자로 자르니 충돌 상대 값(`!= -----BEGIN PGP PUBLIC KEY BLOCK-----`)이 잘렸다. 200자로 늘리고 `W:` 줄도 함께 남기게 했다.
6. stdout이 하네스 보관 한도(뒤쪽 8000자)를 넘지 않도록 3부 출력을 기계별 짧은 키로 줄였다.
