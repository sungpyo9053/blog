# 쿠팡 첫 글: colcon 빌드 RAM 실측 — 작업 순서 (2026-10-10 시작)

사용자 결정(10/10): 수익 주제 병행 = 개발 장비·IT 기기, huntlab.app 별도 카테고리, 쿠팡 파트너스(ID AF8567082).
원칙: 안 써 본 제품 리뷰 금지. 실측 수치로 구매 기준을 제시하고, 기준에 맞는 상품에만 링크.

## 상태

- [x] 쿠팡 파트너스 가입 (최종 승인 전 → API 키 발급 불가, 링크는 사용자가 대시보드에서 수동 생성)
- [x] 임시 측정 서버 `huntlab-measure-ram-tmp` 생성 (Lightsail xlarge_3_0, 4 vCPU / 16 GB, 43.201.112.34, 시간당 약 $0.12)
- [x] 측정 시작 18:23 KST — `experiments/colcon-ram-nav2-real-build/measure.sh` (서버 `~/m/`)
- [x] 1. 측정 완료 확인 (10/11 03:47) (`~/m/DONE`) — 예상 23:00~01:00
- [x] 2. 결과 회수 (커밋 06d4698): `~/m/results.tsv`, `env.txt`, `log-*.txt` → 이 리포 `experiments/colcon-ram-nav2-real-build/`
- [x] 3. **임시 서버 삭제** (10/11 03:5x 삭제 확인) (`aws lightsail delete-instance --instance-name huntlab-measure-ram-tmp`) — 회수 직후 반드시
- [x] 4. 사용자에게 결과 보고 (카톡)
- [x] 5. 글 초안 (WP 임시글 #935, 카테고리 '개발 장비' #326, 원본 editorial/coupang/2026-10-11-colcon-ram-nav2/ko.html) (KO 쿠팡 / EN 링크 없음): "ROS 2 colcon 빌드, RAM 몇 GB면 되나 — Nav2 실측"
      - 2020 인텔 맥북 프로 13 (8GB, 4코어) 실사용 맥락을 사례로 포함 (사용자 실제 기기)
      - 쿠팡 고지 문구 필수: "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
- [x] 6. 상품 요청 카톡 발송 (쿠팡 검색이 Akamai 403 → 사용자가 파트너스 안에서 검색: 삼성 DDR5 16GB / DDR4 16GB / 씽크패드 16GB)
- [ ] 6-b. 결과 기준에 맞는 상품 2~3개 골라 쿠팡 상품 주소를 사용자에게 전달 (RAM 키트 / 16·32GB 노트북 등)
- [ ] 7. 사용자가 파트너스 "간편 링크 만들기"로 만든 link.coupang.com/a/… 링크 회수
- [ ] 8. 링크 삽입 후 공개 (KO+EN), 별도 카테고리
- [ ] 9. 후속 시리즈: MoveIt 2 RAM / SSD 용량 / 라즈베리파이 5 4GB vs 8GB (같은 측정 파이프라인 재사용)

## 메모

- 사용자가 만든 첫 링크 https://link.coupang.com/a/hJuiMQHbYk 는 골드박스(특가) 페이지 — 본문용 아님, 보관.
- 측정 서버가 Lightsail 버스트형이라 빌드 시간은 참고만, 결론은 최대 RAM·OOM 여부로.

## 측정 결과 (10/11)

기본(4워커×-j4): 16g 성공 8.1GiB · 8g 성공 7.8GiB · 4g OOM 실패 / 순차(-j1): 16g·4g 모두 성공 2.7GiB. CPU 크레딧 소진으로 시간 비교 무의미.
