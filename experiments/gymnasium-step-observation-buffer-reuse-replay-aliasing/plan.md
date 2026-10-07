# 실험 계획: step()이 같은 관측 배열을 고쳐 돌려줄 때 버퍼에 남는 값

## 질문

Gym 스타일 로봇 환경이 관절각 관측을 `self._q` 배열 하나에 제자리(in-place)로 고쳐 쓰고
그 객체(또는 같은 메모리의 뷰)를 step()마다 돌려주면, 복사 없이 쌓는 버퍼에 기록된
4스텝 관절각·평균·차분 속도는 실제 값과 얼마나 달라지는가? 그리고 마지막 칸 값 비교,
가장 오래된 칸 값 비교, 메모리 공유(`np.shares_memory`) 검사 중 어떤 테스트가 이를 잡는가?

## research.md 기준 예측값 (손계산, 실행 전)

조건: 관절 1개, 매 스텝 +0.25 rad, 4스텝, 스텝 간격 0.125 s.

- reuse(같은 객체 반환) + list.append → 저장값 [1.0, 1.0, 1.0, 1.0] rad, 평균 1.0 rad
  (정상 0.625 rad, 평균 오차 0.375 rad), 가장 오래된 칸 오차 0.75 rad,
  칸별 오차 0.75, 0.5, 0.25, 0 rad, 차분 속도 3개 모두 0 rad/s (정상은 모두 2 rad/s).
- copy·np_array(반환 전 복사) + list.append → [0.25, 0.5, 0.75, 1.0] rad, 평균 0.625 rad, 속도 2 rad/s.
- reuse + 저장 시 복사 버퍼(SB3 방식 모사) → 정상값과 같음.
- 마지막 칸 차이: 모든 경우 0 → 마지막 칸 비교 테스트는 못 잡음.
- view(`self._q[:]`)·asarray(`np.asarray(self._q)`) → reuse와 같은 값, `shares_memory` True.
  view는 `is` 비교가 False, asarray는 True일 것.
- 프레임 스택 모사(reuse) → 마지막 스택의 4프레임 모두 1.0 rad.
- 정지 관절 반례(증분 0) → 모든 경우 값 차이 0, 하지만 reuse/view/asarray는 `shares_memory` True.
  즉 값 기반 테스트는 못 잡고 메모리 공유 검사만 잡을 것.
- rebind(콜백에서 `self._q = np.array([...])`로 새 배열) → 값 문제 없음, 연속 반환 `shares_memory` False.
- (추가 예측) 에피소드 뒤 reset()이 `self._q[0] = 0.0`으로 제자리 초기화하면, reuse 계열 list 버퍼의
  네 칸이 모두 0.0 rad로 다시 바뀔 것.

## 무엇을 어떻게 재는가

- 컨테이너: 하네스의 `ros:jazzy-ros-base`, 네트워크 없음. gymnasium이 없으므로 Gym API 모양
  (`reset() -> (obs, info)`, `step() -> (obs, r, terminated, truncated, info)`)의 최소 클래스를 쓴다.
  Gymnasium·check_env 자체 실행이 아니라 그 판정 원리(`np.shares_memory`)의 numpy 재현이다.
- ROS 2 부분: `arm_sim` 노드가 매 스텝 `std_msgs/Float64`로 관절각을 `/arm/joint_angle`에 발행하고,
  환경 노드의 rclpy 구독 콜백이 그 값을 `self._q`에 쓴다(ROS-Gym 브리지에서 흔한 구조).
  같은 `SingleThreadedExecutor`에서 콜백이 실행될 때까지 `spin_once`로 기다린다. 4개 메시지 수신 여부와
  발행→콜백 지연(ms)을 실행 중에 잰다. 관절각 값 자체는 시뮬레이션된 입력이며 물리 엔진·실물 로봇이 아니다.
- 반환 정책 6종: reuse, view, asarray(모두 제자리 수정 후 같은 메모리 반환), copy, np_array(반환 전 복사),
  rebind(콜백이 새 배열로 재바인딩 후 그대로 반환).
