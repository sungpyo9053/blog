# 실험 계획: ROS 2 Jazzy에서 PointCloud2를 xyz 배열로 바꿀 때 점 개수·바이트 위치·skip_nans 동작 실측

## 질문

ROS 2 Python 노드가 받은 `sensor_msgs/PointCloud2`의 `data` 바이트 덩어리를
`sensor_msgs_py.point_cloud2.read_points_numpy`로 `(N, 3)` xyz 배열로 바꿀 때 다음이 맞는가?

1. 점 개수는 `width*height`이고, 점 i의 z는 `i*point_step + z.offset` 바이트에서 시작한다.
2. `skip_nans=True`는 `is_dense=False`일 때만 NaN 점을 뺀다.
3. 같은 타입 검사는 고른 필드끼리가 아니라 `fields[0]`을 기준으로 비교한다.
4. inf는 `skip_nans`로 걸러지지 않는다.
5. `reshape_organized_cloud`는 `(width, height)` 모양을 만든다. `uvs`는 NaN 제거 뒤에 인덱싱한다. `row_step`은 쓰지 않는다.

## research.md 기준 예측값(소스 판독 기반, 실측 아님)

| 항목 | 입력 | 예측 |
| --- | --- | --- |
| 점 개수 | 640 × 480, point_step 16 | 307200 |
| data 길이 | 640 × 480 × 16 | 4915200 바이트 |
| 인덱스 1000 점의 z 시작 | 1000 × 16 + 8 | 16008 바이트 (행 1, 열 360) |
| 전체 패딩 | 640 × 480 × (16 − 12) | 1228800 바이트 |
| xyz float32 배열 | 307200 × 3 × 4 | 3686400 바이트, shape (307200, 3) |
| struct로 읽은 z와 read_points_numpy z | 전체 점 비교 | 불일치 0 |
| skip_nans, is_dense=False, NaN 점 40000개 | 307200 − 40000 | 267200행, NaN 행 0 |
| skip_nans, is_dense=True (같은 데이터) | 필터 미실행 | 307200행, NaN 행 40000 |
| 타입 검사 예 A: [x,y,z,intensity f32, ring u16] + ['x','y','z'] | | 통과, (16, 3) float32 |
| 예 B: 같은 레이아웃 + field_names=None / ['x','ring'] | | AssertionError |
| 예 C: [ring u16, x,y,z f32] + ['x','y','z'] | | read_points_numpy AssertionError, read_points + structured_to_unstructured는 (16, 3) |
| 라이다 레이아웃 10번 점 ring 시작 | 10 × 32 + 16 | 336 바이트, struct 값 = read_points 값 |
| inf 행 2개 + NaN 행 1개가 든 5점 클라우드, skip_nans | | 4행 남음(inf 2행 잔존). isfinite 마스크는 2행 |
| reshape_organized_cloud, height 2 × width 3 | | shape (3, 2). 첫 "행"은 평탄 순서 점 0, 1이라 이미지 한 행이 아님 |
| NaN 있는 정렬 클라우드에서 skip_nans + reshape | | ValueError |
| 점 0의 x가 NaN(원래 인덱스는 y에 기록), skip_nans=True, uvs=[0] | | 원래 점 1을 돌려줌. skip_nans=False면 점 0 |
| row_step = 3×16 + 8 = 56, height 2 | | 두 번째 행 첫 점 x가 실제(10)와 다르게 읽힘 |
| data가 width×height×point_step보다 16바이트 짧음 | | TypeError(buffer is too small) |

## 무엇을 어떻게 재는가

