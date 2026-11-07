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
const faqN = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faqN, h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.palaceCalc;
const ALL = { gbg: true, cdg: true, cgg: true, dsg: true, jm: true };
const C = (sel, extra) => Object.assign({ gbg: false, cdg: false, hw: false, cgg: false, dsg: false, jm: false, time: 'day', wed: false, grp: false, a: 0, y: 0, t: 0, k: 0, s: 0, h: 0 }, sel, extra || {});
const cases = [
  ['5곳 주간 어른1: 따로 9,000 / 통합 6,000', C(ALL, { a: 1 }), { indiv: 9000, passTotal: 6000, best: 6000 }],
  ['경복궁 어른2 + 65세1 + 22세1', C({ gbg: true }, { a: 2, s: 1, y: 1 }), { indiv: 6000, best: 6000, people: 4 }],
  ['덕수궁 야간 어른2', C({ dsg: true }, { time: 'night', a: 2 }), { indiv: 2000, best: 2000 }],
  ['5곳 야간 어른1: 덕수궁·창경궁만 2,000', C(ALL, { time: 'night', a: 1 }), { indiv: 2000, best: 2000 }],
  ['경복궁만 야간: 0원 + 제외', C({ gbg: true }, { time: 'night', a: 1 }), { indiv: 0, passTotal: null }],
  ['수요일 창덕·창경·덕수·종묘 어른2: 0원', C({ cdg: true, cgg: true, dsg: true, jm: true }, { wed: true, a: 2 }), { indiv: 0, best: 0, passTotal: null }],
  ['수요일 경복궁 어른1: 3,000', C({ gbg: true }, { wed: true, a: 1 }), { indiv: 3000 }],
  ['후원 어른1+만22세1: 전각3,000+후원10,000', C({ hw: true }, { a: 1, y: 1 }), { indiv: 13000, hwCost: 10000 }],
  ['후원 수요일: 10,000', C({ hw: true }, { wed: true, a: 1, y: 1 }), { indiv: 10000 }],
  ['후원 어른1+청소년1+6세1: 3,000+5,000+2,500', C({ hw: true }, { a: 1, t: 1, k: 1 }), { indiv: 10500 }],
  ['후원 야간은 제외', C({ hw: true }, { time: 'night', a: 1 }), { indiv: 0 }],
  ['4대궁+후원 어른1: 따로 13,000 / 통합 11,000', C({ gbg: true, cdg: true, cgg: true, dsg: true, hw: true }, { a: 1 }), { indiv: 13000, passTotal: 11000, best: 11000 }],
  ['단체 12명 경복궁: 28,800', C({ gbg: true }, { grp: true, a: 12 }), { indiv: 28800 }],
  ['단체 12명 종묘: 12,000', C({ jm: true }, { grp: true, a: 12 }), { indiv: 12000 }],
  ['덕수궁·창경궁·종묘 어른1: 따로 3,000이 통합보다 쌈', C({ cgg: true, dsg: true, jm: true }, { a: 1 }), { indiv: 3000, passTotal: 6000, best: 3000 }],
  ['음수·빈칸 방어', C(ALL, { a: -3, y: '', t: 'x', k: 1.7 }), { indiv: 0, people: 1 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ indiv: r.indiv, passTotal: r.passTotal, best: r.best, notes: r.notes.length }));
}
// UI 기본값(5곳 주간, 어른 2) 렌더 확인 — 최소 DOM 스텁
const vals = { 'pg-time': 'day', 'pg-a': '2', 'pg-y': '0', 'pg-t': '0', 'pg-k': '0', 'pg-s': '0', 'pg-h': '0' };
const checks = { 'pg-gbg': true, 'pg-cdg': true, 'pg-hw': false, 'pg-cgg': true, 'pg-dsg': true, 'pg-jm': true, 'pg-wed': false, 'pg-grp': false };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pg-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('예상 총 입장료: 12,000원'));
console.log('ALL PASS');
