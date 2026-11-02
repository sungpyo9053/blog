# 기초대사량 계산기 — 조사 메모 (2026-11-03)

키워드: 기초대사량계산기 월 17,810 (오케스트레이터 제공).
기존 life 글과 겹침: `2026-11-26-bmi-calculator`(bmi-calculator-2026, 2026-11-26 21:00 발행 예정)는 BMI·비만 단계·허리둘레만 다루고 기초대사량·에너지 필요량은 다루지 않는다(ko.html grep "기초대사|kcal" 결과 없음). 이 글은 BMI 판정을 반복하지 않고 링크한다. 다른 life 글에 기초대사량·에너지필요추정량 주제 없음(`grep -l -E "기초대사|대사량|에너지필요추정량|kcal" */ko.html` 결과 0건).
카테고리: 328(브리프 지시대로 템플릿 weekly-holiday-pay meta.json과 같은 값. 참고로 bmi-calculator는 330).

브리프는 「2020 한국인 영양소 섭취기준」을 지목했지만, 한국영양학회 자료실에서 보건복지부가 2025년 12월 31일 발표한 「2025 한국인 영양소 섭취기준」이 최신본으로 확인돼 2025판을 썼다. 2025판은 에너지 필요추정량 공식을 2020판과 같게 유지했다고 적고 있다(아래 인용).

## 출처와 원문 (curl 11/03, 원본 evidence/ 저장)

kns.or.kr은 상세 페이지·첨부파일 요청에서 인증서 체인 오류("SSL certificate problem: unable to get local issuer certificate")가 나서 `curl -k`로 받았다.

### 한국영양학회 자료실 (kns.or.kr)
- 자료실 목록 https://www.kns.or.kr/FileRoom/FileRoom.asp?BoardID=Kdr → evidence/kns-fileroom.html (EUC-KR)
- 게시글 idx=167 → evidence/kns-fileroom-view-167.html
  - 제목: "2025 KDRI (보건복지부 발간) 공개자료(25.12.31) 배포 및 오타(26.2.2., 2.27., 3.16) 안내", 작성자 "(사)한국영양학회", 작성일 "2025년 12월 31일 수요일"
  - "보건복지부는 한국영양학회를 통해 3개년(2023-2025년)에 걸쳐 영양소 섭취기준 제•개정 연구를 수행하였고, 2025년 12월 31일 새벽에 보도자료 통해 발표하였습니다."
  - "2010년 제정된 「국민영양관리법」에 근거하여 국가차원에서 2015년부터 5년 주기로 국민의 건강증진 및 만성질환 예방을 위한 에너지 및 각 영양소의 적정 섭취 수준을 제시합니다."
  - 첨부: "★2025 KDRI_책자(3권) 요약본(2종)_정오표 적용_f4.zip (16.98MB)", "2025 KDRI_요약표_국문_2025.12.29.pdf (326.55KB)"
- 게시글 idx=165 (헬스조선 기사 전재, 2025.11.11) → evidence/kns-fileroom-view-165.html. 개정 배경 참고용, 글에서 수치 인용하지 않음.
- 요약표 PDF → evidence/kns-2025-kdri-summary-table.pdf
- zip 안의 「1권 에너지와 다량영양소」 → evidence/kdri2025-vol1-energy-macronutrients.pdf, 국문 요약본 → evidence/kdri2025-summary-ko.pdf (나머지 2·3권·영문본·정오표는 주제와 무관해 저장하지 않음)

