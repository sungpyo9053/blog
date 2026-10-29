// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.includes('<')) throw new Error('raw < in string ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.suneungCalc;
const D = [
  ['2026-10-29', 'D-21', 21, 3, 0], ['2026-11-01', 'D-18', 18, 2, 4], ['2026-11-18', 'D-1', 1, 0, 1],
  ['2026-11-19', 'D-DAY', 0, 0, 0], ['2026-11-20', 'D+1', -1, 0, 0], ['2026-01-01', 'D-322', 322, 46, 0],
];
for (const [d, label, diff, w, r] of D) {
  const x = c.dday(d);
  assert.deepStrictEqual([x.label, x.diff, x.weeks, x.days], [label, diff, w, r], d);
  console.log('PASS dday', d, JSON.stringify(x));
}
assert.strictEqual(c.dday(''), null);
// 교시: 공고 표의 소요 시간과 대조
const PER = { '1': ['08:40', '10:00', 80, '08:10'], '2': ['10:30', '12:10', 100, '10:20'], '3': ['13:10', '14:20', 70, '13:00'],
  '4': ['14:50', '16:37', 107, '14:40'], '4h': ['14:50', '15:20', 30, '14:40'], '4a': ['15:35', '16:05', 30, '14:40'],
  '4b': ['16:07', '16:37', 30, '14:40'], '5': ['17:05', '17:45', 40, '16:55'] };
for (const k of Object.keys(PER)) {
  const x = c.period(k), e = PER[k];
  assert.deepStrictEqual([x.start, x.end, x.minutes, x.entry], e, k);
  console.log('PASS period', k, JSON.stringify(x));
}
// 시각 → 진행 중 교시
const AT = [['07:30', '입실 전'], ['08:10', '입실 완료 후'], ['08:39', '입실 완료 후'], ['08:40', '1교시 국어'], ['09:59', '1교시 국어'],
  ['10:00', '쉬는 시간'], ['10:45', '2교시 수학'], ['12:30', '점심시간'], ['13:20', '3교시 영어'], ['14:00', '3교시 영어'],
  ['14:45', '쉬는 시간'], ['15:00', '4교시 한국사'], ['15:25', '회수'], ['15:40', '제1선택'], ['16:06', '문제지 회수'],
  ['16:20', '제2선택'], ['16:50', '5교시 입실'], ['17:30', '5교시'], ['17:45', '시험 종료'], ['23:59', '시험 종료']];
for (const [t, want] of AT) {
  const x = c.at(t);
  assert.ok(x.label.includes(want), t + ' -> ' + x.label);
  console.log('PASS at', t, x.label, '남은', x.left + '분', x.listening ? '(듣기)' : '');
}
assert.strictEqual(c.at('13:20').listening, true); assert.strictEqual(c.at('13:35').listening, false);
assert.strictEqual(c.at('08:40').left, 80); assert.strictEqual(c.at(''), null);
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'sn-date': '2026-11-01', 'sn-period': '2', 'sn-time': '10:45' };
const outs = {};
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['sn-dday', 'sn-pout', 'sn-tout', 'sn-today', 'sn-now', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
for (const id of ['sn-dday', 'sn-pout', 'sn-tout']) console.log('UI', id + ':', outs[id].join(' | '));
assert.ok(outs['sn-dday'].join().includes('D-18'));
assert.ok(outs['sn-pout'].join().includes('100분 (1시간 40분)'));
assert.ok(outs['sn-tout'].join().includes('2교시 수학'));
console.log('ALL PASS');
