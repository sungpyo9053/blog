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
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const c = window.incomeCertCheck;
const cases = [
  ['근로 2025 손택스 본인, 10/31 → 가능(5/1)', ['wage', 2025, 'sontax', 'self', '2026-10-31'], { ok: true, ready: true, avail: '2026-05-01', doc: '소득금액증명', time: '즉시' }],
  ['근로 2025 홈택스, 4/30 → 아직(5/1 전)', ['wage', 2025, 'hometax', 'self', '2026-04-30'], { ok: true, ready: false, avail: '2026-05-01' }],
  ['사업 2025 종소세, 6/30 → 아직(7/1)', ['biz', 2025, 'gov24', 'self', '2026-06-30'], { ready: false, avail: '2026-07-01' }],
  ['사업 2026 귀속 → 2027-07-01(6/30 수)', ['biz', 2026, 'office', 'self', '2027-07-01'], { ok: true, ready: true, avail: '2027-07-01' }],
  ['사업 2028 귀속 → 6/30 토 → 7/3', ['biz', 2028, 'office', 'self', '2029-07-02'], { ready: false, avail: '2029-07-03' }],
  ['사업 2029 귀속 → 6/30 일 → 7/2', ['biz', 2029, 'office', 'self', '2030-07-02'], { ready: true, avail: '2030-07-02' }],
  ['올해 2026 귀속 → 불가', ['wage', 2026, 'hometax', 'self', '2026-10-31'], { ok: false, ready: false }],
  ['대리 + 정부24 → 불가', ['wage', 2025, 'gov24', 'proxy', '2026-10-31'], { ok: false }],
  ['대리 + 무인발급기 → 불가', ['wage', 2025, 'kiosk', 'proxy', '2026-10-31'], { ok: false }],
  ['대리 + 세무서 → 가능, 위임장', ['wage', 2025, 'office', 'proxy', '2026-10-31'], { ok: true, ready: true }],
  ['주민센터 → 3시간 이내', ['yeother', 2025, 'center', 'self', '2026-10-31'], { ok: true }],
  ['기한후신고 → 날짜 없음, 결정 뒤', ['late', 2025, 'office', 'self', '2026-10-31'], { ok: true, ready: null, avail: '' }],
  ['무소득 2025 손택스 10/31 → 사실증명 가능', ['none', 2025, 'sontax', 'self', '2026-10-31'], { ok: true, ready: true, doc: '사실증명(신고사실없음)', avail: '2026-07-01' }],
  ['무소득 2025 6/1 → 아직(7월 이후)', ['none', 2025, 'hometax', 'self', '2026-06-01'], { ready: false }],
  ['무소득 + 무인발급기 → 불가', ['none', 2025, 'kiosk', 'self', '2026-10-31'], { ok: false }],
  ['무소득 + 정부24 → 확인 필요', ['none', 2025, 'gov24', 'self', '2026-10-31'], { ok: null }],
  ['1980 귀속 → 불가(1983년까지)', ['wage', 1980, 'office', 'self', '2026-10-31'], { ok: false }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, '|', r.when, '|', r.time.slice(0, 20), '|', r.notes.length + '개 참고');
}
assert.ok(c('wage', 2025, 'office', 'proxy', '2026-10-31').prep.includes('위임장'));
assert.ok(c('yeother', 2025, 'center', 'self', '2026-10-31').time.includes('3시간'));
assert.ok(c('none', 2025, 'hometax', 'self', '2026-10-31').time.includes('3시간'));
assert.ok(c('wageplus', 2025, 'sontax', 'self', '2026-10-31').notes[0].includes('2026년 7월 1일'));
console.log('PASS 준비물·처리·합산신고 문구');
// UI 렌더(최소 DOM 스텁)
const vals = { 'ic-type': 'wage', 'ic-year': '', 'ic-method': 'hometax', 'ic-who': 'self', 'ic-date': '' };
const outP = []; const opts = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {},
  set innerHTML(v) { outP.length = 0; }, appendChild(o) { if (id === 'ic-out') outP.push(o.textContent); else { opts.push(o); if (o.selected) vals['ic-year'] = String(o.value); } } });
const els = {}; ['ic-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 연도 선택지', opts.length, '개, 기본값', vals['ic-year']);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].startsWith('판정: '));
