// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
assert.strictEqual(scripts.length, 1);
const src = scripts[0];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length;
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.namiCalc;
const O = x => Object.assign({ season: 'winter', route: 'ferry', time: 'normal', buy: 'site', adult: 0, teen: 0, senior: 0, merit: 0, kid: 0, baby: 0, zipf: 0, zipa: 0, park: 'none' }, x);
const has = (r, s) => r.warn.some(w => w.includes(s));
const cases = [
  ['요금표 일반선박 1명씩', O({ adult: 1, teen: 1, senior: 1, merit: 1, kid: 1 }), { ticket: 19000 + 16000 * 3 + 13000 }],
  ['요금표 모터보트 현장 1명씩', O({ route: 'motor', season: 'summer', adult: 1, teen: 1, senior: 1, merit: 1, kid: 1 }), { ticket: 29000 + 26000 * 3 + 23000 }],
  ['모터보트 온라인 성인 26,000', O({ route: 'motor', season: 'summer', buy: 'online', adult: 2, kid: 1 }), { total: 26000 * 2 + 23000 }, r => assert.ok(has(r, '중복'))],
  ['예시1 부부+초등1+아기1 + 소형주차', O({ adult: 2, kid: 1, baby: 1, park: 'small' }), { ticket: 51000, total: 57000, people: 4 }],
  ['예시2 겨울 야간 2명', O({ adult: 2, time: 'special' }), { total: 26000 }, r => assert.ok(has(r, '18:01'))],
  ['예시3 짚와이어 패밀리 2 + 70세 1', O({ zipf: 2, senior: 1 }), { total: 126000, zip: 110000 }, r => assert.ok(has(r, '140'))],
  ['짚와이어 어드벤처 58,000', O({ zipa: 1 }), { total: 58000, ticket: 0 }],
  ['단체 성인 20명 10%', O({ adult: 20 }), { ticket: 380000, group: 38000, total: 342000 }],
  ['19명은 단체 아님', O({ adult: 19 }), { group: 0, total: 361000 }],
  ['단체+야간은 중복 안 함', O({ adult: 20, time: 'special' }), { group: 0, total: 260000 }],
  ['모터보트 단체 할인 없음', O({ route: 'motor', season: 'summer', adult: 20 }), { group: 0, total: 580000 }],
  ['모터보트+야간 → 모터보트 요금', O({ route: 'motor', season: 'summer', time: 'special', adult: 2 }), { total: 58000 }, r => assert.ok(has(r, '일반선박 입출도에만'))],
  ['모터보트 1명 경고, 겨울 경고', O({ route: 'motor', adult: 1 }), { total: 29000 }, r => { assert.ok(has(r, '2인 이상')); assert.ok(has(r, '11월 29일')); }],
  ['온라인 70세 → 현장 유인창구 안내', O({ buy: 'online', senior: 1 }), { total: 16000 }, r => assert.ok(has(r, '유인창구'))],
  ['카카오T 대형 6,000', O({ adult: 1, park: 'largeK' }), { total: 25000 }],
  ['아기만 → 보호자 경고', O({ baby: 1 }), { total: 0 }, r => assert.ok(has(r, '보호자'))],
  ['인원 0 → 오류', O({}), { ok: false }],
];
for (const [name, o, exp, extra] of cases) {
  const r = calc(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  if (extra) extra(r);
  console.log('PASS', name, r.ok === false ? r.msg : JSON.stringify({ ticket: r.ticket, group: r.group, zip: r.zip, park: r.park, total: r.total }));
}
// 본문 요금표 숫자와 evidence 원문 대조
const ev = fs.readFileSync(path.join(__dirname, 'namisum-276-admission-fees.txt'), 'utf8');
for (const v of ['19,000', '29,000', '16,000', '26,000', '13,000', '23,000', '69,000', '98,000', '72,000', '59,000']) assert.ok(ev.includes('￦' + v), v);
const zw = fs.readFileSync(path.join(__dirname, 'namisum-288-zipwire-sky.txt'), 'utf8');
assert.ok(zw.includes('￦55,000') && zw.includes('￦58,000'));
console.log('PASS evidence 요금 12개 대조');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'nm-season': 'winter', 'nm-route': 'ferry', 'nm-time': 'normal', 'nm-buy': 'site', 'nm-adult': '2', 'nm-teen': '0', 'nm-senior': '0', 'nm-merit': '0', 'nm-kid': '1', 'nm-baby': '0', 'nm-zipf': '0', 'nm-zipa': '0', 'nm-park': 'small' };
const out = [];
const mk = () => ({ children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { this._t = v; }, get textContent() { return this._t || this.children.map(c => c.textContent).join(''); } });
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['nm-out'] = { set innerHTML(v) { out.length = 0; }, appendChild(p) { out.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
console.log('UI 기본값 출력:\n  ' + out.join('\n  '));
assert.ok(out.join().includes('합계 57,000원'));
const vis = html.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, '').replace(/\s+/g, '');
const h2 = (html.match(/<h2/g) || []).length, h3 = (html.match(/<h3/g) || []).length;
console.log('visible chars(공백 제외):', vis.length, 'H2:', h2, 'H3:', h3, 'FAQ JSON-LD:', faqN);
