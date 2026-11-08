// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string ' + lit);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.ottCalc, S = window.ottServices;
const pick = (id, i) => { const s = S.find(x => x.id === id), p = s.p[i]; return { id, name: s.n + ' ' + p[0], price: p[1], annual: p[2] === 1, streams: p[3], solo: p[4] === 1, covers: p[5] || [] }; };
const cases = [
  ['넷플릭스·티빙·웨이브 스탠다드, 2명', [pick('nf', 1), pick('tv', 2), pick('wv', 2)], 2, { month: 37900, year: 454800, perMonth: 18950, perYear: 227400, nwarn: 0 }],
  ['넷플릭스 스탠다드 + 더블 스탠다드, 2명', [pick('nf', 1), pick('bd', 3)], 2, { month: 28500, year: 342000, perMonth: 14250, nwarn: 0 }],
  ['넷플릭스 프리미엄 4명', [pick('nf', 2)], 4, { month: 17000, year: 204000, perMonth: 4250, perYear: 51000, nwarn: 0 }],
  ['웨이브 스탠다드 12개월권 1명', [pick('wv', 5)], 1, { month: 9083, year: 109000, perYear: 109000 }],
  ['디즈니+ 프리미엄 연간 + 왓챠 프리미엄, 4명', [pick('dp', 4), pick('wc', 1)], 4, { month: Math.round(139000 / 12 + 12900), year: 139000 + 154800, nwarn: 0 }],
  ['넷플릭스 스탠다드 3명 -> 동시시청 경고', [pick('nf', 1)], 3, { month: 13500, perMonth: 4500, nwarn: 1 }],
  ['3 PACK + 티빙 따로 -> 중복 경고', [pick('bd', 6), pick('tv', 2)], 1, { month: 35000, nwarn: 1 }],
  ['유튜브 Premium 2명 -> 개인 요금제 경고', [pick('yt', 0)], 2, { month: 14900, year: 178800, nwarn: 1 }],
  ['쿠팡 일반회원 0원 + 와우 아님', [pick('cp', 1)], 1, { month: 0, year: 0 }],
  ['왓챠 프리미엄 12개월권 4명', [pick('wc', 3)], 4, { month: 10825, year: 129900, perMonth: 2706, perYear: 32475, nwarn: 0 }],
  ['쿠팡 일반회원 2명 -> 동시시청 1대 경고', [pick('cp', 1)], 2, { month: 0, nwarn: 1 }],
  ['인원 0/NaN -> 1명으로', [pick('tv', 0)], NaN, { people: 1, perMonth: 5500 }],
];
for (const [name, items, ppl, exp] of cases) {
  const r = calc(items, ppl);
  for (const k of Object.keys(exp)) { const v = k === 'nwarn' ? r.warn.length : r[k]; assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v); }
  console.log('PASS', name, JSON.stringify({ month: r.month, year: r.year, perMonth: r.perMonth, perYear: r.perYear, warn: r.warn }));
}
// 결합 상품 정가 대비 차액 검산 (본문 수치)
const P = id => S.find(x => x.id === id).p;
assert.strictEqual(P('tv')[2][1] + P('wv')[2][1], 24400);
assert.strictEqual(P('tv')[2][1] + P('dp')[1][1], 23400);
assert.strictEqual(P('tv')[2][1] + P('dp')[1][1] + P('wv')[2][1], 34300);
assert.strictEqual(P('tv')[3][1] + P('wv')[3][1] - P('bd')[4][1], 11400);
console.log('PASS 결합 정가 합계 4개');
// UI 렌더 확인 — 최소 DOM 스텁 (기본값: 넷플릭스·티빙·웨이브 스탠다드, 2명)
const reg = {};
function mk(tag) { const e = { tag, style: {}, children: [], listeners: {}, value: '', checked: false, textContent: '',
  appendChild(c) { this.children.push(c); if (c.id) reg[c.id] = c; return c; },
  addEventListener(t, f) { this.listeners[t] = f; }, set innerHTML(v) { this.children = []; } };
  return new Proxy(e, { set(t, k, v) { t[k] = v; if (k === 'id') reg[v] = t; return true; } }); }
['oc-rows', 'oc-out', 'oc-ppl'].forEach(id => { reg[id] = mk('div'); reg[id].id = id; });
reg['oc-ppl'].value = '2';
global.document = { getElementById: id => reg[id] || null, createElement: mk };
eval(src);
const txt = () => reg['oc-out'].children.map(c => c.textContent).join(' | ');
console.log('UI 기본값 출력:', txt());
assert.ok(txt().includes('월 합계: 37,900원'));
assert.ok(txt().includes('1인당 월 18,950원'));
// 디즈니+ 체크 후 가격 직접 수정(인상 대비) -> 합계 반영
reg['oc-dp-on'].checked = true; reg['oc-dp-pl'].value = '1'; reg['oc-dp-pr'].value = '11000'; reg['oc-dp-pr'].listeners.input();
console.log('디즈니+ 스탠다드 11,000원으로 고쳐 넣은 뒤:', txt());
assert.ok(txt().includes('월 합계: 48,900원'));
// 결합 상품 선택(change) -> 가격 칸 자동 채움 + 중복 경고
reg['oc-bd-pl'].value = '6'; reg['oc-bd-pl'].listeners.change();
assert.strictEqual(reg['oc-bd-pr'].value, '21500');
console.log('3 PACK 추가 후:', txt());
assert.ok(txt().includes('중복일 수 있다'));
console.log('ALL PASS');
