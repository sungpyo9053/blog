# 유튜브 프리미엄 가격 — 사실 수집 (2026-10-24 확인)

대상 키워드: "유튜브 프리미엄 가격" (+ 가족, 학생, Lite, 아이폰 앱 결제, 가격인상)
원칙: 가격·조건은 공식 페이지에서 직접 본 것만 적음. 못 본 것은 "확인하지 못했다".
확인 방법: 로그인하지 않은 상태로 curl(`?gl=KR&hl=ko`, Accept-Language ko-KR)로 받아 HTML/내장 JSON 텍스트를 추출. 결제 버튼은 누르지 않음. 구매하지 않음.

---

## 1. YouTube 공식 가입 페이지 (2026-10-24)

| URL | 확인 내용 |
|---|---|
| https://www.youtube.com/premium | "₩0에 1개월 무료 체험 • 이후 ₩14,900/월 • VAT 포함 • 언제든지 취소 가능". 같은 페이지 비교표: Premium ₩14,900/월, Premium Lite ₩8,500/월. "*Premium 월간 개인 요금제보다 43% 저렴" (8,500/14,900 = 0.570 → 43% 저렴, 일치) |
| https://www.youtube.com/premium (Lite 문구) | "Premium Lite 혜택(백그라운드 재생, 오프라인 저장, 광고로 끊김 없는 시청)은 Shorts 동영상을 제외한 대부분의 음악 외 콘텐츠에서 이용할 수 있습니다. 검색 또는 탐색 시에는 광고가 표시될 수 있습니다." |
| https://www.youtube.com/musicpremium | "₩0에 1개월 무료 체험 • 이후 ₩11,990/월 • VAT 포함 • 언제든지 취소 가능" |
| https://www.youtube.com/premium/family | 페이지 제목 문구: "현재 거주 국가에서는 가족 요금제가 제공되지 않습니다." "대신 YouTube Premium 개인 요금제에 가입해 보세요." |
| https://www.youtube.com/premium/student | "현재 거주 국가에서는 학생 멤버십이 제공되지 않습니다." |

2026-10-19 확인값(14,900 / 11,990 / 8,500, Lite "대부분의 음악 외 콘텐츠")과 동일. 재확인 완료.

## 2. YouTube 고객센터 (support.google.com, 2026-10-24)

- 취소: https://support.google.com/youtube/answer/6308278?hl=ko
  - "멤버십을 취소하면 다시 구독하지 않는 한 요금이 청구되지 않습니다. YouTube 유료 멤버십 혜택은 결제 기간의 마지막 날까지 유지됩니다."
  - "Apple에서 청구: YouTube iOS 앱에서 가입한 경우에는 Apple 계정에서 유료 멤버십을 취소할 수 있습니다." Google Play 결제는 Google Play 계정 설정에서 취소.
  - 웹 경로: youtube.com/paid_memberships → 멤버십 관리 → 비활성화 → 계속 → 사유 → 취소
- 가족 요금제: https://support.google.com/youtube/answer/7507349?hl=ko
  - "참고: 가족 요금제는 현재 대한민국, 베네수엘라, 벨라루스, 슬로베니아, 아이슬란드에서 이용할 수 없습니다." / "참고: 대한민국에서는 가족 요금제를 사용할 수 없습니다."
- 학생: https://support.google.com/youtube/answer/9158808?hl=ko
  - "학생 멤버십 제공 국가" 목록에 대한민국 없음(일본·타이완 등은 있음).
- 연간 요금제: https://support.google.com/youtube/answer/11417260?hl=ko
  - 이용 가능 지역: "독일, 멕시코, 미국, 브라질, 인도, 일본, 캐나다, 태국, 튀르키예" — 대한민국 없음. 선불·환불 불가·일시중지 불가.
- 2인 요금제: https://support.google.com/youtube/answer/15976004?hl=ko
  - 이용 국가: 아르헨티나, 오스트레일리아, 방글라데시, 캄보디아, 프랑스, 홍콩, 인도, 라오스, 네팔, 대만 — 대한민국 없음.
