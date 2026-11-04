# 아이폰 배터리 교체 비용 — 조사 메모 (2026-11-04)

키워드: 아이폰배터리교체비용 월 19,140, 아이폰배터리교체 월 23,020 (네이버).
기존 life 글과 겹침: 아이폰 배터리·수리 비용을 다룬 글 없음. `2026-11-06-apple-music-price`(apple-music-price-plans)는 Apple 구독 요금 글이라 관련 글로만 링크.
카테고리: 327(구독·요금). 출처는 Apple 공식 한국어 지원 페이지만 사용. 사설 수리점 가격은 공식 출처가 없어 쓰지 않는다.

수집 방법: curl --max-time 30, 일반 Chrome UA, 2026-11-04.
- 배터리 교체 페이지의 가격표는 JS 위젯("가격 정보를 불러오지 못했습니다 ... JavaScript가 비활성화되어 있습니다")이라 HTML에는 숫자가 없다.
- HTML 인라인 설정(window.data)에 `urlLocale: "ko-kr"`, `pricingProductId:"TAG_1754518739895"`, `configApiURL : "https://support.apple.com/ols/api/config"` 가 보인다. config 응답은 `{"config":{"recommendationLocales":[]}}` 뿐(evidence/ols-api-config.json).
- 페이지가 불러오는 스크립트 evidence/js/app-ac-route.efc77d31.js 안에 가격 위젯이 호출하는 주소가 있다: `/ols/api/pricing/products/services/pricing-estimate?locale=${E}&pricing_type=${t?"OOW":"AC%2B"}&parent_tag_id=${T}`
- 그 주소를 locale=ko-kr, parent_tag_id=TAG_1754518739895 로 두 번 받았다: pricing_type=OOW(보증 제외) → evidence/pricing-estimate-OOW.json, pricing_type=AC%2B(AppleCare+) → evidence/pricing-estimate-ACplus.json. 둘 다 HTTP 200. 배터리 항목만 뽑은 것: evidence/battery-prices-OOW.txt, battery-prices-ACplus.txt.

## 1. iPhone 배터리에 대한 Apple 서비스 및 수리 (evidence/support.apple.com_ko-kr_iphone_repair_battery-replacement.html)
https://support.apple.com/ko-kr/iphone/repair/battery-replacement (publish_date "09222026")

- "고객님의 기기를 점검하여 최종 서비스 요금을 결정합니다. 예상 요금은 Apple의 보증 제외 서비스에 대한 비용이며 VAT가 부과됩니다. 기기 배송이 필요한 경우 배송비가 추가됩니다. Apple 공인 서비스 제공업체는 자체적으로 서비스 요금을 책정할 수 있으며 예상 비용을 안내해 드립니다."
- "*정확한 개별 견적을 안내해 드릴 수 있도록 제품을 점검해야 할 수 있습니다."
- "요금에는 세금이 부과될 수 있습니다. AppleCare 플랜이 적용되는 서비스의 경우 본인 부담금은 Apple 및 모든 Apple 공인 서비스 제공업체에서 동일합니다."
- AppleCare 섹션: "배터리 서비스" / "용량이 80% 미만으로 떨어질 경우 추가 비용 없이 배터리를 교체해 드립니다."
- 보증: "Apple 제한 보증은 구매일로부터 2년 동안 iPhone의 제조 결함을 보장합니다. 하지만, 보증은 iPhone과 함께 제공되는 상자에 포함된 배터리 및 Apple 브랜드 액세서리의 제조 결함에 대해 1년 동안 유효합니다."
- "우발적인 손상 또는 정상적으로 사용하여 수명이 다한 배터리에는 Apple 보증이 적용되지 않습니다. 해당 상황이 보증 대상에 해당하지 않고 소비자 보호법이 적용되지 않는 경우, Apple을 통한 수리에는 비용이 발생합니다."
- 수리 보증: "Apple은 Apple 수리 이용 약관에 명시된 대로 서비스 및 교체용 부품에 대해 90일과 Apple 보증의 남은 기간 중 더 긴 기간의 보증을 적용합니다."
- "Apple에서 수리 또는 교체 서비스의 일부로 제공하는 장비에는 테스트를 거쳐 Apple 기능 요구 사항을 통과한 새 Apple 정품 부품 또는 이전에 사용된 Apple 정품 부품이 포함될 수 있습니다. 서비스 옵션은 부품 재고 및 위치에 따라 다를 수 있습니다."
- 수리 내역: "Apple 계정으로 나의 지원 또는 Apple 지원 앱에 로그인하여 현재 또는 최근 수리에 대한 정보를 확인하실 수 있습니다."
- 대면: "Genius Bar 또는 Apple 공인 서비스 제공업체에서 개인적인 지원을 받으실 수 있습니다."

