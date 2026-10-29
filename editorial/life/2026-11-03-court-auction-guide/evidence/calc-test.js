// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD FAQ', faq.mainEntity.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { money, dates } = window.courtAuctionCalc;
const m = [
  ['규칙 제63조: 최저 2억 10% -> 2,000만, 현금 잔액', [200000000, 10, 230000000, 1.1, 'cash'], { deposit: 20000000, balance: 210000000, tax: 2530000, secondOver: 210000000, belowMin: false }],
  ['보증보험증권 -> 전액 납부', [200000000, 10, 230000000, 0, 'ins'], { deposit: 20000000, balance: 230000000, tax: 0 }],
  ['법원이 20%로 정한 경우', [150000000, 20, 150000000, 0, 'cash'], { deposit: 30000000, balance: 120000000 }],
  ['원 미만 버림 123,456,789 -> 12,345,678', [123456789, 10, 123456789, 0, 'cash'], { deposit: 12345678 }],
  ['최저가 미만 입찰 경고', [200000000, 10, 199990000, 0, 'cash'], { belowMin: true }],
];
for (const [name, args, exp] of m) {
  const r = money(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const d = [
  ['화 2026-11-03 -> 결정 11-10, 항고 11-17(화), 대금 12-17', ['2026-11-03', ''], { decision: '2026-11-10', appealEnd: '2026-11-17', payBy: '2026-12-17', delivery: '' }],
  ['토요일 말일 이월: 2026-11-07 매각 -> 항고말일 11-21(토) -> 11-23(월)', ['2026-11-07', ''], { decision: '2026-11-14', appealEnd: '2026-11-23', payBy: '2026-12-23' }],
  ['월말 클램프(민법 160조 3항): 납부 2026-08-31 + 6개월 -> 2027-02-28(일) -> 03-01', ['2026-11-03', '2026-08-31'], { delivery: '2027-03-01' }],
  ['인도명령 평일: 납부 2026-12-10 + 6개월 -> 2027-06-10(목)', ['2026-11-03', '2026-12-10'], { delivery: '2027-06-10' }],
];
for (const [name, args, exp] of d) {
  const r = dates(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ca-min': '200000000', 'ca-rate': '10', 'ca-bid': '230000000', 'ca-tax': '1.1', 'ca-type': 'cash', 'ca-sale': '2026-11-03', 'ca-paid': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ca-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('20,000,000원'));
assert.ok(outP.join().includes('2026. 12. 17.(목)'));
console.log('ALL PASS');
