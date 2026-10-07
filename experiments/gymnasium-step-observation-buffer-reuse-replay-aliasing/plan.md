# 실험 계획: 같은 관측 배열을 고쳐 돌려주는 환경과 복사 없이 쌓는 버퍼

## 질문

환경이 `self` 안의 numpy 배열 하나를 제자리 수정(in-place)해 step()마다 그대로 돌려줄 때,
복사 없이 참조만 쌓는 버퍼(list, deque(maxlen=4))와 저장할 때 복사하는 버퍼에는 각각 어떤 관절각이
남는가? 그 기록으로 계산한 평균과 차분 속도는 얼마나 달라지는가? 마지막 원소만 보는 테스트와
가장 오래된 원소를 보는 테스트 중 어느 쪽이 이 버그를 잡는가? ROS 2 메시지 객체 하나를 재사용해
발행할 때, 발행 노드 안의 기록과 토픽을 건너 받은 구독 쪽 기록은 같은 영향을 받는가?

## 실행 환경과 제약

- 하네스가 `ros:jazzy-ros-base` 컨테이너(네트워크 없음, 1 CPU, 1 GiB)에서 `python3 /work/experiment.py`를 실행한다.
- 이미지에 gymnasium이 없으므로 Gymnasium의 `check_env()`는 측정하지 않는다. check_env 판정은
  research.md의 Research 단계 통제 비교와 Gymnasium 1.4.0 소스 근거로만 인용한다.
- 환경 클래스는 Gymnasium Env의 `reset() -> (obs, info)`, `step() -> (obs, reward, terminated, truncated, info)`
  반환 형태만 흉내 낸 설명용 산술 환경이다. 물리 시뮬레이터나 실제 로봇은 실행하지 않는다.
- 사용 모듈: 표준 라이브러리, numpy(이미지 내장), rclpy, sensor_msgs(ros-base 포함).

## research.md 기준 예측값

설명용 가정: 관절 1개, 매 step +0.25 rad, step 간격 Δt = 0.125 s, 4 step.

| 항목 | 예측 | 근거 |
| --- | --- | --- |
| 정상(copy) 버퍼 값 | 0.25, 0.5, 0.75, 1.0 rad, 평균 0.625 rad | verification.json 산술 |
| 재사용 + 참조 버퍼 값 | 네 칸 모두 1.0 rad, 평균 1.0 rad | 참조 저장 가정(research 통제 비교로 확인된 판정) |
| 평균 오차 | 0.375 rad | 산술 |
| 가장 오래된 원소 오차 | 0.75 rad | 산술 |
| 최신 원소 오차(마지막 칸만 비교) | 0 rad | 산술 |
| 차분 속도 | 정상 2 rad/s, 참조 버퍼 0 rad/s | 산술 |
| `obs[:]`(view), `np.asarray(obs)` | 재사용과 같은 결과 | NumPy 문서(basic indexing은 view, asarray는 맞는 ndarray면 복사 없음) |
| 저장할 때 복사(`np.array(obs)`, SB3 ReplayBuffer.add() 방식) | 반환 방식과 무관하게 정상 값 | SB3 2.9.0 buffers.py 소스 |

추가 측정에 대한 예측(research 산술을 확장한 것이며 실행 전 예측이다):

- deque(maxlen=4)에 6 step을 넣으면 정상은 0.75, 1.0, 1.25, 1.5 rad(평균 1.125 rad),
  재사용은 네 칸 모두 1.5 rad. 평균 오차 0.375 rad, 가장 오래된 원소 오차 0.75 rad로 4칸 창의 오차는 그대로다.
- 재사용 + list에서 step 수 N을 늘리면 가장 오래된 원소 오차 = 0.25 × (N − 1) rad,
  평균 오차 = 0.125 × (N − 1) rad로 길이에 비례해 커지고 최신 원소 오차는 항상 0.
- 마지막 원소 테스트는 네 방식 모두 통과(버그를 놓침), 가장 오래된 원소 테스트는 copy만 통과.
- ROS 2 JointState 하나를 재사용하며 `position[0]`을 고치면 발행 노드 안의 list는 네 칸 모두 마지막 값.
  구독 콜백이 받은 메시지는 rclpy가 발행 시점에 직렬화하고 받을 때 새 객체로 역직렬화하므로
  0.25, 0.5, 0.75, 1.0 rad가 그대로 남는다고 예측한다(가설이며 이번 실행으로 확인한다).
- 7관절 float64 배열의 `.copy()` 1회 비용은 마이크로초 미만으로 예측한다(구체 값은 예측하지 않는다).

## 무엇을 어떻게 재는가

모든 값은 실행 중 계산해 `{"m": ...}` 형식의 JSON 한 줄로 출력한다. 결과 숫자를 코드에 적어 두지 않는다.
참값(`expected_rad`)은 각 step 직후 환경 내부 값을 `float()`로 떼어 숫자로 따로 기록한 것이다.

