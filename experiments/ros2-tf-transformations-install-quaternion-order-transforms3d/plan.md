# 실험 계획: 쿼터니언 순서를 섞으면 tf2가 돌려주는 자세는 얼마나 틀어지는가

- 환경: `ros:jazzy-ros-base` 컨테이너, 네트워크 없음, 1 CPU·1 GiB (하네스가 실행·기록)
- 사용 모듈: `rclpy`(Time), `tf2_ros`(Buffer), `geometry_msgs/msg/Quaternion`·`TransformStamped`, Python 표준 라이브러리
- 실행 시간 목표: 한 번에 60초 이내 (tf2 변환 저장·조회만 하므로 수 초 안쪽 예상)
- 범위: 자세 표현을 tf2에 넣고 다시 꺼낸 결과의 산술. 실물 로봇·시뮬레이터 실행이 아니다.

## 질문

1. ros-base 이미지만 있으면 `tf_transformations`와 `transforms3d`를 바로 import할 수 있나? (apt 설치가 필요한가)
2. README 설치 명령의 `$ROSDISTRO`를 그대로 쓰면 패키지 이름이 어떻게 확장되나? `${ROS_DISTRO}`는?
3. transforms3d 순서 `(w, x, y, z)` 배열을 `Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])`처럼 인덱스로 채워
   tf2에 넣으면(실수 A), 또는 반대로 `(x, y, z, w)` 배열을 w 먼저 소비자처럼 읽으면(실수 B),
   tf2가 돌려주는 자세는 정상 자세와 몇 도 다른가? 평면 heading은 어떻게 읽히나?
4. 정규화(크기 제곱 = 1) 검사로 이 순서 실수를 잡을 수 있나? 크기가 1이 아닌 쿼터니언은 tf2가 어떻게 처리하나?
5. 어떤 테스트 입력이 순서 실수를 잡고, 어떤 입력은 놓치나?

## research.md 기준 예측값

- 1: research.md는 apt 패키지 `ros-<배포판>-tf-transformations` 설치가 필요하다고 정리했다(ros-base 포함 여부는 미확인).
- 2: 미설정 변수는 빈 문자열로 확장 → `ros--tf-transformations`. `${ROS_DISTRO}`는 `ros-jazzy-tf-transformations`.
- 3 (yaw θ, 「Research 유도」):
  - 실수 A: yaw θ가 x축 roll (180° − θ)로 바뀌고, 전방 축은 회전하지 않아 heading이 항상 0°로 읽힌다.
    회전 오차 = 2·acos(|sin θ|/2) → θ = 0°, 180°에서 180°, θ = ±90°에서 120°, 그 밖은 120°~180°.
    상방축 z 성분(r22) = cos(180° − θ) = −cos θ.
  - 실수 B: w 자리에 0이 들어가 항상 180° 회전(축 (0, s, c)) → 같은 오차식 2·acos(|sin θ|/2).
- 4: 순서를 바꿔도 크기 제곱은 1 그대로 → 정규화 검사로 잡히는 경우 0건.
  크기가 1이 아닌 입력에 대해서 research.md는 "ROS 2가 경고한다"고만 적었다(저장 여부·정규화 여부 예측 없음).
- 5: `(0.5,0.5,0.5,0.5)`는 한 칸 밀어도 같은 튜플(성분 차이 제곱합 0, 회전 차이 0°) → 못 잡음.
  `(0.5,−0.5,0.5,−0.5)`는 밀면 −q(성분 차이 제곱합 4, 회전 차이 0°) → 못 잡음.
  항등 `(0,0,0,1)`, yaw 180° `(0,0,1,0)`는 회전 차이 180°, yaw 90° `(0,0,√½,√½)`는 120° → 잡음.
  기대 좌표: 항등 → 전방 (1,0,0)·좌측 (0,1,0), yaw 180° → (−1,0,0)·(0,−1,0), yaw 90° → (0,1,0)·(−1,0,0).

## 무엇을 어떻게 재는가

1. **설치 상태**: `importlib.util.find_spec`로 `tf_transformations`, `transforms3d`, `numpy` import 가능 여부,
   `dpkg-query`로 `ros-jazzy-tf-transformations`, `python3-transforms3d`, `python3-numpy` 설치 상태·버전을 출력한다.
2. **설치 명령 확장**: `ROSDISTRO`를 뺀 환경에서 `bash -c "echo ros-$ROSDISTRO-tf-transformations"`와
   `ros-${ROS_DISTRO}-tf-transformations`를 실제로 실행해 확장 결과를 출력한다. apt는 호출하지 않는다.
