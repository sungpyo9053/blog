// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.pcCostCalc;
const cases = [
  ['전국 일반실 평균 373만원 14일', [373, 14, 0, 0, 0, 0], { daily: 266429, base: 3730000, total: 3730000, pay: 3730000 }],
  ['전남 공공 2주 160만원 (목포·여수 표 1,600천원)', [160, 14, 0, 0, 0, 0], { base: 1600000 }],
  ['전남 공공 1주 (표 800천원)', [160, 7, 0, 0, 0, 0], { base: 800000 }],
  ['전남 공공 4주 (표 3,200천원)', [160, 28, 0, 0, 0, 0], { base: 3200000 }],
  ['전남 공공 70% 감면 2주 (표 480천원)', [160, 14, 0, 70, 0, 0], { afterDisc: 480000, pay: 480000 }],
  ['전남 공공 70% 감면 4주 (표 960천원)', [160, 28, 0, 70, 0, 0], { afterDisc: 960000 }],
  ['서울형 안심 일반 산모 390-140=250', [390, 14, 0, 0, 0, 140], { pay: 2500000 }],
  ['서울형 안심 2순위 390-265=125', [390, 14, 0, 0, 0, 265], { pay: 1250000 }],
  ['서울형 안심 1순위 100% 감면', [390, 14, 0, 100, 0, 0], { pay: 0 }],
  ['예시1 경기 366만원 14일 첫째 200', [366, 14, 0, 0, 200, 0], { pay: 1660000, voucherUsed: 2000000 }],
  ['예시1 경기 366만원 12일 첫째 200', [366, 12, 0, 0, 200, 0], { daily: 261429, base: 3137143, pay: 1137143 }],
  ['예시2 전남 공공 둘째 300 -> 48만원만 사용', [160, 14, 0, 70, 300, 0], { voucherUsed: 480000, pay: 0 }],
  ['예시3 서울 특실 808 + 부가 50, 첫째 200', [808, 14, 50, 0, 200, 0], { total: 8580000, pay: 6580000 }],
  ['FAQ 373만원 10일 약 266만원', [373, 10, 0, 0, 0, 0], { base: 2664286 }],
  ['감면은 부가서비스에 적용 안 함', [200, 14, 30, 50, 0, 0], { afterDisc: 1000000, total: 1300000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표·계산기 프리셋이 원자료 집계(evidence/sido-summary.txt)와 같은지
const sum = fs.readFileSync(path.join(__dirname, 'sido-summary.txt'), 'utf8').trim().split('\n');
const avg = window.pcAvg; let n = 0;
for (const line of sum) {
  const m = line.match(/^(\S+) (\d+) \((\d+), (\d+), (\d+)\) \((\d+), ([\d-]+), ([\d-]+)\)/);
  if (!m) continue;
  const key = m[1] === '전체' ? '전국' : m[1];
  assert.deepStrictEqual(avg[key], [+m[4], +m[7]], key);
  assert.ok(html.includes('<td>' + key + '</td><td>' + m[4] + ' (' + m[3] + ')</td><td>' + m[5] + '</td><td>' + m[7] + ' (' + m[6] + ')</td>'), '표 ' + key);
  n++;
}
console.log('PASS 시도 프리셋·표 ' + n + '개 원자료 집계와 일치');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'pc-region': '전국', 'pc-room': '0', 'pc-fee': '373', 'pc-days': '14', 'pc-extra': '0', 'pc-disc': '0', 'pc-voucher': '200', 'pc-other': '0' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener(t, f) { this['on' + t] = f; }, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['pc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(전국 일반실, 첫째):', outP.join(' | '));
assert.ok(outP.join().includes('본인 부담: 1,730,000원'));
vals['pc-region'] = '서울'; vals['pc-room'] = '1'; els['pc-room'].onchange();
console.log('UI 서울 특실 선택:', outP.join(' | '));
assert.strictEqual(vals['pc-fee'], '808');
assert.ok(outP.join().includes('본인 부담: 6,080,000원'));