같은 문구가 https://support.apple.com/ko-kr/iphone/repair 에도 있다(evidence/support.apple.com_ko-kr_iphone_repair.html). 이 페이지도 가격은 같은 JS 위젯.

## 2. 가격 위젯 JSON (evidence/pricing-estimate-OOW.json, pricing-estimate-ACplus.json)
serviceLabel "배터리 서비스" 의 price 값 그대로.

보증 제외(OOW):
- iPhone Duo: ₩349,000
- iPhone 18 Pro Max, iPhone 18 Pro: ₩199,000
- iPhone Air: ₩179,000
- iPhone 17 Pro Max, iPhone 17 Pro: ₩179,000
- iPhone 17, iPhone 17e: ₩146,000
- iPhone 16 Pro Max, iPhone 16 Pro: ₩179,000
- iPhone 16 Plus, iPhone 16, iPhone 16e: ₩146,000
- iPhone 15 Pro Max, 15 Pro, 15 Plus, 15: ₩146,000
- iPhone 14 Pro Max, 14 Pro, 14 Plus, 14: ₩146,000
- iPhone 13 Pro Max, 13 Pro, 13, 13 mini: ₩129,000
- iPhone 12 Pro Max, 12 Pro, 12, 12 mini: ₩129,000
- iPhone 11: ₩129,000
- iPhone XR: ₩129,000 (자식 모델 없이 products 최상위에 services가 바로 있는 항목)
- iPhone SE(3세대), iPhone SE(2세대): ₩100,000
AppleCare+(AC+): 위 33개 모델 전부 "배터리 서비스" "₩0".
목록에 iPhone 11 Pro, 11 Pro Max, XS, XS Max, X 이하 모델은 없다 → 이 모델들의 공식 예상 비용은 확인하지 못했다.
VAT 포함 여부: 표시 금액이 VAT 포함인지 별도인지는 페이지 문구("VAT가 부과됩니다", "세금이 부과될 수 있습니다")만으로 확인하지 못했다.

## 3. iPhone 배터리 및 성능 (evidence/support.apple.com_ko-kr_101575.html)
https://support.apple.com/ko-kr/101575
- "iPhone 6 및 이후 모델에는 iOS에 배터리 성능 상태를 알려 주고 배터리 교체가 필요하면 교체를 추천해 주는 새 기능이 추가되었습니다."
- "'배터리 성능 상태'를 탭합니다." / "배터리 성능 상태 화면에는 최대 배터리 용량과 최고 성능 기능에 관한 정보가 표시됩니다."
- "iPhone 14 및 이전 모델의 배터리는 이상적인 조건에서 전체 충전 사이클을 500번 반복했을 때 원래 용량의 80%를 유지하도록 설계되었습니다."
- "iPhone 15 모델의 배터리는 이상적인 조건에서 전체 충전 사이클을 1,000번 반복했을 때 원래 용량의 80%를 유지하도록 설계되었습니다."
- "1년 보증(튀르키예의 2년 보증)에는 현지 소비자 보호법에 따라 제공되는 권리 외에도 결함 있는 배터리에 대한 서비스 보증이 포함됩니다. Apple에서는 보증 제외에 해당하는 경우 유상 배터리 서비스를 제공합니다."
- 저하 메시지: "배터리 성능이 매우 저하되었습니다. Apple 공인 서비스 센터에서 배터리를 교체 받아 최고 성능 및 기능 상태로 복원할 수 있습니다. 서비스 옵션에 관하여 더 알아보기…"
- "이 메시지가 표시되어도 안전 문제가 있는 것은 아니며 여전히 배터리를 사용할 수 있습니다. 그러나 배터리 및 성능 문제가 더 확연히 나타날 수 있습니다."
- 정품 확인 불가: "iPhone 배터리의 정품 여부를 확인할 수 없는 경우 다음과 같은 메시지가 표시됩니다. 이 메시지는 iPhone XS, iPhone XS Max, iPhone XR 및 이후 모델에 적용됩니다." / "이 iPhone이 Apple 정품 배터리를 사용하는지 확인할 수 없습니다. 이 배터리의 세부사항이 정확하지 않을 수 있습니다. 더 알아보기..."
- 성능 관리: "배터리가 필수 최고 전력을 제공하지 못하여 이 iPhone의 시스템이 예기치 않게 종료되었습니다. 동일 문제의 재발을 막기 위해 성능 관리가 실행되었습니다."
- "iPhone X 및 이전 모델에서는 '확인되지 않음' 대신 \"중요한 배터리 관련 메시지. 이 iPhone의 배터리 성능 상태를 확인할 수 없습니다.\"라는 메시지가 표시될 수 있습니다."

