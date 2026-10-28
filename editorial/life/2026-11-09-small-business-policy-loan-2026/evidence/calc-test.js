// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^']*'/g) || []) if (m.indexOf('<') >= 0) throw new Error('< in string literal ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const S = window.policyLoanSchedule;
const sum = (rows, k) => rows.reduce((a, r) => a + r[k], 0);
const cases = [
  // 일반경영안정자금: 7천만원, 4.72%, 거치 2년, 3년 분할(3개월마다 70%), 30% 만기 일시
  ['일반경영안정 7천만원 4.72% 거치24 상환36 분기 30%', [70000000, 4.72, 24, 36, 3, 30], s => {
    assert.strictEqual(s.graceCount, 8); assert.strictEqual(s.repayCount, 12);
    assert.strictEqual(s.rows[0].interest, 826000); // 70,000,000 x 4.72% / 4
    assert.strictEqual(s.rows[8].principal, 4083333); // 49,000,000 / 12
    assert.strictEqual(s.rows[8].pay, 4909333);
    assert.strictEqual(s.balloon, 21000000);
    assert.ok(s.rows[19].principal > 21000000);
    assert.strictEqual(s.rows[19].balance, 0);
  }],
  ['매월 원금균등 7천만원 4.72% 거치24 상환36', [70000000, 4.72, 24, 36, 1, 0], s => {
    assert.strictEqual(s.rows[0].interest, 275333);
    assert.strictEqual(s.rows[24].principal, 1944444);
    assert.strictEqual(s.rows.length, 60);
  }],
  ['신용취약 3천만원 5.72% 거치24 상환36 매월', [30000000, 5.72, 24, 36, 1, 0], s => {
    assert.strictEqual(s.rows[0].interest, 143000);
    assert.strictEqual(s.rows[24].pay, 976333);
  }],
  ['대환대출 5천만원 4.5% 비거치 120개월 매월', [50000000, 4.5, 0, 120, 1, 0], s => {
    assert.strictEqual(s.graceCount, 0);
    assert.strictEqual(s.rows[0].interest, 187500);
    assert.strictEqual(s.rows[0].principal, 416667);
  }],
  ['금리 0%: 이자 0, 원금 합 = 대출금', [10000000, 0, 12, 24, 1, 0], s => {
    assert.strictEqual(s.totalInterest, 0);
  }],
];
for (const [name, args, check] of cases) {
  const s = S(...args);
  assert.strictEqual(sum(s.rows, 'principal'), args[0], name + ' 원금 합계');
  assert.strictEqual(s.rows[s.rows.length - 1].balance, 0, name + ' 잔액 0');
  assert.strictEqual(s.totalPay, args[0] + s.totalInterest);
  check(s);
  console.log('PASS', name, '총이자', s.totalInterest, '첫상환', JSON.stringify(s.rows[s.graceCount]), '마지막', JSON.stringify(s.rows[s.rows.length - 1]));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'pl-amt': '7000', 'pl-rate': '4.72', 'pl-grace': '24', 'pl-term': '36', 'pl-step': '3', 'pl-balloon': '30' };
const outP = []; let tableRows = 0;
const mk = tag => ({ tag, style: {}, children: [], textContent: '', appendChild(c) { this.children.push(c); if (tag === 'table') tableRows++; } });
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (id === 'pl-out') outP.length = 0; if (id === 'pl-table') tableRows = 0; }, appendChild(p) { if (id === 'pl-out') outP.push(p.textContent); } });
const els = {}; ['pl-out', 'pl-table', 'pl-p1', 'pl-p2', 'pl-p3', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
console.log('UI 표 행 수(헤더 포함):', tableRows);
assert.ok(outP.join().includes('826,000원'));
assert.ok(outP.join().includes('4,909,333원'));
assert.strictEqual(tableRows, 21);
console.log('PASS UI');
