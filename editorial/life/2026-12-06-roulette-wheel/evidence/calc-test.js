// ko.html의 돌림판 <script>를 그대로 뽑아 node에서 실행하는 검산 (공식 vs 10만 번 모의 실험)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
// WordPress 안전 규칙
assert.ok(src.indexOf('&') < 0, '& in script');
assert.ok(!/\n\s*\n/.test(src), 'blank line in script');
for (const m of src.matchAll(/'(?:[^'\\\n]|\\.)*'/g)) assert.ok(m[0].indexOf('<') < 0, 'raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(ld.indexOf('&') < 0 && ld.indexOf('<') < 0, 'JSON-LD & or <');
const faq = JSON.parse(ld);
console.log('PASS 스크립트 규칙(& 없음, 빈 줄 없음, 문자열 속 < 없음), JSON-LD 파싱, FAQ', faq.mainEntity.length, '개');
global.window = { crypto: require('crypto').webcrypto };
global.document = { getElementById: () => null };
eval(src);
const C = window.rouletteCore;
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, msg + ' ' + a + ' vs ' + b);
const pc = x => (x * 100).toFixed(2) + '%';
// 1) 파싱·확률·각도
const def = C.parseItems('짜장면\n짬뽕\n김치찌개\n돈가스\n비빔밥\n쌀국수*2\n\n잘못*abc\n영*0');
assert.strictEqual(def.items.length, 6); assert.deepStrictEqual(def.errs, ['잘못*abc', '영*0']);
const ps = C.probs(def.items);
near(ps[5], 2 / 7, 1e-12, 'p 쌀국수'); near(ps[0], 1 / 7, 1e-12, 'p 짜장면');
const segs = C.segments(def.items);
near((segs[5].a1 - segs[5].a0) * 180 / Math.PI, 360 * 2 / 7, 1e-9, '각도 쌀국수');
near(segs[5].a1, 2 * Math.PI, 1e-12, '원 한 바퀴');
near(C.probs(C.parseItems('A\nB\nC*2').items)[2], 0.5, 1e-12, '1,1,2');
near(C.probs(C.parseItems('A*10\nB*10\nC*20').items)[2], 0.5, 1e-12, '10,10,20');
console.log('PASS 확률 p=w/Σw: 쌀국수', pc(ps[5]), '각도', (360 * 2 / 7).toFixed(2) + '°, 1·1·2 → 50%');
// 2) pickIndex 경계
const it3 = C.parseItems('A\nB\nC*2').items;
assert.strictEqual(C.pickIndex(it3, 0), 0); assert.strictEqual(C.pickIndex(it3, 0.2499999), 0);
assert.strictEqual(C.pickIndex(it3, 0.25), 1); assert.strictEqual(C.pickIndex(it3, 0.5), 2);
assert.strictEqual(C.pickIndex(it3, 0.9999999999), 2);
// 3) 난수 범위
for (let i = 0; i < 100000; i++) { const u = C.randUnit(); assert.ok(u >= 0 && u < 1); }
console.log('PASS pickIndex 경계, randUnit 10만 개 모두 [0,1)');
// 4) 가중 시뮬레이션 10만 번
const N1 = 100000, cnt = [0, 0, 0, 0, 0, 0];
for (let i = 0; i < N1; i++) cnt[C.pickIndex(def.items, C.randUnit())]++;
const simW = cnt[5] / N1;
near(simW, 2 / 7, 0.005, 'sim 가중');
cnt.forEach((c, i) => near(c / N1, ps[i], 0.005, 'sim item ' + i));
console.log('PASS 가중 1·1·1·1·1·2, 10만 번: 2짜리 공식', pc(2 / 7), '실험', pc(simW), '| 전체', cnt.join(','));
// 5) 회전 각도 → 바늘 아래 칸 = 미리 정한 결과
let R = 0;
const cases = [def.items, it3, C.parseItems(Array.from({ length: 20 }, (_, i) => 'P' + i).join('\n')).items, C.parseItems('a*0.01\nb*100').items];
for (let i = 0; i < 50000; i++) {
  const items = cases[i % cases.length], sg = C.segments(items), idx = C.pickIndex(items, C.randUnit());
  const to = C.targetRotation(R, sg[idx], C.randUnit(), 5 + Math.floor(C.randUnit() * 3));
  assert.ok(to - R >= 5 * 2 * Math.PI && to - R < 8 * 2 * Math.PI, 'turns');
  assert.strictEqual(C.landedIndex(to, sg), idx, 'landed');
  R = to % (2 * Math.PI);
  assert.strictEqual(C.landedIndex(R, sg), idx, 'landed after mod');
}
console.log('PASS 회전 각도 5만 회: 바늘 아래 칸이 미리 정한 당첨 항목과 모두 일치');
// 6) 한 번 이상 걸릴 확률 1-(1-p)^n: 공식표 + 시뮬레이션
const tbl = { '1/6': [16.67, 42.13, 66.51, 83.85, 97.39], '1/10': [10.00, 27.10, 46.86, 65.13, 87.84], '1/20': [5.00, 14.26, 26.49, 40.13, 64.15] };
for (const [k, row] of Object.entries(tbl)) {
  const p = 1 / Number(k.split('/')[1]);
  [1, 3, 6, 10, 20].forEach((n, i) => assert.strictEqual(+(C.atLeastOnce(p, n) * 100).toFixed(2), row[i], k + ' n=' + n));
}
near(1 - C.atLeastOnce(0.1, 10), 0.3487, 0.00005, '10칸 10번 0회');
near((1 / 6) * (1 / 6), 0.0278, 0.00005, '연속 2번');
const six = C.parseItems('1\n2\n3\n4\n5\n6').items;
let hit = 0;
for (let t = 0; t < N1; t++) { let ok = false; for (let s = 0; s < 6; s++) if (C.pickIndex(six, C.randUnit()) === 0) ok = true; if (ok) hit++; }
const simA = hit / N1;
near(simA, C.atLeastOnce(1 / 6, 6), 0.005, 'sim at least once');
console.log('PASS 1-(1-p)^n 표 15칸 일치, 6칸 6번 공식', pc(C.atLeastOnce(1 / 6, 6)), '실험', pc(simA));
// 7) 필요 횟수
const sp = [[1 / 6, .5, 4], [1 / 6, .9, 13], [0.1, .5, 7], [0.1, .9, 22], [0.05, .5, 14], [0.05, .9, 45], [0.5, 0.75, 2], [1, 0.9, 1]];
for (const [p, T, e] of sp) {
  assert.strictEqual(C.spinsFor(p, T), e, 'spinsFor ' + p + ' ' + T);
  assert.ok(C.atLeastOnce(p, e) >= T - 1e-12 && (e === 1 || C.atLeastOnce(p, e - 1) < T), 'minimal ' + p);
}
console.log('PASS 필요 횟수: 6칸 4/13, 10칸 7/22, 20칸 14/45, 경계 p=0.5 목표 75% → 2');
// 8) 비복원 k/N: 뽑힌 항목 빼며 돌리기 시뮬레이션
const ten = Array.from({ length: 10 }, (_, i) => ({ name: 'P' + i, w: 1 }));
let inK = 0; const pos = new Array(10).fill(0);
for (let t = 0; t < N1; t++) {
  const pool = ten.slice();
  for (let d = 0; d < 10; d++) { const i = C.pickIndex(pool, C.randUnit()); if (pool[i].name === 'P0') { pos[d]++; if (d < 3) inK++; } pool.splice(i, 1); }
}
const simK = inK / N1;
near(C.firstK(10, 3), 0.3, 1e-12, 'k/N'); assert.strictEqual(C.firstK(10, 15), 1);
near(simK, 0.3, 0.005, 'sim k/N');
pos.forEach((c, d) => near(c / N1, 0.1, 0.005, 'pos ' + d));
console.log('PASS 10개 중 3개 비복원: 공식', pc(C.firstK(10, 3)), '실험', pc(simK), '| 자리별 P0', pos.map(c => pc(c / N1)).join(' '));
// 9) UI 스모크 테스트 — 최소 DOM 스텁으로 돌리기 1회, 빼기 모드
const ctx2d = new Proxy({}, { get: (o, k) => (k in o ? o[k] : () => {}), set: (o, k, v) => { o[k] = v; return true; } });
const mk = (extra) => Object.assign({ value: '', textContent: '', style: {}, checked: false, disabled: false, readOnly: false, children: [], listeners: {},
  addEventListener(t, f) { this.listeners[t] = f; }, appendChild(c) { this.children.push(c); }, set innerHTML(v) { this.children = []; }, getContext: () => ctx2d }, extra || {});
