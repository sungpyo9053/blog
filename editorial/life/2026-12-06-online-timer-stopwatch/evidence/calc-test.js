// ko.html의 타이머 <script>를 그대로 뽑아 node에서 실행하는 검산 (가짜 시계로 백그라운드 제한 재현)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
  if (/[&<]/.test(m[1])) throw new Error('& or < in JSON-LD'); JSON.parse(m[1]);
}
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const H = window.htimer;

// 1) 포맷
assert.strictEqual(H.fmt(300000), '05:00');
assert.strictEqual(H.fmt(299001), '05:00');   // 남은 시간은 올림: 0.999초 지나도 05:00
assert.strictEqual(H.fmt(299000), '04:59');
assert.strictEqual(H.fmt(3723000), '1:02:03');
assert.strictEqual(H.fmt(-5), '00:00');
assert.strictEqual(H.fmt(65432, true), '01:05.43');
console.log('PASS fmt');

// 2) 백그라운드 제한 시뮬레이션: 25분 타이머, 1분 뒤 탭 숨김
//    MDN/Chrome 88: 숨긴 지 5분 미만은 1초에 한 번, 5분 넘고 연쇄 5회 이상이면 1분에 한 번 확인
const DUR = 25 * 60000, HIDE = 60000;
let t = 0; const fires = [];
while (true) {
  const hiddenFor = t - HIDE;
  t += (hiddenFor >= 5 * 60000) ? 60000 : 1000;
  if (t > DUR) break;
  fires.push(t);
}
const naiveSec = fires.length;                       // 호출 수를 세는 타이머
const c = H.go(H.clock(), 0, 1700000000000);         // performance.now()=0, Date.now() 임의
const last = fires[fires.length - 1];
const corrected = H.used(c, last, 1700000000000 + last);
console.log('setInterval 1초 호출 수(25분 동안):', naiveSec, '회 =', H.fmt(naiveSec * 1000), '-> 화면 남은 시간', H.fmt(DUR - naiveSec * 1000));
console.log('시각 차이 방식 경과:', H.fmt(corrected), '(마지막 호출 시점', H.fmt(last), ')');
assert.strictEqual(naiveSec, 379);
assert.strictEqual(H.fmt(DUR - naiveSec * 1000), '18:41');
assert.strictEqual(corrected, last);
assert.strictEqual(H.fmt(DUR - H.used(c, DUR, 1700000000000 + DUR)), '00:00');
console.log('PASS 백그라운드 제한: 틱 카운트 379초 vs 실제 1500초, 시각 차이 방식은 오차 0');

// 3) 일시정지·재개
let k = H.clock();
H.go(k, 1000, 5000); H.stop(k, 61000, 65000);           // 60초 진행
assert.strictEqual(H.used(k, 999999, 999999), 60000);   // 멈춘 동안은 안 흐름
H.go(k, 500000, 504000);
assert.strictEqual(H.used(k, 530000, 534000), 90000);
console.log('PASS 일시정지·재개 60초+30초=90초');

// 4) 잠자기: performance.now()가 10분 멈추고 Date.now()만 흐른 경우 -> Date 쪽 사용
assert.strictEqual(H.since(0, 0, 60000, 60000 + 600000), 660000);
// 시스템 시계를 1시간 되돌린 경우 -> performance 쪽 유지
assert.strictEqual(H.since(0, 0, 60000, 60000 - 3600000), 60000);
// 2초 이내 차이는 performance 쪽
assert.strictEqual(H.since(0, 0, 60000, 61500), 60000);
console.log('PASS 잠자기 보정(Date로 대체)·시계 되돌림 무시');

// 5) 뽀모도로 일정
const p4 = H.plan(540, 25, 5, 15, 4, 4);
assert.strictEqual(H.hm(p4.end), '10:55'); assert.strictEqual(p4.work, 100); assert.strictEqual(p4.rest, 15);
const p8 = H.plan(540, 25, 5, 15, 8, 4);
assert.strictEqual(H.hm(p8.end), '13:05'); assert.strictEqual(p8.rest, 45);
assert.ok(p8.seg.some(s => s.k === '긴 휴식' && H.hm(s.s) === '10:55' && H.hm(s.e) === '11:10'));
const night = H.plan(23 * 60 + 30, 25, 5, 15, 4, 4);
assert.strictEqual(H.hm(night.end), '01:25 (+1일)');
const noLong = H.plan(540, 25, 5, 15, 8, 0);
assert.strictEqual(noLong.rest, 35);
// 표 값
const table = { 1: ['09:25', '09:50'], 2: ['09:55', '10:50'], 3: ['10:25', '11:50'], 4: ['10:55', '12:50'], 5: ['11:35', '13:50'], 6: ['12:05', '14:50'], 8: ['13:05', '16:50'] };
for (const n of Object.keys(table)) {
  assert.strictEqual(H.hm(H.plan(540, 25, 5, 15, +n, 4).end), table[n][0], '25분 ' + n);
  assert.strictEqual(H.hm(H.plan(540, 50, 10, 10, +n, 4).end), table[n][1], '50분 ' + n);
  assert.ok(html.includes('<td>' + table[n][0] + '</td>') && html.includes('<td>' + table[n][1] + '</td>'));
}
console.log('PASS 뽀모도로 일정·표 값 14개');