#### 1권 에너지 장 인용 (pdftotext)
- 구성: "1일 총에너지소비량은 기초대사량, 신체활동대사량, 그리고 식사성 발열효과로 구성된다 [8]."
- 기초대사량: "기초대사량은 인체의 기본적인 생리적 기능을 유지하는데 소비되는 최소한의 에너지를 말하며, 일반적으로 1일 총에너지소비량의 60-75%를 차지한다." "기초대사량은 식사와 활동이 거의 없는 상태 (약 12-14시간)에서 소비되는 에너지량이므로 이른 아침 기상 직후 측정해야 한다."
- 휴식대사량: "식후 4-6시간이 지난 후 휴식을 취하고 있는 상태에서 측정하는 휴식대사량 (Resting Energy Expenditure, REE)이 기초대사량을 대신하여 이용되고 있다. 휴식대사량은 기초대사량과 약 10% 정도 차이가 있는 것으로 보고되고 있는데" "실제로 에너지소비량에 관한 대부분의 연구에서는 기초대사량과 휴식대사량을 혼용해서 사용하고 있기도 하다."
- 신체활동대사량: "신체활동량이 낮은 사람은 신체활동대사량이 기초대사량의 반에도 미치지 못하는 경우도 있는 반면, 활동량이 많은 운동선수나 일부 고강도의 육체적 노동자는 신체활동대사량이 기초대사량의 2배 이상 되는 경우도 있다" "운동 이외의 활동대사량은 … 1일 총에너지소비량의 20-30%를 차지한다고 알려져 있다"
- 식사성 발열효과: "(지방: 0-5%, 탄수화물: 5-10%, 단백질: 20-30%)" "20대 성인의 식사성 발열효과는 7.4% (남자 6.6%, 여자 8.1%)였고"
- 성별·연령: "동일한 체중이라 할지라도 기초대사량은 일반적으로 남자가 여자보다 높은 것으로 보고되고 있는데, 이는 성호르몬 … 남자가 여자보다 체지방량 (Fat-Mass, FM)이 적은 반면, 제지방량 (Fat-Free Mass, FFM)이 많아 상대적으로 에너지소비량이 높게 나타난다" "기초대사량은 일반적으로 연령이 증가할수록 단위 체중당 그 값이 감소하는 양상을 보인다"
- 제지방량: "특히 제지방량은 휴식대사량과 양의 상관성을 보이며, 독립변수로서 매우 높은 설명력 (R2>60%)을 보여주었다"
- 기초대사량 산출 공식(IoM 2005 인용):
  - "아동 및 청소년 (3-18세) 남자 BEE (kcal/일) = 68 – 43.3×연령 (세) + 712×신장 (m) + 19.2×체중 (kg) / 여자 BEE (kcal/일) = 189 – 17.6×연령 (세) + 625×신장 (m) + 7.9×체중 (kg)"
  - "성인 (19세 이상) 남자 BEE (kcal/일) = 204 – 4.00×연령 (세) + 450.5×신장 (m) + 11.69×체중( kg) / 여자 BEE (kcal/일) = 255 – 2.35×연령 (세) + 361.6×신장 (m) + 9.39×체중(kg)"
  - "[26] Institute of Medicine, IoM; National Academy of Medicine, NAM. 2005." 참고문헌 26: "Institute of Medicine. Dietary Reference Intakes for Energy, Carbohydrate, Fiber, Fat, Fatty Acids, Cholesterol, Protein, and Amino Acids. Washington (DC): The National Academies Press; 2005."
