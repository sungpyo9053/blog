// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); console.log('JSON-LD OK, Q', faq.mainEntity.length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.landPermitCheck;
const base = { region: 'seoul', type: 'apt', zone: 'res', area: 30, how: 'buy', foreign: false, tenant: false };
const cases = [
  ['서울 아파트 주거 대지지분 30㎡ -> 허가, 6㎡ 기준', {}, { need: true, threshold: 6, residence: true, period: '2025.10.20.~2026.12.31.' }],
  ['경계: 서울 아파트 6㎡ 딱 -> 면제(초과만 대상)', { area: 6 }, { need: false, threshold: 6 }],
  ['경계: 6.01㎡ -> 허가', { area: 6.01 }, { need: true }],
  ['경기12 아파트 상업지역 15㎡ -> 면제, 15.5 -> 허가', { region: 'gg12', zone: 'com', area: 15 }, { need: false, threshold: 15 }],
  ['경기12 아파트 상업지역 15.5㎡', { region: 'gg12', zone: 'com', area: 15.5 }, { need: true }],
  ['서울 혼재단지 연립 -> 2025-1219', { type: 'mixed' }, { need: true, threshold: 6 }],
  ['서울 일반 빌라 내국인 -> 확인 필요(null), 기본 60', { type: 'villa' }, { need: null, threshold: 60 }],
  ['서울 빌라 외국인 -> 2026-1105, 6㎡', { type: 'villa', foreign: true }, { need: true, threshold: 6, period: '2026.8.26.~2027.8.25.' }],
  ['인천 아파트 외국인 -> 2026-1105', { region: 'incheon', foreign: true }, { need: true }],
  ['그 밖의 지역 외국인 아파트 -> null', { region: 'other', foreign: true }, { need: null }],
  ['서울 토지 외국인 -> null(주택 아님)', { type: 'land', foreign: true }, { need: null, threshold: 60 }],
  ['경매 -> 불필요', { how: 'auction' }, { need: false, residence: false }],
  ['증여 -> 불필요', { how: 'gift' }, { need: false }],
  ['세입자+무주택 -> 유예 특례 안내', { tenant: true }, { need: true, tenantRelief: true }],
  ['도시지역 밖 임야 기본 1000 (지정 미확인)', { region: 'other', type: 'land', zone: 'forest', area: 1200 }, { need: null, threshold: 1000 }],
  ['신청처: 서울 구청장', {}, { where: '토지 소재지 관할 구청장' }],
  ['신청처: 경기', { region: 'gg12' }, { where: '토지 소재지 관할 시장·군수·구청장' }],
];
for (const [name, over, exp] of cases) {
  const r = check(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ need: r.need, threshold: r.threshold, residence: r.residence, tenantRelief: r.tenantRelief }));
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'lt-region': 'seoul', 'lt-type': 'apt', 'lt-zone': 'res', 'lt-area': '30', 'lt-how': 'buy' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lt-out', 'lt-foreign', 'lt-tenant', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('허가 필요'));
