// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산 (timeout 120 node evidence/calc-test.js)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].indexOf('<') >= 0) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('PASS 스크립트 규칙(& 없음, 빈 줄 없음, 문자열 속 < 없음), JSON-LD 질문', faq.mainEntity.length, '개');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const P = window.pt720Core, S = 5000000;
const near = (a, b, tol) => assert.ok(Math.abs(a - b) < tol, a + ' vs ' + b);
// 1) 번호 수·확률 (math-check.py와 대조)
const exp = { '1등': 1, '2등': 4, '보너스': 5, '3등': 45, '4등': 450, '5등': 4500, '6등': 45000, '7등': 450000 };
P.perTicket(1).forEach(r => { assert.strictEqual(r.count, exp[r.name]); near(r.p, exp[r.name] / S, 1e-18); });
const sum17 = P.TIERS.filter(t => t[0] !== '보너스').reduce((s, t) => s + t[1], 0);
assert.strictEqual(sum17 / S, 0.1);
console.log('PASS 번호 수 1등 1·2등 4·보너스 5·3등 45 … 7등 450,000, 1~7등 합계 1/10');
// 2) 기댓값 750원 = 지급률 75%
near(P.evPerTicket(), 750, 1e-9);
console.log('PASS 1장 명목 기댓값', P.evPerTicket(), '원');
// 3) N장 1번 이상
near(P.perTicket(5)[7].atLeast * 100, 37.5968, 1e-3);
near(P.atLeast(0.1, 5) * 100, 40.951, 1e-9);
near(P.perTicket(10)[7].atLeast * 100, 61.0584, 1e-3);
near(P.perTicket(100)[5].atLeast * 100, 8.61059, 1e-4);
near(P.firstDistinct(5), 1 / 1000000, 1e-18);
assert.strictEqual(P.firstDistinct(S + 1), 1);
console.log('PASS N장 확률 (5장 7등 37.60%, 7등 이상 40.95%, 100장 5등 8.61%)');
// 4) 매주
near(P.weekly(5, 10).p * 100, 0.0520, 1e-4);
near(P.weekly(1, 10).p * 100, 0.0104, 1e-4);
assert.strictEqual(Math.round(P.weekly(1, 1).half), 66649);
assert.strictEqual(Math.round(P.weekly(5, 1).half), 13330);
console.log('PASS 매주 확률·50% 기간');
// 5) 세금·현재가치
assert.strictEqual(P.netMonthly(7000000), 5460000);
assert.strictEqual(P.netMonthly(4000000), 3120000);
assert.strictEqual(P.netMonthly(1000000), 780000);
assert.strictEqual(P.netMonthly(1234567), 1234567 - 246910 - 24690);
assert.strictEqual(P.pvKind('single', 0, false).pv, 1680000000);
assert.strictEqual(P.pvKind('single', 0, true).pv, 1310400000);
assert.strictEqual(P.pvKind('set', 0, false).pv, 2160000000);
const pyPV = { 0.02: [1386065988, 1081131470, 1821168274, 108775572], 0.03: [1266799665, 988103738, 1681849288, 103762406], 0.05: [1070604098, 835071197, 1449666461, 94765591] };
for (const r in pyPV) {
  const v = pyPV[r], rr = Number(r);
  near(P.pvKind('single', rr, false).pv, v[0], 1); near(P.pvKind('single', rr, true).pv, v[1], 1);
  near(P.pvKind('set', rr, false).pv, v[2], 1); near(P.pvKind('second', rr, false).pv, v[3], 1);
}
console.log('PASS 세후 월 546만·312만·78만, 현재가치 0·2·3·5% Python과 1원 이내 일치');
console.log('참고: 3% 세트 세후 PV', Math.round(P.pvKind('set', 0.03, true).pv).toLocaleString('ko-KR'), '원');
// 6) UI 렌더 (최소 DOM 스텁)
const vals = { 'pt-n': '5', 'pt-m': '5', 'pt-y': '10', 'pt-r': '3', 'pt-kind': 'single' };
const els = {};
const mk = id => ({ id, value: vals[id], checked: true, style: {}, children: [], addEventListener(t, f) { this['on' + t] = f; }, set innerHTML(v) { this.children = []; }, appendChild(c) { this.children.push(c); } });
['pt-out', 'pt-out2', 'pt-out3', 'pt-tax', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {}, children: [] }) };
eval(src);
const txt = id => els[id].children.map(p => p.textContent).join(' | ');
console.log('UI 1):', txt('pt-out'));
console.log('UI 2):', txt('pt-out2'));
console.log('UI 3) 1등 낱장 3% 세후:', txt('pt-out3'));
els['pt-kind'].value = 'set'; els['pt-tax'].checked = false; els['pt-r'].value = '3'; els['pt-kind'].onchange();
console.log('UI 3) 1등 세트 3% 세전:', txt('pt-out3'));
els['pt-r'].value = '-1'; els['pt-r'].oninput(); console.log('UI 3) 음수 할인율:', txt('pt-out3'));
els['pt-n'].value = ''; els['pt-n'].oninput(); console.log('UI 1) 빈 입력:', txt('pt-out'));
console.log('ALL PASS');
