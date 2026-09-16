# 주간 편집 운영 배포

- `huntlab-weekly-editorial.timer`: Sun20:00 Asia/Seoul, Persistent=false.
- `huntlab-weekly-editorial.service`: 승인된 기존 글 문단만 최대1개 갱신, 카톡 보고.
- failure service: 비정상 종료 시 경고만 발송. 작업이나 알림의 불확실한 재시도 금지.
- anchor2026-09-20, 첫28일 성과 평가2026-10-18. 28일 비교는 인과 증명이 아니다.
- 기존 daily/deep/Kakao timer, 비활성 legacy weekly timer는 변경하지 않는다.

최초 설치 전 CLI dry-run으로 실제 API·모델·검수 계약을 확인한다. 쓰기 없는 검증을
실제 공개 수정 E2E라고 보고하지 않는다. 수정 가능한 공개 글이 없으면 정상 무수정이다.
원격 설치는 전체 SHA 확인, 원본 상태 보존, 단위 파일 검증 후 daemon-reload와
timer enable --now만 수행한다. service를 --apply로 수동 강제 시작하지 않는다.

수동 점검은 `scripts/run_weekly_editorial.py --dry-run --notify`다. 비공개 output의
result/report·백업·검수·쓰기 marker·카톡 receipt를 함께 확인한다. 상세 경로는
실행 결과를 기준으로 한다. 애매한 쓰기 marker가 있으면 내용 재조회로 운영자가
판정하기 전까지 다시 적용하지 않는다. 일반 예외는 runner가 보고하고 프로세스
강제 종료 등은 systemd OnFailure 경고로 확인한다.

모델 입력 실행은 공식 Codex CLI의 read-only/ignore-user-config와 도구 비활성화
설정을 사용한다. [명령 문서](https://learn.chatgpt.com/docs/developer-commands),
[설정 문서](https://learn.chatgpt.com/docs/config-file/config-reference).
명령이 호환되지 않으면 sandbox를 풀어 우회하지 말고 실행을 멈춘다.
