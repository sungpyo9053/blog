# 실험 계획: ros2-apt-source 단계는 무엇을 바꾸고, 기계 수·변경 횟수에 따라 사람 손이 얼마나 줄어드나

## 질문

1. 공식 문서대로 `ros2-apt-source`가 설치된 이미지에는 실제로 어떤 파일이 어떤 형태(심볼릭 링크·dpkg 소유·내장 키)로 있고,
   그 키는 `F42ED6FBAB17C654`의 몇 년 만료본인가? `grep -r`로 점검하면 이 파일을 찾는가?
2. 예전 수동 방식 `ros2.list`(signed-by=키 파일 경로)를 지우지 않고 새 `ros2.sources`와 함께 두면 apt는 실제로 멈추는가?
3. 같은 키의 만료일 연장 사건이 k번 일어날 때, 수동 방식(A)과 패키지 방식(B)에서 사람이 기계에 손댄 횟수는 몇 번인가?
   갱신을 놓친(꺼져 있던) 기계는 만료 후 `apt-get update`에서 어떤 결과(종료 코드·`EXPKEYSIG`·이전 색인 사용)를 내는가?
   이전 색인이 없는 새 기계는 같은 낡은 키로 어떤 결과를 내는가?

## research.md 기준 예측값

- 1부: 패키지 키링 지문 `C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654`, 만료 2030-06-01 12:39:34 UTC, 키링 1,167 bytes.
  `/etc/apt/sources.list.d/ros2.sources`는 `/usr/share/ros-apt-source/ros2.sources`를 가리키는 심볼릭 링크이고 dpkg 소유자는 `ros2-apt-source`.
  예전 `ros2.list`·`ros-archive-keyring.gpg`는 없음. GNU grep 매뉴얼대로 `grep -rl`은 심볼릭 링크를 건너뛰어 0개, `grep -Rl`은 1개.
  (패키지 버전은 research.md가 이미지 내용을 확인하지 않았으므로 예측하지 않음.)
- 2부: 새 파일만·예전 파일만은 정상(종료 코드 0). 둘 다 두면 apt 2.8 소스(debmetaindex.cc L809–L824)대로
  `Conflicting values set for option Signed-By` 오류. 예전 줄이 패키지 키링 경로를 가리켜도 내장 키 블록과 문자열이 달라 충돌.
  같은 키 경로의 예전 줄 두 개는 충돌이 아니라 `configured multiple times` 경고.
- 3부(n=3, k=2): A = n·k = 3×2 = 6회, B(켜져 있던 3대) = n·1 = 3회, 사건 1 때 꺼져 있던 B 1대 = 이전 1 + 복구 1 = 2회
  (research.md Q2의 B = n + m). 꺼져 있던 기계는 만료 후 `EXPKEYSIG`. 종료 코드와 이전 색인 사용 여부는 research.md가
  "문서만으로 판정하지 않는다"고 했으므로 예측하지 않음(측정 대상). 이전 색인 없는 새 기계는 Robotics SE 2021 출력처럼
  `is not signed` 오류가 함께 날 것으로 예상.

## 무엇을 어떻게 재는가

환경: 하네스가 `ros:jazzy-ros-base`를 네트워크 없이 1 CPU·1 GiB로 실행. 모든 값은 실행 중에 명령을 돌려 얻고 JSON 줄로 출력한다.
ROS 패키지(rclpy 등)는 쓰지 않는다. 대상이 apt 설정이라 이미지에 있는 apt 2.8.3·gpg 2.4.4·dpkg-deb만 쓴다.

- 1부 image: `dpkg-query -W -f '${Version}' ros2-apt-source`, `/etc/apt/sources.list.d`의 각 파일에 대해 `os.path.islink`·`readlink`·`dpkg -S`,
  `gpg --with-colons --show-keys`로 키링과 `ros2.sources`의 `Signed-By` 내장 블록에서 꺼낸 키의 지문·만료일, 예전 파일 존재 여부,
  `grep -rl`/`grep -Rl packages.ros.org /etc/apt/sources.list.d/`의 종료 코드와 찾은 파일 수.
- 2부 conflict: 시스템 설정을 건드리지 않도록 `APT_CONFIG`로 sources·trusted·lists·status를 `/tmp` 아래 빈 디렉터리로 돌린 격리 apt에서
  5개 파일 조합(new_only, old_only, old_and_new, old_pointing_pkg_keyring_and_new, old_line_twice_same_key)마다 `apt-cache policy`의
  종료 코드와 첫 W:/E: 메시지. 새 파일은 이미지의 실제 `/usr/share/ros-apt-source/ros2.sources` 내용을 그대로 쓴다. 네트워크 접속은 하지 않는다
  (`apt-cache policy`는 설정 해석 단계에서 충돌을 판정).
