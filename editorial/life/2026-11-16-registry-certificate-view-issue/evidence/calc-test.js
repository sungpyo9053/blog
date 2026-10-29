// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.strictEqual(faq, (html.split('id="faq"')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS JSON-LD 파싱, FAQ', faq, '개 본문과 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.registryCheck;
const cases = [
  ['전세 확인·인터넷·아파트 -> 열람 700', ['jeonse', 'web', 'unit', 1, ''], { action: 'view', fee: 700 }],
  ['전세 확인·인터넷·단독 -> 열람 2건 1,400', ['jeonse', 'web', 'house', 1, ''], { action: 'view', records: 2, fee: 1400 }],
  ['전세 확인·무인발급기 -> 발급 1,000 (열람 없음)', ['jeonse', 'kiosk', 'unit', 1, ''], { action: 'issue', fee: 1000 }],
  ['전세 확인·창구 -> 열람 1,200', ['jeonse', 'visit', 'unit', 1, ''], { action: 'view', fee: 1200 }],
  ['제출·인터넷 2통 -> 2,000', ['submit', 'web', 'unit', 2, ''], { action: 'issue', fee: 2000 }],
  ['제출·무인 3통 단독 -> 6,000', ['submit', 'kiosk', 'house', 3, ''], { fee: 6000 }],
  ['제출·창구 20장 -> 1,200', ['submit', 'visit', 'unit', 1, 20], { unit: 1200, fee: 1200 }],
  ['제출·창구 23장 -> 1,350 단수 버림 1,300', ['submit', 'visit', 'unit', 1, 23], { unit: 1300 }],
  ['제출·창구 30장 2통 -> 1,700 x 2 = 3,400', ['submit', 'visit', 'unit', 2, 30], { unit: 1700, fee: 3400 }],
  ['소유자·인터넷 전자발급 -> 0', ['owner', 'web', 'unit', 1, ''], { fee: 0 }],
  ['소유자·창구 -> 1,200 (면제 아님)', ['owner', 'visit', 'unit', 1, ''], { fee: 1200 }],
  ['현재 소유자·인터넷 -> 일부 열람 700', ['ownerlist', 'web', 'land', 1, ''], { action: 'view', fee: 700 }],
  ['통수 비움 -> 1통', ['submit', 'web', 'unit', '', ''], { count: 1, fee: 1000 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ action: r.action, unit: r.unit, count: r.count, records: r.records, fee: r.fee }));
}
assert.ok(calc('submit', 'web', 'unit', 6, '').notes.join().includes('5통'));
console.log('PASS 인터넷 6통 -> 5통 한도 안내');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'rg-purpose': 'jeonse', 'rg-method': 'web', 'rg-kind': 'unit', 'rg-copies': '1', 'rg-pages': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['rg-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('700원'));