const els = {};
['rw-canvas', 'rw-items', 'rw-result', 'rw-spin', 'rw-reset', 'rw-remove', 'rw-table', 'rw-history', 'rw-out2', 'rw-out3'].forEach(id => els[id] = mk());
near(C.parseP('1/6'), 1 / 6, 1e-15, 'parseP 분수'); near(C.parseP('25%'), 0.25, 1e-15, 'parseP %'); near(C.parseP('10'), 0.1, 1e-15, 'parseP 숫자');
Object.assign(els, { 'rw-p': mk({ value: '1/6' }), 'rw-n': mk({ value: '6' }), 'rw-t': mk({ value: '90' }), 'rw-N': mk({ value: '10' }), 'rw-k': mk({ value: '3' }) });
let ts = 0;
global.window = { crypto: require('crypto').webcrypto, devicePixelRatio: 2, requestAnimationFrame: f => { ts += 100; f(ts); } };
global.document = { getElementById: id => els[id], createElement: () => mk() };
eval(src);
console.log('UI 계산기2:', els['rw-out2'].children.map(c => c.textContent).join(' | '));
console.log('UI 계산기3:', els['rw-out3'].children.map(c => c.textContent).join(' | '));
assert.ok(els['rw-out2'].children[0].textContent.includes('66.51%'));
assert.ok(els['rw-out2'].children[2].textContent.includes('13번'));
assert.ok(els['rw-out3'].children[0].textContent.includes('30.00%'));
assert.strictEqual(els['rw-table'].children[0].children.length, 7);
els['rw-remove'].checked = true;
els['rw-spin'].listeners.click();
const won = els['rw-result'].textContent;
assert.ok(won.startsWith('당첨: '), won);
const left = els['rw-items'].value.split('\n');
assert.strictEqual(left.length, 5); assert.ok(!left.some(l => l.replace('*2', '') === won.slice(4)));
console.log('UI 돌리기 1회:', won, '| 빼기 후 남은 항목:', left.join(', '), '|', els['rw-history'].textContent);
els['rw-items'].value = 'A'; els['rw-items'].listeners.input();
assert.ok(els['rw-spin'].disabled); console.log('UI 항목 1개:', els['rw-result'].textContent);
els['rw-items'].value = Array.from({ length: 21 }, (_, i) => 'X' + i).join('\n'); els['rw-items'].listeners.input();
assert.ok(els['rw-spin'].disabled); console.log('UI 항목 21개:', els['rw-result'].textContent);
console.log('ALL PASS');