// 6) UI 스모크: DOM 스텁 + 가짜 시계로 타이머 시작 -> 종료 알람, 스톱워치 랩
const vals = { 'tm-h': '0', 'tm-m': '5', 'tm-s': '0', 'pm-start': '09:00', 'pm-n': '4', 'pm-w': '25', 'pm-sb': '5', 'pm-lb': '15', 'pm-ev': '4' };
const els = {}, handlers = {};
function mk(id) {
  return els[id] = { id, value: vals[id], style: {}, textContent: '', children: [],
    addEventListener(ev, f) { (handlers[id + ':' + ev] = handlers[id + ':' + ev] || []).push(f); },
    appendChild(c) { this.children.push(c); }, set innerHTML(v) { this.children = []; } };
}
['tm-display', 'tm-presets', 'tm-start', 'tm-reset', 'tm-stop', 'tm-msg', 'pm-out', 'sw-display', 'sw-start', 'sw-lap', 'sw-reset', 'sw-laps', ...Object.keys(vals)].forEach(mk);
let now = 0, intervals = [], timeouts = [];
global.performance = { now: () => now };
const realDate = Date; global.Date = { now: () => 1700000000000 + now };
global.setInterval = (f) => { intervals.push(f); return intervals.length; };
global.clearInterval = () => { intervals = []; };
global.setTimeout = (f, ms) => { timeouts.push([f, ms]); return timeouts.length; };
global.clearTimeout = () => { timeouts = []; };
global.requestAnimationFrame = () => 1; global.cancelAnimationFrame = () => {};
global.navigator = {};
global.document = { title: '타이머', getElementById: id => els[id], addEventListener() {},
  createElement: () => ({ style: {}, children: [], appendChild(c) { this.children.push(c); }, addEventListener(ev, f) { this.onclick = f; } }) };
eval(src);
const pm = els['pm-out'].children;
console.log('UI 뽀모도로 기본값:', pm[0].textContent, '|', pm[1].textContent);
assert.ok(pm[0].textContent.includes('10:55'));
const fire = (id) => handlers[id + ':click'].forEach(f => f.call(els[id]));
fire('tm-start');
assert.strictEqual(timeouts[0][1], 300030);                     // 알람 1회 예약
now = 61000; intervals[0]();
console.log('UI 61초 뒤:', els['tm-display'].textContent, '/ 탭 제목:', document.title);
assert.strictEqual(els['tm-display'].textContent, '03:59');
assert.ok(document.title.startsWith('03:59 남음'));
fire('tm-start'); now = 200000;                                   // 일시정지 후 139초 대기
assert.strictEqual(els['tm-msg'].textContent, '일시정지');
fire('tm-start');
assert.strictEqual(timeouts[0][1], 239000 + 30);                  // 남은 239초로 재예약
now = 200000 + 239030; timeouts[0][0]();                          // 알람 setTimeout 발화
console.log('UI 종료:', els['tm-display'].textContent, '/', els['tm-msg'].textContent, '/ 탭 제목:', document.title, '/ 알람 끄기 표시:', els['tm-stop'].style.display === '');
assert.strictEqual(els['tm-msg'].textContent, '시간이 다 됐습니다.');
assert.ok(document.title.startsWith('시간 종료'));
// 프리셋 25분
const preset25 = els['tm-presets'].children[4]; assert.strictEqual(preset25.textContent, '25분');
preset25.onclick(); assert.strictEqual(els['tm-display'].textContent, '25:00');
// 스톱워치
now = 1000000; fire('sw-start'); now += 12340; fire('sw-lap'); now += 5000; fire('sw-lap'); fire('sw-start');
console.log('UI 스톱워치 랩:', els['sw-laps'].children.map(c => c.textContent).join(' | '), '/ 표시', els['sw-display'].textContent);
assert.strictEqual(els['sw-laps'].children[1].textContent, '00:05.00 (누적 00:17.34)');
assert.strictEqual(els['sw-display'].textContent, '00:17.34');
global.Date = realDate;
console.log('ALL PASS');
