# 99점 후속 — 복구된 실제 브라우저 검증

2026-09-16 08시대 KST. 기존 95점 판정을 완료/99점으로 바꾸지 않는다.
이전 목표 턴은 9편 정정·배포·공개 감사로 실질적 진전이 있었다. 이번 턴 시작에
Chrome 연결이 다시 발견돼, 미실행 UI 검증을 진행했다. 서비스 점검 중단 승인은
아직 없고 WordPress를 중단하지 않았다.

## 새로 직접 관측한 내용

- 실제 Chrome, 공개 글 749, 배포된 코드 도구의 긴 Bash 예제 1861 bytes,
  SHA `e8a4b647ffdce225c6fb9a58deacc6fdaad5c7293834feb4dd2b371e204e02d2`.
- 복사 버튼은 성공 알림을 표시했다. 그러나 지원되는 브라우저 clipboard 조회는
  빈 문자열을 반환했고, 붙여넣기도 가상 clipboard가 비어 있다는 오류였다.
  **실제 복사 원문 E2E는 여전히 미완료**다. 버튼 알림이나 단위 테스트로 대신하지 않는다.
- 390×844에서 코드 도구 버튼 8개 모두 높이44px, 너비52.5px 이상.
  코드 내부 폭305px/scrollWidth522~1647px이며 페이지 client/scrollWidth는375/375.
- 공개 글 749 및 진단 페이지에서 viewport320/768/1440의 페이지 가로 overflow 없음.
  이는 실기기나 보조공학 검증이 아니다.
- Tab→전체 선택, Shift+Tab→복사, Enter/Space 복사 알림 확인. 초기 포커스 색상은
  테마의0.2초 transition 중간값이었다. 종료 뒤 청색 `rgb(23,102,174)` solid3px,
  offset3px을 확인했다. 중간 애니메이션 값을 최종 결함으로 오판하지 않았다.
- 메뉴 열기→Escape→전환 종료 후 aria-expanded=false 및 메뉴 열기 버튼으로
  포커스 복귀 확인. 목차 펼치기/접기도 동작했다.
- 공개 진단 도구: JSON201 성공, 입력 수정 즉시 오래된 결과 무효화, draft 거절,
  HTML200 거절, Retry-After120초, 목록1/2/2의 중복1·고유2 거절, 초기화 모두 확인.
  Enter/Space로 검사했고 테스트 입력은 공개 합성값뿐이다. 댓글·문의는 제출하지 않았다.

## 실제로 발견한 결함과 첫 배포

목차 및 진단 항목 링크를 누르면 제목이 고정 메뉴 뒤로 숨는다. 전환 종료 뒤 재관측했다.

| 대상 | 링크 이동 뒤 제목 top | 고정 메뉴 bottom |
| --- | --- | --- |
| 글749 `#huntlab-section-4`, 390px | 0.6015625px | 63px |
| 진단 도구 `#inventory-check-title`, 390px | 0.2109375px | 63px |
| 다른 페이지에서 홈 `#hunt-news-latest-verified`로 진입, 390px | h2 45.3125px (section 0.1171875px) | 63px |

글 목차 제목의 computed scroll-margin-top은112px인데도 무시됐다. 스크린샷으로
첫 제목 줄이 메뉴에 가린 것을 확인했다. 담당 구현 에이전트가 Kadence의 공통
앵커 처리와 충돌 원인을 확인했다. 독립 Reviewer의 차단 결함 없음 판정 후,
TOC·진단 내부 클릭 처리와 홈 공식 추가 offset 필터를 배포했다. 기존5파일의
live SHA가 HEAD와 같은지 먼저 확인하고 웹 루트 밖 비공개 백업을 보존했다.
서비스 중단·본문 변경·새 글 생성은 없었다.

로컬 전체510개는 509통과/PHP1 skip. 그 PHP 테스트 원문을 실제 WordPress 서버
PHP8.2.33에서 별도 실행해 exit0, PHP lint도 통과했다. Node 두 종류의 검사는
이벤트/좌표 adapter 테스트이며 실제 브라우저 검증과 구분한다.

첫 배포 후 실제390px Chrome, 전환 종료 뒤:

| 대상 | 제목 또는 section top | 메뉴 bottom | 결과 |
| --- | --- | --- | --- |
| 글749 목차 클릭 | h2 112.1015625 | 63 | 보임, 제목 focus |
| 진단 목록 누락 클릭 | h2 98.2109375 | 63 | 보임, 제목 focus |
| 다른 페이지→홈 fragment | section90.1171875 / h2 135.3125 | 63 | 보임 |

Reviewer가 별도로 지적한 직접 fragment 진입도 검사하자, 글 제목 top0.4296875,
진단 제목 top0.2109375로 여전히 메뉴에 가렸다. 첫 배포의 클릭 이동 해결을
모든 deep link 해결로 확대하지 않는다. 공식 offset 필터의 적용 범위를 글과
진단 페이지로 확장하는 후속 수정·검증을 진행한다.

두 번째 PHP 배포 뒤 진단 직접 진입은390px top100.2109375/1440px top100.1015625,
글 직접 진입은1440px top112.0390625로 보였다. 그러나 모바일 글은 두 번 모두
top -55.5703125로 실패했다. 실제 DOM에서 Kadence navigation은 async이며,
그 뒤에 목차와 코드 도구가 동기 스크립트로 출력된 것을 확인했다. 모바일 목차를
나중에 접으면 위쪽 높이가 바뀌므로, 픽셀 여백만 더하는 것으로 충분하지 않았다.
원래 실패를 성공으로 덮지 않고 WordPress의 스크립트 의존성으로 초기화 순서를
보장하는 세 번째 수정·검증을 진행한다.