- 해리스-베네딕트: "휴식대사량 추정 공식은 1919년에 개발된 해리스-베네딕트공식 (Harris-Benedict equation) [18]이 대표적이며, 이후에 성별, 연령, 인종 및 비만도를 고려한 다양한 공식이 개발되어 활용되고 있다." 참고문헌 18: "Harris JA, Benedict FG. A Biometric Study of Basal Metabolism in Man. Washington: Carnegie Institution of Washington; 1919. p.279." — 계수는 1권에 없다.
- WHO 방식: "[세계보건기구 총에너지소비량 산출 방식] 총에너지소비량(TEE) = 휴식(기초) 대사량(REE=BEE) × 활동계수 (예: 활동계수가 1.3이라면, 일상생활에서 휴식대사량의 1.3배에 달하는 신체활동을 수행함)" "그러나 위의 공식으로 계산된 휴식대사량은 오차가 발생할 수 있고, 신체활동일기를 이용하여 계산된 신체활동수준 역시 일상의 모든 활동을 정확히 기록하는데 있어서의 한계가 있으며"
- 2025 EER 방식: "이에 2020년과 마찬가지로 2025년에도 한국인을 위한 에너지필요추정량은 미국의 영양소 섭취기준에서 제시한 공식을 그대로 사용하였다."
- 산출식: "에너지필요추정량(EER) = α + β×연령(세) + PA[γ×체중(kg) + δ×신장(m)] * PA(physical activity) = 신체활동수준별계수(비활동적, 저활동적, 활동적, 매우활동적)"
- 표 1 성인(19세 이상): 남자 α 662.00, β -9.53, γ 15.91, δ 539.60 / 여자 α 354.00, β -6.91, γ 9.36, δ 726.00 (아동·청소년 남 88.5/-61.9/26.7/903.0, 여 135.3/-30.8/10.0/934.0)
- 표 2 신체활동단계별계수: "비활동적 (Sedentary) 1.00-1.39 … 성인 남 1.00 여 1.00 / 저활동적 (Low active) 1.40-1.59 … 1.11 1.12 / 활동적 (Active) 1.60-1.89 … 1.25 1.27 / 매우활동적 (Very active) 1.90-2.50 … 1.48 1.45" (가운데 숫자가 PAL)
- "신체활동수준은 1일 평균 신체활동의 강도를 휴식대사량의 배수로 나타낸 값이다."
- 성인 적용: "김 등 [34]은 이중표식수법을 이용하여 한국인 성인의 신체활동수준을 분석한 바 (표 4) 남녀 각각 1.55 ± 0.19 및 1.46 ± 0.16으로 '저활동적'수준 (표 2)에 해당하였다. 따라서 성인의 에너지필요추정량 산출시 신체활동단계별계수는 남녀 각각 '저활동적' 수준에 해당하는 1.11과 1.12를 대입하였다." "제시값은 100 kcal 단위로 절삭하였다."
- 표 12 성인기: "19-29 662-9.53×24(세)+1.11[15.91×69.1(kg)+539.6×1.748(m)]=2,701 kcal/일 2,600 / 30-49 662-9.53×39.5(세)+1.11[15.91×68.0(kg)+539.6×1.734(m)]=2,525 kcal/일 2,500 / 50-64 662-9.53×57(세)+1.11[15.91×64.7(kg)+539.6×1.692(m)]=2,275 kcal/일 2,200 / 여자 19-29 354–6.91×24(세)+1.12[9.36×55.9(kg)+726×1.615(m)]=2,087 kcal/일 2,000 / 30-49 354–6.91×39.5(세)+1.12[9.36×54.8(kg)+726×1.600(m)]=1,957 kcal/일 1,900 / 50-64 354–6.91×57(세)+1.12[9.36×52.5(kg)+726×1.567(m)]=1,785 kcal/일 1,700"
- 19-29세 남자 예외: "19-29세 남성에서 2025년도 산출된 에너지필요추정량은 2,701 kcal로 100 kcal 단위 절삭 원칙을 적용하면 설정값은 2,700 kcal가 되어 … 비만유병율의 증가, 특히, 20대 남자의 비만유병률 40%를 고려하여 2020년도 제시한 에너지필추정량 제시값과 동일하게 유지하기로 하였다."
- 표 13 노년기: "65-74 662-9.53×69.5(세)+1.11[15.91×62.7(kg)+539.6×1.665(m)]=2,104 kcal/일 2,000 / 75이상 662-9.53×75(세)+1.11[15.91×60.4(kg)+539.6×1.635(m)]=1,993 kcal/일 1,900 / 여자 65-74 354–6.91×69.5(세)+1.12[9.36×50.1(kg)+726×1.530(m)]=1,643 kcal/일 1,600 / 75이상 354–6.91×75(세)+1.12[9.36×46.2(kg)+726×1.469(m)]=1,515 kcal/일 1,500"

#### 요약표 (kns-2025-kdri-summary-table.pdf)
- "2025 한국인 영양소 섭취기준 – 에너지와 다량영양소 보건복지부, 2025" 에너지 열은 '필요추정량'만 채워져 있다.
- 남자 19-29 2,600 / 30-49 2,500 / 50-64 2,200 / 65-74 2,000 / 75 이상 1,900; 여자 19-29 2,000 / 30-49 1,900 / 50-64 1,700 / 65-74 1,600 / 75 이상 1,500 (kcal/일)
- 각주: "임신부·수유부 부가량, 단, 에너지: 임신부 1,2,3 분기별 부가량" (글에서는 임신 시 의료진 상담 한 줄만 쓰고 부가량 수치는 다루지 않음)

