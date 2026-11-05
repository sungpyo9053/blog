# 온라인 타이머·스톱워치 — 조사 메모 (2026-11-05)

키워드(네이버 월간): 타이머 130,000 · 초시계 89,200 · 스톱워치 48,700.
유형: 도구형(계산기형 허용). 정부 기관이 정하는 기준이 없는 도구라, 브라우저 동작은 공식 기술 문서(MDN, Chrome for Developers)로 확인하고 계산은 공식 자체를 node로 검산.
기존 life 글과 겹침: grep '타이머|스톱워치|뽀모도로' → 2026-11-17-forklift-license(무관)만. 겹치는 글 없음. '몇 분 뒤 시각' 계산은 time-calculator-2026(도착 시각 계산기)이 이미 있어 링크로 대신하고, 이 글은 뽀모도로 일정 계산기를 넣음.
카테고리 330. 같은 날 형제 글(random-draw-picker, son-eomneun-nal-calculator)은 링크하지 않음.
내부 링크(wpdates.csv, 모두 2026-12-06 18:00 이전): time-calculator-2026(12/03 12:00), date-day-count-calculator(10/31), suneung-2027-dday-timetable(11/01), ladder-game-online-2026(12/06 12:00), roulette-wheel-spinner-2026(12/06 15:00).

## 출처와 원문 (curl 11/05, 일반 브라우저 UA, evidence/ 저장 — 각 파일 1행에 URL)

### MDN Window: setTimeout() — evidence/mdn-settimeout.txt
https://developer.mozilla.org/en-US/docs/Web/API/Window/setTimeout
- "Timeouts in inactive tabs To reduce the load (and associated battery usage) from background tabs, browsers will enforce a minimum timeout delay in inactive tabs. It may also be waived if a page is playing sound using a Web Audio API AudioContext ."
- "Firefox Desktop has a minimum timeout of 1 second for inactive tabs."
- "Firefox for Android has a minimum timeout of 15 minutes for inactive tabs and may unload them entirely."
- "Minimal throttling : Applies to timers when the page is visible, has made sound recently, or is otherwise considered active by Chrome. Timers run close to the requested interval."
- "Throttling : Applies to timers when minimal throttle conditions are not met and any of these conditions are true: Nesting count (i.e., number of chained timer calls) is lower than 5. Page has been invisible for less than 5 minutes. WebRTC is active. Timers in this state are checked once per second"
- "Intensive throttling : Introduced in Chrome 88 (January 2021). ... Nesting count is 5 or higher. Page has been invisible for more than 5 minutes. Page has been silent for more than 30 seconds. WebRTC is inactive. Timers in this state are checked once per minute"

### MDN Window: setInterval() — evidence/mdn-setinterval.txt
- "Note also that the actual amount of time that elapses between calls to the callback may be longer than the given delay ; see Reasons for delays longer than specified for examples."

### Chrome for Developers, Heavy throttling of chained JS timers beginning in Chrome 88 — evidence/chrome-timer-throttling-88.txt
https://developer.chrome.com/blog/timer-throttling-in-chrome-88
- "With setInterval , each iteration is part of the chain ."
- Throttling: "The chain count is less than 5. The page has been hidden for less than 5 minutes. ... The browser will check timers in this group once per second ."
- Intensive: "The page has been hidden for more than 5 minutes. The chain count is 5 or greater. The page has been silent for at least 30 seconds. WebRTC is not in use. In this case, the browser will check timers in this group once per minute ."
- "This change will be enabled for all Chrome users in Chrome 88 (January 2021)."
→ 본문 설계: 알람은 시작 시 setTimeout 1회(연쇄 0) 예약 → 1분 단위 제한 대상이 아님. 표시 갱신 setInterval은 연쇄로 집계되어 제한될 수 있으나 경과 시간을 시각 차이로 계산하므로 표시 오차는 없음.

### MDN Performance: now() — evidence/mdn-perfnow.txt
https://developer.mozilla.org/en-US/docs/Web/API/Performance/now
- "Also, Date.now() may have been impacted by system and user clock adjustments, clock skew, etc. as it is relative to the Unix epoch (1970-01-01T00:00:00Z) and dependent on the system clock. The performance.now() method on the other hand is relative to the timeOrigin property which is a monotonic clock : its current time never decreases and isn't subject to adjustments."
- "Ticking during sleep The specification (Level 2) requires that performance.now() should tick when the operating system sleeps or the browser process freezes in any other way. It appears that only browsers on Windows keep ticking during sleep."
- "Resolution in isolated contexts: 5 microseconds" / "Resolution in non-isolated contexts: 100 microseconds"
→ 본문: 평소 performance.now(), 두 시계 경과 차이가 2초 넘으면(잠자기로 perf가 멈춘 경우) Date.now() 쪽 사용. FAQ의 '0.1밀리초' = 100 microseconds.

### MDN Page Visibility API — evidence/mdn-visibility.txt
- "Most browsers stop sending requestAnimationFrame() callbacks to background tabs or hidden <iframe> s in order to improve performance and battery life."
- "Timers such as setTimeout() are throttled in background/inactive tabs to help improve performance."
- "Tabs which are playing audio are considered foreground and aren't throttled."
(스톱워치 표시는 requestAnimationFrame이라 숨긴 탭에서 멈추지만 경과 시간은 시각 차이로 계산되어 돌아오면 정확.)

### MDN Autoplay guide — evidence/mdn-autoplay.txt
https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay
- "In the Web Audio API , a website or app can start playing audio using the start() method on a source node linked to the AudioContext . Doing so outside the context of handling a user input event is subject to autoplay rules."
- "playback of any media that includes audio is generally blocked if the playback is programmatically initiated in a tab which has not yet had any user interaction."
→ 시작/프리셋 클릭 시 AudioContext 생성·resume.

### The Pomodoro Technique 공식 사이트 — evidence/pomodorotechnique-what-is.txt
https://www.pomodorotechnique.com/what-is-the-pomodoro-technique/
- "The timer is part of the practice, but the Technique is much more than a sequence of 25-minute sessions ."
- "Francesco began developing the Pomodoro® Technique in the 80's , while preparing for a university examination."
- 휴식 길이(5분/15분/4회마다)는 이 페이지에 없음 → 본문에 "확인하지 못했다", 기본값으로만 사용. (francescocirillo.com 기법 페이지 2곳 404.)

## 직접 계산한 값 (evidence/calc-test.js, calc-test-output.txt)

- 틱 카운트 시뮬레이션: 25분 타이머, 60초 뒤 숨김. 숨긴 뒤 5분 동안 1초 간격, 이후 60초 간격(크롬 집중 제한). 호출 60+300+19 = 379회 → 6분 19초, 화면 남은 시간 18:41. 시각 차이 방식은 실제 경과와 오차 0.
- 뽀모도로(09:00 시작, 25/5/15, 4회마다 긴 휴식, 마지막 집중 뒤 휴식 제외): 1회 09:25, 2회 09:55, 3회 10:25, 4회 10:55, 5회 11:35, 6회 12:05, 8회 13:05.
- 50분 집중·10분 휴식: n회 종료 = 09:00 + 50n + 10(n-1) → 09:50, 10:50, 11:50, 12:50, 13:50, 14:50, 16:50(8회).
- 자정 넘김: 23:30 시작 4회 → 01:25 (+1일).

## 확인하지 못한 것
- 크롬 외 브라우저(사파리 등)에서 숨긴 탭의 단발 setTimeout 지연 크기.
- 뽀모도로 공식 휴식 길이.
