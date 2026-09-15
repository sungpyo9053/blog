# 99점 사이클 — 배포·실행 기록 (진행 중)

## 발행 안전성

- 자동화 서버 배포 SHA: `f35f19872955f8450d1a10b36b195dda94675389`.
- 구버전 혼합 실행 방지: daily/deep 서비스 MainPID 0·inactive 및 해당 스크립트 프로세스 없음 확인. 두 timer만 잠시 중지하고 ff-only 배포·회귀 후 EXIT trap으로 복원했다. 진행 중인 실행을 종료하거나 lock을 삭제하지 않았다.
- 로컬 전체 Python 507 tests / 7.042s PASS, 실제 배포 서버 507 tests / 3.246s PASS. 장애 주입 테스트의 로그는 모의 실패이며 운영 WordPress 장애가 아니다.
- 서버 Node 코드 도구 테스트 PASS.
- 배포 후 읽기 전용 당일 원장: 2026-09-16 `published_today=1`, `DAILY_LIMIT=1`.
- 복원된 timer: 10:00 deep, 11:00 Kakao, 다음 날 04:00 briefing. 10·11시 자연 실행은 아직 도래 전이며 완료로 기록하지 않는다.
- 서버 기존 `output/humanize-experiment-state.json` 변경 및 `backups/`를 보존했다.

## 공개 코드 도구

- 구현 commit `8ddc7dd`, PHP 8.2 서버 문법 검사 PASS 후 새 WordPress 플러그인 활성화. 기존 플러그인 파일 덮어쓰기 없음. 롤백은 이 새 플러그인 비활성화이며 글 본문을 변경하지 않는다.
- 서버/로컬 SHA-256 일치:
  - PHP `c48036a5f1dfd9b138c2309b0d9c57705df457cffff575b7bf5ca18b4256f3e4`
  - JS `cf9cffcdfb5f71c7428dffbf877d166bec5db0ec378336ca59ad8af02e2842fc`
  - CSS `b6f9af7f207326265abda40647c4bb6293ff2e5a57d60d0a497cdb4f9c3e8352`
- 실제 공개 글 749에서 코드 5개/toolbar 5개, Clipboard API 성공 알림, 복사 후 포커스 유지 확인.
- Tab→전체 선택, Shift+Tab→복사, Enter·Space 복사 성공 및 focus outline `solid` 확인.
- 실제 전체 선택→키보드 복사→미제출 댓글란 붙여넣기를 확인했다. 텍스트는 일치하지만 브라우저 선택 복사는 끝 개행을 제거했다. **버튼 Clipboard API 원문 바이트와 동일하다고 주장하지 않는다.** 댓글은 제출하지 않고 입력을 지웠다.
- 버튼 Clipboard API와 브라우저 자동화의 가상 clipboard가 분리돼 직접 붙여넣기는 `virtual clipboard has no data`로 실패했다. 버튼 성공 알림만으로 clipboard 원문 E2E 검증을 완료하지 않는다. 단위 테스트의 exact-text 전달은 별도 모의 증거다.
- 390×844 viewport에서 document clientWidth/scrollWidth 모두 375 확인. 이는 실제 휴대전화 검사가 아니다. 후속 모바일 클릭·스크린샷은 도구 timeout/reset으로 결과를 얻지 못했다.

99점 승인, 실제 보조공학 검사, 전체 WordPress 복구 완료를 의미하지 않는다.

## 기존 글 정정·공개 감사

- 별도 Reviewer가 manifest `0dd524ce7c55c776e28002db34772f7f4ec447c9d80b7da50638242209773704` 승인 및 본문 예제를 직접 실행했다.
- Publisher가 기존 132·301·749 본문 업데이트 정확히 3회 수행. 새 글/미디어 0, 재시도 0. fresh 전체 123건 비교, 변경 전 raw 3개 백업, attempt/verified 각각 3개 보존.
- 승인 raw 해시와 저장 후 해시 일치, 제목·slug·category·media 등 보호 메타 보존. 공개 GET 3개 200 및 235개 본문 블록 누락 0.
- root 별도 공개 감사: 2026-09-16 07:33:33 KST, `passed=true`, 실패 0. 공개 글 10개, 페이지 19개, 내부 URL 65개, sitemap 5개/URL 35개, ads.txt, 전체 inventory 확인. 저장 파일 `output/quality99-corrections-20260916/root-public-audit.json`.
- 이 공개 기술 감사는 독자 가치·AdSense 승인·실기기 검증을 대신하지 않는다.
