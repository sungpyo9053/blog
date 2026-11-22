# 실험 계획: 스테레오 baseline은 camera_info 어디에 있고, 시차에서 깊이는 어떻게 나오는가

## 질문

1. ROS 2 Jazzy `sensor_msgs/CameraInfo`에 baseline 전용 필드가 정말 없는가? 왼쪽·오른쪽 camera_info를 실제
   rclpy 토픽으로 주고받았을 때 baseline 정보는 어느 칸(`p[3]`)에 남고, 왼쪽은 왜 0인가?
2. 받은 메시지에서 `B = -p[3] / p[0]`로 계산하면 설계 baseline이 그대로 나오는가? 흔한 오답(Tx를 그대로 씀,
   K의 fx로 나눔, 왼쪽 camera_info를 읽음, 보정 길이 단위 mm)은 각각 얼마로 틀리는가?
3. 같은 3D 점을 **받은** 두 P 행렬로 투영하면 시차가 몇 픽셀이 되고, `Z = -Tx / d`로 원래 깊이가 돌아오는가?
4. 깊이가 멀어질수록 시차 1픽셀 차이(그리고 정수 픽셀·1/16픽셀 양자화)가 깊이를 얼마나 흔드는가?
5. binning, 좌우 cx'가 다른 경우, 좌우 토픽이 뒤바뀐 경우, `stereo_msgs/DisparityImage`의 float32 `f`·`t`는
   결과를 어떻게 바꾸는가? ros-base 이미지에 `image_geometry`가 들어 있는가?

## research.md 기준 예측값

research.md(CameraInfo.msg 정의, image_geometry·stereo_image_proc 소스 읽기, verification.json 산술 검산)에서
나온 실행 전 예측이다. 실측이 아니다. 입력: fx' = 700 px, cx' = 320 px, cy' = 240 px, B = 0.12 m,
K의 fx = 750 px, 점 (0.5, 0, 2.0) m.

- CameraInfo 필드 이름 중 baseline이 들어간 필드: 없음.
- 왼쪽 `p[3]` = 0, `p[7]` = 0. 오른쪽 `p[3]` = −84, `p[7]` = 0.
- B = −(−84)/700 = 0.12 m. 오답: Tx 그대로 84(700배), K의 fx로 나누면 0.112 m(약 −6.7%),
  왼쪽을 읽으면 0, mm로 보정하면 120(1000배).
- 투영: x_l = 495 px, x_r = 453 px, 두 영상 y 모두 240 px, d = 42 px, Z = 84/42 = 2 m.
- 깊이 스윕(Z = 0.5, 1, 2, 4, 8, 16, 32 m)의 시차 = 84/Z = 168, 84, 42, 21, 10.5, 5.25, 2.625 px.
  시차를 1픽셀 덜 읽으면 4 m → 4.2 m(0.2 m), research.md의 d 4→3 사례처럼 먼 곳일수록 차이가 급격히 커진다.
  1차 근사 ΔZ ≈ Z²/(fx'·B)·Δd는 정확값보다 작게 나올 것이다.
- binning 2: fx' 350, Tx −42로 같이 줄어 B = 0.12 m 그대로. binning된 영상의 시차(21 px)에 원래 Tx(−84)를
  쓰면 깊이가 2배(4 m)로 틀린다.
- 오른쪽 cx' = 330(왼쪽 320): 원시 시차는 cx' 차이(10 px)만큼 줄어 32 px, 보정 없이 Z = 84/32 = 2.625 m.
  (cx'_l − cx'_r) = −10을 빼면 42 px, 2 m로 돌아온다.
- 좌우 토픽이 뒤바뀌면 "오른쪽"으로 믿은 메시지에서 B = 0, 시차 부호가 반대(−42 px)라 깊이가 −2 m.
- DisparityImage의 `t`는 float32라 0.12가 정확히 표현되지 않지만, 깊이 오차는 마이크로미터 이하일 것이다.
  min/max disparity 1·128 px이면 측정 가능 범위 Z_min = 84/128, Z_max = 84/1.
- ros-base에는 vision_opencv(image_geometry)가 없을 것으로 예측(perception 이미지 소속).

## 무엇을 어떻게 재는가

- 환경: 하네스의 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB). rclpy, sensor_msgs, stereo_msgs,
  numpy만 쓴다. 실제 카메라·드라이버·Gazebo·stereo_image_proc는 실행하지 않는다.
