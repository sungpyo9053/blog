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
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(h3faq, faq.mainEntity.length, 'FAQ h3 수와 JSON-LD 수 불일치');
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const c = window.hpcCheck;
const C = (type, purpose, method, who, senior) => c({ type, purpose, method, who, senior: !!senior });
const cases = [
  ['직장 복지 홈페이지 본인 → 납부확인서 가능', ['work', 'welfare', 'homepage', 'self'], { ok: true, doc: '보험료 납부확인서' }],
  ['지역 대출 앱 본인 → 가능', ['region', 'loan', 'app', 'self'], { ok: true, doc: '보험료 납부확인서' }],
  ['지역 복지 정부24 → 가능', ['region', 'welfare', 'gov24', 'self'], { ok: true }],
  ['지역 복지 무인발급기 → 가능', ['region', 'welfare', 'kiosk', 'self'], { ok: true }],
  ['피부양자 복지 → 납부확인서 불가', ['dependent', 'welfare', 'homepage', 'self'], { ok: false, doc: '보험료 납부확인서' }],
  ['피부양자 가입기간 → 자격득실 가능', ['dependent', 'history', 'app', 'self'], { ok: true, doc: '건강보험 자격득실확인서' }],
  ['피부양자 계약 → 완납 확인 필요', ['dependent', 'contract', 'branch', 'self'], { ok: null, doc: '보험료 완납증명서' }],
  ['계약 홈페이지 → 완납증명서 가능', ['work', 'contract', 'homepage', 'self'], { ok: true, doc: '보험료 완납증명서' }],
  ['완납 + 정부24 → 확인 필요', ['region', 'contract', 'gov24', 'self'], { ok: null }],
  ['자격득실 + 무인발급기 → 확인 필요', ['work', 'history', 'kiosk', 'self'], { ok: null }],
  ['대리 + 지사 + 납부확인서 → 가능, 위임장', ['region', 'welfare', 'branch', 'proxy'], { ok: true, prep: '발급대상자 신분증(사본), 대리인 신분증, 위임장' }],
  ['대리 + 홈페이지 → 불가', ['work', 'welfare', 'homepage', 'proxy'], { ok: false }],
  ['대리 + ARS → 불가', ['region', 'loan', 'ars', 'proxy'], { ok: false }],
  ['대리 + 지사 + 자격득실 → 확인 필요', ['work', 'history', 'branch', 'proxy'], { ok: null }],
  ['ARS 일반 → 디지털ARS 셀프', ['region', 'loan', 'ars', 'self', false], { ok: true, route: '1577-1000 디지털ARS 셀프 발급' }],
  ['ARS 65세 → 상담사 팩스', ['region', 'loan', 'ars', 'self', true], { ok: true, route: '1577-1000 고객센터 상담사 연결 후 팩스 발급' }],
];
for (const [name, args, exp] of cases) {
  const r = C(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, '|', r.route, '|', r.notes.length + '개 참고');
}
const has = (r, s) => r.notes.some(n => n.includes(s));
assert.ok(has(C('region', 'loan', 'ars', 'self'), '3개월, 6개월, 1년, 이전년도 전체'));
assert.ok(has(C('work', 'yearend', 'homepage', 'self'), '제52조'));
assert.ok(has(C('region', 'yearend', 'homepage', 'self'), '근로자가 부담하는 보험료만'));
assert.ok(has(C('work', 'welfare', 'app', 'self'), '보수 외 소득월액'));
assert.ok(!has(C('region', 'welfare', 'app', 'self'), '보수 외 소득월액'));
assert.ok(has(C('region', 'welfare', 'app', 'self'), '직전월'));
assert.ok(has(C('work', 'contract', 'homepage', 'self'), '제81조의4'));
assert.ok(C('work', 'welfare', 'homepage', 'self').fee.includes('확인하지 못했다'));
console.log('PASS 기간·연말정산·보수외소득·복지·계약·수수료 문구');
// UI 렌더(최소 DOM 스텁)
const vals = { 'hpc-type': 'work', 'hpc-purpose': 'welfare', 'hpc-method': 'homepage', 'hpc-who': 'self' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, checked: false, style: {}, addEventListener() {},
  set innerHTML(v) { outP.length = 0; }, appendChild(o) { outP.push(o.textContent); } });
const els = {}; ['hpc-out', 'hpc-senior', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].startsWith('판정: '));
console.log('ALL PASS');
