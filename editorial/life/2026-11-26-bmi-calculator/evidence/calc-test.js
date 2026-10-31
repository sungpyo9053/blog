// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.mainEntity.length, h3faq);
console.log('PASS JSON-LD 파싱, FAQ', h3faq, '개 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.bmiCalc;
const cases = [
  ['학회 예: 170cm 70kg -> 24.2 비만 전 단계', 170, 70, '', NaN, { bmi: 24.2, ksso: '비만 전 단계', who: '정상 범위', checkup: '정상A', abdominal: null, risk: null }],
  ['경계 18.5 정상', 160, 47.36, '', NaN, { bmi: 18.5, ksso: '정상', checkup: '정상A' }],
  ['18.4 저체중, 검진 정상B', 160, 47.1, '', NaN, { bmi: 18.4, ksso: '저체중', who: '저체중', checkup: '정상B(경계)' }],
  ['경계 23.0 비만 전 단계', 170, 66.47, '', NaN, { bmi: 23, ksso: '비만 전 단계' }],
  ['22.96은 23.0으로 반올림돼 비만 전 단계(학회 표 빈틈 제거)', 100, 22.96, '', NaN, { bmi: 23, ksso: '비만 전 단계' }],
  ['경계 25.0 1단계, WHO 과체중, 검진 정상B', 170, 72.25, '', NaN, { bmi: 25, ksso: '1단계 비만', who: '과체중', checkup: '정상B(경계)' }],
  ['30.0 2단계, WHO 비만, 검진 질환의심', 170, 86.7, '', NaN, { bmi: 30, ksso: '2단계 비만', who: '비만', checkup: '질환의심' }],
  ['35.0 3단계', 170, 101.15, '', NaN, { bmi: 35, ksso: '3단계 비만(고도비만)' }],
  ['남 90cm 이상 + 정상 -> 약간 높음', 175, 65, 'M', 90, { ksso: '정상', abdominal: true, risk: '약간 높음' }],
  ['남 89.9cm + 정상 -> 보통', 175, 65, 'M', 89.9, { abdominal: false, risk: '보통' }],
  ['여 85cm + 1단계 -> 매우 높음', 160, 66, 'F', 85, { ksso: '1단계 비만', abdominal: true, risk: '매우 높음' }],
  ['여 84.9cm + 2단계 -> 매우 높음', 160, 80, 'F', 84.9, { ksso: '2단계 비만', abdominal: false, risk: '매우 높음' }],
  ['저체중 + 허리 미만 -> 낮음', 170, 50, 'F', 70, { ksso: '저체중', risk: '낮음' }],
  ['3단계는 허리 무관 가장 높음', 160, 95, 'F', 80, { ksso: '3단계 비만(고도비만)', risk: '가장 높음' }],
  ['성별 없이 허리만 -> 판정 없음', 170, 70, '', 95, { abdominal: null, risk: null }],
];
for (const [name, h, w, sex, waist, exp] of cases) {
  const r = calc(h, w, sex, waist);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 키별 정상 체중 표 값 검산 (ko.html 표와 대조)
const table = html.split('<h2 id="range">')[1].split('</table>')[0];
for (let h = 150; h <= 190; h += 5) {
  const r = calc(h, 60, '', NaN);
  const row = r.normalMin.toFixed(1) + '~' + r.normalMax.toFixed(1) + 'kg</td><td>' + r.obeseFrom.toFixed(1) + 'kg';
  assert.ok(table.includes('<td>' + h + 'cm</td><td>' + row), h + 'cm row ' + row);
  const b30 = Math.round(30 * (h / 100) ** 2 * 10) / 10;
  assert.ok(table.includes(b30.toFixed(1) + 'kg</td></tr>'), h + ' bmi30 ' + b30);
}
console.log('PASS 키별 표 9행');
// UI 기본값(170cm 70kg) 렌더 확인 — 최소 DOM 스텁
const vals = { 'bmi-h': '170', 'bmi-w': '70', 'bmi-sex': 'M', 'bmi-waist': '92' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['bmi-out', 'bmi-btn', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(170/70/남/92):', outP.join(' | '));
assert.ok(outP.join().includes('24.2'));
assert.ok(outP.join().includes('높음'));
vals['bmi-h'] = '50';
eval(src);
console.log('UI 오류 입력:', outP.join(' | '));
assert.ok(outP[0].includes('100~250'));
