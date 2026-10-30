// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검증
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.socialWorkerCheck;
const cases = [
  ['학사 신기준 10/7/160 -> 충족, 1급 바로', ['ba', 'new', 10, 7, 160, 0], { ok: true, level1: 'direct' }],
  ['학사 신기준 10/6/160 -> 선택 1 부족', ['ba', 'new', 10, 6, 160, 0], { ok: false, gapElec: 1, gapReq: 0, gapHours: 0 }],
  ['학사 신기준 실습 159h -> 1시간 부족', ['ba', 'new', 10, 7, 159, 0], { ok: false, gapHours: 1 }],
  ['학사 구기준 10/4/120 -> 충족', ['ba', 'old', 10, 4, 120, 0], { ok: true, needElec: 4, needHours: 120 }],
  ['학사 구기준 10/3/100 -> 선택1·20h 부족', ['ba', 'old', 10, 3, 100, 0], { ok: false, gapElec: 1, gapHours: 20 }],
  ['전문학사 10/7/160 -> 충족, 1급은 실무1년', ['as', 'new', 10, 7, 160, 0], { ok: true, level1: 'exp' }],
  ['고졸 과목 다 채움 -> 학위 없어 미충족', ['hs', 'new', 10, 7, 160, 0], { ok: false, degree: false, gapReq: 0, gapElec: 0 }],
  ['기본값 8/5/0 -> 필수2 선택2 실습160', ['ba', 'new', 8, 5, 0, 0], { gapReq: 2, gapElec: 2, gapHours: 160 }],
  ['석사 6/2/160 대학원4 -> 충족', ['ma_sw', 'new', 6, 2, 160, 4], { ok: true, needReq: 6, needElec: 2 }],
  ['석사 대학원 필수 3 -> 1 부족', ['ma_sw', 'new', 6, 2, 160, 3], { ok: false, gapGrad: 1 }],
  ['석사 구기준 선택2 유지·실습120', ['ma_sw', 'old', 6, 2, 120, 4], { ok: true, needElec: 2, needHours: 120 }],
  ['박사 -> 과목 무관 충족', ['phd', 'new', 0, 0, 0, 0], { ok: true, level1: 'direct' }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ ok: r.ok, gapReq: r.gapReq, gapElec: r.gapElec, gapHours: r.gapHours, gapGrad: r.gapGrad, level1: r.level1 }));
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'sw-edu': 'ba', 'sw-start': 'new', 'sw-req': '8', 'sw-elec': '5', 'sw-hours': '0', 'sw-grad': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sw-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('부족분: 필수 2과목, 선택 2과목, 현장실습 160시간'));
console.log('ALL PASS');