- 노드 두 개를 한 프로세스의 SingleThreadedExecutor에서 돌린다.
  - `stereo_driver`: CameraInfo.msg 정의대로 P를 만든다. 왼쪽 Tx = 0, 오른쪽 Tx = −fx'·B(실행 중 계산).
    변형으로 mm 보정(Tx = −fx'·B·1000), cx'가 다른 오른쪽, 그리고 DisparityImage(f = fx', t = B, 깊이 스윕의
    시차를 32FC1 한 줄 영상으로)를 RELIABLE + TRANSIENT_LOCAL QoS로 발행한다.
  - `stereo_consumer`: 다섯 토픽을 구독하고, 이후 모든 계산은 **받은 메시지**의 `p`, `k`, `f`, `t`, 영상 바이트로 한다.
- 측정 항목(JSON 줄, `metric` 키):
  - `transport`: 디스커버리 시간, 받은 토픽, 발행→콜백 지연(ms).
  - `received_p_exact`: 보낸 p 12칸과 받은 p가 비트 단위로 같은지, rclpy가 주는 필드 타입.
  - `p_fields`: 좌우 p[0], p[2], p[3], p[7], 오른쪽 k[0], CameraInfo 필드 이름 중 "base"가 들어간 것.
  - `baseline`: 정답식과 오답 네 가지의 값과 비율.
  - `worked_point`: 받은 P로 점을 투영한 x_l, x_r, y_l, y_r, 시차, Z(= −Tx/d, = fx'·B/d).
  - `depth_sweep`: 점 (0.3, 0, Z)를 투영해 잰 시차, 되돌린 Z, 시차 −1 px일 때 Z와 차이, 정수 픽셀(1 px)·
    1/16 px 양자화의 반 단계 오차 범위(먼 쪽·가까운 쪽), 1차 근사 Z²/(−Tx).
  - `binning`: image_geometry PinholeCameraModel의 binning 규칙(P의 해당 칸을 1/b로)을 적용한 P로 투영·계산.
  - `unequal_cx`: cx' 보정 전후 시차와 깊이.
  - `swapped_topics`: 좌우를 바꿔 읽었을 때의 B, 시차, 깊이.
  - `disparity_image`: 받은 float32 t와 float64 B의 차, 받은 시차 영상에서 Z = f·t/d, float64 대비 최대 오차,
    min/max disparity가 정하는 깊이 범위.
  - `image_geometry`: import 가능 여부(가능하면 baseline()과 get_z(42)).
- 한계: 산술·메시지 전달 실험이다. 실제 렌즈 보정 정확도, 시차 매칭 품질, 실물 깊이 잡음은 재지 않는다.
  양자화 오차는 "보고되는 시차가 단계 q로 반올림될 때의 최대 오차"라는 모델이며 특정 매처의 측정값이 아니다.

## 시행착오

- 첫 시험 실행에서 `rclpy.executors`를 명시적으로 import하지 않은 채 `rclpy.executors.SingleThreadedExecutor`를
  쓰려 해서, 실행 전에 `import rclpy.executors`를 추가했다(실행 실패로 확인한 것은 아니고 코드 검토 중 수정).
- 첫 시험 실행(성공)에서 정수 픽셀 반올림을 `round(x_l) − round(x_r)`로 쟀더니, 이 입력에서는 x가 정확히 .5에
  떨어지는 경우가 많아 Python의 은행가 반올림(짝수 쪽) 때문에 Z = 4 m에서 시차 21이 20으로 바뀌어 0.2 m 오차가
  나왔다. 이것은 스테레오 원리가 아니라 반올림 규칙의 산물이라, 시차를 단계 q(1 px, 1/16 px)로 양자화했을 때의
  반 단계 최대 오차(d ± q/2)로 바꿨다.
- 같은 실행에서 왼쪽 camera_info로 계산한 B가 `-0.0`으로 출력돼(−0.0/700) 독자가 부호 문제로 오해할 수 있어
  `+ 0.0`으로 0.0을 출력하게 했다. 값 자체는 같다.
- ros-base 이미지에서 `image_geometry` import는 `ModuleNotFoundError`였다(예측과 일치). 그래서 binning·cx' 보정은
  image_geometry 소스의 규칙을 코드로 옮겨 계산했다.
