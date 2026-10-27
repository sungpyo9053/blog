# 수익 사이트 벤치마크 (2026-10-26 밤)

목적: 수익 내는 WordPress 사이트 공통점 = 정답, 우리와 차이 = loss → 큰 것부터 고친다. 매주 재측정.
측정 스크립트: scratchpad bench/m.py (같은 지표로 상위 사이트·우리 동시 측정).

## EN (5곳 10글: roboticsbackend, automaticaddison, theconstruct, linuxhint, phoenixnap)
| 항목 | 상위 중앙값 | 우리 | loss |
|---|---|---|---|
| 본문 단어 | 1,000~2,300 | 2,300~3,200 | 0 |
| h2/h3, 코드블록 | 3~5 / 7~17 | 9 / 4~5 | 0 |
| 본문 내부 링크(고유) | 8 | 8 | 0 |
| 구조화 데이터·목차·관련글 | 있음 | 있음 | 0 |
| 이미지 | 2~22 | 0 | 큼 |
| 글 수 | 137~1,521 | 100 | 중간(roboticsbackend 137로 충분) |
| 사이트 나이·백링크 | 5~10년 | 3개월 | 가장 큼 |
| 수익원 | ROS 3곳 광고 0(강의·컨설팅·뉴스레터), 일반 dev 2곳 Ezoic+대량 | AdSense 자동광고 | 모델 차이 |

결론: 글 구조는 정답과 같음. loss는 이미지·신뢰(나이·백링크)·수익 모델.
- ROS 니치 광고 $200 구조적으로 어려움 → 광고는 검색량 큰 dev 일반(Docker·Ubuntu·Python 설치/에러) 확장, ROS는 유료 자료(2번, 사용자 보류).
- 최신 배포판(Lyrical) 문제 해결 글 경쟁 적음(automaticaddison만 진입).

## 적용 순서
1. EN ROS 노출 상위 글에 실측 그림(터미널 출력·비교 차트) 추가. — (20:50) #874 colcon 글에 빌드시간·메모리 차트(results.json 5회 중앙값) 삽입, 백업 /var/backups/post874.20261026.html. 주의: wp media import URL이 127.0.0.1로 나와 https://huntlab.app 로 교체 필요.
2. 새 EN 글: Lyrical 문제 해결 + dev 일반 고검색량 주제.
3. 커뮤니티 실측 답변으로 백링크·유입(3번).

## KO (7곳: blanclucy, aboda, yellowit, foxcg, benefitshub, patross0303, thecheck — 원표 scratchpad bench/ko.md)
| 항목 | 상위 공통(중앙값) | 우리 | loss |
|---|---|---|---|
| 관련 글 블록·BlogPosting JSON-LD·날짜/바이라인·FAQ 섹션·목차 | 7/7·7/7·7/7·7/7·6/7 | 있음 | 0 |
| 본문 3,057자·h2 7·표 1 | | 비슷 | 0 |
| AdSense 수동 슬롯 | 5/6, 페이지당 3(본문 1+) | 0(자동만) | **큼, 수익 직결** — 슬롯 ID 사용자 필요 |
| 캐시 플러그인 | 6/7, 홈 TTFB 0.23s | 없음 0.7s | (10/26 21시 Cache Enabler 적용) |
| 이미지 | 4 | 0~3 | 중간 |
| 글 수 | ~2,000 | KO ~70 | 큼 — 검색량 큰 주제로 늘림 |
| 제목 패턴 | '총정리/비교/가이드' 7/7, 연도 5/14 | '비교' 일부 | 작음 |
| FAQPage 스키마 | 2/7 | 없음 | 차별화 여지 |

## 같이 찾아 고친 것
- 빈 태그 225·빈 카테고리 22 삭제(NOINDEX 210의 대부분).
- 비활성 UI 백업 플러그인 13개가 웹에서 200으로 열림 → /var/backups/plugin-backups-20261026 으로 이동, 404 확인.
- 감사(116 URL): 깨진 내부 링크 0, canonical·noindex 정상, ads.txt 정상, 수동 광고 단위 0(자동광고만).
- (21:00) Cache Enabler 적용: WP_CACHE 추가(백업 /var/backups/wp-config.20261026.php), 12시간 만료·글 저장 시 전체 비움. 브라우저 요청(Accept: text/html)에서 캐시 HTML 확인. 롤백: 플러그인 비활성 + wp-config 1행 삭제.
- (20:50) EN #1060 'Lyrical Unknown CMake command ament_target_dependencies' 10/29 10시 예약 — Docker humble/jazzy/kilted/lyrical 실측, 결과 매트릭스 이미지 포함(이미지 loss 대응). SE 118519 조회 417(Lyrical 질문 1위).
- (10/27 08:45) 외부 도메인 복제 차단: api.cokoedu.com·서버 IP가 우리 글 전체를 200+자기 canonical로 내보내던 것 → .htaccess Host 301(상위 사이트는 vhost ServerName으로 기본 차단, 우리만 HTTP_HOST 그대로 쓰던 구조).
- (10/27 08:55) 제목 패턴 loss: 멜론 #514 '총정리(2026)'+가격 답 첫 문단, EN #890 'ros2: command not found on Jazzy?'+Short answer.
- (10/27 09:04) 차별화: 생활글 #1063 근로장려금에 공식 산정표 447구간 계산기(상위 KO 사이트들의 계산기형 유입 대응).
- (10/27 09:12) 이미지 loss: EN #890(노출 2위)에 실측 막대그래프. EN 이미지 있는 글 2→3편(#874·#890·#1060).
