# 실험 계획: PointCloud2를 laser → base_link로 옮길 때 무엇이 남고 무엇이 바뀌는가

## 질문

`research.md`는 소스 읽기와 산술 검산만으로 "xyz만 꺼내 `create_cloud`로 다시 만들면 intensity가 빠지고
frame_id는 laser로 남는다", "공식 `do_transform_cloud`는 필드와 target frame_id를 유지하지만 Jazzy에서는
끝 패딩 클라우드에서 실패한다"고 예측했다. 이 실험은 ROS 2 Jazzy ros-base 이미지의 실제
`sensor_msgs_py`·`tf2_sensor_msgs`·`tf2_ros`로 같은 합성 클라우드를 처리해, 결과 메시지의 필드 이름·
`point_step`·`len(data)`·`height/width`·`header.frame_id`·intensity 값을 실행 중에 잰다.

1. (A) `read_points_numpy`로 xyz를 꺼내 R·p+t를 적용하고 x·y·z 필드 정의 + 원본 `msg.header`로
   `create_cloud`를 부르면 결과 메시지는 어떤 모양인가? 옛 intensity offset 12를 믿고 읽으면 무엇을 읽는가?
2. (A2) 원본 header 객체를 넘긴 뒤 결과의 frame_id를 고치면 원본 메시지의 frame_id도 바뀌는가?
3. (B) N×3 배열과 원본 4필드를 함께 넘기면 어떻게 되는가?
4. (C) `read_points(cloud).copy()`의 xyz만 바꾸고 새 Header(stamp 유지, frame_id=base_link) +
   원본 fields + `point_step=cloud.point_step`으로 다시 만들면 원본과 같은 레이아웃이 되는가?
   (research.md "발행 전 검사 패턴" 후보 코드를 그대로 실행한다.)
5. (C0) `read_points` 결과를 복사 없이 고치면 원본 메시지 data가 바뀌는가?
6. (D·D2) `do_transform_cloud`에 TransformStamped / 일반 Transform을 넘기면 frame_id·필드·원본 불변은?
7. (E·E2·E3) 끝 패딩 클라우드(point_step 32)에서 `do_transform_cloud`, point_step 명시 재생성,
   xyz만 재생성은 각각 어떻게 되는가?
8. (F) organized 클라우드(width 4, height 3)를 `do_transform_cloud`에 넣으면 모양이 유지되는가?
9. (G·G0) `tf2_ros.Buffer.transform(cloud, 'base_link')`는 `import tf2_sensor_msgs` 유무에 따라 어떻게 되는가?
10. (H) 실제 토픽 경로(`/tf_static` 정적 변환 + `/cloud_laser` 발행 → 변환 노드가 `Buffer.transform` →
    `/cloud_base` 수신)에서 직렬화를 거쳐 받은 메시지도 같은 판정을 통과하는가?

## research.md 기준 예측값 (실행 전)

공통 입력: width 1000, height 1, 필드 x·y·z·intensity float32 offset 0·4·8·12, point_step 16,
data 16000바이트, frame_id `laser`, 점 0 = (1.0, 0.5, 0). TransformStamped(header.frame_id=base_link,
child_frame_id=laser, translation (0.25, 0, 0.125), rotation z=w=√0.5 ≈ 0.70710678, 즉 z축 +90°).

| 경우 | 예측 |
|---|---|
| A | fields x·y·z 3개, point_step 12, len(data) 12000(원본 대비 75%, 25% 감소), frame_id laser, intensity 없음, 점 0 ≈ (−0.25, 1.0, 0.125), 예외 없음 |
| A′ | 점 2의 옛 offset 12 위치 = 바이트 36 = 점 3의 x 시작 바이트. 비교한 모든 점에서 다음 점의 x와 같은 값 |
| A2 | 같은 Header 객체이므로 원본 frame_id도 base_link로 바뀐다(예측) |
| B | 예외(열 수 3 ≠ 필드 수 4) |
| C | fields 4개, point_step 16, len(data) 16000, intensity 원본과 동일, frame_id base_link, stamp 유지, height 1·width 1000, 원본 불변 |
| C0 | 원본 data가 바뀐다(read_points는 원본 바이트 위의 뷰) |
| D | C와 같은 판정, xyz는 C와 허용오차 안에서 일치, 원본 data·header 불변, is_dense False |
| D2 | frame_id laser 유지, 좌표는 D와 같음 |
| E | Jazzy 5.3.8에서 AssertionError("PointFields and structured NumPy array dtype do not match ...") |
| E2 | 성공, point_step 32, len(data) 32000 |
| E3 | point_step 12, len(data) 12000(원본 32000 대비 37.5%), 패딩도 사라짐 |
| F | height 1, width 12, len(data) 192로 동일, is_dense False |
| G | frame_id base_link, 필드 유지 |
| G0 | PointCloud2를 처리하지 못하는 예외(tf2_ros 등록 없음) |
| H | G와 같은 판정이 수신 메시지에서도 성립 |

