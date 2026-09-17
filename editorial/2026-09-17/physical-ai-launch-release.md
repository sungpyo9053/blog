# 피지컬 AI 학습 경로 초기 발행

사용자 승인: 검수 통과한 글부터 최대 4편. 배치 `physical-ai-launch-20260917`.
이번 초기 구성만 분야별 1편을 허용하며, 매일 10:00 KST 평가·READY 조건·하루 최대 1편 정책은 변경하지 않았다.

## 공개 결과

| 분야 | 글 | WordPress ID | 결과 |
| --- | --- | --- | --- |
| 기초 | [관측·행동·피드백](https://huntlab.app/physical-ai-observation-action-feedback/) | 761 | 기존 초안 공개 전환, 공개 감사 통과, 카톡 sent |
| 원리·알고리즘 | [같은 물체의 위치가 다르게 보이는 이유](https://huntlab.app/physical-ai-coordinate-frames/) | 773 | 좌표 그림 교정 후 독립 재검수, 공개 감사 통과, 카톡 sent |
| 프레임워크·라이브러리 | [ROS 2와 tf2](https://huntlab.app/ros2-tf2-roles/) | 768 | 새 글 공개, 공개 감사 통과, 카톡 sent |
| 실습·실험 | [이동평균 필터의 노이즈와 지연](https://huntlab.app/sensor-moving-average-noise-delay/) | 771 | 새 글 공개, 공개 감사 통과, 카톡 sent |

총 4편 공개 완료. 네 카테고리의 공개 글 수는 각각 1이며, 실제 Chrome 홈에서 네 경로 모두 `1편 읽기`로 표시되는 것을 확인했다. 네 카테고리 페이지 HTTP200, 네 글 H1·대표 이미지 로딩·데스크톱 가로 넘침 없음을 확인했다. 실제 iPhone Safari 확인을 뜻하지 않는다.

## 검증과 한계

- Writer와 Reviewer를 분리하고 최종 원고 SHA에 승인을 연결했다. 발행 직전 공개 글과 초안을 포함한 WordPress 전체 목록을 다시 조회했다.
- 각 슬롯은 읽기 검증 후 한 번만 쓰기 경계를 넘는다. 시도 기록이 있는 실패는 자동 재발행하지 않고 먼저 조정한다.
- REST 저장 본문을 승인 원고와 대조하고, 공개 상태·대표 이미지·ALT·이미지 HTTP200·공개 본문·출처 링크를 확인했다.
- 서버의 슬롯별 `launch-result.json`, `publisher-result.json`, `publisher-audit.jsonl`과 카톡 `post-ID.json`을 별도로 보존했다. 비공개 초안 목록과 자격 증명은 이 보고서에 포함하지 않는다.
- 네 카톡 영수증은 각각 `status=sent`, `attempt=1`이다. 마지막 공개 검증 및 알림은 2026-09-17 20:44 KST 완료했다.
- 기초는 수치 모델, 원리는 정적 좌표 변환, 도구는 공식 문서 해설, 실습은 결정론적 수치열 실험이다. 실물 로봇·센서 또는 ROS 실행을 했다고 주장하지 않는다.
- 내부 편집 평가 점수는 AdSense 승인 확률이나 외부의 객관적 품질 보증이 아니다.
- 이번 발행은 이전 오전 자동 실행의 실패 기록을 덮어쓰지 않는 별도 배치다.
