// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert'), nodeCrypto = require('crypto');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
global.window = { crypto: { getRandomValues: a => nodeCrypto.getRandomValues(a) } };
global.document = { getElementById: () => null };
eval(src);
const L = window.lottoCore, C = 8145060;
assert.strictEqual(L.C, C);
// 1) 1게임 등수별 경우의 수와 확률
const exp = [1, 6, 228, 11115, 182780];
L.perGame(1).forEach((r, i) => { assert.strictEqual(r.count, exp[i]); assert.ok(Math.abs(r.p - exp[i] / C) < 1e-15); });
console.log('PASS 경우의 수', exp.join(', '));
// 2) N게임 1번 이상 (Python math-check 출력과 대조)
const near = (a, b, tol) => assert.ok(Math.abs(a - b) < tol, a + ' vs ' + b);
near(L.perGame(5)[4].atLeast * 100, 10.727892, 1e-5);
near(L.perGame(100)[4].atLeast * 100, 89.664873, 1e-5);
near(L.perGame(100)[3].atLeast * 100, 12.764278, 1e-5);
near(L.perGame(10)[3].atLeast * 100, 1.356281, 1e-5);
near(L.perGame(10000)[2].atLeast * 100, 24.416198, 1e-5);
near(L.firstDistinct(100), 100 / C, 1e-18);
assert.strictEqual(L.firstDistinct(C + 5), 1);
console.log('PASS N게임 확률 (5게임 5등 10.73%, 100게임 5등 89.66%, 4등 12.76%)');
// 3) 매주 M게임 X년
near(L.weekly(5, 50).p * 100, 0.1595, 1e-4);
near(L.weekly(1, 10).p * 100, 0.0064, 1e-4);
near(L.weekly(10, 50).p * 100, 0.3187, 1e-4);
assert.strictEqual(Math.round(L.weekly(1, 1).half), 108572);
assert.strictEqual(Math.round(L.weekly(5, 1).half), 21714);
assert.strictEqual(Math.round(L.weekly(10, 1).half), 10857);
assert.strictEqual(Math.round(L.weekly(1, 1).mean), 156636);
assert.strictEqual(Math.round(L.weekly(5, 1).mean), 31327);
console.log('PASS 매주 확률·50% 기간·평균 대기');
// 4) 4·5등 고정 기댓값
near(L.fixedReturn(1), 180.43, 0.005);
console.log('PASS 4·5등 기댓값 1게임', L.fixedReturn(1).toFixed(2), '원');
assert.strictEqual(L.PRICE, 1000); assert.strictEqual(L.spent(5), 5000);
near(L.fixedReturn(1) / L.PRICE * 100, 18.04, 0.005);
console.log('PASS 금액: 1게임 1,000원, 4·5등 기댓값 = 낸 돈의', (L.fixedReturn(1) / 10).toFixed(2) + '%');
// 5) 번호 생성기: 6개, 1~45, 중복 없음, 정렬 / 균등성 카이제곱
const freq = new Array(46).fill(0), T = 200000;
for (let k = 0; k < T; k++) {
  const s = L.pick6();
  assert.strictEqual(s.length, 6); assert.strictEqual(new Set(s).size, 6);
  for (let i = 0; i < 6; i++) { assert.ok(s[i] >= 1 && s[i] <= 45); if (i) assert.ok(s[i] > s[i - 1]); freq[s[i]]++; }
}
const e = T * 6 / 45; let chi = 0; for (let v = 1; v <= 45; v++) chi += (freq[v] - e) ** 2 / e;
console.log('PASS 생성기 20만 회: 번호별 카이제곱', chi.toFixed(2), '(자유도 44, 5% 기준값 60.48)');
assert.ok(chi < 60.48 * 1.3);
// 6) UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'lt-n': '5', 'lt-m': '5', 'lt-y': '50', 'lt-g': '' };
const outs = {}; const els = {};
const mk = id => ({ id, value: vals[id], style: {}, children: [], addEventListener(t, f) { this['on' + t] = f; }, set innerHTML(v) { this.children = []; }, appendChild(c) { this.children.push(c); } });
['lt-out', 'lt-out2', 'lt-balls', 'lt-hist', 'lt-pick', 'lt-clear', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {}, children: [], setAttribute() {}, appendChild(c) { this.children.push(c); } }) };
eval(src);
const txt = id => els[id].children.map(p => p.textContent).join(' | ');
console.log('UI 1):', txt('lt-out'));
console.log('UI 2):', txt('lt-out2'));
assert.ok(txt('lt-out').includes('5등 1번 이상: 10.73%'));
assert.ok(txt('lt-out2').includes('0.159%'));
assert.ok(txt('lt-out').includes('구입 금액 5,000원'));
assert.ok(txt('lt-out').includes('약 902원'));
assert.ok(txt('lt-out').includes('평균 환급 2,500원, 평균 손실 2,500원'));
assert.ok(txt('lt-out2').includes('구입 금액 13,000,000원'));
assert.strictEqual(els['lt-g'].children.length, 5);
els['lt-pick'].onclick();
assert.strictEqual(els['lt-balls'].children.length, 5);
console.log('UI 생성기 5게임:', els['lt-hist'].children.map(li => li.textContent).join(' / '));
console.log('ALL PASS');
