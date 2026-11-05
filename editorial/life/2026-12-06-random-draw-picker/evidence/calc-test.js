// ko.html의 추첨기 <script>를 그대로 뽑아 node에서 실행하는 검산 (정확한 값 vs 10만 번 모의 실험, 카이제곱, 모듈로 편향)
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(src.length, 1);
const js = src[0];
assert.ok(js.indexOf('&') < 0, '& in script');
assert.ok(!/\n\s*\n/.test(js), 'blank line in script');
for (const m of js.matchAll(/'(?:[^'\\\n]|\\.)*'/g)) assert.ok(m[0].indexOf('<') < 0, 'raw < in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(ld.indexOf('&') < 0 && ld.indexOf('<') < 0, 'JSON-LD & or <');
const faq = JSON.parse(ld);
assert.ok(faq.mainEntity.length >= 6);
console.log('PASS 스크립트 규칙(& 없음, 빈 줄 없음, 문자열 속 < 없음), JSON-LD 파싱, FAQ', faq.mainEntity.length, '개');
global.window = { crypto: require('crypto').webcrypto };
global.document = { getElementById: () => null };
eval(js);
const C = window.drawCore;
const pc = x => (x * 100).toFixed(2) + '%';
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, msg + ' ' + a + ' vs ' + b);
const N = 100000;
// 1) 파싱·중복 처리
let pr = C.parseNames(' 민준\n서연\n\n민준\n하은 \n민준\nconstructor\n__proto__', false);
assert.deepStrictEqual(pr.list, ['민준', '서연', '하은', 'constructor', '__proto__']);
assert.deepStrictEqual(pr.dups, [{ name: '민준', n: 3 }]);
pr = C.parseNames('민준\n서연\n민준', true);
assert.deepStrictEqual(pr.list, ['민준', '서연', '민준']);
console.log('PASS 명단 파싱: 빈 줄·공백 무시, 중복 합치기/유지, 특수 이름');
// 2) randInt 범위·거부 샘플링 경계
for (const n of [1, 2, 3, 10, 4294967296, 3000000000]) for (let i = 0; i < 2000; i++) { const v = C.randInt(n); assert.ok(Number.isInteger(v) && v >= 0 && v < n); }
assert.throws(() => C.randInt(0));
// 3) 추첨: 중복 없음, 인원
const ten = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];
for (let i = 0; i < 1000; i++) { const d = C.draw(ten, 3, 2); assert.strictEqual(new Set(d.winners.concat(d.reserves)).size, 5); assert.strictEqual(d.winners.length, 3); }
assert.strictEqual(C.draw(ten, 10, 0).winners.slice().sort().join(''), 'ABCDEFGHIJ');
console.log('PASS randInt 범위(n=1..2^32), 추첨 결과 중복 없음');
// 4) 랜덤 숫자
assert.strictEqual(C.randNums(1, 10, 11, false), null);
let r = C.randNums(1, 10, 10, false); assert.deepStrictEqual(C.sortNums(r, 'asc'), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
r = C.randNums(-1000000000, 1000000000, 1000, false); assert.strictEqual(new Set(r).size, 1000); r.forEach(v => assert.ok(v >= -1e9 && v <= 1e9));
r = C.randNums(5, 5, 7, true); assert.deepStrictEqual(r, [5, 5, 5, 5, 5, 5, 5]);
assert.deepStrictEqual(C.sortNums([3, 10, 2], 'desc'), [10, 3, 2]); assert.deepStrictEqual(C.sortNums([3, 10, 2], 'none'), [3, 10, 2]);
assert.strictEqual(C.stamp(new Date(2026, 11, 6, 20, 5, 9)), '2026-12-06 20:05:09');
console.log('PASS 랜덤 숫자: 중복 없음/허용, 범위 초과 거절, 큰 범위, 정렬, 시각 형식');
// 5) 정확한 값 vs 10만 번
const rows = [];
let hit = 0; for (let i = 0; i < N; i++) if (C.draw(ten, 3, 0).winners.includes('A')) hit++;
rows.push(['10명 중 3명, 특정인 당첨', 0.3, hit / N]);
hit = 0; for (let i = 0; i < N; i++) { const d = C.draw(ten, 3, 1); if (d.winners.concat(d.reserves).includes('A')) hit++; }
rows.push(['10명 중 3+예비1, 특정인 포함', 0.4, hit / N]);
const twenty = Array.from({ length: 20 }, (_, i) => 'P' + i);
hit = 0; for (let i = 0; i < N; i++) { let won = false; for (let k = 0; k < 5; k++) if (C.draw(twenty, 1, 0).winners[0] === 'P0') won = true; if (won) hit++; }
rows.push(['20명 중 1명 x5회, 1회 이상', C.atLeastOnce(1 / 20, 5), hit / N]);
const bytes = require('crypto').randomBytes(N); hit = 0; for (const b of bytes) if (b % 100 <= 55) hit++;
rows.push(['0~255 % 100, 0~55 중 하나', 56 * 3 / 256, hit / N]);
for (const [name, exact, sim] of rows) { near(sim, exact, 0.01, name); console.log('PASS', name, '정확', pc(exact), '실험', pc(sim)); }
// 6) 반복 추첨 표 값
const tbl = { 0.1: ['10.00%', '27.10%', '40.95%', '65.13%', '71.76%'], 0.05: ['5.00%', '14.26%', '22.62%', '40.13%', '45.96%'], 0.02: ['2.00%', '5.88%', '9.61%', '18.29%', '21.53%'], 0.01: ['1.00%', '2.97%', '4.90%', '9.56%', '11.36%'] };
for (const p of Object.keys(tbl)) [1, 3, 5, 10, 12].forEach((m, i) => assert.strictEqual(pc(C.atLeastOnce(+p, m)), tbl[p][i]));
console.log('PASS 반복 추첨 표 20칸, 30명 중 3명 x5회 =', pc(C.atLeastOnce(0.1, 5)));
// 7) 카이제곱
const chi = (counts, n) => { const e = n / counts.length; return counts.reduce((s, c) => s + (c - e) ** 2 / e, 0); };
let cnt = new Array(10).fill(0); for (let i = 0; i < N; i++) cnt[C.randInt(10)]++;
const chiR = chi(cnt, N);
cnt = new Array(10).fill(0); for (let i = 0; i < N; i++) cnt[ten.indexOf(C.draw(ten, 1, 0).winners[0])]++;
const chiD = chi(cnt, N);
cnt = new Array(100).fill(0); for (const b of bytes) cnt[b % 100]++;
const chiB = chi(cnt, N);
assert.ok(chiR < 27.88 && chiD < 27.88, 'uniform chi too big'); // 자유도 9, 0.1% 기준값
assert.ok(chiB > 123.23, 'bias not detected'); // 자유도 99, 5% 기준값
console.log('PASS 카이제곱: randInt(10)', chiR.toFixed(2), '/ 첫 당첨자', chiD.toFixed(2), '(df 9, 5% 기준 16.92) / byte%100', chiB.toFixed(2), '(df 99, 5% 기준 123.23)');
// 8) 모듈로 편향 정확 계산
const modCounts = (range, n) => { const c = new Array(n).fill(0); for (let v = 0; v < range; v++) c[v % n]++; return c; };
const m3 = modCounts(256, 3); assert.deepStrictEqual(m3, [86, 85, 85]);
const m100 = modCounts(256, 100); assert.ok(m100.slice(0, 56).every(x => x === 3) && m100.slice(56).every(x => x === 2));
console.log('PASS 편향 예: 256%3 →', m3.join('/'), pc(86 / 256), pc(85 / 256), '| 256%100 → 0~55 3번', pc(3 / 256), ', 56~99 2번', pc(2 / 256));
assert.strictEqual(4294967296 % 3000000000, 1294967296); assert.strictEqual(4294967296 % 10, 6);
console.log('PASS 2^32 % 30억 =', 4294967296 % 3000000000, '버림 확률', pc(1294967296 / 4294967296), '평균 시도', (4294967296 / 3000000000).toFixed(2), '| 2^32 % 10 = 6, 몫', Math.floor(4294967296 / 10));
// 9) 잘못된 셔플(전체와 교환) vs 피셔-예이츠: 3명 전수 열거
const perm = {}; for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) for (let c = 0; c < 3; c++) { const x = [0, 1, 2]; [a, b, c].forEach((j, i) => { const t = x[i]; x[i] = x[j]; x[j] = t; }); perm[x.join('')] = (perm[x.join('')] || 0) + 1; }
const vals = Object.values(perm).sort(); assert.deepStrictEqual(vals, [4, 4, 4, 5, 5, 5]);
const fy = {}; for (let a = 0; a < 3; a++) for (let b = 1; b < 3; b++) { const x = [0, 1, 2]; [[0, a], [1, b]].forEach(([i, j]) => { const t = x[i]; x[i] = x[j]; x[j] = t; }); fy[x.join('')] = (fy[x.join('')] || 0) + 1; }
assert.ok(Object.keys(fy).length === 6 && Object.values(fy).every(v => v === 1));
console.log('PASS 잘못된 셔플 27가지 →', JSON.stringify(perm), pc(5 / 27), pc(4 / 27), '| 피셔-예이츠 6가지 각 1번');
// 10) FAQ 생일 문제
const birthday = 1 - (100 * 99 * 98 * 97 * 96) / 100 ** 5; console.log('PASS 1~100 중복 허용 5개 중 겹침 확률', pc(birthday));
// 11) UI 렌더(최소 DOM 스텁)
const els = {}; const mk = (id, v) => (els[id] = { id, value: v, checked: false, textContent: '', disabled: false, style: {}, children: [], addEventListener() {}, appendChild(c) { this.children.push(c.textContent); }, set innerHTML(x) { this.children = []; } });
mk('dr-names', ''); mk('dr-title', '테스트'); mk('dr-w', '3'); mk('dr-r', '1'); mk('dr-dup-one', ''); mk('dr-dup-keep', ''); mk('dr-info'); mk('dr-go'); mk('dr-copy'); mk('dr-out'); mk('dr-text', '');
mk('rn-min', '1'); mk('rn-max', '100'); mk('rn-count', '5'); mk('rn-dup'); mk('rn-sort', 'asc'); mk('rn-go'); mk('rn-copy'); mk('rn-out'); mk('rn-text', '');
mk('pc-N', '30'); mk('pc-w', '3'); mk('pc-m', '5'); mk('pc-out');
const handlers = {}; Object.values(els).forEach(e => { e.addEventListener = (t, f) => { handlers[e.id] = f; }; });
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
global.navigator = {};
eval(js);
console.log('UI 기본 정보:', els['dr-info'].textContent);
handlers['dr-go']();
console.log('UI 추첨 결과:', els['dr-out'].children.join(' | '));
console.log('UI 복사 문장:', els['dr-text'].value.replace(/\n/g, ' / '));
handlers['rn-go']();
console.log('UI 숫자 결과:', els['rn-out'].children.join(' | '));
console.log('UI 확률 계산기:', els['pc-out'].children.join(' | '));
assert.ok(els['pc-out'].children.join().includes('40.95%'));
els['dr-w'].value = '10'; handlers['dr-w'](); assert.ok(els['dr-go'].disabled); console.log('UI 인원 초과:', els['dr-info'].textContent);
console.log('ALL PASS');
