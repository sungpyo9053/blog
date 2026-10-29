# 실험 계획: 합성 이미지 토픽이 실제로 초당 몇 MB를 받는가

## 질문

Gazebo 없이 같은 해상도의 합성 `sensor_msgs/Image`(rgb8)를 목표 Hz로 발행하면, 다른 프로세스의
구독자가 받은 바이트/초와 Hz가 `W × H × 3 × fps` 계산과 얼마나 맞는가? 해상도가 커지면 어디서부터
목표 Hz를 못 받는가? QoS(best effort depth 5 / reliable depth 10 / depth 1)에 따라 달라지는가?

이 실험은 Gazebo의 렌더링·GPU→CPU 복사 비용을 재지 않는다. 메시지 경로(직렬화·Fast DDS·Python
구독자)만의 부담을 보는 대조군이다.

## research.md 기준 예측값 (실행 전 계산값, 측정 아님)

1 MB = 1,000,000 B (`ros2 topic bw`와 같은 10⁶ 기준). rgb8 = 픽셀당 3바이트.

| 조건 | 프레임 바이트 | 목표 Hz | 예측 MB/s | depth 상한 |
|---|---|---|---|---|
| 640×480 | 921,600 | 30 | 27.648 | depth 5: 4.608 MB / depth 10: 9.216 MB |
| 1280×720 | 2,764,800 | 30 | 82.944 | depth 5: 13.824 MB / depth 10: 27.648 MB |
| 1920×1080 | 6,220,800 | 30 | 186.624 | depth 5: 31.104 MB / depth 10: 62.208 MB |
| 3840×2160 | 24,883,200 | 30 | 746.496 | depth 5: 124.416 MB |
| 4512×4512 (질문자 설정) | 61,074,432 | 19 | 1160.414 | depth 1: 61.074 MB / depth 5: 305.372 MB / depth 10: 610.744 MB |

- 직렬화된 메시지는 header·encoding 문자열·길이 필드 때문에 `W×H×3`보다 "약간" 클 것이다. research는
  정확한 오버헤드 바이트를 예측하지 않았다.
- sensor data 프로필 depth는 rmw 소스상 5, best effort다.
- research는 "어디서부터 목표 Hz를 못 받는지"를 예측하지 않았다. 열린 질문으로 둔다.

## 무엇을 어떻게 재는가

환경: 하네스의 `ros:jazzy-ros-base` 컨테이너. 네트워크 없음, 1 CPU, 1 GiB. rmw_fastrtps_cpp 기본 설정.
rclpy·sensor_msgs·표준 라이브러리만 쓴다(numpy, Gazebo, image_transport 미사용).

1. **직렬화 크기·시간(전송 없음):** 해상도별로 Image를 한 번 만들고, `rclpy.serialization.serialize_message`를
   예열 1회 뒤 3회 호출한다. 직렬화 바이트 수, `직렬화 바이트 − W×H×3` 오버헤드, 3회 중앙값(ms)을 출력한다.
   depth 5·10 상한 MB는 실행 중 읽은 `qos_profile_sensor_data.depth`와 10으로 계산해 함께 적는다.
2. **프로세스 간 발행·구독:** 조건마다 구독자를 별도 Python 프로세스로 띄운다. 발행자는 메인 프로세스다.
   - 이미지 버퍼는 조건마다 한 번만 만들어 재사용한다(`array.array('B')`). 발행 루프에는 header stamp 갱신과
     `publish()`만 있다.
   - 발행자는 구독 매칭(`get_subscription_count() > 0`)을 기다린 뒤 목표 주기로 발행한다. 밀리면 따라잡지 않고
     다음 주기로 넘어간다. 발행 횟수, 실제 발행 Hz, `publish()` 호출 평균 시간(ms)을 잰다.
   - 구독자는 `ros2 topic bw`처럼 `raw=True`로 직렬화 바이트열을 받아 `len()`과 수신 시각(`time.monotonic`,
     벽시계)을 기록한다. 첫 수신 이후 2.5초 동안 기록한다. 수신 Hz = (n−1)/(마지막−첫 수신 시각),
     수신 MB/s = 첫 메시지를 뺀 바이트 합 / 같은 구간이다.
   - 비율: 수신 MB/s ÷ 예측 MB/s, 수신 Hz ÷ 발행 Hz.
   - 메모리: 구독 프로세스의 `/proc/self/status` VmHWM(최대 상주 메모리)과 발행 프로세스의 VmHWM을 잰다.
     발행 프로세스는 조건 시작 전에 `/proc/self/clear_refs`에 5를 써서 최대치를 되돌린다. 성공 여부를
     `pub_rss_reset`으로 남긴다.
