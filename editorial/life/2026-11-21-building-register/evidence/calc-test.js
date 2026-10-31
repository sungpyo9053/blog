// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= FAQ h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.buildingRegisterCheck;
const cases = [
  ['아파트 계약 전 정부24 -> 표제부+전유부 무료', ['unit', 'check', 'gov24'], { action: 'issue', count: 2, fee: 0, route: 'gov24' }],
  ['아파트 계약 전 창구 -> 열람 300x2=600', ['unit', 'check', 'visit'], { action: 'view', unit: 300, count: 2, fee: 600 }],
  ['아파트 제출 창구 -> 발급 500x1', ['unit', 'submit', 'visit'], { action: 'issue', unit: 500, count: 1, fee: 500 }],
  ['단독 제출 세움터 -> 무료', ['single', 'submit', 'eais'], { action: 'issue', fee: 0, count: 1 }],
  ['단독 계약 전 창구 -> 열람 300', ['single', 'check', 'visit'], { action: 'view', fee: 300 }],
  ['다가구 계약 전 창구 -> 일반 1건 300 + 면적대장 안내', ['dagagu', 'check', 'visit'], { fee: 300, count: 1 }],
  ['무인발급기 -> 수수료 미확인(-1)', ['unit', 'submit', 'kiosk'], { fee: -1 }],
  ['평면도 정부24 선택 -> 세움터로 전환, 수수료 미확인', ['unit', 'plan', 'gov24'], { route: 'eais', fee: -1 }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ docs: r.docs, action: r.action, route: r.route, unit: r.unit, count: r.count, fee: r.fee }));
}
assert.ok(c('dagagu', 'check', 'visit').notes.join().includes('면적대장'));
assert.ok(c('dagagu', 'check', 'gov24').notes.join().includes('가구수'));
assert.ok(c('unit', 'plan', 'visit').notes.join().includes('임차인'));
assert.ok(c('unit', 'check', 'visit').notes.join().includes('각각 1건'));
console.log('PASS 안내 문구 4개');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'br-kind': 'unit', 'br-purpose': 'check', 'br-method': 'gov24' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['br-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('수수료: 0원'));
