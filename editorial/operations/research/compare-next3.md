# 예약 계산기 글 3편 경쟁 비교 (2026-11-28 조사)

- 조사: Market Researcher. WebSearch·WebFetch·curl(--max-time 30)만 썼고, 브라우저·로그인·폼 제출은 하지 않았다. 클리앙은 공개 검색 결과 페이지(GET)만 읽었다.
- 칸마다 출처를 달았다. 직접 열어 확인하지 못한 칸은 「미확인」으로 적었다.
- 우리 글(HuntLab) 칸의 출처는 로컬 원고 `/Users/sungpyo/huntlab-ops/team1128b/{1919,1925,1798}.html`이다.
- 국가법령정보센터(law.go.kr)는 조문 본문을 스크립트로 불러와 WebFetch·curl로 본문이 보이지 않았다. 그래서 법령 조문은 지자체·부처의 공식 안내 페이지로 대신 확인했고, 대신 확인할 곳이 없는 조문은 「미확인」으로 남겼다.
- 우리 글의 계산 예시(할부 월 납입액·총이자 표, 유예 할부, 임플란트 본인부담 표, 글자수·바이트 예문)는 파이썬으로 다시 계산했고 모두 일치했다.

---

## 1. 임플란트 본인부담금 계산기 (우리: 1919 「임플란트 가격 2026」)

