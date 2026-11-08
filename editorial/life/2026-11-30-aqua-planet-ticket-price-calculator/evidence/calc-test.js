// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.length, h3faq, 'FAQ JSON-LD count');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.aquaPlanetCalc;
const C = (a, y, c, s, i) => ({ adult: a, youth: y, child: c, senior: s, infant: i || 0 });
const cases = [
  // name, branch, cnt, ticket, disc, day total
  ['여수 부부+초등1 정상가', 'yeosu', C(2, 0, 1, 0), 'day', 'none', 108700],
  ['여수 부부+초등1 시민 25%', 'yeosu', C(2, 0, 1, 0), 'day', 'local', 81525],
  ['여수 부부+초등1 문화누리 26,000', 'yeosu', C(2, 0, 1, 0), 'day', 'nuri', 78000],
  ['여수 대인5 문화누리(4인 한도)', 'yeosu', C(5, 0, 0, 0), 'day', 'nuri', 26000 * 4 + 37900],
  ['여수 청소년1+경로1', 'yeosu', C(0, 1, 0, 1), 'day', 'none', 69800],
  ['일산 부부+어린이1 정상가', 'ilsan', C(2, 0, 1, 0), 'day', 'none', 101500],
  ['일산 부부+어린이1 문화누리 30% 정상가 기준', 'ilsan', C(2, 0, 1, 0), 'day', 'nuri', 73500],
  ['일산 중학생1(정상가)', 'ilsan', C(0, 1, 0, 0), 'day', 'none', 35000],
  ['제주 3대 가족 5인', 'jeju', C(2, 0, 1, 2), 'day', 'fam3', 182000],
  ['제주 3대 가족 정상가', 'jeju', C(2, 0, 1, 2), 'day', 'none', 219600],
  ['제주 도민 5인', 'jeju', C(2, 0, 1, 2), 'day', 'dom', 153720],
  ['제주 4대 가족 1인', 'jeju', C(1, 0, 0, 0), 'day', 'fam4', 34125],
  ['제주 문화누리(1명)', 'jeju', C(2, 0, 0, 0), 'day', 'nuri', 31850 + 45500],
  ['광교 부부+어린이2 정상가', 'gwanggyo', C(2, 0, 2, 0), 'day', 'none', 114000],
  ['광교 부부+어린이2 문화누리 40%', 'gwanggyo', C(2, 0, 2, 0), 'day', 'nuri', 72000],
  ['광교 장애 어린이+부모1 30%(할인가 중복)', 'gwanggyo', C(1, 0, 1, 0), 'day', 'welfare', 21000 + 18900],
  ['광교 경로1 소방 20%(정상가 기준 24,000이 할인가보다 쌈)', 'gwanggyo', C(0, 0, 0, 1), 'day', 'fire', 24000],
  ['음수·빈값 방어', 'yeosu', C(-3, '', 'x', 0), 'day', 'none', 0],
];
for (const [name, br, cnt, t, d, exp] of cases) {
  const r = calc(br, cnt, t, d, 1);
  assert.strictEqual(r.day, exp, name + ' day=' + r.day);
  console.log('PASS', name, r.day.toLocaleString('ko-KR') + '원');
}
// 연간이용권 본전(대인 1명 정상가)
const be = [['yeosu', 'new', 4], ['yeosu', 'renew', 3], ['ilsan', 'new', 4], ['ilsan', 'pm', 3], ['jeju', 'new', 4], ['gwanggyo', 'new', 6], ['gwanggyo', 'renew', 4]];
for (const [br, t, k] of be) {
  const r = calc(br, C(1, 0, 0, 0), t, 'none', 1);
  assert.strictEqual(r.breakEven, k, br + ' ' + t + ' breakEven=' + r.breakEven);
  console.log('PASS 본전', br, t, r.annual.toLocaleString('ko-KR') + '원', k + '번째');
}
assert.strictEqual(calc('gwanggyo', C(0, 0, 0, 1), 'senior', 'none', 1).breakEven, 3);
console.log('PASS 광교 시니어 66,000원 vs 27,000원 3번째');
assert.strictEqual(calc('jeju', C(2, 0, 1, 0), 'new', 'none', 2).annual, 495000);
console.log('PASS 제주 AQ권 3명 495,000원');
// UI 기본값 렌더
const vals = { 'ap-branch': 'yeosu', 'ap-ticket': 'day', 'ap-adult': '2', 'ap-youth': '0', 'ap-child': '1', 'ap-senior': '0', 'ap-infant': '1', 'ap-disc': 'none', 'ap-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {}, set innerHTML(v) {}, appendChild() {} });
els['ap-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('108,700원'));
assert.ok(outP[1].includes('무료'));
console.log('ALL PASS');
