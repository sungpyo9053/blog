// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const s of src.match(/'(?:[^'\\]|\\.)*'/g) || []) if (s.indexOf('<') >= 0) throw new Error('< in string literal: ' + s);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.youthTomorrowCalc;
const cases = [
  ['복지부: 차상위 이하 10만 x 36 만기 = 1,440만', 30, 10, 36, 'full', { own: 3600000, gov: 10800000, total: 14400000 }],
  ['지침: 차상위 초과 10만 x 36 만기 = 720만', 10, 10, 36, 'full', { own: 3600000, gov: 3600000, total: 7200000 }],
  ['정액: 50만 x 36 차상위 이하 = 2,880만', 30, 50, 36, 'full', { own: 18000000, gov: 10800000, total: 28800000 }],
  ['표: 20만 x 36 차상위 이하 = 1,800만', 30, 20, 36, 'full', { total: 18000000 }],
  ['표: 30만 x 36 차상위 초과 = 1,440만', 10, 30, 36, 'full', { total: 14400000 }],
  ['본문 예: 10만 x 20 본인 요청 환수 = 200만, 지원금 600만 환수', 30, 10, 20, 'refund', { own: 2000000, gov: 6000000, total: 2000000, mode: 'refund' }],
  ['만기 24개월(적립중지 12개월) = 지급', 30, 10, 24, 'full', { total: 9600000, forcedRefund: false }],
  ['만기 23개월 -> 누적 12개월 미납, 환수', 30, 10, 23, 'full', { total: 2300000, forcedRefund: true, mode: 'refund' }],
  ['중도지급 10개월 -> 교육 4시간', 30, 10, 10, 'early', { total: 4000000, eduHours: 4 }],
  ['중도지급 18개월 -> 교육 7시간', 30, 10, 18, 'early', { total: 7200000, eduHours: 7 }],
  ['중도지급 30개월 -> 교육 10시간', 30, 10, 30, 'early', { total: 12000000, eduHours: 10 }],
  ['상한: 60만 -> 50만, 40개월 -> 36', 30, 60, 40, 'full', { own: 18000000, months: 36, total: 28800000 }],
];
for (const [name, match, save, months, end, exp] of cases) {
  const r = calc(match, save, months, end);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(차상위 이하, 10만, 36개월, 만기) 렌더 확인 — 최소 DOM 스텁
const vals = { 'yt-type': '30', 'yt-save': '10', 'yt-months': '36', 'yt-end': 'full' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['yt-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('14,400,000원'));
console.log('ALL PASS');
