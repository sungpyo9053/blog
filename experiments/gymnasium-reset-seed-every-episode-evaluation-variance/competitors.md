# 경쟁 글 대비 차별점: gymnasium-reset-seed-every-episode-evaluation-variance

1. https://www.kevsrobots.com/learn/gymnasium/06_seeding_and_lifecycle.html (Kevin McAleer, "Seeding and the Episode Lifecycle", 2026-06-14 갱신, 원문 직접 확인)
   - 그 글이 다루는 것: "BAD: re-seeds every episode … Every episode becomes identical" / "GOOD: seed once" 코드 대비, `env.action_space.seed(42)` 별도 설정, NumPy·random 모듈은 따로 시딩해야 한다는 주의, 실험별로 seed를 바꾸는 루프.
   - 빠졌거나 틀린 것: "Every episode becomes identical"은 결정적 정책·추가 난수원 없음·reset이 상태를 완전히 지움이라는 조건 없이 단정한다(확률적 정책이나 LunarLander-v2 같은 reset 버그에서는 성립하지 않음). 그 실수가 평가 통계에 미치는 영향(독립 표본 수, 분산), 성공률 지표에서 실수가 숨는 조건, 로봇 환경에서 seed가 고정하는 대상, 정책 비교용 seed 목록은 없다.
   - 이 글이 더할 것: 같은 seed 반복이 성공률 추정의 독립 표본 수를 20에서 1로 줄인다는 것을 p(1−p)/n으로 계산하고(0.012 대 0.24), 하네스 실측으로 매번 같은 seed / 한 번만 seed / seed 목록 세 루프에서 서로 다른 시작 수와 반복 평가 간 성공률 퍼짐을 측정해 보여 준다.
2. https://tutorials.pytorch.kr/intermediate/reinforcement_q_learning.html (PyTorch 한국어 튜토리얼 "강화 학습 (DQN) 튜토리얼", 원저자 Adam Paszke·Mark Towers, 번역 황성수·박정환, 원문 직접 확인)
   - 그 글이 다루는 것: 재현성을 위해 주석 처리된 `random.seed`, `torch.manual_seed`, `env.reset(seed=seed)`, `env.action_space.seed(seed)`, `env.observation_space.seed(seed)` 묶음. 실제 루프는 매 에피소드 `env.reset()`(seed 없음). 평가는 에피소드 길이와 100 에피소드 이동 평균 그래프.
   - 빠졌거나 틀린 것: 왜 seed를 루프 밖에서 한 번만 주는지 설명하지 않는다. 평가 에피소드 수와 추정 신뢰도, 성공률 지표, 로봇 환경 언급이 없다.
   - 이 글이 더할 것: 같은 seed 자리를 루프 안으로 옮겼을 때 무엇이 바뀌는지(PRNG 재생성 한 줄)와 그 결과 성공률이 0/1로만 나오는 이유를 소스와 산술로 연결하고, 하네스 실측으로 루프별 서로 다른 시작 수를 보여 준다.
3. https://harald.co/2019/07/30/reproducibility-issues-using-openai-gym/ (Harald Carlens, 2019-07-30, 원문 직접 확인)
   - 그 글이 다루는 것: 구 OpenAI Gym의 `env.seed()`가 action space를 시딩하지 않아 CartPole 학습이 재현되지 않던 문제와 `env.action_space.seed()` 해결, seed별 학습 결과 차이 그래프.
   - 빠졌거나 틀린 것: 구 API(`env.seed()`) 기준이라 Gymnasium 0.26+의 `reset(seed=)` 의미(정수면 매번 재설정, None이면 유지)를 다루지 않는다. 평가 루프의 seed 위치와 평가 통계는 범위 밖이다.
   - 이 글이 더할 것: 현재 API(Gymnasium 1.4.0) 기준 규칙 세 가지를 소스 줄로 고정하고, 재현성 문제를 "학습 재현"에서 "평가 숫자의 신뢰도" 문제로 넓혀 하네스 실측과 분산 계산으로 판정 기준을 준다.
4. https://www.datacamp.com/tutorial/reinforcement-learning-with-gymnasium (Arun Nanda, 2024-12-25, 웹 도구로 원문 확인. 단 이 runner의 `source_digest` 확인에서 HTTP 오류 → **본문 인용·링크 금지**, 경쟁 구도 파악용으로만 기록)
   - 그 글이 다루는 것: `env.reset(seed=SEED)`, `np.random.seed`, `torch.manual_seed`로 학습 재현, `N_TRIALS = 25` 평균 return이 임계값을 넘는지로 평가.
   - 빠졌거나 틀린 것: "initialize the environment to the same state every time the program is run"이라고만 설명해 매 에피소드 seed와 한 번 seed의 차이를 다루지 않는다. 25회 평균의 불확실성 논의가 없다.
   - 이 글이 더할 것: 평가 횟수 n이 실제로 독립 표본 몇 개인지 판정하는 방법과 p(1−p)/n 계산, 하네스 실측 비교.
