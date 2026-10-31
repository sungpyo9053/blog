// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.matchAll(/'([^'\\]|\\.)*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD FAQ', faq.mainEntity.length, '개');
const faqH3 = (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length;
assert.strictEqual(faqH3, faq.mainEntity.length, 'FAQ h3 수와 JSON-LD 수 불일치');
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const c = window.bizRegCheck;
const base = { purpose: 'new', form: 'indiv', method: 'hometax', who: 'self', rent: true, license: false, partner: false, start: '', today: '', sales: '', presales: '', taxType: 'general' };
const run = o => c(Object.assign({}, base, o));
const cases = [
  ['신규 개인 홈택스: 2일, 수수료 없음', {}, { ok: true, fee: '없음' }],
  ['개시 11/2(월) → +20 = 11/22(일) → 11/23(월)', { start: '2026-11-02', today: '2026-11-20' }, { deadline: '2026-11-23', late: false }],
  ['개시 11/3(화) → 11/23(월) 그대로', { start: '2026-11-03', today: '2026-11-23' }, { deadline: '2026-11-23', late: false }],
  ['개시 11/1(일) → 11/21(토) → 11/23(월)', { start: '2026-11-01', today: '2026-11-24' }, { deadline: '2026-11-23', late: true }],
  ['지연 일반 600만 → 6만', { start: '2026-11-02', today: '2026-12-15', presales: 6000000, taxType: 'general' }, { late: true, penalty: 60000 }],
  ['지연 간이 600만 → 3만', { start: '2026-11-02', today: '2026-12-15', presales: 6000000, taxType: 'simple' }, { penalty: 30000 }],
  ['지연 납부면제 간이 600만 → 최소 5만', { start: '2026-11-02', today: '2026-12-15', presales: 6000000, taxType: 'exempt' }, { penalty: 50000 }],
  ['지연 납부면제 간이 2,000만 → 10만', { start: '2026-11-02', today: '2026-12-15', presales: 20000000, taxType: 'exempt' }, { penalty: 100000 }],
  ['지연 법인은 유형 무관 1%', { form: 'corp', start: '2026-11-02', today: '2026-12-15', presales: 6000000, taxType: 'simple' }, { penalty: 60000 }],
  ['기한 안이면 가산세 0', { start: '2026-11-02', today: '2026-11-23', presales: 6000000 }, { late: false, penalty: 0 }],
  ['신규 + 무인발급기 → 불가', { method: 'kiosk' }, { ok: false }],
  ['신규 + 정부24 → 불가', { method: 'gov24' }, { ok: false }],
  ['신규 + 행정복지센터 → 확인 못함', { method: 'center' }, { ok: null }],
  ['재발급 + 손택스 → 불가(규정 제58조)', { purpose: 'reissue', method: 'sontax' }, { ok: false }],
  ['재발급 + 홈택스 → 가능', { purpose: 'reissue', method: 'hometax' }, { ok: true }],
  ['재발급 + 세무서 → 가능', { purpose: 'reissue', method: 'office' }, { ok: true }],
  ['재발급 + 무인발급기 → 확인 못함', { purpose: 'reissue', method: 'kiosk' }, { ok: null }],
  ['재발급 + 홈택스 대리 → 불가', { purpose: 'reissue', method: 'hometax', who: 'proxy' }, { ok: false }],
  ['증명 + 무인발급기 → 즉시', { purpose: 'proof', method: 'kiosk' }, { ok: true, time: '즉시' }],
  ['증명 + 손택스 → 즉시', { purpose: 'proof', method: 'sontax' }, { ok: true, time: '즉시' }],
  ['증명 + 정부24 대리 → 불가', { purpose: 'proof', method: 'gov24', who: 'proxy' }, { ok: false }],
  ['증명 + 세무서 대리 → 가능', { purpose: 'proof', method: 'office', who: 'proxy' }, { ok: true }],
];
for (const [name, o, exp] of cases) {
  const r = run(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, '|', r.deadline || '-', '|', r.penalty, '|', r.time.slice(0, 24));
}
// 준비물·과세유형 문구
let r = run({ rent: true, license: true, partner: true });
assert.ok(r.prep.some(s => s.includes('임대차계약서')) && r.prep.some(s => s.includes('허가')) && r.prep.some(s => s.includes('동업계약서')));
r = run({ rent: false }); assert.ok(!r.prep.some(s => s.includes('임대차계약서')));
r = run({ form: 'corp' }); assert.ok(r.prep.includes('주주 또는 출자자 명세서') && r.prep.includes('정관') && r.type.includes('일반과세자'));
r = run({ sales: 10400 }); assert.ok(r.type.includes('일반과세자로 등록해야'));
r = run({ sales: 10399 }); assert.ok(r.type.includes('간이과세자로 신청할 수 있다'));
r = run({ sales: 4000 }); assert.ok(r.notes.some(s => s.includes('4,800만 원 미만')));
r = run({ purpose: 'proof', method: 'office', who: 'proxy', form: 'corp' }); assert.ok(r.prep.includes('위임장') && r.prep.some(s => s.includes('인감증명서')));
r = run({ purpose: 'proof', method: 'center' }); assert.ok(r.time.includes('3시간'));
console.log('PASS 준비물·과세유형·대리 문구');
// UI 렌더(최소 DOM 스텁)
const vals = { 'cr-purpose': 'new', 'cr-form': 'indiv', 'cr-method': 'hometax', 'cr-who': 'self', 'cr-start': '2026-11-02', 'cr-today': '', 'cr-sales': '6000', 'cr-presales': '', 'cr-taxtype': 'general' };
const checks = { 'cr-rent': true, 'cr-license': false, 'cr-partner': false };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, get checked() { return checks[id]; }, style: {}, addEventListener() {},
  set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cr-out', 'cr-newbox', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2026년 11월 23일(월)'));
assert.ok(outP.join().includes('간이과세자로 신청할 수 있다'));
console.log('ALL PASS');
