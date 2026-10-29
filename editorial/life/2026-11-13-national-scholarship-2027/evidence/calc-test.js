// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.includes('<')) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { fund, grade, newBand } = window.nsCalc;
// 재단 I유형 지원금액표 (학기, 연간)
const I = { 1: [3e6, 6e6], 2: [3e6, 6e6], 3: [3e6, 6e6], 4: [2.2e6, 4.4e6], 5: [2.2e6, 4.4e6], 6: [2.2e6, 4.4e6], 7: [1.8e6, 3.6e6], 8: [1.8e6, 3.6e6], 9: [5e5, 1e6], 10: [0, 0] };
const M = { 1: [3.05e6, 6.1e6], 4: [2.525e6, 5.05e6], 7: [2.325e6, 4.65e6], 9: [6.75e5, 1.35e6], 10: [0, 0] };
for (const b in I) { const r = fund(+b, 'none'); assert.deepStrictEqual([r.sem, r.year], I[b], 'I ' + b); }
for (const b in M) { const r = fund(+b, '12'); assert.deepStrictEqual([r.sem, r.year], M[b], 'M ' + b); }
console.log('PASS I유형 10개 구간, 다자녀 첫째·둘째 대표 구간');
assert.ok(fund(0, 'none').full); assert.ok(fund(8, '3').full);
assert.deepStrictEqual([fund(9, '3').sem, fund(9, '3').year], [1e6, 2e6]);
assert.strictEqual(fund(10, '3').year, 0);
console.log('PASS 기초·차상위 전액, 셋째 이상 8구간 전액 / 9구간 100만·200만 / 10구간 0');
assert.strictEqual(fund(2, 'none', 2500000).paid, 2500000); // 등록금 상한
assert.strictEqual(fund(5, 'none', 4000000).paid, 2200000);
console.log('PASS 등록금 상한 min(학기 최대, 등록금)');
assert.deepStrictEqual([1, 3, 4, 6, 7, 8, 9, 10].map(newBand), ['가 구간', '가 구간', '나 구간', '나 구간', '다 구간', '다 구간', '라 구간', '마 구간']);
console.log('PASS 2027 개편 구간 매핑');
const G = (st, sp, b, c, s, w) => grade(st, sp, b, c, s, w).res;
const gc = [
  ['신입생 첫 학기 → 미적용', G('new', 'none', 5, 0, 0, 0), '충족'],
  ['재학생 12학점 80점', G('cur', 'none', 5, 12, 80, 0), '충족'],
  ['재학생 11학점', G('cur', 'none', 5, 11, 95, 0), '미충족'],
  ['5구간 78점', G('cur', 'none', 5, 15, 78, 0), '미충족'],
  ['2구간 78점 경고 0회 → 경고', G('cur', 'none', 2, 15, 78, 0), '경고'],
  ['2구간 78점 경고 2회 → 미충족', G('cur', 'none', 2, 15, 78, 2), '미충족'],
  ['3구간 69.9점 → 미충족', G('cur', 'none', 3, 15, 69.9, 0), '미충족'],
  ['기초 72점 → 충족(70)', G('cur', 'none', 0, 12, 72, 0), '충족'],
  ['장애인 6학점 50점 → 충족', G('cur', 'disabled', 5, 6, 50, 0), '충족'],
  ['자립준비청년 12학점 40점 → 충족', G('cur', 'selfreliant', 5, 12, 40, 0), '충족'],
  ['자립준비청년 9학점 → 미충족', G('cur', 'selfreliant', 5, 9, 90, 0), '미충족'],
  ['초과학기 6학점 85점 → 충족', G('grad', 'none', 5, 6, 85, 0), '충족'],
];
for (const [n, got, exp] of gc) { assert.strictEqual(got, exp, n); console.log('PASS', n, got); }
// UI 기본값 렌더 (5구간, 해당 없음, 2027, 재학생 15학점 82점)
const vals = { 'ns-band': '5', 'ns-multi': 'none', 'ns-term': '2027', 'ns-tuition': '', 'ns-status': 'cur', 'ns-special': 'none', 'ns-credits': '15', 'ns-score': '82', 'ns-warn': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ns-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2,200,000원')); assert.ok(outP.join().includes('나 구간'));
