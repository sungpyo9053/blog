// ko.html의 주사위 <script>를 그대로 뽑아 node에서 실행하는 검산 (정확한 DP vs 20만 번 모의 실험, 카이제곱)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
assert.ok(src.indexOf('&') < 0, '& in script');
assert.ok(!/\n\s*\n/.test(src), 'blank line in script');
for (const m of src.matchAll(/'(?:[^'\\\n]|\\.)*'/g)) assert.ok(m[0].indexOf('<') < 0, 'raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(ld.indexOf('&') < 0 && ld.indexOf('<') < 0, 'JSON-LD & or <');
const faq = JSON.parse(ld);
const faqH3 = (html.split('<h2 id="faq">')[1].split('<h2')[0].match(/<h3>/g) || []).length;
assert.strictEqual(faq.mainEntity.length, faqH3);
console.log('PASS 스크립트 규칙(& 없음, 빈 줄 없음, 문자열 속 < 없음), JSON-LD 파싱, FAQ', faq.mainEntity.length, '개 = 본문 h3', faqH3);
global.window = { crypto: require('crypto').webcrypto };
global.document = { getElementById: () => null };
eval(src);
const C = window.diceCore;
const pc = x => (x * 100).toFixed(2) + '%';
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, msg + ' ' + a + ' vs ' + b);
// 1) DP vs 완전 열거 (작은 경우 전부)
function brute(n, s) { const c = {}; const rec = (i, sum) => { if (i === n) { c[sum] = (c[sum] || 0) + 1; return; } for (let f = 1; f <= s; f++) rec(i + 1, sum + f); }; rec(0, 0); return c; }
for (const s of [4, 6, 8, 10, 12, 20]) for (let n = 1; n <= (s <= 6 ? 5 : 3); n++) {
  const D = C.dist(n, s), b = brute(n, s);
  assert.strictEqual(D.counts.reduce((x, y) => x + y), D.total);
  for (let k = n; k <= n * s; k++) assert.strictEqual(C.cntEq(D, k), b[k], n + 'd' + s + ' ' + k);
}
const big = C.dist(10, 20);
assert.strictEqual(big.counts.reduce((x, y) => x + y), big.total); assert.ok(big.total <= Number.MAX_SAFE_INTEGER);
console.log('PASS DP = 완전 열거 (d4~d20, 1~5개), 10d20 경우의 수 합', big.total, '정확(2^53 이하)');
// 2) 글에 쓴 숫자
const d2 = C.dist(2, 6), d3 = C.dist(3, 6), d10 = C.dist(10, 6);
assert.deepStrictEqual(d2.counts, [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]);
const chk = (v, s) => assert.strictEqual(pc(v), s, s);
chk(C.cntEq(d2, 7) / 36, '16.67%'); chk(1 / 36, '2.78%'); chk(2 / 36, '5.56%'); chk(3 / 36, '8.33%'); chk(4 / 36, '11.11%'); chk(5 / 36, '13.89%');
chk(C.cntGe(d2, 8) / 36, '41.67%'); chk(C.cntGe(d2, 10) / 36, '16.67%'); chk(C.cntGe(d2, 7) / 36, '58.33%');
assert.deepStrictEqual(C.modes(d3), [10, 11]); assert.strictEqual(C.cntEq(d3, 10), 27); assert.strictEqual(C.cntEq(d3, 9), 25);
chk(27 / 216, '12.50%'); chk(25 / 216, '11.57%'); chk(1 / 216, '0.46%'); assert.strictEqual(C.cntGe(d3, 15), 20); chk(20 / 216, '9.26%');
assert.strictEqual(C.mean(2, 6), 7); assert.strictEqual(C.sd(2, 6).toFixed(2), '2.42'); assert.strictEqual(C.mean(3, 6), 10.5); assert.strictEqual(C.sd(3, 6).toFixed(2), '2.96');
assert.strictEqual(C.mean(10, 6), 35); assert.strictEqual(C.sd(10, 6).toFixed(2), '5.40');
chk(C.cntEq(d10, 35) / d10.total, '7.27%');
chk((C.cntLe(d10, 40) - C.cntLe(d10, 29)) / d10.total, '68.70%'); chk((C.cntLe(d10, 42) - C.cntLe(d10, 27)) / d10.total, '83.32%');
assert.strictEqual(d10.total, 60466176);
// 기댓값 = Σ k P(k) 확인
for (const [n, s] of [[2, 6], [3, 6], [10, 6], [4, 20]]) { const D = C.dist(n, s); let m = 0; D.counts.forEach((c, i) => m += (i + D.min) * c / D.total); near(m, C.mean(n, s), 1e-9, 'mean'); let v = 0; D.counts.forEach((c, i) => v += (i + D.min - m) ** 2 * c / D.total); near(Math.sqrt(v), C.sd(n, s), 1e-9, 'sd'); }
const tbl = { 1: ['16.67%', '83.33%'], 2: ['30.56%', '69.44%'], 3: ['42.13%', '57.87%'], 4: ['51.77%', '48.23%'], 6: ['66.51%', '33.49%'], 10: ['83.85%', '16.15%'], 20: ['97.39%', '2.61%'] };
for (const [n, [a, b]] of Object.entries(tbl)) { chk(C.atLeastOne(+n, 6), a); chk(1 - C.atLeastOne(+n, 6), b); }
chk(1 - (35 / 36) ** 24, '49.14%'); chk(1 - (35 / 36) ** 25, '50.55%'); chk((5 / 6) ** 5, '40.19%'); chk(C.atLeastOne(2, 20), '9.75%');
chk(C.cntGe(C.dist(1, 20), 15) / 20, '30.00%');
const tie = s => 1 - (s * (s - 1) * (s - 2) * (s - 3)) / s ** 4;
chk(tie(6), '72.22%'); console.log('동점 확률 4명 d20:', pc(tie(20)));
const rf = { 4: [3, 9], 6: [4, 13], 8: [6, 18], 10: [7, 22], 12: [8, 27], 20: [14, 45] };
for (const [s, [a, b]] of Object.entries(rf)) {
  assert.strictEqual(C.rollsFor(+s, 0.5), a); assert.strictEqual(C.rollsFor(+s, 0.9), b);
  assert.ok(C.atLeastOne(a, +s) >= 0.5 && C.atLeastOne(a - 1, +s) < 0.5); assert.ok(C.atLeastOne(b, +s) >= 0.9 && C.atLeastOne(b - 1, +s) < 0.9);
}
assert.strictEqual(2 ** 32 % 6, 4); assert.strictEqual(2 ** 32 % 20, 16); assert.strictEqual(2 ** 32 % 10, 6);
console.log('PASS 글의 숫자: 2d6 표·3d6·10d6 구간·1-(5/6)^n 표·6-6 24/25번·필요 횟수 표·거부 개수 4/16/6');
// 3) 모의 실험 20만 번
const N = 200000;
let c7 = 0, c10 = 0, hit = 0, wait = 0;
const f6 = new Array(7).fill(0), f20 = new Array(21).fill(0), s2 = new Array(13).fill(0);
for (let i = 0; i < N; i++) {
  const a = C.roll(2, 6), s = a[0] + a[1]; s2[s]++; if (s === 7) c7++;
  if (C.roll(3, 6).reduce((x, y) => x + y) === 10) c10++;
  if (C.roll(4, 6).some(v => v === 6)) hit++;
  let t = 1; while (C.randInt(20) !== 20) t++; wait += t;
  f6[C.randInt(6)]++; f20[C.randInt(20)]++;
}
const r7 = c7 / N, r10 = c10 / N, rh = hit / N, rw = wait / N;
near(r7, 1 / 6, 0.005, '2d6 7'); near(r10, 0.125, 0.005, '3d6 10'); near(rh, C.atLeastOne(4, 6), 0.005, 'atleast'); near(rw, 20, 0.3, 'wait');
console.log('실험 20만 번: 2d6 합7', pc(1 / 6), '→', pc(r7), '| 3d6 합10', pc(0.125), '→', pc(r10), '| 4번 중 6', pc(C.atLeastOne(4, 6)), '→', pc(rh), '| d20 20 대기 평균 20 →', rw.toFixed(2));
assert.ok(f6[0] === 0 && f20[0] === 0 && f6.slice(1).every(x => x > 0));
function chi(obs, exp) { return obs.reduce((x, o, i) => x + (o - exp[i]) ** 2 / exp[i], 0); }
const x6 = chi(f6.slice(1), new Array(6).fill(N / 6)), x20 = chi(f20.slice(1), new Array(20).fill(N / 20));
const x2 = chi(s2.slice(2), d2.counts.map(c => N * c / 36));
// 5% 임계값: df5 11.07, df19 30.14, df10 18.31
console.log('카이제곱: d6', x6.toFixed(2), '(df5, 기준 11.07) | d20', x20.toFixed(2), '(df19, 기준 30.14) | 2d6 합계', x2.toFixed(2), '(df10, 기준 18.31)');
assert.ok(x6 < 20.52 && x20 < 43.82 && x2 < 29.59, 'chi-square 0.1% 기준 초과');
// 4) 거부 샘플링: 가짜 난수로 경계 확인
const seq = [4294967295, 4294967292, 4294967291, 5];
global.window.crypto = { getRandomValues: a => { a[0] = seq.shift(); return a; } };
assert.strictEqual(C.randInt(6), 4294967291 % 6 + 1); // 4294967295·4294967292는 버림 (lim=4294967292)
assert.strictEqual(seq.length, 1);
global.window.crypto = require('crypto').webcrypto;
console.log('PASS 거부 샘플링: 2^32-4 이상 값은 버리고 다시 뽑음');
// 5) UI 스모크
const mk = (extra) => Object.assign({ value: '', textContent: '', title: '', style: {}, selected: false, children: [], listeners: {}, attrs: {},
  addEventListener(t, f) { this.listeners[t] = f; }, appendChild(c) { this.children.push(c); }, setAttribute(k, v) { this.attrs[k] = v; }, set innerHTML(v) { this.children = []; } }, extra || {});