- 환경: 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 실행한다. 사용 패키지는 rclpy, sensor_msgs, sensor_msgs_py, ament_index_python, numpy뿐이다. 실행 중 `sensor_msgs_py` package.xml 버전, numpy·Python 버전, 바이트 순서를 출력한다.
- 입력: 640×480 정렬 클라우드(x, y, z float32, offset 0/4/8, point_step 16, 행 끝 패딩 없음)를 NumPy 구조화 배열로 직접 만든다. 시드 23782로 고른 40000개 점의 x/y/z 중 한 칸에 NaN을 넣는다. `create_cloud`는 항상 `is_dense=False`로 만들기 때문에 쓰지 않고, 메시지 필드를 직접 채운다.
- 구독 경로: 같은 프로세스의 rclpy 노드에서 `probe_cloud` 토픽으로 publish하고 subscribe 콜백으로 한 번 받는다(최대 20초). 이후 측정은 모두 **받은 메시지**로 한다. 받은 `width`, `height`, `point_step`, `row_step`, `is_dense`, `fields`, `len(data)`를 출력한다.
- 바이트 위치: 인덱스 0, 1000, 307199에서 `struct.unpack_from('<f', data, i*point_step + z.offset)`와 `read_points_numpy(...)[i, 2]`를 비교한다. 전체 점은 stride가 point_step인 NumPy 뷰로 비교해 불일치 개수를 센다.
- 열 순서: `field_names=['z','x']`의 열 순서를 확인한다.
- skip_nans/is_dense: 받은 메시지의 `is_dense`를 False/True로 바꿔 가며 `skip_nans=True` 결과의 행 수와 남은 NaN 행 수를 센다. `np.isfinite` 마스크 결과 행 수도 함께 센다.
- 타입 검사: 라이다식 point_step 32 레이아웃(예 A, B)과 첫 필드가 uint16인 레이아웃(예 C)에서 결과 shape/dtype 또는 예외 종류·문구를 기록한다.
- inf, reshape, uvs, row_step, 짧은 data: 작은 합성 클라우드로 행 수, shape, 예외 종류를 기록한다. reshape는 각 점의 x에 열 번호, y에 행 번호를 넣는다. 그다음 `(width, height)` 결과의 각 "행"이 이미지 두 행에 걸치는지 세고, 직접 `reshape(height, width, 3)`한 결과와 비교한다. uvs는 y에 원래 인덱스를 넣고 반환된 점의 y를 기록한다. row_step은 행 끝마다 8바이트를 덧붙인 data에서 두 번째 행 첫 점의 x를 실제 값(struct, `row_step` 기준 위치)과 비교한다.
- 출력: 항목마다 `{"measure": ...}` JSON 한 줄을 출력한다. 결과 숫자는 코드에 적지 않고 실행 중에 계산한다. 위 예측표는 비교용이다.
- 범위 밖: 실제 센서 드라이버·하드웨어, Humble 런타임, 속도·메모리 성능. 처리 시간은 실행 확인용 경과 시간만 기록하며 성능 근거로 쓰지 않는다.

## 시행착오

시험 실행은 `scripts.experiment_runner --try`로 두 번 했다. 두 번 모두 exit 0이었다.

1. 1차 시험: uvs 항목의 `skip_nans=False` 결과를 반환된 점의 x로 기록했다. 그런데 그 점은 x가 NaN인 점 0이었다. 그래서 출력에 JSON 표준이 아닌 `NaN` 토큰이 찍혔고, 원래 인덱스도 읽을 수 없었다. → 원래 인덱스를 y에 넣고 y를 출력하도록 고쳤다. 또 `emit`이 NaN/inf를 문자열로 바꾸고 `allow_nan=False`로 출력하게 했다.
2. 1차 시험: reshape 지표 "첫 행이 이미지 한 행인가"가 true로 나왔다. height 2 × width 3에서 `(3, 2)`의 첫 "행"은 점 0, 1이고, 둘 다 우연히 이미지 0행에 있기 때문이다. 이 지표로는 축 순서 문제가 드러나지 않았다. → 모든 "행"의 (열, 행) 좌표를 출력하고, 이미지 두 행에 걸친 "행"의 개수를 세도록 바꿨다. 직접 `reshape(height, width, 3)`한 결과도 같은 방식으로 센다.
3. 바이트 위치 비교의 `equal` 값이 NaN 경로에서 numpy bool이 되면 JSON 직렬화가 실패할 수 있다. 그래서 `bool()`로 감쌌다. 이번 시드에서 실제로 실패한 적은 없고, 예방 차원의 수정이다.
4. 2차 시험: 17줄이 모두 엄격한 JSON으로 파싱됐다. 컨테이너 한 번 실행은 약 1.5초였고 stderr는 비어 있었다. rclpy 왕복은 publish 한 번으로 수신됐다. 받은 `data`는 `array` 타입이었고 `read_points_numpy`는 이를 그대로 처리했다.