- 소비자 4종: `list.append`, `deque(maxlen=4)`, 저장 시 `np.array(obs)`로 복사하는 미리 할당 버퍼,
  프레임 스택 모사(참조 deque + 매 스텝 `np.stack` 결과 복사, 마지막 출력 측정).
- 증분 2종: 0.25 rad(움직임), 0.0 rad(정지 반례). 총 6×4×2 = 48 케이스.
- 참값: step()이 반환한 순간 `float(obs[0])`로 뜬 스냅샷.
- 측정: 4스텝 뒤 소비자에서 읽은 저장값, 평균, 평균 오차, 칸별 오차, 가장 오래된/마지막 칸 오차,
  차분 속도 (q[k+1]−q[k])/0.125, 연속 반환값의 `is`·`np.shares_memory`, reset→step 공유,
  check_env 순서(reset→step→step→reset)의 모든 짝 공유 여부, 끝 reset 뒤 list 버퍼 값.
- 검출 테스트 3종을 각 케이스에 적용: 마지막 칸 값 비교, 가장 오래된 칸 값 비교, 연속 반환 메모리 공유.
- 출력: 실행 중 계산한 값을 JSON 줄로 출력한다. `kind=env`(Python·NumPy·ROS 배포판), 반환 정책×증분마다
  `kind=ep` 한 줄(참값 `true`, 소비자별 저장값 `stored`, 값이 틀어진 소비자 `bad`, list 버퍼의 평균·가장 오래된
  칸 오차·차분 속도, 연속 반환의 `is_`·`shares`, check_env 순서 6짝 중 공유 짝 수 `ck_pairs`, 끝 reset 뒤
  list 버퍼 값), 마지막에 `kind=summary`(48케이스 중 값이 틀어진 수, 각 검출 테스트가 잡은 수, 값은 맞지만
  메모리를 공유한 수, 복사 정책에서 공유 검사가 오탐한 수, ROS 발행·수신 메시지 수, 발행→콜백 지연 중앙값·최댓값).
- 판정: 값이 틀어짐 = 저장값과 참값이 한 칸이라도 다름. 각 테스트가 "잡음" = 마지막 칸 값 불일치 /
  가장 오래된 칸 값 불일치 / 연속 반환 중 하나라도 `np.shares_memory` True.

## 시행착오

- 1차 시험 실행: 코드는 정상 종료했지만, 케이스마다 한 줄씩(48줄 + 정체성 12줄) 출력하자 하네스가 stdout의
  마지막 8000자만 보존해서 앞쪽의 환경 줄과 핵심 케이스(reuse·view·asarray, 0.25 rad)가 results.json에서 잘려 나갔다.
  → 반환 정책×증분마다 한 줄로 합치고, 소비자별 파생값은 참조 보관 list 버퍼에만 남겼다.
- 2차 시험 실행: 여전히 8000자를 넘어 첫 줄들이 잘렸다. → `json.dumps`의 구분자를 공백 없는 `(",", ":")`로 바꾸고
  키 이름을 줄여 전체 출력을 8000자 아래로 낮췄다. 3차 시험 실행에서 env 줄부터 summary 줄까지 모두 보존됐다.
- 요약의 ROS 수신 메시지 수가 실제 콜백 수신 횟수가 아니라 지연 측정 횟수를 세고 있었다. → 각 에피소드의
  콜백 수신 횟수를 합산하도록 고치고, 비교용으로 발행 메시지 수를 함께 출력했다.
- ROS 2 구독 매칭: 발행 전에 `get_subscription_count()`로 구독 매칭을 기다리고, 스텝마다 콜백이 실행될 때까지
  `spin_once`로 기다리게 했다(5초 안에 오지 않으면 예외로 실패). 시험 실행에서 메시지 유실이나 시간 초과는 없었다.
- 시험 실행 결과는 위 손계산 예측과 다른 항목이 없었다. 실측 숫자의 근거는 하네스가 정식 실행해 쓴 results.json뿐이다.
