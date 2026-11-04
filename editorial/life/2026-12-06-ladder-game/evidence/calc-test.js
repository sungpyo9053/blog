// ko.html의 사다리 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = { crypto: require('crypto').webcrypto };
global.document = { getElementById: () => null };
eval(src);
const L = window.ladder;
// 1) 정확한 마르코프 체인 값 vs 단순 모형 몬테카를로 (가로줄마다 이웃 쌍 하나를 균등하게)
function simP11(n, k, trials) {
  let hit = 0;
  for (let t = 0; t < trials; t++) {
    const r = []; for (let i = 0; i < k; i++) r.push(Math.floor(Math.random() * (n - 1)));
    if (L.ends(n, r)[0] === 0) hit++;
  }
  return hit / trials;
}
const T = 200000;
for (const [n, k] of [[3, 3], [4, 4], [6, 6], [6, 18], [10, 10], [12, 12], [12, 36]]) {
  const ex = L.exact(n, k)[0][0], sim = simP11(n, k, T), se = Math.sqrt(ex * (1 - ex) / T);
  assert.ok(Math.abs(ex - sim) < 5 * se, `n=${n} k=${k}`);
  console.log(`PASS 1번->1번 n=${n} K=${k}: exact ${(ex * 100).toFixed(2)}% sim ${(sim * 100).toFixed(2)}%`);
}
// 2) 본문 표 값 재계산
const table = { 3: [37.5, 33.4, 5, 6], 4: [43.2, 28.1, 14, 17], 5: [45.1, 28.1, 29, 36], 6: [46.4, 28.7, 54, 66], 7: [47.3, 29.1, 88, 109], 8: [47.9, 29.5, 135, 166], 9: [48.5, 29.7, 196, 241], 10: [48.9, 30.0, 272, 336], 11: [49.2, 30.1, 366, 451], 12: [49.5, 30.3, 480, 591] };
for (const n in table) {
  const N = +n, [a, b, c, d] = table[n];
  assert.strictEqual(+(L.exact(N, N)[0][0] * 100).toFixed(1), a, 'N ' + n);
  assert.strictEqual(+(L.exact(N, 3 * N)[0][0] * 100).toFixed(1), b, '3N ' + n);
  assert.strictEqual(L.need(N, 0.1), c, 'need10 ' + n);
  assert.strictEqual(L.need(N, 0.05), d, 'need5 ' + n);
}
console.log('PASS 표 값 40개 (N=3..12)');
assert.strictEqual(+(Math.pow(4 / 5, 6) * 100).toFixed(1), 26.2); console.log('PASS (4/5)^6 = 26.2%');
// 2명: 짝수면 제자리, 홀수면 바뀜
assert.strictEqual(L.exact(2, 2)[0][0], 1); assert.strictEqual(L.exact(2, 3)[0][0], 0); assert.strictEqual(L.need(2, 0.1), -1);
console.log('PASS 2명 짝/홀');
// 3) 페이지 사다리 생성기: 일대일, 전체 순열 균등
for (let n = 2; n <= 12; n++) for (let t = 0; t < 2000; t++) {
  const e = L.ends(n, L.gen(n, n)); assert.strictEqual(new Set(e).size, n);
  const r = L.gen(n, n); assert.ok(r.length <= n + n * (n - 1) / 2);
}
console.log('PASS 2~12명 각 2,000회 일대일·가로줄 수 상한');
const cnt = {}; const M = 200000;
for (let t = 0; t < M; t++) { const k = L.ends(4, L.gen(4, 4)).join(''); cnt[k] = (cnt[k] || 0) + 1; }
const keys = Object.keys(cnt); assert.strictEqual(keys.length, 24);
let chi = 0; for (const k of keys) chi += Math.pow(cnt[k] - M / 24, 2) / (M / 24);
assert.ok(chi < 49.7, 'chi2 ' + chi); // df=23, p=0.001
console.log(`PASS 4명 20만 회: 24가지 배정 모두 등장, 최소 ${Math.min(...Object.values(cnt))} 최대 ${Math.max(...Object.values(cnt))} (기대 ${M / 24 | 0}), chi2=${chi.toFixed(1)} (df=23)`);
const c12 = new Array(12).fill(0); for (let t = 0; t < 120000; t++) c12[L.ends(12, L.gen(12, 12))[0]]++;
c12.forEach(v => assert.ok(Math.abs(v / 120000 - 1 / 12) < 0.004));
console.log('PASS 12명 12만 회 1번 자리 결과 칸별 비율', c12.map(v => (v / 1200).toFixed(2) + '%').join(' '));
// rnd 범위
for (let i = 0; i < 10000; i++) { const x = L.rnd(7); assert.ok(x >= 0 && x < 7 && Number.isInteger(x)); }
// 레이아웃: 같은 세로줄을 쓰는 가로줄은 서로 다른 행, 순서 유지
for (let t = 0; t < 2000; t++) {
  const n = 2 + (t % 11), r = L.gen(n, n), lay = L.layout(n, r);
  for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) if (Math.abs(r[i] - r[j]) <= 1) assert.ok(lay.rows[i] < lay.rows[j]);
}
console.log('PASS 레이아웃 2,000회: 겹치는 가로줄 순서 보존');
// 4) UI 스텁 실행: 기본값으로 사다리·공정도 출력
const els = {}, out = { fair: [], res: [] };
function el(id, value) { return { id, value, style: {}, children: [], textContent: '', addEventListener(ev, f) { this['on' + ev] = f; }, set innerHTML(v) { this.children = []; }, appendChild(c) { this.children.push(c); }, getContext() { return new Proxy({}, { get: (o, k) => k in o ? o[k] : () => {}, set: (o, k, v) => (o[k] = v, true) }); } }; }
const vals = { 'ld-names': '민수\n지영\n현우\n서연', 'ld-results': '청소 당번', 'ld-n': '6', 'ld-k': '6' };
['ld-canvas', 'ld-msg', 'ld-people', 'ld-out', 'ld-fair', 'ld-draw', 'ld-all', 'ld-n', 'ld-k', 'ld-names', 'ld-results'].forEach(i => els[i] = el(i, vals[i]));
global.document = { getElementById: i => els[i], createElement: () => ({ style: {}, addEventListener() {} }) };
global.requestAnimationFrame = () => 0; global.cancelAnimationFrame = () => {};
eval(src);
console.log('공정도 기본값(6명, 6개):', els['ld-fair'].children.map(c => c.textContent).join(' | '));
assert.ok(els['ld-fair'].children[1].textContent.includes('46.4%'));
els['ld-all'].onclick();
const lines = els['ld-out'].children.map(c => c.textContent);
console.log('전체 결과:', lines.join(' | '));
assert.strictEqual(lines.length, 4); assert.strictEqual(lines.filter(s => s.endsWith('청소 당번')).length, 1);
console.log('사람 버튼 수:', els['ld-people'].children.length, '/ 캔버스 높이:', els['ld-canvas'].height);
els['ld-names'].value = 'a'; els['ld-draw'].onclick(); console.log('1명 입력 메시지:', els['ld-msg'].textContent);
els['ld-n'].value = '2'; els['ld-k'].value = '3'; els['ld-n'].oninput(); console.log('2명 3개:', els['ld-fair'].children[0].textContent);
console.log('ALL PASS');
