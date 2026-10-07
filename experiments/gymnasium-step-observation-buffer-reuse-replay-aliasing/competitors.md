# 경쟁 글 대비 차별점: gymnasium-step-observation-buffer-reuse-replay-aliasing

1. https://gymnasium.farama.org/introduction/create_custom_env/ (Gymnasium 공식 "Create a Custom Environment", 영어, 2026-10-07 열람)
   - 다루는 것: GridWorld 예제로 observation_space·reset·step·_get_obs·등록·`check_env` 디버깅까지 커스텀 환경 전 과정.
   - 빠졌거나 틀린 것: step/reset이 매번 새 객체를 돌려줘야 한다는 1.4.0 요구를 튜토리얼 본문에서 설명하지 않는다. `_get_obs`가 `{"agent": self._agent_location, "target": self._target_location}`처럼 내부 배열을 복사 없이 담아 돌려준다([소스 L132-L138](https://github.com/Farama-Foundation/Gymnasium/blob/8ba8c3a63bb4e000b7f33923f43d292acac07be1/docs/introduction/create_custom_env.md#L132-L138)). agent는 `np.clip`으로 매번 새 배열이 되지만 target은 step에서 다시 만들지 않는다. 1.4.0 docstring 기준으로는 상수 배열도 복사 대상이다(실행 확인 안 함). 버퍼에 무엇이 남는지 숫자로 보여 주지 않는다.
   - 이 글이 더할 것: (실측) 같은 객체를 고쳐 돌려줄 때 참조 버퍼의 4스텝 기록·평균·차분 속도가 어떻게 바뀌는지와, 제자리 수정 vs 재바인딩의 차이, 1.4.0 버전 조건을 하네스 실측으로 보여 준다.
2. https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html (Stable-Baselines3 "Using Custom Environments", 영어)
   - 다루는 것: SB3와 함께 쓸 커스텀 환경의 공간 정의, 이미지 관측 dtype·정규화, SB3 `check_env` 사용.
   - 빠졌거나 틀린 것: 관측 객체 재사용·복사 문제를 언급하지 않는다. SB3 2.9.0의 자체 `check_env` 소스(stable_baselines3/common/env_checker.py)에서 `shares_memory`·객체 재사용 검사 문구를 찾지 못했다(grep 기준). SB3 버퍼가 저장 시 복사하기 때문에 SB3 안에서는 증상이 덜 드러난다는 조건도 설명하지 않는다.
   - 이 글이 더할 것: (실측) 저장 시 복사하는 버퍼(SB3 방식)와 참조 보관 버퍼(list/deque)를 같은 재사용 환경에 붙여 결과가 갈리는 것을 보여 주고, "SB3를 쓰니 괜찮다"가 어디까지 맞는지 범위를 정한다.
3. https://nuguziii.github.io/dev/dev-001/ (ZZEN's Blog "[Numpy] 배열의 복사", 한국어, 2020-03-11 업데이트 표기)
   - 다루는 것: numpy 배열의 `=`·`view()`·`copy()` 차이를 작은 예로 설명.
   - 빠졌거나 틀린 것: 강화학습 환경·버퍼 맥락이 없다. "함수가 같은 배열을 반환하고 호출자가 쌓는" 구조, `np.asarray`의 비복사, 메모리 공유를 판정하는 `np.shares_memory`, 이를 잡는 테스트가 없다.
   - 이 글이 더할 것: (실측) view·asarray로 "고친 것처럼 보이는" 반환이 참조 버퍼에서 실제로 같은 오류를 내는지와 shares_memory 판정을 측정해 보여 준다.
4. https://tutorials.pytorch.kr/intermediate/reinforcement_q_learning.html (파이토치 한국어 튜토리얼 "강화 학습 (DQN) 튜토리얼", 한국어)
   - 다루는 것: deque 기반 `ReplayMemory`로 전이를 저장하는 DQN 전체 구현.
   - 빠졌거나 틀린 것: 관측을 `torch.tensor(...)`로 변환한 뒤 저장해 우연히 복사가 일어나므로 안전하지만, 그 이유를 설명하지 않는다. numpy 관측을 그대로 deque에 넣도록 바꾸면 환경이 버퍼를 재사용할 때 문제가 생긴다는 조건이 드러나지 않는다.
   - 이 글이 더할 것: (실측) 같은 deque 버퍼에 "복사 없이 numpy 관측"과 "복사한 관측"을 넣었을 때의 차이를 측정해, 어느 줄이 안전을 보장하는지 보여 준다.