### Mifflin-St Jeor (1990) — PubMed 초록 (미국 국립의학도서관)
- https://pubmed.ncbi.nlm.nih.gov/2305711/ → evidence/pubmed-2305711.html
- 제목 "A new predictive equation for resting energy expenditure in healthy individuals", M D Mifflin et al., Am J Clin Nutr (1990)
- "A predictive equation for resting energy expenditure (REE) was derived from data from 498 healthy subjects, including females (n = 247) and males (n = 251), aged 19-78 y (45 +/- 14 y, mean +/- SD). Normal-weight (n = 264) and obese (n = 234) individuals were studied and REE was measured by indirect calorimetry."
- "REE = 9.99 x weight + 6.25 x height - 4.92 x age + 166 x sex (males, 1; females, 0) - 161. Simplification of this formula and separation by sex did not affect its predictive value: REE (males) = 10 x weight (kg) + 6.25 x height (cm) - 5 x age (y) + 5; REE (females) = 10 x weight (kg) + 6.25 x height (cm) - 5 x age (y) - 161."
- "The Harris-Benedict Equations derived in 1919 overestimated measured REE by 5% (p less than 0.01)."
- "Fat-free mass (FFM) was the best single predictor of REE (R2 = 0.64): REE = 19.7 x FFM + 413."

### Harris-Benedict — 계수 확인하지 못함
- 원 논문 PNAS 1918 (PMC1091498) 페이지 https://pmc.ncbi.nlm.nih.gov/articles/PMC1091498/ → evidence/pmc-1091498.html: 서지("Proc Natl Acad Sci U S A . 1918 Dec;4(12):370–373")만 HTML이고 본문은 PDF. PDF 링크는 자바스크립트 proof-of-work 페이지("Preparing to download ...")를 돌려줘 curl로 받지 못했다. Europe PMC PDF는 403.
- 1984년 개정식 Roza & Shizgal, "The Harris Benedict equation reevaluated: resting energy requirements and the body cell mass", Am J Clin Nutr — https://pubmed.ncbi.nlm.nih.gov/6741850/ → evidence/pubmed-6741850.html. 초록에 계수가 없다. 초록 인용: "The HBE estimate resting energy expenditure of a normal subject with a precision of 14%." "The HBE accurately predict resting energy expenditure in normally nourished individuals with a precision of +/- 14%, but are unreliable in the malnourished patient."
- 결론: 해리스-베네딕트 원식·개정식 계수는 확인하지 못했다. 계산기에 넣지 않고 글에 그렇게 쓴다.

### Katch-McArdle — 확인하지 못함
- 원출처가 교과서(McArdle·Katch·Katch, Exercise Physiology)이고 공개 기관 페이지에서 공식 계수를 찾지 못했다. 계산기에 넣지 않았다. 체지방률 입력 시에는 Mifflin(1990) 초록에 실린 제지방량 식(REE = 19.7 × FFM + 413)을 쓴다.

### 확인하지 못한 것 (글에 그대로 표시)
- 해리스-베네딕트 1919 원식·1984 개정식 계수
- Katch-McArdle 공식 계수
- 체성분 측정기가 표시하는 기초대사량의 계산 방식 (기기마다 다르고 공개 자료를 받지 못함)
- 흔히 쓰는 활동 계수 1.2·1.375·1.55·1.725·1.9의 공식 출처. 이 글의 활동 수준 선택지는 2025 KDRI 표 2의 PAL 구간(1.00-1.39 / 1.40-1.59 / 1.60-1.89 / 1.90-2.50)에서 대표값을 고른 것(1.2, 1.5, 1.75, 1.9)이라고 글에 밝힌다. 대표값 선택은 글쓴이 판단이다.
- 보건복지부 2025.12.31. 보도자료 원문 (mohw.go.kr에서 찾아 받지 않음. 발표 사실은 한국영양학회 게시글로 확인)

## 계산 검산 (evidence/calc-test.js)
- KDRI 표 12·13의 산출값 10개(2,701 / 2,525 / 2,275 / 2,087 / 1,957 / 1,785 / 2,104 / 1,993 / 1,643 / 1,515)를 계산기 EER 함수로 재현.
- Mifflin 단순식 예: 남 30세 175cm 70kg → 10×70 + 6.25×175 − 5×30 + 5 = 1,648.75 → 1,649 kcal.
- IoM BEE 같은 사람: 204 − 120 + 450.5×1.75 + 11.69×70 = 1,690.7 → 1,691 kcal.
- 제지방량 식: 체지방 20% → FFM 56kg → 19.7×56 + 413 = 1,516.2 → 1,516 kcal.
