# 상위 유입 글 품질 보강 백로그 (2026-08-10)

## 감사 범위

Search Console·GA4 관측 글과 공개 본문을 대조했다. 이번 작업에서는 WordPress 공개 글을
직접 변경하지 않고, 실제 근거가 부족한 글만 보강 대상으로 분류한다.

## 확인 결과

### 유지 후보

- `cloudflare-workers-types-migration`: 실행·검증·버전·오류·판단 흐름이 확인됨
- `cloudflare-email-preview-retention`: 실행·테스트·결과와 운영 판단이 확인됨
- `github-code-scanning-ai-detections`: 실행·실패·오류·출처·테스트가 확인됨
- `wordpress-internal-link-backup`: 실행·실패·검증 결과와 운영 판단이 확인됨
- `cloudflare-tunnel-connections-migration`: 실행·실패·검증 결과와 한계가 확인됨

### 보강 우선 후보

- `resident-registration-survey`: 공식 절차 설명은 충분하지만 HuntLab의 고유한 확인
  범위와 독자 행동 판단을 더 분명히 한다.
- `heatwave-work-stop-rules`: 기준·의무를 공식 1차 자료와 대조한 날짜와 적용 한계를
  본문 가까이에 표시한다.
- `oil-price-cap-8th`: 기준일·공급가와 소매가의 차이는 설명되어 있으므로, 공식 원문
  링크와 변경 시 재확인 지점을 더 명시한다.

## 적용 원칙

1. 기존 수치·법적 판단·정책 문구를 새로 만들어내지 않는다.
2. 공식 원문, 확인일, 적용 대상, 미확인 범위만 보강한다.
3. 공개 글 업데이트는 기존 게시물 ID를 고정하고 새 Reviewer 승인 후 Publisher를
   통해서만 수행한다.
4. 근거를 추가할 수 없는 문단은 삭제하거나 단정 표현을 낮춘다.

## 다음 실행 단위

- 각 후보의 현재 본문과 공식 출처를 격리된 업데이트 원고로 만든다.
- Reviewer가 사실·출처·변경 범위를 승인한다.
- 승인된 글만 기존 WordPress 게시물에 업데이트하고 공개 URL·canonical·이미지를
  재검증한다.