좌표 허용오차: float32 저장 반올림을 고려해 손 공식 대비 최대 절대 오차 1e-6 m 이하면 일치로 본다.

## 무엇을 어떻게 재는가

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB). rclpy, tf2_ros, tf2_sensor_msgs,
  sensor_msgs_py, std_msgs, geometry_msgs, NumPy(이미지 포함)만 쓴다. 버전은 실행 중에
  `/opt/ros/jazzy/share/<pkg>/package.xml`과 `numpy.__version__`에서 읽어 `env` 줄로 출력한다.
- 입력 클라우드는 `create_cloud`를 쓰지 않고 NumPy 구조화 배열(offset·itemsize 지정)을 `tobytes()`로 직접
  포장해 만든다. 검사 대상 함수가 자기 입력을 만들지 않도록 하기 위해서다. intensity는 점마다 다른 값.
- 경우마다 새 입력 클라우드를 만들고, 결과 메시지에서 다음을 실행 중에 계산해 JSON 한 줄(`kind: case`)로 출력한다:
  필드 이름·offset, point_step, row_step, height/width, `len(data)`, `width×height×point_step`과의 일치,
  원본 대비 `len(data)` 비율, frame_id, stamp, is_dense, 점 0 좌표, 손 공식((x, y)→(−y, x) 후 t 더하기,
  입력값에서 NumPy float64로 계산) 대비 최대 절대 오차와 허용오차 통과 여부, intensity 존재·원본과 완전 일치 여부,
  변환 전후 원본 메시지 바이트·frame_id·stamp 불변 여부, 결과 header가 원본과 같은 객체인지.
- A′: A 결과의 바이트를 float32로 보고 점 i의 옛 offset 12 값과 점 i+1의 x 값을 모든 i에서 비교해 같은 개수를 센다.
- 예외는 측정값으로 취급해 타입과 메시지 원문(300자)을 기록한다(B·E·G0).
- G0는 `tf2_sensor_msgs`를 import하지 않은 새 python3 자식 프로세스에서 같은 `Buffer.transform` 호출을 해
  `sys.modules` 등록 여부와 결과를 받는다.
- H는 한 프로세스에 노드 세 개(talker: StaticTransformBroadcaster + `/cloud_laser` 발행, transformer:
  TransformListener 버퍼 + `Buffer.transform` 후 `/cloud_base` 발행, checker: 수신)를 SingleThreadedExecutor로
  돌리고 최대 15초 기다린다. 변환 준비 시간과 수신까지 걸린 시간도 잰다.
- 경우별 소요 ms와 전체 소요 시간도 출력한다(단일 1 CPU 컨테이너 기준, 성능 비교용 아님).
- 결과 숫자는 코드에 적지 않는다. 코드의 숫자는 입력(점 수, offset, point_step 16·32, 4×3 격자, 변환값)과
  대기 한도·허용오차뿐이다.

## 시행착오 (시험 실행)

- 1차 시험 실행(`--try`): 모든 경우가 예외 처리 의도대로 끝났고 종료 코드 0. 실패나 수정할 오류는 없었다.
  이미지가 처음 받아져 그 회차의 실행 시간에는 이미지 다운로드가 포함됐다.
- 수정 1건: 1차 결과에서 좌표 오차는 출력됐지만 허용오차(1e-6 m) 통과 여부가 따로 없어 Writer가 판정을
  직접 해야 했다. `within_tol` 필드를 추가하고 2차 시험 실행했으며 역시 종료 코드 0이었다.
- 관찰(실패 아님): D와 C는 좌표가 허용오차 안에서 같지만 바이트까지 동일하지는 않다. C는 스크립트가 만든 회전행렬,
  D는 tf2_sensor_msgs 내부 회전행렬을 써서 float 반올림 경로가 다르기 때문으로 해석하며, 그래서 바이트 동일성이
  아니라 좌표 최대 차이로 비교한다.

## 한계

- 합성 메시지 실험이며 실물 라이다·깊이 카메라·로봇에서 검증하지 않았다.
- 90° 한 각도, float32 4필드 레이아웃, 끝 패딩 한 종류(32바이트), organized 4×3 한 크기만 다룬다.
  row 끝 패딩(row_step > width×point_step), NaN 점, normal 같은 방향 필드, 시간 동기 lookup은 다루지 않는다.
- 결론은 sensor_msgs_py 5.3.8 · tf2_sensor_msgs 0.36.23(실행 중 출력값으로 확인) 기준이다. Jazzy 백포트
  PR #326이 릴리스되면 E의 결과가 바뀔 수 있다.
