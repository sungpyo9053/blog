# 경쟁 글 대비 차별점: gymnasium-step-observation-buffer-reuse-replay-aliasing

같은 질문(커스텀 환경 관측 반환·버퍼 저장·복사)으로 검색되는 문서를 직접 열어 읽었다(2026-10-08). Medium "Create a gymnasium custom environment (Part 2)"는 403으로 원문을 확인하지 못해 비교에서 제외했다.

1. https://gymnasium.farama.org/introduction/create_custom_env/ (Gymnasium 공식 "Create a Custom Environment")
   - 다루는 것: GridWorldEnv로 `_get_obs()`, reset/step 구현, Dict 관측 설계, 디버깅 단계의 `check_env(env)` 실행 권장.
   - 빠졌거나 틀린 것: `_get_obs()`가 `{"agent": self._agent_location, "target": self._target_location}`처럼 내부 배열을 그대로 돌려준다. 새 객체를 반환하라는 요구는 언급하지 않는다. 페이지 코드를 그대로 실행하면 Gymnasium 1.4.0 check_env가 "share an object" AssertionError로 실패했다(target 배열이 reset과 step 사이에 같은 객체). 수동 테스트에서 `obs['agent'].copy()`를 쓰지만 이유는 설명하지 않는다.
   - 이 글이 더할 것: 1.4.0 check_env의 동일성 검사 기준(고정 배열도 복사), 튜토리얼 코드가 실패하는 이유와 `.copy()` 수정, 그리고 이 실패가 곧 값 오염은 아니라는 판정 기준을 실측 판정과 함께 제시한다.
2. https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html (SB3 "Using Custom Environments")
   - 다루는 것: 커스텀 환경 골격, SB3 `stable_baselines3.common.env_checker.check_env` 사용 권장. Gymnasium checker는 SB3가 지원하는 것의 상위 집합을 검사한다고 언급.
   - 빠졌거나 틀린 것: 관측 객체 재사용을 다루지 않는다. SB3 2.9.0 env_checker.py 소스에서는 반환 객체 공유를 검사하는 함수를 찾지 못했다(함수 목록 확인). SB3 ReplayBuffer가 저장 시 복사한다는 사실(buffers.py 265–271행)도 가이드에는 없어, 독자는 자기 코드의 어느 부분이 안전하고 어느 부분이 위험한지 판단할 수 없다.
   - 이 글이 더할 것: SB3 버퍼는 복사하므로 저장된 전이는 안전하지만, 직접 만든 리스트 로그나 FrameStackObservation은 오염된다는 경계를 소스와 로컬 재현으로 구분해 보여 준다.
3. https://tutorials.pytorch.kr/intermediate/reinforcement_q_learning.html (파이토치 한국어 튜토리얼 "강화 학습 (DQN) 튜토리얼")
   - 다루는 것: `ReplayMemory`를 `deque(maxlen=capacity)`와 `append(Transition(*args))`로 구현하고, 매 step `torch.tensor(observation, ...)`로 변환해 push한다.
   - 빠졌거나 틀린 것: 이 구현은 `torch.tensor`가 데이터를 항상 복사하기 때문에 안전하다(PyTorch 2.14.1 `_torch_docs.py` 9587행 "by copying data"). 튜토리얼은 그 이유를 말하지 않는다. 독자가 성능을 위해 `torch.from_numpy`(같은 메모리 공유, 4606–4607행)로 바꾸거나 관측을 그대로 deque에 넣으면, 재사용 환경에서 모든 칸이 같은 값이 될 수 있다는 위험을 알 수 없다.
   - 이 글이 더할 것: 참조만 쌓는 deque/list가 어떤 숫자를 남기는지(평균 0.375 rad 치우침, 최고 0.75 rad 오차, 속도 0)를 계산으로 보이고, 가장 오래된 원소 테스트로 잡는 방법을 실행 확인된 코드로 준다.
4. https://nuguziii.github.io/dev/dev-001/ (ZZEN's Blog "[Numpy] 배열의 복사")
   - 다루는 것: `=`, `view()`, `copy()`의 차이를 예제로 설명한다.
   - 빠졌거나 틀린 것: 강화학습 버퍼·환경 반환값과 연결하지 않는다. basic slicing(`x[:]`)과 `np.asarray`가 복사하지 않는다는 점, 공유 여부를 확인하는 `np.shares_memory`, 그리고 이를 잡아내는 테스트나 검사기는 다루지 않는다.
   - 이 글이 더할 것: view/asarray로 고친 환경이 1.4.0 check_env에서 여전히 실패한다는 판정과, 공유 여부를 직접 확인하는 방법(`np.shares_memory`)을 피지컬 AI 관절각 예제에 연결한다.