const els = {};
['dr-n', 'dr-s', 'dc-s', 'dr-faces', 'dr-total', 'dr-roll', 'dr-clear', 'dr-hist', 'dc-out', 'dc-chart', 'dc-axis'].forEach(id => els[id] = mk());
els['dc-n'] = mk({ value: '2' }); els['dc-k'] = mk({ value: '7' });
global.document = { getElementById: id => els[id], createElement: () => mk() };
eval(src);
const outT = () => els['dc-out'].children.map(c => c.textContent);
console.log('UI 계산기 2d6 k=7:', outT().join(' | '));
assert.ok(outT()[0].includes('16.67% (6 / 36)')); assert.strictEqual(els['dc-chart'].children.length, 11);
assert.strictEqual(els['dc-axis'].children[1].textContent, '최빈 7');
assert.strictEqual(els['dr-n'].value, '2'); assert.strictEqual(els['dr-s'].value, '6'); assert.strictEqual(els['dr-n'].children.length, 10);
els['dc-n'].value = '10'; els['dc-s'].value = '20'; els['dc-k'].value = '200'; els['dc-s'].listeners.change();
console.log('UI 계산기 10d20 k=200:', outT().slice(0, 4).join(' | '));
assert.ok(outT()[0].includes('0.0001% 미만 (1 / 10,240,000,000,000)')); assert.strictEqual(els['dc-chart'].children.length, 191);
els['dc-n'].value = '3'; els['dc-s'].value = '6'; els['dc-k'].value = '15'; els['dc-n'].listeners.input();
assert.ok(outT()[1].startsWith('15 이상: 9.26%')); assert.ok(outT()[3].includes('10, 11'));
els['dc-n'].value = '11'; els['dc-n'].listeners.input(); console.log('UI n=11:', outT()[0]);
els['dc-n'].value = '0'; els['dc-n'].listeners.input(); console.log('UI n=0:', outT()[0]);
els['dr-n'].value = '3'; els['dr-s'].value = '20';
for (let i = 0; i < 25; i++) els['dr-roll'].listeners.click();
const faces = els['dr-faces'].children.map(c => +c.textContent);
assert.strictEqual(faces.length, 3); assert.ok(faces.every(v => v >= 1 && v <= 20));
assert.strictEqual(els['dr-total'].textContent, '3d20 합계: ' + faces.reduce((x, y) => x + y));
assert.strictEqual(els['dr-hist'].children.length, 20);
console.log('UI 굴리기:', els['dr-total'].textContent, '| 기록', els['dr-hist'].children.length, '개, 첫 줄', els['dr-hist'].children[0].textContent);
els['dr-clear'].listeners.click(); assert.strictEqual(els['dr-hist'].children.length, 0);
console.log('ALL PASS');
