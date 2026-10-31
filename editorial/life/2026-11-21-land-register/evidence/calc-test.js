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
const calc = window.landDocCheck;
const cases = [
  ['소유자·인터넷·열람 -> 토지대장 무료', ['owner', 'web', 'view', 'land', 1], { doc: '토지대장', fee: 0 }],
  ['소유자·인터넷·발급 3필지 -> 무료', ['owner', 'web', 'issue', 'land', 3], { fee: 0 }],
  ['소유자·방문·열람 -> 300', ['owner', 'visit', 'view', 'land', 1], { fee: 300 }],
  ['소유자·방문·발급 2필지 -> 1,000', ['owner', 'visit', 'issue', 'land', 2], { unit: 500, fee: 1000 }],
  ['산 번지 -> 임야대장', ['owner', 'visit', 'issue', 'forest', 1], { doc: '임야대장', fee: 500 }],
  ['소유자·무인발급기 -> 확인 못함(null)', ['owner', 'kiosk', 'issue', 'land', 1], { fee: null }],
  ['공시지가·인터넷 -> 무료', ['price', 'web', 'view', 'land', 1], { fee: 0 }],
  ['용도지역·인터넷 열람 -> 토지이음, 금액 null', ['zone', 'web', 'view', 'land', 1], { doc: '토지이용계획확인서', where: '토지이음(eum.go.kr)', fee: null }],
  ['용도지역·방문 발급 -> 조례, null', ['zone', 'visit', 'issue', 'land', 1], { fee: null }],
  ['경계·방문 열람 -> 지적도 400', ['shape', 'visit', 'view', 'land', 1], { doc: '지적도', fee: 400 }],
  ['경계·방문 발급 2장 -> 1,400', ['shape', 'visit', 'issue', 'land', 2], { fee: 1400 }],
  ['산 번지 경계·인터넷 -> 임야도 무료', ['shape', 'web', 'issue', 'forest', 1], { doc: '임야도', fee: 0 }],
  ['권리관계·인터넷 열람 -> 등기부 700', ['right', 'web', 'view', 'land', 1], { fee: 700 }],
  ['권리관계·인터넷 발급 -> 1,000', ['right', 'web', 'issue', 'land', 1], { fee: 1000 }],
  ['권리관계·무인발급기 열람 -> 발급 1,000', ['right', 'kiosk', 'view', 'land', 1], { fee: 1000 }],
  ['권리관계·창구 -> 1,200', ['right', 'visit', 'issue', 'land', 1], { fee: 1200 }],
  ['종합·인터넷 열람 -> 무료', ['all', 'web', 'view', 'land', 1], { doc: '부동산종합증명서', fee: 0 }],
  ['종합·인터넷 발급 -> 종합형 1,000', ['all', 'web', 'issue', 'land', 1], { fee: 1000 }],
  ['종합·방문 발급 2필지 -> 3,000', ['all', 'visit', 'issue', 'land', 2], { fee: 3000 }],
  ['종합·방문 열람 -> null', ['all', 'visit', 'view', 'land', 1], { fee: null }],
  ['필지 수 비움 -> 1', ['owner', 'visit', 'issue', 'land', ''], { count: 1, fee: 500 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ doc: r.doc, unit: r.unit, count: r.count, fee: r.fee }));
}
assert.ok(calc('owner', 'web', 'view', 'apt', 1).notes.join().includes('대지권등록부'));
console.log('PASS 아파트 -> 대지권등록부 안내');
assert.ok(calc('owner', 'kiosk', 'issue', 'land', 1).notes.join().includes('확인하지 못했다'));
console.log('PASS 무인발급기 -> 확인하지 못했다 안내');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ld-need': 'owner', 'ld-method': 'web', 'ld-form': 'view', 'ld-land': 'land', 'ld-count': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ld-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('무료'));
