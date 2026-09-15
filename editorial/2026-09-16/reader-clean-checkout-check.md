# 새 독자 환경에서 실행 확인

2026-09-16, 기존 작업 폴더와 별개인 임시 디렉터리에 공개 저장소를 새로 clone했다.
대상 코드는 `8c35049f77ba4ec8c5fbcc6fcff75871782f44c7`, Python은 3.12.9다.
저장소 안에 새 가상환경을 만들고 `requirements-publisher.txt`를 설치했다.
기존 작업 폴더의 설치 패키지를 재사용하지 않았다. 실제 WordPress 발행은 하지 않았다.

## 확인한 결과

- 373 수정 HTML에서 복사 실행 heredoc을 그대로 추출하여 새 checkout에서 실행: 종료 0.
  두 번 누락은 실패 상태, 재시도 때 생성은 성공, 호출 상한은 두 번이라는 단언 통과.
- 같은 환경에서 Retry-After·진단기·Publisher 성공/실패 테스트 10개: 종료 0.
- 패키지를 설치하지 않은 별도의 새 가상환경에서도 REST/noindex Evidence Lab 두 경로가
  각각 READY, 쓰기 0, 종료 0이었다. 698·699 실험에 전체 Publisher 패키지는 필요 없다.
- 반면 패키지가 없는 환경의 `tests.test_wordpress_retry`는 Publisher 패키지의 초기화에서
  `ModuleNotFoundError: No module named 'markdown'`으로 실패했다. 이 경로의 설치 안내는
  진단 실험과 구분해야 한다.

새 환경의 전체 패키지 설치는 실제로 소스 빌드 단계를 거쳤다. 독자에게 간단한 진단을
시키기 위해 Analytics·Playwright를 포함한 전체 발행 환경 설치를 강제하지 않는 편이
좋다. 설치 속도를 일반화하거나 이 환경에서의 성공을 모든 OS 지원 증거로 삼지 않는다.
