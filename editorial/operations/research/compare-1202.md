# 12/02~12/04 계산기 글 3편 경쟁 비교 (2026-11-28 조사)

- 조사: Market Researcher. WebSearch·WebFetch·curl(--max-time 30)만 썼고, 브라우저·로그인·폼 제출은 하지 않았다.
- 칸마다 출처를 달았다. 직접 열어 확인하지 못한 칸은 「미확인」으로 적었다.
- 우리 글(HuntLab) 칸의 출처는 로컬 원고 `/Users/sungpyo/huntlab-ops/team1128/{1916,2006,2070}.html`이다.
- 사용자 불만은 커뮤니티 원글·댓글에서 인용할 수 있었던 것만 실었다. 경쟁 페이지 자체에는 댓글란이 없거나 열람이 막혀 페이지별 불만은 대부분 「미확인」이고, 키워드 전반의 불만은 표 아래에 따로 정리했다.

---

## 1. 기초연금 계산기 (우리: 1916 「기초연금 금액 계산기 2026」)

| 항목 | 공식: 기초연금 누리집 → 복지로 모의계산 | 블로그·도구 A: glasswallet | 블로그 B: moneyroan | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 누리집에는 소득인정액 모의계산 안내만 있고, 실제 계산은 비회원은 복지로, 회원은 국민연금공단으로 연결한다. "실제 금액과 근사치의 금액을 계산하시려면 국민연금의 모의계산 서비스를 이용해주세요" [누리집](https://basicpension.mohw.go.kr/menu.es?mid=a10303000000). NPS 쪽은 "국민연금 (예상) 급여액을 반영한 기초연금 예상 급여액과 나의 소득인정액"을 보여 준다고 안내한다 [NPS](https://www.nps.or.kr/comm/pop/getOHAH0015P1.do) | 수급 여부, 예상 월액, 소득인정액, 국민연금 연계감액, 부부감액. 소득역전방지는 별도 안내 페이지에서만 다룬다 [glasswallet](https://glasswallet.com/calculate/basic-pension) | 소득인정액 간편 계산만 한다(소득평가액·재산환산액·합계·선정기준액). 기초연금액은 계산하지 않는다 [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/) | 소득인정액, 예상 기초연금액, 국민연금 연계감액(A급여를 모르면 범위로 표시), 부부감액 20%, 소득역전방지, 고급차·회원권 처리 (로컬 1916) |
| 입력 항목 | 미확인 (복지로 페이지가 JS 앱이라 curl로 입력 항목이 보이지 않음) [복지로](https://www.bokjiro.go.kr/ssis-teu/twatbz/mkclAsis/mkclInsertBspnPage.do) | 가구유형, 지역(3구분), 근로소득, 기타소득, 국민연금액, 일반재산, 금융재산, 부채 [glasswallet](https://glasswallet.com/calculate/basic-pension) | 가구유형, 지역, 근로소득, 기타소득(국민연금 포함), 재산 합계, 부채 [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/) | 가구 3유형(단독, 부부 둘 다 수급, 부부 1인 수급), 본인·배우자 근로소득, 본인·배우자 국민연금 노령/유족·장애 구분, A급여, 기타 공적연금, 이자, 사업·임대, 지역, 일반재산, 금융재산, 부채, 4천만 원 이상 차·회원권 (로컬 1916) |
| 2026 기준값 | 선정기준액 단독 2,470,000원·부부 3,952,000원 [대상자 안내](https://basicpension.mohw.go.kr/menu.es?mid=a10102010000). 기준연금액 월 349,700원, 150% 선 524,550원 [기초연금액 산정](https://basicpension.mohw.go.kr/menu.es?mid=a10103010000). 근로소득공제 116만 원 [소득인정액 산정방식](https://basicpension.mohw.go.kr/menu.es?mid=a10102020000) | 247만/395.2만, 349,700원, 524,550원, 116만 원, 기본재산 대도시 1억 3,500만, 금융재산 2,000만. **단, FAQ 부부 예시에 349,360원이라는 다른 값이 섞여 있음** [glasswallet](https://glasswallet.com/calculate/basic-pension) | 247만/395.2만, 349,700원. **근로소득공제를 "112만원"(2025년 값)으로 적었고 "기준연금액 약 52만 4,550원"이라고 잘못 표기** [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/) | 247만/395.2만, 349,700원, 116만 원, 524,550원, 이자공제 4만 원, 기본재산액 3구분 (로컬 1916). 공식값과 일치 |
| 2027 반영 | 누리집은 2026년 값만 게시. 정부안은 복지부 9/4 보도자료에 있다: 2027 예산안에서 하위 0~30% 부부 월 56만→68.4만 원, 30~45% 부부 56만→64.6만 원, 부부감액 비율 축소(234만 명), 직역연금 수급자도 최대 38만 원. 국회 심의 전 [복지부 보도자료 2026-09-04](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491795&mid=a10503010100&nPage=1&tag=) | 2027 언급 없음 [glasswallet](https://glasswallet.com/calculate/basic-pension) | 2027 언급 없음 (작성 2026-03-24, 수정 2026-04-02) [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/) | 거주요건 법 개정(10/1)과 6월 포럼만 언급하고 "2027년 값은 아직 발표되지 않았다"고 적음. **9/4 정부안(차등지급·부부감액 축소·직역연금 지원)은 빠져 있음** (로컬 1916) |
| 사용자 불만 (페이지별) | 미확인 | 미확인 (댓글란 없음) | 원문에 댓글란 없음 [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/) | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)**
- "소득이 아니라 소득산정액입니다. 집 가격을 월 소득으로 계산하는 방식이 있더라구요": 월 213만 원이면 왜 받느냐는 질문에 달린 답 댓글로, 소득인정액 개념이 헷갈린다는 신호 [클리앙 2024-05-06](https://www.clien.net/service/board/park/18719271)
- 부모 주식 10억 원 보유 시 탈락 여부를 묻는 글. 댓글마다 선정기준액이 247만 원과 228만 원으로 엇갈리고, "왜 금융소득에 대한 잣대만 다를까요?"라는 댓글이 있음 [82cook 2026-04-26](https://www.82cook.com/entiz/read.php?bn=15&num=4181726)

**공식값 대조 (QA)**: 1916의 수치(349,700 / 2,470,000·3,952,000 / 116만 / 524,550 / 34,970·174,850·699,400·874,250)는 공식값과 일치하고, 수치 불일치는 없다. 다만 "2027년에 달라지는 것" 섹션이 복지부 2026-09-04 정부안을 반영하지 않아 내용이 낡았다. 직역연금 제외 문단에도 2027 정부안 내용(직역연금 수급자 최대 38만 원 지원 예정, 국회 확정 전)을 덧붙여야 한다.

---

## 2. 주택연금 계산기 (우리: 2006 「주택연금 계산기 2026」)

| 항목 | 공식: HF 예상연금조회 | 도구 A: glasswallet | 도구 B: devcomma | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 지급방식별 월지급금, 최대인출한도(50/70/90/45%), 인출한도 설정액, 초기보증료, 정액형·초기증액형(3/5/7/10년)·정기증가형 월지급금 표 [HF 예상연금조회](https://www.hf.go.kr/ko/sub03/sub03_02_02.do) | 월·연 수령액, 초기보증료, 연보증료 추정, 10/20/30년 누적액, 집을 팔아 연 4%로 굴렸을 때와 비교 [glasswallet](https://glasswallet.com/calculate/housing-pension) | 예상 월지급액, 가입 가능성 간이 판정, 생활비 목표 대비 % [devcomma](https://tools.devcomma.com/calculators/home-pension) | 일람표 기준 월지급금, 인출한도, 초기보증료. 중간 가격은 직선 보간 (로컬 2006) |
| 입력 항목 | 소유자 생년월일, 배우자 유무·생년월일, 주택구분(일반, 노인복지, 오피스텔), 최저층 여부, 주택가격(시세검색), 기초연금 수급 여부, 1가구 1주택 여부, 지급방식 7종, 인출한도 비율, 지급기간 [HF](https://www.hf.go.kr/ko/sub03/sub03_02_02.do) | 시세, 연소자 나이, 주택유형 3종 [glasswallet](https://glasswallet.com/calculate/housing-pension) | 주택구분 2종, 연소자 나이, 시세, 공시가격, 주택 수, 국적·실거주 충족 여부, 기초연금 여부, 지급방식 4종, 생활비 목표 [devcomma](https://tools.devcomma.com/calculators/home-pension) | 본인·배우자 나이, 시세, 주택유형 2종, 우대형 체크 (로컬 2006) |
| 2026 기준값 | 월지급금 예시표 "2026.03.01. 기준"(70세·3억 = 923천원) [HF 월지급금 예시](https://www.hf.go.kr/ko/sub03/sub03_01_01_02.do). 일람표 엑셀 "2026. 6. 1. 신청접수분부터 적용"(85세·90세, 우대형 65세 1억 297·2억 568 포함) [같은 페이지 다운로드](https://www.hf.go.kr/ko/sub03/sub03_01_01_02.do). 초기보증료 1.0%, 연보증료 0.95%(대출상환(우대) 1.0%) [HF 주택연금이란](https://www.hf.go.kr/ko/sub03/sub03_01_01_01.do) | 적용일을 "2026-03-01 이후 신규 신청분"으로 적음. 초기 1.0%, 연 0.95% [glasswallet](https://glasswallet.com/calculate/housing-pension) | "2026년 6월 1일 기준 일람표" 55~90세, 1억~12억. 보증료·금리 수치 없음 [devcomma](https://tools.devcomma.com/calculators/home-pension) | 6/1 일람표 55~90세. 초기 1.0%, 연 0.95%, COFIX+0.85% (로컬 2006). **표 55~90세 전 칸을 공식값과 대조했고 일치함** |
| 2027 반영 | 미확인 (2027 조정 발표를 찾지 못함) | 2027 언급 없음 [glasswallet](https://glasswallet.com/calculate/housing-pension) | 2027 언급 없음 [devcomma](https://tools.devcomma.com/calculators/home-pension) | "2027 조정은 미발표"라고 명시. 재산세 감면 2027년까지 (로컬 2006) |
| 사용자 불만 (페이지별) | 미확인 | 미확인 | 미확인 | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)** [클리앙 2023-08-29 「주택연금 생각보다 많지 않네요???」](https://www.clien.net/service/board/park/18274762)
- "계산기 두들겨보면..생각보다 적게 받아요."
- "수령액이 월세내는정도의 금액을 제하고 주는것 같더군요"
- "주택연금은 이름 때문에 혼동이 생겨서 그렇지 그냥 대출이죠."

**공식값 대조 (QA)**: 2006의 일람표 수치(55·60·65·70·75·80세는 HF 예시 페이지, 85·90세와 우대형은 HF 엑셀), 오피스텔·노인복지주택 70세·3억(746·789), 초기보증료 1.0%·연보증료 0.95%는 모두 일치하고, 수치 불일치는 없다. 참고로 HF 「주택연금이란」 페이지 HTML에는 "CD금리+1.1% 또는 COFIX+0.85%" 문구가 아직 남아 있다(주석 처리된 영역일 수 있음). 우리 글은 백문백답을 근거로 CD 기준 잠정 중단이라고 적었으므로, 발행 전 백문백답 원문을 한 번 더 확인할 것을 권한다.

---

## 3. 출산휴가 급여 계산기 (우리: 2070 「출산휴가 급여 계산기 2026」)

| 항목 | 공식: 고용24 출산휴가급여 모의계산 | 도구 A: glasswallet | 블로그 B: studygov | HuntLab(우리) |
|---|---|---|---|---|
| 제공 범위 | 모의계산 메뉴 "출산휴가급여 계산해보기"가 있다 [고용24 지원금 모의계산](https://www.work24.go.kr/cm/c/f/1200/selecSimulateCalc.do?currentPageNo=1&recordCountPerPage=10). 안내 페이지에는 "모의계산에서 나온 급여액과 실제 고용센터에서 지급되는 출산전후휴가급여는 상이할 수 있습니다"라고 적혀 있다 [고용24 안내](https://m.work24.go.kr/cm/ou3) | 총 급여, 월평균, 고용보험 몫과 회사 몫 분리 [glasswallet](https://glasswallet.com/calculate/maternity-benefit) | 계산기 없음. 자격, 금액, 회사 규모, 신청, 서류를 설명하는 글 [studygov](https://studygov.kr/blog/0401-maternity-leave-benefit-2026/) | 구간별로 누가 얼마를 주는지(고용보험, 회사), 90일 합계, 최저임금 하한 보정, 휴가 일수 단축 반영 (로컬 2070) |
| 입력 항목 | 미확인 (계산 화면이 POST로만 열려 GET 요청은 405 응답. 폼 제출 금지 규칙에 따라 열지 않음) | 월 통상임금, 출산유형(90/100/120일), 회사 규모(대기업·우선지원), 휴가기간 [glasswallet](https://glasswallet.com/calculate/maternity-benefit) | 해당 없음(계산기 없음) | 월 통상임금, 월 소정근로시간, 회사 규모, 출산유형 3종, 휴가 일수 (로컬 2070) |
| 2026 기준값 | 30일 기준 최대 220만 원 [고용24 안내](https://m.work24.go.kr/cm/ou3). 고시 제2026-67호: 90일 660만 원, 미숙아 100일 7,333,330원, 다태아 120일 880만 원, 배우자 20일 1,684,210원, 2026-09-18 시행, 12-31까지 효력 [고용노동부 고시](https://www.moel.go.kr/info/lawinfo/instruction/view.do?bbs_seq=20260900589) | 월 상한 220만 원, 하한 약 215만 원 [glasswallet](https://glasswallet.com/calculate/maternity-benefit) | 월 220만 원, 하한 215만 6,880원(시급 10,320원), 작성 2026-01-03 [studygov](https://studygov.kr/blog/0401-maternity-leave-benefit-2026/) | 660만 / 7,333,330 / 880만 / 1,684,210원, 하한 2,156,880원 (로컬 2070). 공식값과 일치 |
| 2027 반영 | 2027 최저임금 시급 10,700원, 월 2,236,300원(2026-08-05 고시) [고용노동부](https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq=19744). 상한액 고시 개정안(공고 제2026-491호, 11/2 행정예고)은 출산휴가 상한을 그대로 두고 난임치료휴가 4일분 상한(336,840원)을 추가하며 2026-11-27 시행, 12-31까지 효력. 2027 상한은 아직 없음 [행정예고](https://www.moel.go.kr/info/lawinfo/lawmaking/view.do?bbs_seq=20261100031) | 2027 언급 없음 [glasswallet](https://glasswallet.com/calculate/maternity-benefit) | 2027 언급 없음 [studygov](https://studygov.kr/blog/0401-maternity-leave-benefit-2026/) | 2027 상한은 미발표로 명시하고 2027 하한 기준 시급 10,700원을 적음 (로컬 2070) |
| 사용자 불만 (페이지별) | 미확인 | 미확인 | 댓글 없음(FAQ는 사이트 자체 작성) [studygov](https://studygov.kr/blog/0401-maternity-leave-benefit-2026/) | 해당 없음 |

**키워드 전반의 사용자 불만 (인용 가능분)**
- 출산휴가와 육아휴직 급여를 혼동한 사례: "출산휴직이 월급 80%, 육아휴직은 무급일거에요."(사실과 다른 설명) / "출산휴가(2개월은 회사에서 기본급 100% 지급, 1개월은 고용보험에서 기본급 100% 지급)" [클리앙 2020-09-25](https://www.clien.net/service/board/park/15421733). 누가 얼마를 주는지 헷갈려 한다는 근거다. 2020년 글이라 금액은 낡았다.
- 최근 불만 글(블라인드, 더쿠)은 402·403 응답으로 열리지 않아 「미확인」.

**공식값 대조 (QA)**: 2070의 상한·하한 수치는 공식값과 일치하고, 수치 불일치는 없다. 다만 본문의 "지금 적용되는 고시(제2026-67호, 2026.9.18. 시행)" 표현은 11/27 개정 고시(공고 제2026-491호 행정예고안, 출산휴가 금액은 같음)가 시행됐다면 바뀌어야 한다. 행정예고안대로 확정·시행됐는지는 확인하지 못했다(미확인). 또 2027 최저임금 월 환산액 2,236,300원이 현행 30일 상한 220만 원보다 크다. 2027 상한 고시가 나오지 않은 상태에서 "2027년 시작이면 시급 10,700원이 하한"이라는 문장만 두면, 하한이 상한을 넘는 셈이 되어 독자가 헷갈릴 수 있다.

---

## 우리 글 vs 공식값 불일치 목록

| 글 | 항목 | 우리 글 | 공식 | 판정 |
|---|---|---|---|---|
| 1916 | 2027 기초연금 | "2027년 값 미발표, 6월 포럼은 확정 아님"만 적음 | 2027 예산안: 하위 0~30% 부부 68.4만 원, 30~45% 64.6만 원, 부부감액 축소, 직역연금 최대 38만 원 (국회 심의 전) [복지부 2026-09-04](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491795&mid=a10503010100&nPage=1&tag=) | 낡은 내용, 보강 필요 |
| 2070 | 현행 고시 번호 | 제2026-67호 | 2026-11-27 시행 개정안 행정예고(출산휴가 금액은 같음) [공고 제2026-491호](https://www.moel.go.kr/info/lawinfo/lawmaking/view.do?bbs_seq=20261100031) | 확정 여부 미확인, 금액 영향 없음 |
| 2070 | 2027 하한 vs 상한 | 하한 시급 10,700원만 적음 | 2027 월 2,236,300원 > 현행 상한 220만 원 [고용노동부](https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq=19744) | 수치 오류는 아님, 설명 보강 권장 |
| 2006 | 없음 | 일람표·보증료 전부 일치 | [HF](https://www.hf.go.kr/ko/sub03/sub03_01_01_02.do) | 일치 |

## 우리가 노릴 빈틈 3개

1. **"2027 기초연금 얼마 받나"를 계산기로 보여 주기.** 경쟁 두 곳은 2027을 전혀 다루지 않는다([glasswallet](https://glasswallet.com/calculate/basic-pension), [moneyroan](https://moneyroan.com/gichoeyongeum-moeuigyesan-2026/)). moneyroan은 근로소득공제를 2025년 값(112만 원)으로 계산한다. 복지부 9/4 정부안(하위 30% 부부 68.4만 원, 부부감액 축소)이 있으므로 "정부안 기준, 국회 확정 전"이라고 표시해 2026 금액과 2027 정부안 금액을 나란히 보여 주면 된다. [근거: 복지부 2026-09-04](https://mohw.go.kr/board.es?act=view&bid=0027&list_no=1491795&mid=a10503010100&nPage=1&tag=)
2. **출산휴가 2027 상한·하한 역전 미리 알리기.** 2027 최저임금 월 환산액 2,236,300원이 현행 30일 상한 220만 원을 넘는다([고용노동부](https://www.moel.go.kr/news/enews/report/enewsView.do?news_seq=19744)). 그런데 현행 고시는 12/31에 효력이 끝난다([행정예고](https://www.moel.go.kr/info/lawinfo/lawmaking/view.do?bbs_seq=20261100031)). 경쟁 페이지 중 2027을 다룬 곳은 없다([glasswallet](https://glasswallet.com/calculate/maternity-benefit), [studygov](https://studygov.kr/blog/0401-maternity-leave-benefit-2026/)). "2027년 1월 휴가 시작자는 상한 고시를 확인하라"는 안내와 함께, 고시가 나오는 날 바로 갱신할 수 있게 준비해 둔다.
3. **주택연금 "생각보다 적다, 그냥 대출"이라는 불만에 답하기.** 실제 커뮤니티 반응이 이렇다([클리앙](https://www.clien.net/service/board/park/18274762)). 공식 HF 조회는 초기증액형·정기증가형·인출한도까지 보여 주지만([HF 예상연금조회](https://www.hf.go.kr/ko/sub03/sub03_02_02.do)), 민간 도구는 정액형만 다루거나 보증료 수치를 아예 빼 둔다([devcomma](https://tools.devcomma.com/calculators/home-pension)). 우리 글에 "가입 후 대출잔액이 어떻게 늘어나는지(초기보증료 1.0% + 연 0.95% + 이자)" 예시를 넣고, 초기증액형은 HF 조회로 확인하도록 안내하면 차별점이 된다.