| 항목 | 공식: 국민건강보험공단 치과임플란트 급여 안내 | 도구 A: glasswallet 임플란트 비용 계산기 | 블로그 B: tilnote | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 계산기 없음. 대상(65세 이상 가입자·피부양자, 부분무치악, 평생 2개), 본인부담 30%(차상위 C 10%, E·F 20%), 시술 전체 비급여 사유 4가지, 고정체·지대주 별도 산정을 안내 [공단 안내](https://www.nhis.or.kr/nhis/minwon/wbhapa01000m01.do?mode=view&articleNo=10946916) | 임플란트 브랜드·지역 시세 기준 예상 비용 + 65세 건강보험 적용 여부 + 뼈이식 등 추가 비용 [glasswallet](https://glasswallet.com/calculate/dental-implant-cost) | 계산기 없음. 임플란트·틀니 급여 기준과 정적 금액표, FAQ [tilnote 2026-10-19](https://tilnote.io/pages/6ad564da19114ceafa104114) | 기관 종류 10종별 행위료 + 고정체·지대주 재료값으로 급여비용 총액과 본인부담 계산, 평생 2개 잔여 개수·완전무치악·비급여 보철 판정 (로컬 1919) |
| 입력 항목 | 미확인 (공단 안내 페이지에는 입력 화면이 없고, 요양급여비용 조회 화면은 스크립트로 열려 입력 항목을 확인하지 못함) [요양급여비용 조회](https://www.nhis.or.kr/nhis/together/retrieveMediDentiList.do) | 브랜드 6종, 개수, 지역 5구분, 만 65세 건강보험 적용, 추가 시술(뼈이식·CBCT·임시치아·수면마취·지르코니아 업그레이드) [glasswallet](https://glasswallet.com/calculate/dental-implant-cost) | 해당 없음(계산기 없음) [tilnote](https://tilnote.io/pages/6ad564da19114ceafa104114) | 만 나이, 자격 5종(건강보험·차상위 C·E·F·의료급여 1종·2종), 치과 종류 10종, 기존 급여 개수, 이번 개수, 완전무치악 여부, 비급여 보철 여부, 고정체·지대주 금액 (로컬 1919) |
| 2026 기준값 | 65세, 부분무치악, 평생 2개, 30%, 차상위 C 10%·E·F 20%, 본인부담상한제 미적용 [공단 안내](https://www.nhis.or.kr/nhis/minwon/wbhapa01000m01.do?mode=view&articleNo=10946916). 2026 치과 환산지수 101.1원 [공단 환산지수 표](https://www.nhis.or.kr/announce/wbhaec11413m01.do) | 30%, 의료급여 1종·차상위 희귀난치 10%, 의료급여 2종·차상위 만성 20%. 수가는 "2025~2026년 시세 기준"이라고만 적었고 공단 수가는 쓰지 않음 [glasswallet](https://glasswallet.com/calculate/dental-implant-cost) | "총 진료비 약 120만 원 내외, 본인부담 약 38만~40만 원 내외". 30%로 계산하면 약 36만 원이라 표 안에서 숫자가 맞지 않음. 의료급여 1종 "5%~10%", 2종·차상위 "15%~20%"로 범위 표기 [tilnote](https://tilnote.io/pages/6ad564da19114ceafa104114) | 치과의원 행위료 135,100·580,950·634,990원(합계 1,351,040원), 재료 중간값 포함 1개 1,525,980원, 본인부담 457,700원 (로컬 1919). 치과의원 단가는 상대가치점수 × 101.1원과 일치 (1,336.35점 × 101.1 = 135,105원) |
| 2027 반영 | **2027년 1월부터 65세 이상 완전 무치악도 임플란트 2개 급여.** 완전틀니를 지원받은 사람은 7년이 지난 뒤부터. 본인부담률은 보도자료에 없음 [복지부 2026-09-08](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491824&mid=a10503010100&nPage=1&tag=). 2027 치과 환산지수 103.5원(2.4% + 상대가치 연계 0.2%) [공단 환산지수 표](https://www.nhis.or.kr/announce/wbhaec11413m01.do) | 2027 언급 없음. 완전무치악 확대 언급 없음 [glasswallet](https://glasswallet.com/calculate/dental-implant-cost) | 2027년 1월 완전무치악 2개 지원, 약 7만 명, 1인당 약 228만 원, 완전틀니 후 7년 조건까지 반영 [tilnote](https://tilnote.io/pages/6ad564da19114ceafa104114) | **2027 내용 없음.** "완전무치악 → 시술 전체 비급여, 노인틀니 급여를 알아봐야"라고만 적음 (로컬 1919) |
| 사용자 불만 (페이지별) | 미확인 | 미확인 | 댓글란 없음 [tilnote](https://tilnote.io/pages/6ad564da19114ceafa104114) | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)**
- "65세이상은 2개까지는 저렴하게 해주잖아요, 그이후에 임플란트시술도 모두닥에 올린 가격(오스템BA,48만원) 으로 해 주시는건가요!": 2개 이후 비용이 어떻게 되는지 헷갈려 하는 질문 [모두닥 커뮤니티](https://www.modoodoc.com/community/2359/%EC%9E%84%ED%94%8C%EB%9E%80%ED%8A%B8-%EA%B0%80%EA%B2%A9.)
- "나이가드니 3~4개씩 하게되는데 ... 어르신들 보험도 적용되잖아요": 실제로는 2개를 넘게 하는 경우가 많다는 댓글 [클리앙 2026-10-08](https://www.clien.net/service/board/park/19275074)
- "크라운도 지르코니아 65만원 금으로 하면 110만원 ... 임플란트 보다 보철치료가 비용이 더 비싸네요": 보철 재료값 부담 [클리앙 2026-08-08](https://www.clien.net/service/board/park/19243532)

**공식값 대조 (QA)**: 1919의 2026 수치(30%, 차상위 C 10%·E·F 20%, 평생 2개, 비급여 사유 4가지, 본인부담상한제 제외, 치과의원 단가)는 공식값과 일치한다. 그런데 2027년 1월부터 완전무치악에도 급여가 적용되기 때문에, 12월 이후 발행이면 핵심 조건 문단과 계산기 판정 하나가 곧 틀린 내용이 된다. 2027 수가(환산지수 103.5원)도 반영하지 않았다.

---

## 2. 자동차 할부 계산기 (우리: 1925 「자동차 할부 계산기 2026」)

| 항목 | 공식: 광명시 차량 취득세 안내(지방세법) · 금융감독원 | 도구 A: glasswallet 자동차 할부 계산기 | 도구 B: calcnara 할부 계산기 | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 할부 계산기는 없음. 광명시는 취득세 세율·과세표준·신고기한을 안내한다 [광명시 취득세](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN963.jsp). 경형차 감면도 안내 [광명시 감면](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN966.jsp). 금감원은 유예 할부 구조와 유의사항을 설명 [금감원 2013-05-23](https://www.fss.or.kr/fss/bbs/B0000188/view.do?nttId=10008&menuNo=200218) | 월 납입금, 총이자, 총 상환금, 원리금균등·원금균등 비교, 월별 상환표. 유예 할부·취득세 없음 [glasswallet](https://glasswallet.com/calculate/car-installment) | 원리금균등 월 할부금·총이자, 취등록세, 차량가×금리 매트릭스. 유예 할부는 개념 설명만 [calcnara](https://calcnara.com/calculators/installment) | 원리금균등 월 납입액·총이자, 12~60개월 비교표, 유예(잔가) 할부, 취득세 3구분, 취득세 할부원금 포함 옵션 (로컬 1925) |
| 입력 항목 | 미확인 (공식 할부 계산 화면을 찾지 못함. 여신금융협회 공시는 스크립트로 열려 확인하지 못함) [여신협회 공시](https://gongsi.crefia.or.kr/portal/quota/quotaFinancingDisclosureDetail1?ifgcMode=1) | 차량 가격, 선수금, 연 금리, 기간, 상환방식 [glasswallet](https://glasswallet.com/calculate/car-installment) | 차량 가격, 선수금, 기간, 금리, 취등록세 포함(7%)/미포함 [calcnara](https://calcnara.com/calculators/installment) | 차량가, 선수금, 기간 5종, 연 금리, 유예 비율, 취득세 구분, 취득세 기준 금액, 취득세 할부 포함 여부 (로컬 1925) |
| 2026 기준값 | 비영업용 승용 1천분의 70(경자동차 1천분의 40), 그 밖의 비영업용 1천분의 50(경자동차 40), 영업용 1천분의 40, 이륜 125cc 초과 1천분의 50·50cc~125cc 1천분의 20, 취득일부터 60일 안에 신고·납부(등록 전까지) [광명시 취득세](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN963.jsp). 경형 승용·**승합·화물** 비영업용 취득세 75만 원 감면, 2027-12-31까지 [광명시 감면](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN966.jsp). 실제연간요율 상한 연 20%(할부거래법 시행령): 미확인 | 금리 예시 캐피탈 5~9%, 은행 4~6%, 프로모션 2~4%. 연도 기준 없음(저작권 2025) [glasswallet](https://glasswallet.com/calculate/car-installment) | 승용 7%, 경차 4%("2025년 기준"). **지방교육세 = 취득세×30%, 농특세 0.2%를 더해 약 9.3%로 계산.** 우리 글은 지방세법 제150조 기준으로 차량에는 지방교육세가 붙지 않는다고 적었다(공식 원문 대조는 미확인). FAQ의 전기차 감면 "300만원 한도", 하이브리드 "40만원 한도"는 출처 없음. 최종 검토 2026년 6월 [calcnara](https://calcnara.com/calculators/installment) | 7%·경형 4%(75만 원, 2027년까지)·승용 외 5%·영업용 4%·"125cc 이하 등 이륜 2%", 60일 신고, 개인 할부이자·부가세는 과세표준 제외 (로컬 1925) |
| 2027 반영 | 경차 감면은 현행 2027-12-31까지 [광명시 감면](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN966.jsp). 2026 지방세제 개편안(행안부 2026-08-26 발표)에서 전기차 취득세 감면 한도를 140만→70만 원으로 줄이고 2029년까지 연장한다는 보도는 있다. 부처 원문은 첨부파일이라 확인하지 못했고, 국회 처리도 미확인 [뉴스1 2026-08-26](https://www.news1.kr/local/moi/6269647), [KDI 게시 보도자료 요약](https://eiec.kdi.re.kr/policy/materialView.do?num=285829). 전기차 개별소비세 감면은 2027년 200만 원, 2028년 100만 원, 2029년 종료(정부 세제개편안, 국회 심의 전) [정책브리핑 2026-08-13](https://www.korea.kr/news/policyNewsView.do?newsId=148969870) | 2027 언급 없음 [glasswallet](https://glasswallet.com/calculate/car-installment) | 2027 언급 없음 [calcnara](https://calcnara.com/calculators/installment) | 경차 감면 기한 "2027년까지"만 적음. 전기차 감면·2027 개편안 언급 없음 (로컬 1925) |
| 사용자 불만 (페이지별) | 미확인 | 미확인 | 미확인 | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)**
- "아반테를 유예할부 써서 이자 겁나 내면서 타야 하나요", "저거 이율이 낮아서 그렇게 보이고 사실상 비쌉니다.. 최대 유예를 해버리면 유예한 금액이 그대로 남아있다보니 2.8%지만 이자가 꽤 나옵니다", "초기비용만 적지 나중에 결국 다 내긴 해야하더라구요" [클리앙 2026-10-11](https://www.clien.net/service/board/cm_car/19276153)
- "뒤로 빼둔 유예금을 제외하고 리스총액이 계산되는 게 아니라 차값과 제등록비 모두가 리스총액이 됩니다 ... 당연히 소비자에게 불리한 프로그램입니다" (유예리스 관련) [클리앙 2026-07-04](https://www.clien.net/service/board/cm_car/19220770)

**공식값 대조 (QA)**: 1925의 세율(7%·4%·5%·영업용 4%), 경차 75만 원과 2027-12-31 기한, 60일 신고, 금감원 유예 할부 30%·10%·60% 설명은 공식 안내와 일치한다. 계산 예시도 모두 다시 계산해 일치했다. 어긋나거나 빠진 곳은 세 가지다. (1) 경차 감면 대상에 경형 승합·화물이 빠졌다. (2) 이륜차는 125cc 초과면 5%라는 내용이 없다. (3) 등록 전까지 납부해야 한다는 조건이 없다. 할부거래법·금소법 조문(7일·14일 철회, 연 20% 상한, 10만/20만 원 항변권, 2회·10% 기한이익 상실)은 law.go.kr 본문을 열지 못해 미확인이다.

---

## 3. 글자수 계산기 (우리: 1798 「글자수 계산기 2026」)

> 글자수·바이트 계산을 정한 정부 기준이나 공식 계산기는 찾지 못했다. 공식 칸에는 띄어쓰기 규범(국립국어원)과 문자 부호 표준(KS X 1001)만 적었고, 계산 방식은 채용 사이트 상위 도구 두 곳의 실제 코드와 비교했다.

| 항목 | 공식: 국립국어원 한글 맞춤법 · KS X 1001 | 도구 A: 사람인 글자수 세기 | 도구 B: 잡코리아 글자수 세기 | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 계산 도구 없음. 띄어쓰기 규범(제2·41·43·44·46·47항, 문장 부호)만 있다 [국립국어원](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001). KS X 1001은 "정보 교환에 사용하는 부호계의 표현 형식"을 정한 표준 [KS X 1001](https://standard.go.kr/KSCI/standardIntro/getStandardSearchView.do?menuId=919&topMenuId=502&upperMenuId=503&ksNo=KSX1001) | 공백 포함·제외 글자수와 byte, 맞춤법 검사(최대 4000자) [사람인](https://www.saramin.co.kr/zf_user/tools/character-counter) | 공백 포함·제외 글자수와 byte [잡코리아](https://www.jobkorea.co.kr/service/user/tool/textcount) | 공백 포함, 공백 포함(줄바꿈 제외), 공백 제외, 2바이트·UTF-8 바이트, 줄 수, 어절 수, 200자 원고지 매수, 제한 대비 남은 분량 (로컬 1798) |
| 입력 항목 | 해당 없음(도구 없음) [국립국어원](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001) | 본문 텍스트 하나 [사람인](https://www.saramin.co.kr/zf_user/tools/character-counter) | 본문 텍스트 하나 [잡코리아](https://www.jobkorea.co.kr/service/user/tool/textcount) | 본문 텍스트, 제한 분량, 기준(단위) 선택 (로컬 1798) |
| 2026 기준값 | 한글 맞춤법은 문화체육관광부 고시 제2017-12호. 조문 인용 6곳 확인. 쌍점 "앞은 붙여 쓰고 뒤는 띄어 쓴다. 다만, (3)과 (4)에서는 쌍점의 앞뒤를 붙여 쓴다" [국립국어원](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001). KS X 1001 최종 개정·확인 2024-10-30 [KS X 1001](https://standard.go.kr/KSCI/standardIntro/getStandardSearchView.do?menuId=919&topMenuId=502&upperMenuId=503&ksNo=KSX1001). 원고지 쓰기 공식 규정: 미확인 | 코드 확인: 한글 등 비ASCII 문자는 2byte, 줄바꿈 1byte, 나머지 1byte. 글자수는 JS `length`라 이모지가 2자. 공백 제외는 `\s` 전체 제거 [사람인 스크립트](https://www.saramin.co.kr/js/tools/character_counter.js?20261126103303) | 코드 확인: 문자 코드 127 초과는 2byte(이모지는 4byte), 글자수는 JS `length`(이모지 2자), 공백 제외는 공백·줄바꿈 제거 [잡코리아](https://www.jobkorea.co.kr/service/user/tool/textcount) | 한글 UTF-8 3바이트·2바이트 기준 2바이트, 이모지 1자(Array.from), 200자 원고지 = 공백 포함 ÷ 200 올림 (로컬 1798) |
| 2027 반영 | 미확인 (개정 예고를 찾지 못함) | 해당 없음(연도별로 바뀌는 기준값 없음) | 해당 없음(연도별로 바뀌는 기준값 없음) | 해당 없음 |
| 사용자 불만 (페이지별) | 미확인 | 미확인 | 미확인 | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)**
- "글자 제한 700자라 길래 평소대로 공백포함 600~700자로 맞췄는데 오늘 들어가서 입력해보니 Byte 기준이네요 .. 1100/1400 정도인데 괜찮을까요" [코멘토 2026-03-27](https://comento.kr/job-questions/모든회사/모든직무/자소서_글자수%20제한%20byte-623029)
- "같은 문장을 붙여 넣어도 편집 프로그램과 채용 사이트의 글자 수가 다르게 표시되는 경우가 있더라고요." / 답변: "글자 수 차이 때문에 마감 직전에 당황하는 지원자분들 정말 많습니다." [코멘토 2026-10-26](https://comento.kr/job-questions/모든회사/모든직무/자소서_글자%20수가%20편집기와%20지원%20사이트에서%20다르게%20나오면%20어떻게%20맞추나요-640534)

**공식값 대조 (QA)**: 1798에 인용한 맞춤법 조문 6곳과 쌍점 규정, KS X 1001 적용범위 문구는 원문과 일치한다. 예문 3개, 바이트 제한별 최대 글자수 표, EUC-KR 2,350자와 CP949 11,172자도 다시 계산해 일치했다. 다만 파이썬 `euc-kr` 코덱은 나머지 8,822자를 오류로 내지 않고 8바이트 조합형 문자열로 바꾼다. 본문의 "2바이트로 표현되지 않았다"는 틀린 말은 아니지만, "저장되지 않는다"로 읽히지 않게 다듬는 편이 좋다. 원고지는 공식 규범이 없다(아래 목록 참고).

---

## 우리 글 vs 공식값 불일치·낡은 내용 목록

| 글 | 항목 | 우리 글 | 공식 | 판정 |
|---|---|---|---|---|
| 1919 | 완전무치악 | "완전무치악 환자에게 시술하면 시술 전체가 비급여 ... 노인틀니 급여를 따로 알아봐야", 계산기도 완전무치악이면 비급여로 판정 | 2027년 1월부터 65세 이상 완전 무치악도 2개 급여, 완전틀니를 받았으면 7년 뒤부터 [복지부 2026-09-08](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491824&mid=a10503010100&nPage=1&tag=). 공단 안내는 아직 현행(비급여)으로 남아 있음 [공단](https://www.nhis.or.kr/nhis/minwon/wbhapa01000m01.do?mode=view&articleNo=10946916) | **곧 낡음, 가장 시급.** 2026년 중엔 맞지만 1월 1일부터 틀림. "2027년 1월 바뀜" 문단, FAQ, 계산기 시술 시점 선택이 필요하다. 시행 고시와 본인부담률은 미확인 |
| 1919 | 2027 수가 | 2026.1.1. 단가만 적음 | 치과 환산지수 2026 101.1원 → 2027 103.5원 [공단 환산지수 표](https://www.nhis.or.kr/announce/wbhaec11413m01.do) | 낡음 예정. 점수가 그대로라면 치과의원 행위료 합계는 약 138만 3천 원(우리 계산, 공식 단가표 아님) |
| 1919 | 차상위 C 10% | 시행령 별표 2 라목 기준 10% | 복지부는 희귀·중증난치질환 본인부담을 2026년 12월 7%, 2028년 상반기 5%로 낮춘다고 발표(산정특례 대상). 차상위 임플란트 비율에도 영향이 있는지는 보도자료에 없음 [복지부 2026-09-08](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491824&mid=a10503010100&nPage=1&tag=) | 미확인. 발행 전 공단에 확인 권장 |
| 1919 | 치과의원 외 9개 기관 단가, 재료 중간값 | 표 기재 | 미확인 (요양급여비용 조회 화면이 스크립트로 열림) | 미확인 |
| 1919 | 의료급여 1종 10%·2종 20% | 시행령 별표 1 인용 | 미확인 (law.go.kr 본문 미표시). 민간 도구 glasswallet도 같은 값 | 미확인 |
| 1925 | 경차 감면 대상 | 경형 **승용**만 4%·75만 원 감면 | 경형 승용·승합·화물 모두 비영업용이면 75만 원 감면 [광명시](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN966.jsp) | 누락, 보강 필요 |
| 1925 | 이륜차 세율 | "125cc 이하 등 이륜자동차 2%" | 50cc~125cc 2%, 125cc 초과 5% [광명시](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN963.jsp) | 틀리진 않지만 불완전 |
| 1925 | 신고·납부 기한 | 취득일부터 60일 | 60일 이내, 등록하려면 등록 전까지 [광명시](https://www.gm.go.kr/pt/partInfo/tf/tf01/registration_costs/PTMN963.jsp) | 보강 권장(신차는 대개 등록 때 납부) |
| 1925 | 전기차 취득세 | 언급 없음 | 2026 지방세제 개편안: 감면 한도 140만→70만, 2029년까지(보도, 국회 처리 미확인) [뉴스1](https://www.news1.kr/local/moi/6269647) | 빈틈. 확정되면 추가 |
| 1925 | 할부거래법·금소법 조문 | 7일·14일 철회, 연 20%, 10만/20만 원, 2회·10% | 미확인 (law.go.kr 본문 미표시) | 미확인 |
| 1798 | 채용 사이트 바이트 기준 | "공식 자료로 확인하지 못했다" | 공식 자료는 없다. 다만 사람인·잡코리아 두 곳 모두 코드상 한글 2바이트, 이모지 2자 [사람인](https://www.saramin.co.kr/js/tools/character_counter.js?20261126103303), [잡코리아](https://www.jobkorea.co.kr/service/user/tool/textcount) | 보강 가능(실측 근거) |
| 1798 | 원고지 최소 매수 | 공백 포함 ÷ 200 올림이 "최소치" | 국립국어원 어문 규범에는 원고지 사용법이 없다는 온라인가나다 답변이 2차 인용으로만 확인됨 [yugacrew 블로그](https://www.yugacrew.com/crewletter/manuscript-paper-writing-rules-printable). 관행상 두 자리 이상 숫자·영문 소문자는 한 칸에 두 자 [다음 카페](https://m.cafe.daum.net/hahaca/RtjI/14) | 공식 근거 미확인. 숫자가 많은 글은 "최소치"보다 적게 나올 수 있어 표현을 다듬을 것 |
| 1798 | 맞춤법·KS X 1001 인용 | 조문 6곳·쌍점·적용범위 | 원문과 일치 [국립국어원](https://korean.go.kr/kornorms/regltn/regltnView.do?regltn_code=0001), [KS X 1001](https://standard.go.kr/KSCI/standardIntro/getStandardSearchView.do?menuId=919&topMenuId=502&upperMenuId=503&ksNo=KSX1001) | 일치 |

## 우리가 노릴 빈틈 3개

1. **임플란트 "2027년 1월부터 치아가 하나도 없어도 2개"를 계산기에 넣기.** 민간 계산기 glasswallet은 완전무치악 확대를 다루지 않고 공단 수가도 쓰지 않는다([glasswallet](https://glasswallet.com/calculate/dental-implant-cost)). tilnote는 확대 내용은 적었지만 계산기가 없고 금액표 숫자도 맞지 않는다([tilnote](https://tilnote.io/pages/6ad564da19114ceafa104114)). 복지부가 확정 발표했고([복지부 2026-09-08](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491824&mid=a10503010100&nPage=1&tag=)) 2027 환산지수 103.5원도 나와 있다([공단](https://www.nhis.or.kr/announce/wbhaec11413m01.do)). 그러니 계산기에 "시술 시점: 2026년 / 2027년 1월 이후"를 두면 된다. 완전무치악 판정을 시점에 따라 바꾸고, 완전틀니 7년 조건을 함께 보여 주면 공단 수가로 계산하는 유일한 도구가 된다. "2개 이후 비용" 질문도 실제로 있다([모두닥](https://www.modoodoc.com/community/2359/%EC%9E%84%ED%94%8C%EB%9E%80%ED%8A%B8-%EA%B0%80%EA%B2%A9.)).
2. **유예 할부 "숨은 이자"를 같은 차·같은 금리로 바로 비교하기.** 클리앙에서는 "2.8%지만 이자가 꽤 나옵니다", "이자 겁나 내면서"처럼 유예 이자가 크다는 불만이 반복된다([클리앙](https://www.clien.net/service/board/cm_car/19276153)). glasswallet은 유예 할부를 계산하지 않고([glasswallet](https://glasswallet.com/calculate/car-installment)), calcnara는 일반 할부만 계산하면서 차량에 지방교육세 30%를 더한다([calcnara](https://calcnara.com/calculators/installment)). 우리는 이미 유예 비율을 계산한다. 여기에 "일반 할부 대비 총이자 차이"와 "만기에 필요한 목돈"을 결과 첫 줄에 크게 보여 주고, 경형 승합·화물 감면과 이륜 125cc 초과 5%를 채우면 취득세까지 공식과 맞는 유일한 할부 계산기가 된다.
3. **"이 사이트는 몇 바이트로 세나"를 사이트별 실측표로 보여 주기.** 지원자는 "700자인 줄 알았는데 Byte 기준"이었다며 혼란을 겪는다([코멘토](https://comento.kr/job-questions/모든회사/모든직무/자소서_글자수%20제한%20byte-623029), [코멘토](https://comento.kr/job-questions/모든회사/모든직무/자소서_글자%20수가%20편집기와%20지원%20사이트에서%20다르게%20나오면%20어떻게%20맞추나요-640534)). 사람인과 잡코리아는 한글 2바이트로 세고 이모지는 2자로 센다(각 사이트 코드에서 확인: [사람인](https://www.saramin.co.kr/js/tools/character_counter.js?20261126103303), [잡코리아](https://www.jobkorea.co.kr/service/user/tool/textcount)). 그런데 두 사이트 모두 이 기준을 화면에 적어 두지 않았다. 우리 글의 "공식 자료로 확인하지 못했다"를 "사람인·잡코리아는 2바이트 기준(2026-11-28 코드 확인)"으로 바꾸고, 계산기에 "사람인·잡코리아와 같은 방식" 값을 따로 보여 주면 된다.
