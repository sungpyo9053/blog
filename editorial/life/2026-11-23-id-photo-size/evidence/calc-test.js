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
const c = window.idPhotoCheck;
const cases = [
  ['여권 5/1 촬영 -> 11/1까지, 10/31 신청 가능', ['passport', '2026-05-01', '2026-10-31'], { usable: true, deadline: '2026-11-01', daysLeft: 1 }],
  ['기한 당일 신청 -> 가능, 0일', ['idcard', '2026-05-01', '2026-11-01'], { usable: true, daysLeft: 0 }],
  ['기한 다음 날 -> 불가', ['license-renew', '2026-05-01', '2026-11-02'], { usable: false, deadline: '2026-11-01' }],
  ['8/31 촬영 -> 2/28(말일 보정)', ['passport-online', '2026-08-31', '2027-02-28'], { usable: true, deadline: '2027-02-28' }],
  ['8/31 촬영 -> 3/1 불가', ['intl', '2026-08-31', '2027-03-01'], { usable: false }],
  ['2027-08-31 -> 2028-02-29(윤년)', ['license-test', '2027-08-31', '2028-02-29'], { deadline: '2028-02-29', usable: true }],
  ['연도 넘김 10/15 -> 4/15', ['passport', '2026-10-15', '2027-04-15'], { deadline: '2027-04-15', usable: true, daysLeft: 0 }],
  ['큐넷 -> 기한 미확인 null', ['qnet', '2026-01-01', '2026-10-31'], { usable: null, deadline: '' }],
  ['촬영일이 신청일보다 늦음', ['passport', '2026-11-05', '2026-10-31'], { err: 'future' }],
  ['촬영일 미입력', ['passport', '', '2026-10-31'], { err: 'shot', usable: null }],
  ['없는 서류', ['xx', '2026-01-01', '2026-01-02'], { ok: false }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ usable: r.usable, deadline: r.deadline, daysLeft: r.daysLeft, err: r.err }));
}
// 규격 값 대조 (본문 비교표와 같은지)
assert.ok(c('passport', '2026-10-01', '2026-10-31').info.head.includes('3.2~3.6cm'));
assert.ok(c('passport-online', '2026-10-01', '2026-10-31').info.file.includes('500KB'));
assert.ok(c('license-renew', '2026-10-01', '2026-10-31').info.file.includes('413×세로 531'));
assert.ok(c('idcard', '2026-10-01', '2026-10-31').info.bg.includes('확인하지 못했다'));
assert.strictEqual(c('license-test', '2026-10-01', '2026-10-31').info.count, '3장');
console.log('PASS 규격 값 5개');
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'ip-doc': 'passport', 'ip-shot': '2026-05-20', 'ip-apply': '' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ip-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값(오늘 신청) 출력:', outP.slice(0, 7).join(' | '));
assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(vals['ip-apply']));
assert.ok(outP.join().includes('2026-11-20'));
console.log('PASS UI');