- 3부 lab: `gpg --quick-gen-key`로 실험용 ed25519 서명 키(수명 6초)를 만들고, `file:` 저장소에 `lab-apt-source`(키링을 담은 `.deb`, `dpkg-deb`로 빌드)와
  서명한 `InRelease`를 둔다. 기계 7개(각자 격리된 apt 설정): A 3대(수동), B 3대(패키지), B_off 1대(패키지, 사건 1 때만 꺼짐).
  - 출발: 7대 모두 예전 수동 방식(키 파일 + signed-by `.list`)으로 설정하고 `apt-get update` 성공 확인. 출발 설정은 두 방식 공통이라 횟수에서 뺀다.
  - 이전: B·B_off는 예전 저장소에서 `apt-get download`로 패키지를 받아 `dpkg-deb -x`로 풀고, 예전 `.list`·키 파일을 지우고 `.sources`로 교체 → 사람 1회.
  - 사건 j(j=1..k): 예전 사본이 만료되기 전에 운영자가 `gpg --quick-set-expire`로 **같은 키(같은 지문)**의 만료일을 연장하고 새 키링을 담은
    `lab-apt-source 1.j`를 올린다. A는 사람이 기계마다 키 파일을 덮어쓴다(1회씩). 켜져 있는 B는 사람 없이 `apt-get update` → 후보 버전 다운로드 →
    풀기(무인 갱신 흉내). 그다음 예전 만료 시각이 지날 때까지 실제로 기다리고, 저장소를 재서명한 뒤 7대 모두 `apt-get update`.
    종료 코드·`EXPKEYSIG`·"previous index files will be used" 여부와 W:/E: 줄을 기록. 실패하거나 EXPKEYSIG가 난 기계는 사람이 새 패키지를 직접 풀어
    고치고(1회) 다시 `apt-get update` 종료 코드를 잰다. 사건마다 A1·B1·B_off의 키 사본 지문과 만료일을 `gpg --show-keys`로 읽는다.
  - 새 기계 비교: 별도 키(수명 3초)로, 만료 전에 한 번 update해 색인이 있는 기계와 색인이 없는 새 기계를 만든 뒤, 만료 후 운영자는 연장했지만
    두 기계는 옛 사본을 가진 상태에서 `apt-get update`의 종료 코드·메시지·lists 파일 수·패키지 후보 보임 여부.
  - 사람 손 횟수는 코드가 작업을 실행할 때마다 기계별 카운터를 1 올려 센다(결과 숫자를 미리 적지 않음).

## 한계

- 실제 `packages.ros.org`·실제 ROS 키(RSA 4096)·HTTP 전송·미러·프록시는 재현하지 않는다(네트워크 없음, `file:` 저장소, ed25519 실험 키).
- "패키지 방식"은 `apt-get download` + `dpkg-deb -x`로 키링만 갱신하는 흉내다. 실제 `apt upgrade`·unattended-upgrades의 도착 시점, dpkg 데이터베이스 등록,
  `.sources` 파일의 패키지 관리는 재현하지 않았다(실험의 `.sources`는 이전 때 사람이 쓴 것으로 센다).
- 만료 주기를 초 단위로 압축했다. "사람 손 1회"의 시간·실수 확률은 재지 않는다. 로봇·시뮬레이터·하드웨어 실행은 없다.

## 시행착오(시험 실행에서 실제로 겪은 것)

1. 첫 시험 실행은 도구 확인용 탐색 스크립트였다. 이미지에 gpg 2.4.4·gpgv·dpkg-deb는 있지만 `apt-ftparchive`는 없어서,
   `Packages`·`Release` 색인은 Python으로 직접 쓰고 해시를 계산하도록 설계했다. 이미지의 `ros2-apt-source`가 research.md가 다룬 최신 1.3.0이 아니라
   1.2.0~noble이라는 것도 이때 알았다(그래서 버전은 측정값으로만 출력).
2. 2부에서 처음엔 "ROS 저장소가 `apt-cache policy` 출력에 보이는지"도 기록했는데, 격리 환경에는 내려받은 색인이 없어 모든 경우가 false로 나와
   의미가 없었다. 그 필드를 지우고 종료 코드와 첫 W:/E: 메시지만 남겼다.
3. 처음 출력은 기계별 상세를 모두 담아 하네스가 보존하는 stdout 끝 8,000자에 가까웠다. 1부 줄이 잘릴 위험이 있어 사건별 출력을 종료 코드 표와
   해당 기계 목록으로 줄이고 키 사본 정보는 별도 줄로 분리했다. 메시지도 `Err:` 줄 대신 실제 원인이 담긴 W:/E: 줄을 남기게 고쳤다.
4. 사건 사이 대기를 줄이려고 연장 수명을 처음 18초(6×3)에서 12초(6×2)로 줄였다. 시험 실행 전체 시간은 약 18–20초였다.
