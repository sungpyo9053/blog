// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('< in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(!/[&<]/.test(ld)); const faq = JSON.parse(ld);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS JSON-LD 파싱, FAQ', faq.mainEntity.length, '개 = 본문 h3 수');
// 수수료가 evidence 원본과 같은지
const q = fs.readFileSync(path.join(__dirname, 'qnet-7875-B0.html'), 'utf8').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
assert.ok(q.includes('14,500원 25,200원'));
const b23 = fs.readFileSync(path.join(__dirname, 'law-cem-rule-byl23.txt'), 'utf8');
assert.ok(/건설기계조종사면허의 신청\s+2,500원/.test(b23));
console.log('PASS 수수료 14,500 / 25,200 (큐넷), 면허 신청 2,500 (별표 23)');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const P = window.flPlan, S = window.flScore, W = window.flWon;
const cases = [
  ['3톤 이상 도로', 'ge3', 'road', 'yes', { construction: true, costs: [42200], warn: 0 }],
  ['3톤 이상 도로, 운전면허 없음(경고 없음)', 'ge3', 'road', 'no', { construction: true, costs: [42200], warn: 0 }],
  ['3톤 미만 도로, 운전면허 있음', 'lt3', 'road', 'yes', { construction: true, costs: [42200, 2500], warn: 0 }],
  ['3톤 미만 도로, 운전면허 없음', 'lt3', 'road', 'no', { construction: true, costs: [42200, 2500], warn: 1 }],
  ['전동 솔리드 실내(3톤 이상)', 'ge3', 'indoor', 'no', { construction: false, costs: [39700, 0], warn: 0 }],
  ['전동 솔리드 실내(3톤 미만)', 'lt3', 'indoor', 'yes', { construction: false, costs: [39700, 0], warn: 0 }],
];
for (const [name, a, b, c, exp] of cases) {
  const r = P(a, b, c);
  assert.strictEqual(r.construction, exp.construction, name);
  assert.deepStrictEqual(r.paths.map(p => p.cost), exp.costs, name);
  assert.strictEqual(r.warn.length, exp.warn, name);
  console.log('PASS', name, JSON.stringify(r.paths.map(p => [p.name, p.cost])), r.warn.length ? '경고 1' : '');
}
const sc = [[60, 'pass'], [59.99, 'fail'], [100, 'pass'], ['', 'none'], [101, 'invalid'], [-1, 'invalid'], ['abc', 'invalid'], ['0', 'fail']];
for (const [v, e] of sc) assert.strictEqual(S(v), e, String(v));
console.log('PASS 필기 판정 8건 (60 합격, 59.99 불합격, 범위 밖 invalid)');
assert.strictEqual(W(42200), '42,200원'); assert.strictEqual(W(0), '0원'); assert.strictEqual(W(39700), '39,700원');
console.log('PASS 금액 표기');
// UI 렌더 (최소 DOM 스텁): 3톤 미만, 도로, 운전면허 없음, 필기 58
const outP = []; const els = {};
const vals = { 'fl-size': 'lt3', 'fl-use': 'road', 'fl-drv': 'no', 'fl-score': '58' };
const mk = id => ({ value: vals[id] || '', style: {}, addEventListener() {}, set innerHTML(x) { if (id === 'fl-out') outP.length = 0; }, appendChild(p) { if (id === 'fl-out') outP.push(p.textContent); } });
['fl-out', 'fl-size', 'fl-use', 'fl-drv', 'fl-score'].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(3톤 미만·도로·운전면허 없음·필기 58):\n  ' + outP.join('\n  '));
const all = outP.join('|');
assert.ok(all.includes('공식 비용 42,200원'));
assert.ok(all.includes('공식 비용 2,500원'));
assert.ok(all.includes('주의: 시행규칙 제73조제3항'));
assert.ok(all.includes('필기: 60점 미만, 불합격'));
// 본문 예시 문장과 일치
assert.ok(html.includes('기능사 경로 42,200원과 교육 경로 2,500원'));
console.log('ALL PASS');