- Premium Lite: https://support.google.com/youtube/answer/15968883?hl=ko
  - 음악 콘텐츠(공식 뮤직비디오, 아트 트랙, 아동용 음악, 음악 파트너 콘텐츠가 들어간 커버·댄스·브이로그 등)와 Shorts에서는 광고 제거·백그라운드·오프라인 미적용. YouTube Music Premium, 이어서 시청하기, 구간 건너뛰기, 현재 재생목록, 고품질 오디오, 고화질 동영상 미포함.
  - 웹/Google Play 가입자는 youtube.com/paid_memberships에서 Premium으로 업그레이드.
- 사용 가능 지역: https://support.google.com/youtube/answer/6307365?hl=ko
  - Premium·Music Premium 목록: "대한민국: 유료 멤버십만 해당". Premium Lite 목록에 대한민국 포함.
  - 오프라인 저장 콘텐츠는 지원되지 않는 국가 여행 시 30일 동안 시청 가능.

## 3. 아이폰 앱 결제 가격 — Apple App Store 공식 페이지 (2026-10-24)

※ 지정 출처 목록(youtube.com/support.google.com) 밖이지만 Apple 공식 스토어 페이지. 인앱 가격의 1차 출처로 사용하되 한계를 본문에 명시.

- https://apps.apple.com/kr/app/youtube/id544007664 — "앱 내 구입" 목록: YouTube Premium ￦19,500 (3회 표시), Premium Lite ￦10,900, 그 외 Super Chat·Movies & Shows 등.
- https://apps.apple.com/kr/app/youtube-music/id1017492454 — "앱 내 구입": YouTube Music ￦15,500 / ￦11,500, YouTube Premium ￦19,500 / ￦14,000, YouTube Red ￦12,000(옛 상품명).
- 한계: 목록에 기간(월/년) 표기 없음. YouTube Music 항목은 값이 두 개라 현재 판매가를 특정 못 함. 실제 인앱 결제 화면은 보지 않음 → 본문에서 "앱스토어 목록 기준, 결제 화면은 확인하지 못했다"로 씀. 웹 가격이 VAT 포함이라는 건 youtube.com 표기, 앱스토어 가격의 VAT 표기는 확인 못함.

## 4. 가격 인상 이력

공식 페이지(youtube.com/premium, 고객센터)에서 국내 인상 이력·일자를 적은 문서를 찾지 못함 → 본문에 "공식 페이지에서 인상 이력은 확인하지 못했다"로 씀. 블로그·뉴스의 인상 수치는 사용하지 않음.

## 5. 네이버 상위 결과 점검 (2026-10-24, search.naver.com "유튜브 프리미엄 가격")

상위 블로그: blog.naver.com/itexpert/224447344920, rlawnstn119/224446901362, ya_nt/224440392718, cocounni_/224443974819, freewind_azu/224444269799 (+ 카페 글 다수, 우회·할인코드 글 다수).
- ya_nt: 웹 14,900 vs 아이폰 19,500, Lite 8,500 vs 10,900의 **월 차액**(4,600/2,400), Premium vs Lite 연 76,800원 차이, Lite+Music 20,490원 계산까지 있음.
- 다섯 글 모두 **아이폰 앱 결제의 연간 추가 비용(55,200원/28,800원)** 과 할증률은 없음. 가족·학생·연간 요금제가 국내에 없다는 공식 근거를 제시한 글도 없음(우회 가입 유도 글 다수).
→ 채운 빈칸: 결제 경로별 연간 비용표 + 할증률.

## 6. 계산 (검증 수치만)

- 웹 연간: Premium 14,900×12 = 178,800 / Lite 8,500×12 = 102,000 / Music 11,990×12 = 143,880
- 아이폰 앱 연간(앱스토어 목록가가 월 요금이라는 전제): Premium 19,500×12 = 234,000 / Lite 10,900×12 = 130,800
- 차액: Premium 4,600/월 → 55,200/년, 할증 4,600/14,900 = 30.9% / Lite 2,400/월 → 28,800/년, 할증 2,400/8,500 = 28.2%
- Premium − Music Premium = 2,910/월 (34,920/년), Premium − Lite = 6,400/월 (76,800/년)
- 아이폰 앱 Lite(10,900) vs 웹 Premium(14,900): 4,000원 차이
