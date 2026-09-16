# 2026-09-16 자연 예약 실행 — 발행-P2 읽기 전용 인수

판정: **발행-P2 PASS 근거 확보**. `quality99-acceptance.md`의 항목별 최종 가점은 독립 인수 판정에 맡긴다. 연속 7일 관측인 발행-P3 완료를 뜻하지 않는다.

읽기 검증 완료 시각: 2026-09-16 16:55 KST.

확인 방법: 자동화 서버에서 timer/service 속성, 해당 시간대 journal, 원래 저장된 결과·카카오 영수증을 읽었다. 당일 브리핑은 비로그인 WordPress REST로 별도 확인했다. 서비스 시작·발행·카카오 전송·재시도·설정 변경을 실행하지 않았다. 현재 조회한 서버 checkout은 `43a341f574da4c54d810ce5a0697c8e4f54ced7a`다. 이를 과거 각 실행 시점의 SHA가 별도로 기록됐다는 뜻으로 확대하지 않는다.

## 자연 실행 대조

모든 시각은 KST다. timer의 OnCalendar는 04시, 10시, 07/11시로 설정됐고 모두 `Persistent=no`다. LastTrigger 및 아래 journal 시작/종료가 일치한다.

| 예정 | 실제 시작–종료 | 실행/영수증 | 확인한 결과 |
|---|---|---|---|
| 04:00 브리핑 | 04:00:00–04:10:40 | `20260915T190000Z-f9f05f973b` | service success/exit 0, pipeline `failed=false`, `briefing_only`. 브리핑 750은 04:10:38 공개. 독립 글 `posts=[]`이며 정책에 따라 별도 기사 발행을 건너뜀 |
| 07:00 카카오 | 07:00:00–07:00:03 | `2026-09-16-07.json` | 07:00:01 생성, `status=sent`; journal의 `sent 2026-09-16 07`과 일치. 메시지는 브리핑 발행 완료와 당일 URL |
| 10:00 심층 평가 | 10:00:17–10:00:20 | `20260916T010017Z-f9e53484a5` | service success/exit 0, `failed=false`, `candidate_count=0`, `deep_article=no_publishable_topic`, `wordpress_write_count=0` |
| 11:00 카카오 | 11:00:00–11:00:03 | `2026-09-16-11.json` | 11:00:01 생성, `status=sent`; journal의 `sent 2026-09-16 11`과 일치. 브리핑 발행 완료 + 심층글 발행 1건(발행 기록), 각각 정확한 공개 URL |

04시 브리핑 manifest는 `complete=true`, `analysis_complete=true`, `expected_publication_count=0`, `published_count=0`, `published=[]`다. 이 배열은 독립 기사 발행 목록이다. 브리핑까지 0건이라는 뜻은 아니다. 공개 REST는 브리핑 ID 750, `status=publish`, date/modified 04:10:38, `https://huntlab.app/briefing/2026-09-16/`를 반환했다.

## 하루 1건과 11시 보고의 의미

확인된 당일 심층 발행은 하나다. run `20260915T183332Z-188bac8755`가 post 749를 발행했고, Publisher 감사 이벤트는 03:59:59.784561 KST의 `post_published`/`Success`다. 결과에는 `deep_article=published`, `failed=false`, `wordpress_write_count=1`이 남아 있다. URL은 `https://huntlab.app/wordpress-db-restore-attachment-audit/`다.

배포 코드의 읽기 전용 집계 `published_today(..., '2026-09-16')`는 1을 반환했고 `DAILY_LIMIT=1`이다. 10시 평가는 기존 발행 1건에 추가하지 않았다. 단, 실제 종료 이유는 **한도 차단이 아니라 READY 후보 없음**이다. 코드가 후보 없음 분기를 먼저 처리하므로 이 관측을 `daily_limit_reached` 실행 시험으로 바꿔 말하면 안 된다. 오늘의 결과는 ‘당일 확인된 심층 글 1건, 10시 추가 쓰기 0’이라는 운영 일치성 증거다.

11시 보고 함수는 당일 `post_published` 성공 ID를 우선 집계한다. 따라서 메시지의 “발행 1건(발행 기록)”은 새벽의 기존 749를 가리키며, 10시에 새 글을 발행했다는 주장이 아니다. 메시지 자체는 10시 READY 0건 세부 이유를 담지 않았지만 당일 누적 상태를 잘못 표시하지 않았다. 그 세부 종료 이유는 위 10시 결과에서 별도로 확인했다.

현재 카카오 영수증의 `sent`는 전송 도구의 성공 응답을 애플리케이션이 확인한 상태다. 사용자가 메시지를 실제 읽었다거나 카카오 앱 화면을 이번 감사에서 확인했다는 뜻은 아니다. 실패/진행/미발행 표현의 모든 분기를 오늘 실제로 발생시켜 시험하지 않았으며, 오늘 관측은 브리핑·심층 누적 발행 상태와 후보 없음 평가다.

## 보존된 증거 식별

기밀 원문·호스트명·인증정보는 옮기지 않았다. 아래 SHA는 서버 원래 파일의 바이트 SHA-256이다.

- 10시 `output/evidence-deep-article-runs/20260916T010017Z-f9e53484a5/result.json`: `2540a288f1d59216dec114665ff1b734fdc81cde97abc625503b70165b143863`
- 07시 `output/kakao-reports/2026-09-16-07.json`: `56f971bdf2756d335fa217f733139fb72e949e381ac81ee436a04c04f5d8378f`
- 11시 `output/kakao-reports/2026-09-16-11.json`: `defc8baf613bd167506d43ac1547c877c1ffd6f6d09e8803f45bf79afb56551c`
- 04시 `output/runs/20260915T190000Z-f9f05f973b/briefing-manifest.json`: `baca59064939ed3a2ec372c9de2d73264efeab878f325777321ce520786ea1d2`

수동 개편 보고 영수증은 이 인수의 07/11시 자연 전송 증거에 포함하지 않았다. 앞으로의 예약 실행은 아직 관측하지 않았으며, 오늘 한 번의 성공으로 7일 안정성이나 향후 발행 성공을 보장하지 않는다.
