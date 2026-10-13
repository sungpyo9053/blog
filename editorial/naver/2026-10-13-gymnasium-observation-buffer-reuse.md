제목: Gymnasium step()이 같은 관측 배열을 돌려주면 리플레이 버퍼가 망가지는 이유 — 관절각 4스텝으로 직접 계산
커스텀 로봇 환경에서 step()이 self._q += 0.25 다음에 return self._q를 하고, 학습 루프가 buffer.append(obs)로 쌓으면 버퍼에는 무엇이 남을까요. 4스텝 뒤에 열어 보면 네 칸 모두 마지막 값 1.0 rad입니다.

■ 숫자로 보면
- 실제로 지나간 값: 0.25, 0.5, 0.75, 1.0 rad → 평균 0.625 rad
- 버퍼에 남은 값: 1.0, 1.0, 1.0, 1.0 rad → 평균 1.0 rad
- 차분 속도(Δt 0.125 s): 2 rad/s여야 하는데 0 rad/s
- 오차는 가장 오래된 칸이 0.75 rad로 가장 크고 최신 칸은 0 → 마지막 칸만 보는 테스트는 그대로 통과합니다

■ 왜 이렇게 되나
- 파이썬 list.append는 배열을 복사하지 않고 같은 배열을 가리키기만 합니다
- 환경이 그 배열을 제자리에서 고치면 지나간 칸도 같이 바뀝니다
- Gymnasium Env API 문서도 step()은 같은 버퍼를 고쳐 돌려주지 말고 새 관측 객체를 돌려주라고 적고 있습니다

■ 고친 것처럼 보여도 안 되는 것
- obs[:] → 데이터를 공유하는 뷰라서 그대로 망가집니다
- np.asarray(obs) → 이미 ndarray면 같은 객체를 돌려줍니다
- 해결: return self._q.copy() 또는 저장할 때 np.array(obs)

■ 확인 방법
- np.shares_memory(가장 오래된 칸, 최신 칸)이 True면 문제 있음
- Gymnasium 1.4.0(2026-10-05 배포)부터 check_env()가 이 문제를 잡습니다. 1.3.0에서는 같은 환경이 통과했습니다

반환 방식 4종 × 버퍼 3종을 ROS 2 Jazzy 컨테이너에서 5번 돌린 결과표와 재현 스크립트는 원문에 정리했습니다.
원문: https://huntlab.app/gymnasium-step-observation-buffer-reuse-replay-aliasing/

#Gymnasium #강화학습 #로봇학습 #리플레이버퍼 #numpy #ROS2 #파이썬
