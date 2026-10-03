# 경쟁 글 대비 차별점: colcon-build-executor-sequential-memory-budget

검색어 "colcon build number of threads", "colcon build parallel-workers MAKEFLAGS raspberry pi", "colcon build 라즈베리파이 멈춤 --executor sequential", "colcon build 메모리 부족 parallel-workers MAKEFLAGS" 등으로 찾은 상위 문서를 직접 열어 읽었다(2026-10-04). 한국어 검색에서는 이 질문을 직접 다룬 한국어 해설 글을 찾지 못했다. 결과에 뜬 ROBOTIS 한국 사용자 포럼 글은 DNS 실패로 열지 못해 비교에서 제외했다(읽지 않은 글을 비교하지 않음).

1. **Robotics Stack Exchange 97896 "colcon build - number of threads"** — https://robotics.stackexchange.com/questions/97896/colcon-build-number-of-threads (StackExchange API로 질문·답변 원문 확인. 페이지 자체는 runner에서 403)
   - 다루는 것: colcon 저자(Dirk Thomas)의 채택 답변이 두 겹 병렬성(`--parallel-workers`/`--executor sequential` vs `MAKEFLAGS`)과 "전체 스레드 수는 둘의 곱"을 설명. 다른 답변은 `--parallel-workers`가 `-j N`의 대체라고 안내. 댓글: Pi 4에서 sequential로 해결했고 "큰 시간 손해는 없었다"(일화). 2024년 답변: `MAKEFLAGS="-j 1"`로 `cc1plus Killed signal` 해결.
   - 빠진 것: 기본값의 근거 코드, `-l` 부하 제한, 메모리 예산 계산, 시간 대가의 상·하한, 의존성 그래프의 영향, 측정 방법.
   - 이 글이 더할 것: 곱셈식을 커밋 고정 소스로 확인하고 4코어 보드 기준 16→4→1 계산, 검산된 메모리·시간 예제와 일렬 의존 반례, "큰 시간 손해 없음"이 가능한 이유(일렬 의존·패키지 내부 병렬이 이미 CPU를 채움)를 가정과 함께 설명, `/usr/bin/time` 함정과 `vmstat` 확인 절차.
2. **MoveIt 2 "Getting Started"** — https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html
   - 다루는 것: 일부 패키지가 빌드에 최대 16 GB RAM을 요구할 수 있다는 경고, 기본적으로 colcon이 가능한 많은 패키지를 동시에 빌드한다는 설명, `--executor sequential`·`--parallel-workers <X>`, 더 제한된 장비용 `MAKEFLAGS="-j4 -l1" colcon build --executor sequential`.
   - 빠진 것: `<X>`를 정하는 방법, `-j4 -l1`의 의미(make 매뉴얼상 load 1 이상이면 이미 하나가 돌 때 새 작업을 미룸), 메모리 원인 진단, 시간 대가.
   - 이 글이 더할 것: X를 "RAM ÷ 패키지당 최대 메모리"의 정수 부분으로 고르는 계산(예제 3.2 → 3)과 그 계산이 안쪽 `-j`를 포함해야 한다는 조건, 측정 절차.
3. **Robotics Stack Exchange 105813 "Compiler issues using Raspberry Pi 4B"** — https://robotics.stackexchange.com/questions/105813/compiler-issues-using-raspberry-pi-4b (API로 원문 확인, 페이지는 runner에서 403 가능성 높음 — 같은 사이트)
   - 다루는 것: Pi 4B 2GB + Humble에서 sequential·`--parallel-workers 1`·`CMAKE_BUILD_PARALLEL_LEVEL=1`을 줘도 컴파일러 4개가 동시에 돈 사례, 질문자가 colcon-cmake 소스를 보고 `export MAKEFLAGS="-j 1"`로 해결, 다른 답변은 zswap + 1 GB 스왑 파일로 해결.
   - 빠진 것: 왜 4개인지(=CPU 수 기본값)와 바깥/안쪽 병렬성의 관계를 일반화한 설명, 시간 대가, 스왑의 대가.
   - 이 글이 더할 것: "sequential인데 왜 4개?"를 첫 질문으로 놓고 소스 기본값으로 답, `CMAKE_BUILD_PARALLEL_LEVEL`이 무시되는 이유를 코드 경로로 설명, 스왑 사용을 `vmstat` si/so로 관측하는 판정 기준.
4. **colcon-core issue #657 "`colcon build` executor not affecting `make -j` command"** — https://github.com/colcon/colcon-core/issues/657 (2024-07-25 개설, 확인 시점 메인테이너 답변 없음)
   - 다루는 것: `--parallel-workers 2`나 sequential이 make 작업 수를 줄이지 않는다는 사용자 관찰과 `MAKEFLAGS="-j2"` 우회.
   - 빠진 것: 공식 답변·설명 없음, 메모리·시간 판단 없음.
   - 이 글이 더할 것: 관찰을 소스 코드 동작으로 설명하고 판단 절차로 연결. (GitHub issue는 내용이 계속 바뀌고 확인 도구가 별도 캐시를 쓰므로 본문 인용 출처로는 권하지 않는다.)
5. **colcon-mem README** — https://github.com/benaliabderrahmane/colcon-mem
   - 다루는 것: "`--parallel-workers`는 동시에 처리하는 패키지 수를 제한할 뿐 메모리 사용량을 제한하지 않는다"는 지적, 가용 메모리 기준으로 패키지 시작을 미루는 확장.
   - 빠진 것: 확인 시점 별 1개·커밋 4개·릴리스 없음의 초기 단계라 입문자 권장 근거가 약함. 계산식 문서화 없음.
   - 이 글이 더할 것: 추가 확장 없이 기본 옵션과 산술로 같은 판단을 하는 법. 이 확장은 본문에서 권장하지 않는다.
6. 참고로 읽었으나 깊이가 얕았던 글: TU Delft RO47003 실습 매뉴얼(https://manual.ro47003.me.tudelft.nl/8_workspace/create_ws.html — sequential을 한 줄로 소개, 이유·숫자 없음), HansRobo colcon cheatsheet(https://hansrobo.github.io/mycheatsheets/colcon — 일본어, `--parallel-workers` 한 줄, sequential·MAKEFLAGS·메모리 없음).

판정: 상위 문서들은 "어떤 옵션을 쓰라"는 처방은 충분하지만, "얼마나 줄여야 하고 그 대가가 얼마인지"를 계산하는 기준, 기본값의 코드 근거, 측정 도구가 실제로 재는 값은 없다. 이 글은 colcon 실측 수치를 더하지는 않는다. 더하는 것은 **검산된 산술 예제 + 커밋 고정 소스로 확인한 기본값 + 측정 도구 의미 교정 + 독자가 직접 할 측정 절차**다. `foundation_concept` 계약(1차 자료·자체 예제·검산 기록)에 맞는 고유 가치가 있으므로 INSUFFICIENT가 아니다.
