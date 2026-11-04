// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.templeCalc;
const C = (type, mode, nights, fee, cnt, extra) => Object.assign({ type, mode, nights, fee, cnt, single: false, singleFee: 0, disc: 'none', pct: 0 }, extra || {});
const cases = [
  ['도갑사 휴식형 1박기준 성인2 2박', C('rest', 'night', 2, [70000, 60000, 50000, 0], [2, 0, 0, 0]), { days: 2, base: 280000, total: 280000 }],
  ['백련사(가평) 1회요금 성인2+중고1+미취학1', C('rest', 'fixed', 1, [80000, 70000, 50000, 40000], [2, 1, 0, 1]), { people: 4, base: 270000 }],
  ['1회요금은 박수 무시', C('rest', 'fixed', 3, [80000, 70000, 50000, 40000], [2, 0, 0, 0]), { days: 1, base: 160000 }],
  ['백련사 4인 행복두배', C('rest', 'fixed', 1, [80000, 70000, 50000, 40000], [2, 1, 0, 1], { disc: 'happy' }), { total: 120000, saved: 150000 }],
  ['서고사 성인3 행복두배', C('exp', 'fixed', 1, [80000, 70000, 60000, 0], [3, 0, 0, 0], { disc: 'happy' }), { base: 240000, total: 90000, saved: 150000, perPerson: 30000 }],
  ['당일형은 행복두배 제외', C('day', 'fixed', 1, [40000, 30000, 25000, 0], [2, 0, 1, 0], { disc: 'happy' }), { base: 105000, total: 105000, saved: 0 }],
  ['당일형은 1박기준이어도 1회', C('day', 'night', 3, [40000, 0, 0, 0], [1, 0, 0, 0]), { days: 1, base: 40000 }],
  ['망경산사 30,000 행복두배 = 효과 없음', C('exp', 'fixed', 1, [30000, 0, 0, 0], [1, 0, 0, 0], { disc: 'happy' }), { total: 30000, saved: 0 }],
  ['혼자쓰기 1박기준 2박 추가 20,000', C('rest', 'night', 2, [100000, 0, 0, 0], [3, 0, 0, 0], { single: true, singleFee: 20000 }), { people: 1, base: 240000 }],
  ['혼자쓰기 1회요금 추가 20,000', C('rest', 'fixed', 2, [80000, 0, 0, 0], [1, 0, 0, 0], { single: true, singleFee: 20000 }), { base: 100000 }],
  ['직접 할인율 50%', C('exp', 'fixed', 1, [80000, 0, 0, 0], [2, 0, 0, 0], { disc: 'pct', pct: 50 }), { total: 80000, saved: 80000 }],
  ['음수·빈칸 방어', C('exp', 'fixed', '', [-5, '', 'x', 0], ['', -2, 1.7, 0]), { people: 1, base: 0 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const r5 = calc(C('exp', 'fixed', 1, [80000, 0, 0, 0], [5, 0, 0, 0], { disc: 'happy' }));
assert.ok(r5.notes.some(n => n.includes('4명까지')));
console.log('PASS 행복두배 5명 경고:', r5.notes.join(' / '));
// UI 기본값 렌더 — 최소 DOM 스텁
const ids = ['ts-type', 'ts-mode', 'ts-nights', 'ts-f0', 'ts-f1', 'ts-f2', 'ts-f3', 'ts-c0', 'ts-c1', 'ts-c2', 'ts-c3', 'ts-single', 'ts-sfee', 'ts-disc', 'ts-pct', 'ts-out'];
const init = { 'ts-type': 'exp', 'ts-nights': '1', 'ts-c0': '2', 'ts-c1': '0', 'ts-c2': '0', 'ts-c3': '0', 'ts-sfee': '0', 'ts-disc': 'none', 'ts-pct': '50' };
const outP = [], handlers = {};
const els = {};
ids.forEach(id => els[id] = { value: init[id] || '', checked: false, style: {}, addEventListener(ev, f) { (handlers[id] = handlers[id] || []).push(f); }, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(체험형 서고사 성인2):', outP.join(' | '));
assert.ok(outP.join().includes('160,000원'));
els['ts-disc'].value = 'happy'; handlers['ts-disc'].forEach(f => f());
console.log('UI 행복두배 선택:', outP.join(' | '));
assert.ok(outP.join().includes('60,000원') && outP.join().includes('할인액: 100,000원'));
els['ts-type'].value = 'rest'; handlers['ts-type'].forEach(f => f());
els['ts-nights'].value = '2'; handlers['ts-nights'].forEach(f => f());
els['ts-disc'].value = 'none'; handlers['ts-disc'].forEach(f => f());
console.log('UI 휴식형 도갑사 성인2 2박:', outP.join(' | '));
assert.ok(outP.join().includes('280,000원'));
console.log('ALL PASS');
