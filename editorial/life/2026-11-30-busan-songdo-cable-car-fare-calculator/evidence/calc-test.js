// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq, 'FAQ JSON-LD count matches h3');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.songdoCableCalc;
const Z = { day: 'wd', a: 0, c: 0, b: 0, k: 1, dc: 'none' };
const cases = [
  ['4인 에어 왕복', { type: 'ar', a: 2, c: 2 }, { total: 66000 }],
  ['4인 크리스탈 왕복', { type: 'cr', a: 2, c: 2 }, { total: 84000 }],
  ['대인1 에어 편도', { type: 'ao', a: 1 }, { total: 15000 }],
  ['소인1 크리스탈 편도', { type: 'co', c: 1 }, { total: 15000 }],
  ['부산시민 2명 평일 크리스탈 왕복 4인', { type: 'cr', a: 2, c: 2, dc: 'busan', k: 2 }, { total: 76000, saved: 8000 }],
  ['부산시민 주말 → 할인 없음', { type: 'cr', a: 2, dc: 'busan', k: 2, day: 'we' }, { total: 48000, notes: 1 }],
  ['부산시민 평일 에어 왕복 1명', { type: 'ar', a: 1, dc: 'busan' }, { total: 16000 }],
  ['다자녀 대인2 소인3 에어 왕복', { type: 'ar', a: 2, c: 3, dc: 'multi', k: 0 }, { total: 70000 }],
  ['경로 76세 + 동반 1 크리스탈 왕복', { type: 'cr', a: 2, dc: 's76' }, { total: 44000 }],
  ['경로 65세 본인만, 대인2', { type: 'cr', a: 2, dc: 's65' }, { total: 46000 }],
  ['중증장애 본인+동반 + 소인1 에어 왕복', { type: 'ar', a: 2, c: 1, dc: 'dsev' }, { total: 48000 }],
  ['경증장애 본인 + 소인1 에어 왕복', { type: 'ar', a: 1, c: 1, dc: 'dmild' }, { total: 31000 }],
  ['국가유공자 본인, 대인2', { type: 'ar', a: 2, dc: 'merit' }, { total: 36000, notes: 1 }],
  ['문화누리 본인 크리스탈 편도 → 편도 안내', { type: 'co', a: 1, dc: 'nuri' }, { total: 17000, notes: 1 }],
  ['서구 구민 2 크리스탈 왕복', { type: 'cr', a: 2, dc: 'seogu', k: 2 }, { total: 36000 }],
  ['서구 구민 에어 왕복 주말도 할인', { type: 'ar', a: 1, dc: 'seogu', day: 'we' }, { total: 14000 }],
  ['서구 70세 부부 크리스탈 왕복', { type: 'cr', a: 2, dc: 'seogu70', k: 2 }, { total: 24000 }],
  ['자유이용권 대인2 소인1', { type: 'free', a: 2, c: 1 }, { total: 100000 }],
  ['자유이용권 + 우대 → 정상가', { type: 'free', a: 1, dc: 's65' }, { total: 35000, notes: 1 }],
  ['스피디 크리스탈 대인1 소인1', { type: 'sc', a: 1, c: 1 }, { total: 110000 }],
  ['스피디 에어 3명', { type: 'sa', a: 3 }, { total: 135000 }],
  ['프리미엄 크리스탈 8명 → 1대', { type: 'pc', a: 6, c: 2 }, { total: 340000, cabins: 1 }],
  ['프리미엄 에어 9명 → 2대', { type: 'pa', a: 9 }, { total: 540000, cabins: 2 }],
  ['영유아만 → 0원', { type: 'ar', b: 2 }, { total: 0 }],
  ['우대 대상자 0명 → 안내', { type: 'ar', a: 1, dc: 'nuri', k: 0 }, { total: 19000, notes: 1 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, Z, o));
  for (const k of Object.keys(exp)) {
    const v = k === 'notes' ? r.notes.length : r[k];
    assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v);
  }
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(에어 왕복, 평일, 대인2 소인2, 우대 없음) 렌더 확인
const vals = { 'sdc-type': 'ar', 'sdc-day': 'wd', 'sdc-a': '2', 'sdc-c': '2', 'sdc-b': '0', 'sdc-dc': 'none', 'sdc-k': '1' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sdc-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('66,000원'));
console.log('ALL PASS');