## 4. 정품 iPhone 배터리에 관하여 (evidence/support.apple.com_ko-kr_103269.html, 게시일 2026년 10월 23일)
https://support.apple.com/ko-kr/103269
- "서비스 제공업체에서 정품이 아닌 배터리 부품을 사용할 경우 교체용 배터리는 다음과 같은 상태일 수 있습니다." 잘못 설계되었거나 올바르지 않게 제조된 배터리 / 이전에 사용한 배터리 / 손상된 배터리 / iPhone 모델에 맞지 않는 잘못된 배터리
- "정품이 아닌 배터리를 사용하면 배터리 설치 이후, 기기 소프트웨어 업데이트 이후 또는 충전 중에 정상적이지 않은 동작이 발생할 수도 있습니다. 정품이 아닌 배터리를 사용하면 안전 문제도 발생할 수 있습니다."
- 부품 기록: "iPhone XR, iPhone XS 및 이후 모델에서는 다음과 같이 iPhone의 부품 및 서비스 기록을 확인하고 배터리가 교체되었는지도 확인할 수 있습니다." 설정 > '일반' > '정보'. "Apple 정품 부품 및 절차를 사용하여 수리된 경우 배터리 옆에 '정품'이라고 표시됩니다."
- "알 수 없는 부품은 기기의 보상 판매 금액에 영향을 미칠 수 있습니다."
- "독립 수리 제공업체에서 수행하는 수리에는 Apple 보증 또는 AppleCare 플랜이 적용되지 않지만 제공업체의 자체 수리 보증이 적용될 수 있습니다."
- "셀프 서비스 수리는 현재 일부 국가 또는 지역에서 2021년 이후에 출시된 특정 iPhone 모델에 사용할 수 있습니다."
- "다음과 같이 배터리의 처음 사용일, 성능 최대치 및 사이클 수를 확인할 수 있습니다." 설정 > '배터리' > '배터리 성능 상태'.

## 5. 셀프 서비스 수리
- https://support.apple.com/ko-kr/self-service-repair → HTTP 200이지만 본문 "찾으시는 페이지를 찾을 수 없습니다." (evidence/support.apple.com_ko-kr_self-service-repair.html)
- https://support.apple.com/self-service-repair (evidence/support.apple.com_self-service-repair.html) 국가 선택 목록: België … United Kingdom, United States. 대한민국은 목록에 없다.
- 결론: 한국에서 셀프 서비스 수리를 이용할 수 있는지는 Apple 한국어 공식 페이지에서 확인하지 못했다.

## 6. 보증이 만료된 Apple 제품에 대한 서비스 받기 (evidence/support.apple.com_ko-kr_102772.html)
https://support.apple.com/ko-kr/102772
- "Apple이 마지막으로 제품을 판매용으로 공급한 날로부터 최소 5년 동안 Apple 서비스 제공업체로부터 서비스 및 부품을 받을 수 있습니다."
- "서비스와 부품을 받을 수 있는 기간은 법으로 정해진 규정에 따라 연장되거나 최대 7년까지 연장될 수 있으며, 이는 부품 재고 여부에 따라 달라질 수 있습니다."
- "Apple이 판매를 위한 공급을 중단한 지 5년은 넘었지만 아직 7년은 되지 않은 제품은 구형 제품으로 간주됩니다."
- "Apple이 판매를 위한 공급을 중단한 지 7년이 지난 제품은 단종 제품으로 간주됩니다." / "Apple은 단종 제품에 대한 모든 하드웨어 서비스를 중단하며, 서비스 제공업체는 단종 제품의 부품을 주문할 수 없습니다."

## 확인하지 못한 것
- 표시 가격의 VAT 포함 여부, 배송 수리 배송비 금액.
- AppleCare+ 가입비(이 글 범위 밖, 출처 미수집).
- iPhone 11 Pro·11 Pro Max·XS·XS Max·X 이하 모델의 공식 배터리 교체 예상 비용.
- 한국 셀프 서비스 수리 제공 여부.
