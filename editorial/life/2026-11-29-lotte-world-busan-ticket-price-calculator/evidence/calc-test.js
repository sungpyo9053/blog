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
const calc = window.lotteWorldBusanCalc;
const Z = { a: 0, t: 0, c: 0, s: 0, b: 0, b1: 0, x: 0, v: 0 };
const cases = [
  ['4인 1Day 정상가', { time: 'day', a: 2, c: 2, dc: 'none' }, { total: 168000 }],
  ['4인 1Day 온라인', { time: 'day', a: 2, c: 2, dc: 'online' }, { total: 142000, saved: 26000, notes: 0 }],
  ['5인 온라인 → 4매 경고', { time: 'day', a: 5, dc: 'online' }, { total: 41500 * 5, notes: 1 }],
  ['4인 T 멤버십', { time: 'day', a: 2, c: 2, dc: 'tmem' }, { total: 138950 }],
  ['4인 롯데멤버스카드', { time: 'day', a: 2, c: 2, dc: 'lmc' }, { total: 143500 }],
  ['어린이 1명 롯데멤버스카드 → 성인 요금 24,500', { time: 'day', c: 1, dc: 'lmc' }, { total: 24500 }],
  ['After3 2인 정상가', { time: 'a3', a: 2, dc: 'none' }, { total: 76000 }],
  ['After3 2인 대중교통', { time: 'a3', a: 2, dc: 'transit' }, { total: 60800 }],
  ['After3 2인 온라인', { time: 'a3', a: 2, dc: 'online' }, { total: 64000 }],
  ['장애인 어른2 어린이1', { time: 'day', a: 2, c: 1, dc: 'disabled' }, { total: 84000 }],
  ['국가유공자 After3 청소년2', { time: 'a3', t: 2, dc: 'merit' }, { total: 34000 }],
  ['문화누리 어른1 어린이3', { time: 'day', a: 1, c: 3, dc: 'nuri' }, { total: 29400 + 21000 + 35000 * 2 }],
  ['문화누리 가족 어른1 어린이3', { time: 'day', a: 1, c: 3, dc: 'nurifam' }, { total: 29400 + 21000 * 3 }],
  ['연간 동반 어른4 → 3명만', { time: 'day', a: 4, dc: 'annual' }, { total: 29400 * 3 + 49000 }],
  ['LG VIP 어린이 본인 22,700', { time: 'day', c: 2, dc: 'lgvip' }, { total: 22700 + 31500 }],
  ['LG 우수 어른3 After3', { time: 'a3', a: 3, dc: 'lgnorm' }, { total: 28500 + 34200 * 2 }],
  ['임신부 어른2', { time: 'day', a: 2, dc: 'pregnant' }, { total: 24500 + 49000 }],
  ['군인 청소년만 → 정상가+안내', { time: 'day', t: 1, dc: 'soldier' }, { total: 41000, notes: 1 }],
  ['경로 1 + 베이비 1 + 1회권 2, 1Day', { time: 'day', s: 1, b: 1, b1: 2, dc: 'none' }, { total: 34300 + 13000 + 6000, notes: 1 }],
  ['경로 After3', { time: 'a3', s: 1, dc: 'none' }, { total: 26600 }],
  ['추가 금액 30,000', { time: 'day', a: 1, dc: 'none', x: 30000 }, { ticket: 49000, total: 79000 }],
  ['연간 비교 어른1 4회', { time: 'day', a: 1, dc: 'none', v: 4 }, { visitsNormal: 196000, green: 190000 }],
  ['연간 비교 어린이1 4회', { time: 'day', c: 1, dc: 'none', v: 4 }, { visitsNormal: 140000, green: 150000 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, Z, o));
  for (const k of Object.keys(exp)) {
    const v = k === 'notes' ? r.notes.length : r[k];
    assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v);
  }
  console.log('PASS', name, JSON.stringify(r));
}
// UI 기본값(1Day 어른2 어린이2 할인 없음) 렌더 확인
const vals = { 'lwb-time': 'day', 'lwb-a': '2', 'lwb-t': '0', 'lwb-c': '2', 'lwb-s': '0', 'lwb-b': '0', 'lwb-b1': '0', 'lwb-dc': 'none', 'lwb-x': '0', 'lwb-v': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['lwb-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('168,000원'));
console.log('ALL PASS');
