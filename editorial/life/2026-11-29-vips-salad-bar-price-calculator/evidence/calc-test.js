// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.strictEqual(faq, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length, 'FAQ h3 = JSON-LD');
console.log('PASS 스크립트 규칙(& 없음, < 없음, 빈 줄 없음), JSON-LD 파싱, FAQ ' + faq + '개 일치');
// 계산기 가격 = 빕스 공식 JS 번들 SaladBar 컴포넌트 가격
const ex = fs.readFileSync(path.join(__dirname, 'ivips-js-574-saladbar-excerpt.txt'), 'utf8');
const off = {}; for (const m of ex.matchAll(/title:"([^"]+)",detail:"[^"]*",price:"([0-9,]+)"/g)) off[m[1]] = parseInt(m[2].replace(/,/g, ''), 10);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.vipsCalc, S = window.vipsSteaks;
const one = (time, who) => { const o = { time, store: 'normal', a: 0, t: 0, k: 0, p: 0, b: 0, steak: 0, sn: 0, disc: 'none' }; o[who] = 1; return calc(o).total; };
assert.strictEqual(one('lunch', 'a'), off['성인 평일 런치']);
assert.strictEqual(one('dinner', 'a'), off['성인 디너/주말/공휴일']);
assert.strictEqual(one('lunch', 't'), off['청소년 평일 런치']);
assert.strictEqual(one('weekend', 't'), off['청소년 디너/주말/공휴일']);
assert.strictEqual(one('weekend', 'k'), off['취학 어린이']);
assert.strictEqual(one('lunch', 'p'), off['미취학 어린이']);
assert.strictEqual(one('lunch', 'b'), 0);
console.log('PASS 1인 요금 6종 = 공식 번들 가격', JSON.stringify(off));
// 스테이크 가격 = brand-api 메뉴 JSON cost
const menu = JSON.parse(fs.readFileSync(path.join(__dirname, 'brand-api-menus-VIPS-6-main.json'), 'utf8')).data.content;
const cost = {}; for (const m of menu) cost[m.koreanMenuName] = m.cost;
for (const [n, p] of S.slice(1)) { if (n === '엘본 스테이크 650g 기준') { assert.ok(menu.find(m => m.koreanMenuName === '엘본 스테이크').description.includes('650g 기준 91,000원')); assert.strictEqual(p, 91000); continue; } assert.strictEqual(p, cost[n], n); }
console.log('PASS 스테이크 ' + (S.length - 1) + '종 = 공식 메뉴 JSON');
const base = { store: 'normal', a: 2, t: 0, k: 1, p: 1, b: 0, steak: 0, sn: 0, disc: 'none' };
const cases = [
  ['가족 4인 평일 런치', { time: 'lunch' }, { total: 106200, band: 'lunch' }],
  ['가족 4인 주말', { time: 'weekend' }, { total: 126200, band: 'dinner' }],
  ['런치 입장 17시 이후 퇴점 = 디너', { time: 'late' }, { total: 126200, band: 'dinner' }],
  ['성인2 디너 통신사 15%', { time: 'dinner', k: 0, p: 0, disc: 't15' }, { sub: 99400, discount: 14910, total: 84490 }],
  ['성인2 디너 생일쿠폰', { time: 'dinner', k: 0, p: 0, disc: 'bday' }, { total: 89400 }],
  ['성인2 디너 통신사 5%', { time: 'dinner', k: 0, p: 0, disc: 't5' }, { discount: 4970, total: 94430 }],
  ['성인1 청소년1 주말', { time: 'weekend', a: 1, t: 1, k: 0, p: 0 }, { total: 92600 }],
  ['미취학 1명만 생일쿠폰 4만 원 미만', { time: 'lunch', a: 0, k: 0, p: 1, disc: 'bday' }, { total: 9100, note: 'bday-under' }],
  ['통신사 15% 20만 원 한도', { time: 'dinner', a: 6, k: 0, p: 0, disc: 't15' }, { sub: 298200, discount: 30000, total: 268200 }],
  ['스테이크 안심150 x2', { time: 'lunch', k: 0, p: 0, steak: 1, sn: 2 }, { steak: 60000, total: 139400 }],
  ['그릴 다이닝은 참고값 표시', { time: 'lunch', store: 'grill' }, { status: 'grill', total: 106200 }],
  ['35개월 이하만', { time: 'lunch', a: 0, k: 0, p: 0, b: 1 }, { total: 0, status: 'ok' }],
  ['인원 0', { time: 'lunch', a: 0, k: 0, p: 0 }, { status: 'empty' }],
  ['음수·문자 입력은 0', { time: 'lunch', a: '-3', k: 'abc', p: 0, t: 1 }, { total: 39700 }],
];
for (const [name, over, exp] of cases) {
  const r = calc(Object.assign({}, base, over));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
for (const v of ['39,700원', '49,700원', '42,900원', '17,700원', '9,100원', '106,200원', '126,200원', '84,490원', '89,400원', '92,600원']) assert.ok(html.includes(v), 'body ' + v);
console.log('PASS 본문 금액이 계산기 결과와 일치');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'vp-time': 'lunch', 'vp-store': 'normal', 'vp-a': '2', 'vp-t': '0', 'vp-k': '1', 'vp-p': '1', 'vp-b': '0', 'vp-steak': '0', 'vp-sn': '0', 'vp-disc': 'none' };
const outP = [], opts = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(c) { if (id === 'vp-out') outP.push(c.textContent); else opts.push(c); } });
const els = {}; ['vp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
assert.strictEqual(opts.length, S.length);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('106,200원'));
