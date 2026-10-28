// ko.html의 계산기 <script>를 그대로 뽑아 최소 DOM 스텁으로 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < inside string literal');
for (const m of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) if (m[1].indexOf('&') >= 0) throw new Error('& in a script block');
const ld = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
assert.ok(ld.mainEntity.length >= 6);

function run(vals) {
  const out = [];
  const els = {};
  for (const id of ['ub-w', 'ub-d', 'ub-y', 'ub-cap']) els[id] = { value: vals[id], addEventListener() {} };
  els['ub-50'] = { checked: vals['ub-50'], addEventListener() {} };
  els['ub-out'] = { set innerHTML(v) { out.length = 0; }, set textContent(v) { out.push(v); }, appendChild(p) { out.push(p.textContent); } };
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  return out;
}
const cases = [
  ['기본값 900만/92일 -> 하한액 적용', { 'ub-w': '9000000', 'ub-d': '92', 'ub-y': '2', 'ub-50': false, 'ub-cap': '68100' },
    ['1일 평균임금 97,826원 → 60% 58,695원', '하루 실업급여 66,048원 (하한액 적용(8시간 기준))', '받는 일수 180일', '총액 약 11,888,640원']],
  ['1,200만/92일, 50세 이상 10년 -> 상한액 68,100 x 270', { 'ub-w': '12000000', 'ub-d': '92', 'ub-y': '4', 'ub-50': true, 'ub-cap': '68100' },
    ['1일 평균임금 130,434원 → 60% 78,260원', '하루 실업급여 68,100원 (상한액 적용)', '받는 일수 270일', '총액 약 18,387,000원']],
  ['1,035만/92일 -> 60% 그대로(상·하한 사이)', { 'ub-w': '10350000', 'ub-d': '92', 'ub-y': '0', 'ub-50': false, 'ub-cap': '68100' },
    ['1일 평균임금 112,500원 → 60% 67,500원', '하루 실업급여 67,500원 (평균임금의 60%)', '받는 일수 120일', '총액 약 8,100,000원']],
  ['이전 상한 66,000 선택, 1,200만 -> 상한 66,000', { 'ub-w': '12000000', 'ub-d': '92', 'ub-y': '1', 'ub-50': false, 'ub-cap': '66000' },
    [null, '하루 실업급여 66,000원 (상한액 적용)', '받는 일수 150일', '총액 약 9,900,000원']],
  ['입력 0 -> 안내 문구', { 'ub-w': '0', 'ub-d': '92', 'ub-y': '2', 'ub-50': false, 'ub-cap': '68100' },
    ['3개월 임금과 일수를 넣어 주세요.']],
];
for (const [name, vals, exp] of cases) {
  const out = run(vals);
  exp.forEach((e, i) => { if (e !== null) assert.strictEqual(out[i], e, name + ' line ' + i + ': ' + out[i]); });
  console.log('PASS', name, '|', out.join(' | '));
}
// 총액 예시 표 검산
for (const d of [120, 150, 180, 210, 240, 270]) {
  for (const v of [66048, 68100]) assert.ok(html.includes((v * d).toLocaleString('ko-KR') + '원'), 'table ' + v + 'x' + d);
}
console.log('PASS 총액 표 12칸');
console.log('PASS 조기재취업수당 예시', 66048 * 120 / 2 === 3962880 ? '3,962,880원' : 'FAIL');