설계 근거: [WordPress 스크립트 의존성과 로딩 전략](https://developer.wordpress.org/reference/functions/wp_enqueue_script/),
[Kadence1.5.2 공식 offset 필터 소스](https://themes.svn.wordpress.org/kadence/1.5.2/inc/components/scripts/component.php).

## 세 번째 배포 후 확인

별도 Reviewer 검토와 WordPress 서버 PHP lint/runtime2개 exit0 후 TOC PHP를
백업하고 교체했다. 실제 공개 HTML의 실행 순서는 이제 TOC(sync)→Code Tools(sync)
→Kadence(async)다. 목차 접힘과 코드 도구 삽입이 먼저 끝난다.

- 390px 글 직접 fragment, reload 포함3회: h2 top112.9296875 /112.4296875 /
  112.9296875, 고정 메뉴 bottom63. 세 번 모두 가림 없음.
- 1440px 글 직접 fragment: h2 top112.5390625, 메뉴 bottom59, 페이지1425/1425.
- 최종390px 목차 Enter: h2 top112.1015625, 메뉴 bottom63, heading focus,
  페이지375/375. 실제 스크린샷에서 제목·본문·복사/선택 버튼과 코드 내부 스크롤 확인.
- 앞선1440px 클릭/키보드 검사: 글 h2 top112.0390625, 진단100.1015625,
  두 제목 모두 청색3px outline/focus. 홈 section90.0546875/h2 135.25, 메뉴59.
- 전체 로컬512개: 510통과/PHP2 skip(8.037s). 동일 PHP 테스트 원문2개는
  실제 서버 PHP8.2.33에서 별도 실행해 모두 exit0. 테스트 수를 승인 확률로 환산하지 않는다.
- 공개 읽기 전용 감사08:22 KST: 글10·페이지19·내부URL64·sitemap5/35,
  ads.txt/inventory PASS. 비공개 `output/quality99-anchor-public-audit.json`.
- 브라우저 검사 viewport는 종료 전 기본값으로 reset했다.

변경은 플러그인6파일이다. WordPress 기존 원문·글/미디어 생성은0,
서비스 중단0. 원본 파일은 웹 루트 밖에 보존했다.
이 배포 시점의 확인은 클릭 및 직접 진입 경로에 한정됐다. browser back/forward는
아래 후속 실제 검사에서 별도로 확인했다.
clipboard 원문 E2E·권한 거절 실제 검사와 실기기/보조공학은 여전히 완료하지 않았다.
따라서 U1/U2를 가점하지 않고 **95/100 유지**한다.

최종 코드 커밋 `82677cb37ba7a0d88297e75abaf898736fca0dc0`은 origin과 자동화 서버에
동일하게 반영했다. 자동화 서버에서도512개 실행(510통과/PHP2 skip,3.255s)을 확인했고,
앞서 WordPress 서버에서 실행한 동일 PHP2개와 구분한다. 배포6파일 SHA는
로컬 커밋과 WordPress 서버 모두 일치했다. 원격의 기존 상태 파일·backups는 보존했다.

08:26 KST 카카오 본인 보고는 실제 `status=sent` 영수증
`2026-09-16-quality99-anchor-followup.json`으로 확인했다. 점수95 유지와 남은
검증을 명시했으며 읽음 확인이나 AdSense 승인으로 해석하지 않는다.

## 탐색 기록 후속 검사

다음 목표 턴에서 최신 로컬·자동화 서버 SHA `f18135bcdf61831d087738e55a468db03466c738`
및 실제 active/waiting 타이머를 재확인했다. 10시 심층 평가와11시 보고는 아직
시각 도래 전이며 실행 완료로 기록하지 않았다. 점검 중단 승인도 여전히 없었다.

새 Chrome 검사 탭에서 지원되는 `tab.back()`/`tab.forward()`로 실제 탐색 기록을
이동했다. 처음 시도한 키보드 단축키는 주소를 바꾸지 않았으므로 통과 증거로
쓰지 않는다. raw CDP history는 도구가 지원하지 않아 사용하지 않았다.

- 데스크톱 글: 뒤로가기로 fragment 없는 원래 URL과 scrollY0 복원,
  앞으로가기로 `#huntlab-section-4` 복원. 이 첫 검사에서는 단축키용 locator가
  제목을 먼저 화면 안으로 스크롤한 위치(top411.0390625)가 그대로 복원됐다.
- 별도 깨끗한390px 목차 클릭 검사: 이동 직후 h2 top112.1015625,
  뒤로가기로 fragment 없는 URL, 앞으로가기로 같은 fragment 및 정확히
  top112.1015625 복원. 메뉴 bottom63으로 제목 가림 없음.
- 390px 진단 목록 누락: 이동 직후 h2 top98.2109375,
  뒤로가기로 fragment 없는 진단 URL, 앞으로가기로 `#inventory-check-title`
  및 정확히 top98.2109375 복원. 메뉴 bottom63으로 제목 가림 없음.
- 검사 후 viewport reset. 댓글·문의·발행·원문 변경0.

탐색 기록 경로의 미검증 범위는 줄었지만 실제 clipboard/권한 실패·실기기/보조공학,
일관 백업·전체 복구, 예약/장기 관측은 그대로 남아95점 유지다.

홈→자동화·테스트 분류의 실제 링크 이동과 해당 분류의 3편 목록 표시도 확인했다.

실제 모바일·screen reader, 새 일관 백업/전체 복구, 자연10/11시 실행 및7일 관측은
별도로 남는다. 이번 브라우저 연결 복구가 이 항목들을 완료했다는 뜻은 아니다.