3. **순서 실수의 회전 오차** (yaw θ ∈ {0, 30, 45, 90, 135, 180, −90, −150}°):
   - 정상 `(x,y,z,w) = (0, 0, sin θ/2, cos θ/2)`, w 먼저 배열 `(cos θ/2, 0, 0, sin θ/2)`를 만든다.
     ros-base에 transforms3d가 없으면 `euler2quat(0, 0, θ)`와 같은 정의의 yaw 식으로 대신 만들고,
     있으면 실제 `transforms3d.euler.euler2quat`를 쓴다(출력의 `producer` 필드에 어느 쪽인지 기록).
   - 정상·실수 A·실수 B 세 메시지를 각각 `TransformStamped`의 rotation으로 `tf2_ros.Buffer.set_transform_static`에
     저장하고 `lookup_transform("base_link", child)`로 다시 꺼낸다.
   - tf2가 돌려준 쿼터니언으로 x·y·z 단위축을 회전시켜 3×3 회전 행렬을 만든다.
   - 측정: heading = atan2(r10, r00), 상방축 z 성분 r22, 정상 행렬과의 회전 오차각
     acos((trace(Rᵀ_ok · R_mistake) − 1)/2), 실수 배열의 크기 제곱.
   - 같은 θ로 예측식 2·acos(|sin θ|/2)를 계산해 측정 오차각과 1e−6° 이내로 일치하는지 `match`로 출력한다
     (예측값은 비교용이며 결과를 코드에 적어 두지 않는다).
4. **대조군**: 크기가 1이 아닌 `(0,0,1,1)`을 같은 경로로 넣고, tf2가 돌려준 쿼터니언과 heading을 출력한다.
5. **테스트 입력의 검출력**: 다섯 입력(모두 0.5, 부호 교대, yaw 180°, 항등, yaw 90°)을 한 칸 순환 이동
   (w 먼저 소비자가 x,y,z,w 배열을 읽을 때의 자리 이동)한 뒤 둘 다 tf2를 거쳐 회전 차이각,
   성분 차이 제곱합, 원래 입력으로 회전시킨 전방·좌측 축 좌표를 출력한다. 회전 차이가 0이 아니면 `caught=true`.
6. 각 측정은 `{"kind": ...}` JSON 한 줄. 마지막 `summary`에 정규화 검사로 잡힌 실수 건수, 저장한 변환 수, 경과 시간.

실패 판정: 스크립트 예외로 종료 코드가 0이 아니거나, `yaw_case_error`가 나오거나, `match=false`가 하나라도 나오면
예측식과 tf2 결과가 어긋난 것으로 본다(이 경우 글은 예측식이 아니라 측정값을 따른다).

## 한계

- ros-base 이미지에 transforms3d가 없으면 w 먼저 배열은 라이브러리 출력이 아니라 같은 정의의 식으로 만든 값이다.
  `producer` 필드로 구분된다. 네트워크가 없어 apt 설치·실제 `tf_transformations` 호출은 하지 않는다.
- DDS 통신(브로드캐스터·리스너)을 거치지 않고 같은 프로세스의 tf2 Buffer만 사용한다.
- 평면 yaw만 다룬다. roll·pitch가 섞인 일반 자세의 오차 분포는 재지 않는다.

## 시행착오 (시험 실행 `--try`)

1. 첫 시험 실행은 성공(종료 코드 0)했지만 출력이 길어 하네스가 저장하는 stdout 마지막 8000자에서
   앞부분(환경·패키지 줄)이 잘렸다. 필드 이름을 줄이고 축 좌표 출력을 상방축 z 성분으로 줄여 전체 출력을 8000자 안으로 맞췄다.
2. `tf2_ros.Buffer.set_transform_static`의 반환값을 "tf2가 받아들였는지"로 기록하려 했으나 Python API는 `None`을 돌려줘
   의미가 없었다. 반환값 대신 lookup으로 다시 꺼낸 쿼터니언 자체를 대조군 출력에 남기도록 바꿨다.
   이 과정에서 크기가 1이 아닌 대조군 입력이 거부되지 않고 조회된다는 것을 확인했다(값은 results.json의 `denormalized_control`).
3. 반올림 결과에 `-0.0`이 섞여 나와 `round(v, 6) + 0.0`으로 0.0으로 통일했다.
4. 시험 실행 환경에서 `tf_transformations`, `transforms3d`는 import 불가·미설치로 나와, w 먼저 배열은
   대체 식(`w_first_yaw_formula(emulated)`)으로 만들어졌다.
