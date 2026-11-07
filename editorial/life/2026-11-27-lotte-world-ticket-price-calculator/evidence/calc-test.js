// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.lotteWorldCalc;
const Z = { a: 0, t: 0, c: 0, s: 0, b: 0, ml: 0, ma: 0, mb: 0, mp: 0 };
const cases = [
  ['4인 종합 1Day 정상가', { kind: 'all', time: 'day', a: 2, c: 2, dc: 'none' }, { total: 234000 }],
  ['4인 종합 1Day 당일 온라인', { kind: 'all', time: 'day', a: 2, c: 2, dc: 'online' }, { total: 163800, saved: 70200 }],
  ['4인 SKT VIP', { kind: 'all', time: 'day', a: 2, c: 2, dc: 'skt' }, { total: 157100 }],
  ['4인 KT', { kind: 'all', time: 'day', a: 2, c: 2, dc: 'kt' }, { total: 150400 }],
  ['After4 2인 + Premium 2', { kind: 'all', time: 'a4', a: 2, dc: 'none', mp: 2 }, { ticket: 110000, mp: 160000, total: 270000 }],
  ['After4 2인 온라인 + Premium 2', { kind: 'all', time: 'a4', a: 2, dc: 'online', mp: 2 }, { total: 237000 }],
  ['파크 + 온라인 → 정상가', { kind: 'park', time: 'day', a: 1, dc: 'online' }, { total: 64000, notes: 1 }],
  ['파크 After4 장애인 어른+청소년', { kind: 'park', time: 'a4', a: 1, t: 1, dc: 'disabled' }, { total: 48500 }],
  ['장애인 3인 → 2인만 할인', { kind: 'all', time: 'day', a: 3, dc: 'disabled' }, { total: 33500 * 2 + 67000 }],
  ['군인 After4 → 정상가', { kind: 'all', time: 'a4', a: 1, dc: 'soldier' }, { total: 55000, notes: 1 }],
  ['다둥이 어른1+65세1+베이비1', { kind: 'all', time: 'day', a: 1, s: 1, b: 1, dc: 'dadung' }, { total: 46900 + 50000 + 17000 }],
  ['문화누리 어른1 어린이3', { kind: 'all', time: 'day', a: 1, c: 3, dc: 'nuri' }, { total: 37000 + 27500 + 50000 * 2 }],
  ['임신부 공통 33,500', { kind: 'all', time: 'day', a: 2, dc: 'pregnant' }, { total: 33500 + 67000 }],
  ['LGU+ 3인', { kind: 'all', time: 'day', a: 3, dc: 'lgu' }, { total: 38850 + 46900 + 67000 }],
  ['SKT Silver After4 5인', { kind: 'all', time: 'a4', a: 5, dc: 'skts' }, { total: 33000 + 44000 * 3 + 55000 }],
  ['매직패스 Light/A/B 각1, 1인 → 경고', { kind: 'all', time: 'day', a: 1, dc: 'none', ml: 1, ma: 1, mb: 1 }, { mp: 184000, notes: 1 }],
  ['카드 본인 50% 청소년 1', { kind: 'all', time: 'day', t: 1, dc: 'card' }, { total: 29000 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, Z, o));
  for (const k of Object.keys(exp)) {
    const v = k === 'notes' ? r.notes.length : r[k];
    assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v);
  }
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(종합 1Day 어른2 어린이2 할인 없음) 렌더 확인
const vals = { 'lw-kind': 'all', 'lw-time': 'day', 'lw-a': '2', 'lw-t': '0', 'lw-c': '2', 'lw-s': '0', 'lw-b': '0', 'lw-dc': 'none', 'lw-ml': '0', 'lw-ma': '0', 'lw-mb': '0', 'lw-mp': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lw-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('234,000원'));
console.log('ALL PASS');