1. `m=buffer`: 반환 방식 4종(`reuse`=`self._q`, `view`=`self._q[:]`, `asarray`=`np.asarray(self._q)`,
   `copy`=`self._q.copy()`) × 버퍼 3종(`list`에 4 step, `deque4`=`deque(maxlen=4)`에 6 step,
   `copy_on_store`=`np.array(obs)`로 복사해 4 step). 기록값, 참값, 평균과 평균 오차, 가장 오래된/최신 원소 오차,
   첫 쌍의 차분 속도(저장값/참값), 버퍼 안 서로 다른 객체 수(`id`), 첫 칸과 마지막 칸의
   `np.shares_memory` 여부. view는 객체 id가 달라도 메모리를 공유하는지 이 두 값으로 구분한다.
2. `m=reuse_length`: 재사용 + list에서 N = 2, 4, 8, 16, 64 step일 때 가장 오래된/평균/최신 원소 오차.
3. `m=unit_test`: 반환 방식 4종에서 "마지막 원소 == 참값", "가장 오래된 원소 == 참값", "전체 == 참값" 판정.
4. `m=ros2_jointstate`: 한 노드 안에 `joint_obs` 토픽 publisher와 subscription(RELIABLE, KEEP_LAST 16)을 만들고
   매칭을 기다린 뒤, `sensor_msgs/JointState` 객체 하나의 `position[0]`을 매 step +0.25 rad 고쳐 4번 발행한다.
   발행할 때마다 같은 객체를 발행 노드의 list에 append하고, 구독 콜백은 받은 메시지를 그대로 list에 append한다.
   두 list의 값, 서로 다른 객체 수, 가장 오래된 원소 오차, `position` 필드의 Python 타입, 수신 개수를 기록한다.
5. `m=cost_7joint`: 7관절 float64 배열에 대해 `ndarray.copy`, `np.array`, 참조 반환(호출 오버헤드 기준선)을
   20000회씩 7번 재고 1회당 중앙값·최솟값(ns)을 기록한다. 기준선과의 차이가 복사 자체의 대략적 비용이다.
6. `m=env`, `m=done`: Python·numpy 버전, 설명용 상수, 총 실행 시간.

판정 기준: `buffer`의 reuse/view/asarray × list·deque4에서 `oldest_err`가 0이 아니고 `newest_err`가 0이면
"참조 저장으로 오래된 기록이 덮어써지고 최신 칸 비교로는 보이지 않는다"는 예측이 확인된 것이다.
copy 또는 copy_on_store 행에서 오차가 0이 아니면 실험 설계가 잘못된 것으로 본다.

## 한계

- Gymnasium 자체, check_env, FrameStackObservation은 컨테이너에서 실행하지 않는다. deque4는
  FrameStackObservation이 내부 deque에 관측을 참조로 쌓는 구조와 같은 모양일 뿐 래퍼 자체의 측정이 아니다.
- 컨테이너의 numpy 버전은 research.md의 독자용 예제 환경(numpy 2.5.3)과 다를 수 있다(`m=env` 줄에 실제 버전 기록).
  view·asarray·copy 의미는 두 버전 모두 NumPy 문서상 같다.
- ROS 2 측정은 rclpy 단일 프로세스·기본 RMW(rmw_fastrtps_cpp) 경로다. C++ intra-process 통신이나
  다른 RMW, 발행 후 수신 타이밍을 바꾼 조건은 재지 않았다. 구독 쪽 결과를 "ROS 2는 항상 안전하다"로 일반화하지 않는다.
- 복사 비용은 공유 CPU 1개짜리 컨테이너의 마이크로벤치마크이며 실제 제어 주기나 로봇 사양과 무관하다.
- 학습 성능 영향은 재지 않는다.

## 시행착오 (시험 실행 `--try`에서 실제로 겪은 것)

1. 첫 시험 실행은 종료 코드 0으로 성공했지만, 하네스가 stdout의 마지막 8000자만 `results.json`에 남겨
   첫 줄들(`env` 줄과 reuse × list 행)이 잘렸다. 가장 중요한 행이 사라지므로 JSON 키를 줄이고
   중복 필드(최대 절대 오차, 전체 쌍 평균 속도)를 빼서 전체 출력을 8000자 아래로 줄였다.
2. 첫 버전은 deque(maxlen=4)에도 4 step만 넣어 list와 결과가 완전히 같았다. 최근 4칸 창이 밀려나는
   경우(프레임 스택과 같은 모양)를 보려고 deque에는 6 step을 넣도록 바꿨다.
3. numpy가 이미지에 있는지 research.md에서 확인하지 않았는데, 시험 실행에서 import가 성공했다
   (fallback 코드는 넣지 않았다). sensor_msgs도 ros-base 이미지에서 import됐다.