3. **조건(순서대로):**
   - sensor_data(best effort, depth 5) × 640×480, 1280×720, 1920×1080, 3840×2160 @ 30 Hz
   - default(reliable, depth 10) × 640×480, 1280×720, 1920×1080 @ 30 Hz
   - 4512×4512 @ 19 Hz × best effort depth 1, reliable depth 1
   - 3840×2160 이상은 1 GiB 한도 때문에 depth 10으로 돌리지 않는다.
4. **출력:** JSON 한 줄씩. `kind`가 `env`, `serialize`, `condition`, `skipped`, `done`이다. 스크립트 시작 후 48초(내부 예산)가
   지나면 남은 조건은 `skipped`로 남긴다. 결과 숫자는 코드에 미리 적지 않는다.

### 해석 경계

- 같은 컨테이너 안의 프로세스 간 전송이다(공유 메모리·loopback). 실제 네트워크, Gazebo 렌더링, GPU readback,
  C++ 구독자를 대표하지 않는다.
- 1 CPU를 발행자·구독자·DDS 스레드가 나눠 쓴다. 큰 해상도에서 목표 Hz를 못 받는 것은 이 환경에서 메시지
  경로만으로 생긴 한계이며, 다른 머신의 한계값으로 일반화하지 않는다.
- VmHWM은 rclpy·DDS를 포함한 프로세스 전체 메모리다. depth × 프레임 바이트 상한과 1:1로 비교하지 않는다.
- 수신 Hz는 짧은 창에서 도착 간격으로 계산하므로 발행 Hz보다 아주 조금 높게 나올 수 있다(도착 지터).

## 시행착오 (시험 실행에서 실제로 실패하거나 고친 점)

1. 첫 시험 실행에서 가장 작은 해상도의 직렬화 시간이 더 큰 해상도보다 길게 나왔다. 첫
   `serialize_message` 호출에 타입 지원 로딩 비용이 섞였기 때문이다. 예열 1회와 3회 중앙값으로 바꿨다.
2. 첫 설계(640×480·1280×720·1920×1080 × QoS 2종)에서는 모든 조건이 목표 Hz에 가깝게 수신돼
   "어디서부터 못 받는가"에 답할 수 없었다. 3840×2160(depth 5)과 질문자 설정 4512×4512 @ 19 Hz(depth 1,
   best effort·reliable)를 추가했다.
3. 구독 프로세스의 최대 메모리를 `resource.getrusage(...).ru_maxrss`로 쟀더니, 모든 조건에서 부모(발행)
   프로세스의 값과 똑같이 나왔다. Linux에서 이 값은 exec 뒤에도 부모의 최대치를 이어받는다. 구독자는
   `/proc/self/status`의 VmHWM으로 바꿨다. 발행자는 조건마다 clear_refs로 최대치를 되돌린 뒤 VmHWM을 읽도록 고쳤다.
4. 조건을 늘리자 컨테이너 포함 실행 시간이 60초 한도에 가까워졌다. 수신 기록 창을 3초에서 2.5초로, 추가
   발행 여유를 1.5초에서 1.0초로 줄였다. 하나의 `publish()` 호출이 오래 걸려도 전체 예산을 넘기지 않도록
   발행 루프에 시각 상한을 넣었다.
5. 4512×4512 best effort depth 1 조건은 시험 실행에서 구독자가 창 안에서 메시지를 1개만 받아 수신 Hz를
   계산할 수 없었다(간격이 0개). 이 경우 `sub_rx_hz`는 비우고 `sub_received`와 `sub_window_s`만 남긴다.
   이것은 측정 실패가 아니라 결과다.
