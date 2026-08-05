# 2026-08-05 퇴근 후 작업 체크리스트

## 현재 상태

- AdSense: 사이트 검토 중. 코드 변경, 재신청 또는 광고 직접 클릭 금지
- Planner 개선: 로컬 테스트 및 GitHub push 완료
- 적용 대상 커밋: `555dc9d` (`Prioritize ML thinking topics in planner`)
- 서버: 기존 버전으로 정상 운영 중이며 위 커밋만 아직 미적용
- 기존 새벽 1시 분석, 2시 발행, 낮 12시 실패 재시도 일정은 유지

## 사용자가 할 일

- [ ] AWS 계정 `8925-3223-3726`의 정확한 루트 이메일 확인
- [ ] 맥의 AWS 로그인 화면에서 루트 계정 로그인
- [ ] 비밀번호와 MFA 인증 완료
- [ ] Codex에 `AWS 로그인됨, 서버 적용해`라고 전달

비밀번호, MFA 코드, 복구 코드와 SSH 개인 키는 이 문서나 Git에 기록하지 않는다.

## 인증 후 Codex가 할 일

- [ ] `aws sts get-caller-identity`로 CLI 인증 상태 확인
- [ ] Lightsail `huntlab-blog-automation-prod` 상태와 접속 경로 확인
- [ ] 서버 `/home/ubuntu/apps/huntlab-blog`의 변경 파일과 현재 커밋 확인
- [ ] 사용자 파일을 건드리지 않고 `origin/main`을 fast-forward pull
- [ ] 서버 HEAD가 최신 `origin/main`과 일치하고 `555dc9d`를 포함하는지 확인
- [ ] Daily Pipeline 테스트 실행
- [ ] ML적 사고력·핵심 개념 주제 우대 문구가 서버 Harness에 존재하는지 확인
- [ ] 새벽 1시 분석, 2시 발행, 낮 12시 재시도 timer 활성화 및 다음 실행 시각 확인
- [ ] 수동 추가 발행은 하지 않고 기존 예약 발행 유지
- [ ] 변경 커밋, 테스트 결과, timer 상태를 최종 보고

## 적용 후 다음 날 확인

- [ ] 새벽 1시 Analytics Optimizer 결과 확인
- [ ] 새벽 2시 Pipeline의 Topic Planner TOP10·TOP2 확인
- [ ] ML 개념 또는 ML적 사고력 후보가 품질·검색 의도 기준으로 평가됐는지 확인
- [ ] Reviewer 승인, Publisher 성공과 실제 WordPress 공개 글을 각각 확인
- [ ] 이미지, 카테고리, 내부 링크와 공개 HTTP 200 확인

## 재발 방지 검토

AWS 로그인 없이 배포할 수 있는 기존 GitHub Secret과 self-hosted runner는 현재 없다.
서버 접속이 복구된 뒤 전용 배포 사용자와 제한된 self-hosted runner 또는 이에 준하는
안전한 배포 경로를 별도 검토한다. 자동 `git pull`은 테스트 실패 시 운영을 깨뜨릴 수
있으므로 검증·롤백 조건 없이 도입하지 않는다.
