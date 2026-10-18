제목: 도커 램 사용량, 맥에서는 얼마나 빠질까 — Docker Desktop 메모리 8GB 맥북 실측
docker stats로 보면 컨테이너 메모리는 작아 보입니다. 그런데 맥에서는 Docker Desktop이 리눅스 VM을 띄우고 그 안에서 컨테이너를 돌리기 때문에, 맥이 실제로 내주는 메모리는 다릅니다. 8GB 인텔 맥북에서 세 번 쟀습니다.

■ 숫자로 보면
- Postgres·Redis·Node 컨테이너 3개: docker stats 합계 약 85MiB → 맥 쪽 Docker 메모리는 320~472MiB 증가
- 1.5GB 쓰는 컨테이너를 지우면 VM 안에서는 60초 안에 풀림(약 0.95GB로 복귀)
- 그런데 맥 쪽은 3분 뒤에도 지우기 전보다 129~991MiB 높음
- 측정용 컨테이너를 모두 지우고 2분 뒤에도 시작보다 266~1,376MiB 높음
- 최대치는 VM 메모리 설정(기본 4GiB) 아래, 측정 중 최고 3,063MiB

■ 8GB 맥이라면
- Docker Desktop 설정 → Resources → Memory limit이 Docker가 가져갈 수 있는 최대치입니다. DB 한두 개만 쓴다면 낮추는 편이 맥 전체에 낫습니다
- 무거운 작업 뒤 맥이 느리면 컨테이너 삭제만으로는 바로 안 풀립니다. Docker Desktop 재시작이 가장 확실합니다
- 메모리는 docker stats만 보지 말고 활동 모니터의 Docker·가상 머신 프로세스도 같이 보세요

측정 조건(Docker Desktop 4.73.0, macOS 14.0), 단계별 표, 재현 스크립트는 원문에 정리했습니다.
원문: https://huntlab.app/docker-desktop-mac-memory-usage-measured/

#도커 #Docker #DockerDesktop #맥북 #램 #메모리 #개발환경

게시: https://blog.naver.com/sungpyo9053/224445768179 (2026-10-18)
