// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.homeInternetCalc, pen = window.homeInternetPenalty;
// calc(c, speed, years, tv, mobile, months, ktStb, quit)
const cases = [
  ['SK 공식 예시: 기가 와이파이 3년 13개월 해지 -> 270,167원', ['sk', '1000', 3, false, 0, 36, 0, 13], { disc: 25300, penalty: 270167 }],
  ['KT 1G 3년 인터넷만', ['kt', '1000', 3, false, 0, 36, 0, 0], { inet: 42900, modem: 0, monthly: 42900, inst: 36000, total: 42900 * 36 + 36000 }],
  ['KT 1G 무약정 모뎀 4,400', ['kt', '1000', 0, false, 0, 36, 0, 0], { inet: 72600, modem: 4400, monthly: 77000 }],
  ['SK 100M 2년 모뎀 1,100', ['sk', '100', 2, false, 0, 24, 0, 0], { inet: 36300, modem: 1100, monthly: 37400 }],
  ['LG 500M 3년 TV 함께', ['lg', '500', 3, true, 0, 36, 0, 0], { inet: 27500, tv: 13200, stb: 4400, monthly: 45100, inst: 56100 }],
  ['SK 1G 3년 TV 함께', ['sk', '1000', 3, true, 0, 36, 0, 0], { inet: 35200, tv: 9900, stb: 4400, monthly: 49500, inst: 56100 }],
  ['KT 1G 3년 TV 함께(셋톱 입력 5,000)', ['kt', '1000', 3, true, 0, 36, 5000, 0], { inet: 37400, tv: 12100, stb: 5000, monthly: 54500, fallback: false, inst: 32000 }],
  ['KT 1G 2년 TV -> 단독 요금 대체', ['kt', '1000', 2, true, 0, 24, 0, 0], { inet: 55000, tv: 16390, fallback: true }],
  ['LG 1G 3년 휴대폰 결합 13,200', ['lg', '1000', 3, false, 13200, 36, 0, 0], { monthly: 25300 }],
  ['KT 1G 3년 13개월 해지(180일 공제)', ['kt', '1000', 3, false, 0, 36, 0, 13], { disc: 29700, penalty: Math.floor(29700 * 13 * 23 / 30) }],
  ['LG 2년 5개월 해지 -> 전액(6개월 이하)', ['lg', '1000', 2, false, 0, 24, 0, 5], { disc: 17600, penalty: 17600 * 5 }],
  ['무약정은 반환금 0', ['sk', '1000', 0, false, 0, 36, 0, 5], { penalty: 0 }],
];
for (const [name, args, exp] of cases) {
  const r = calc(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 표 값: 글 본문 요금표와 계산기 데이터 일치
const tbl = { kt: { '100': [57200, 48400, 40700, 27500], '500': [63800, 55550, 48400, 38500], '1000': [72600, 63250, 55000, 42900] },
  sk: { '100': [47300, 40700, 36300, 24200], '500': [60500, 52800, 45100, 35200], '1000': [66000, 58300, 50600, 40700] },
  lg: { '100': [42900, 34100, 28600, 22000], '500': [56100, 49500, 41580, 33000], '1000': [64900, 57200, 47300, 38500] } };
let n = 0;
for (const c of Object.keys(tbl)) for (const sp of Object.keys(tbl[c])) tbl[c][sp].forEach((v, y) => { assert.strictEqual(calc(c, sp, y, false, 0, 12, 0, 0).inet, v); n++; });
console.log('PASS 표 값', n + '개');
// UI 기본값 렌더 (1G, 3년, 인터넷만, 36개월) — 최소 DOM 스텁
const vals = { 'ip-speed': '1000', 'ip-years': '3', 'ip-tv': '0', 'ip-mkt': '0', 'ip-msk': '0', 'ip-mlg': '0', 'ip-months': '36', 'ip-ktstb': '0', 'ip-quit': '' };
const mk = (tag) => ({ tag, style: {}, children: [], textContent: '', appendChild(c) { this.children.push(c); } });
const outEl = { style: {}, children: [], set innerHTML(v) { this.children = []; }, appendChild(c) { this.children.push(c); } };
const els = { 'ip-out': outEl };
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
const rows = outEl.children[0].children.map(tr => tr.children.map(c => c.textContent).join(' | '));
console.log('UI 기본값 출력:\n  ' + rows.join('\n  '));
assert.ok(rows[6].includes('42,900원') && rows[6].includes('40,700원') && rows[6].includes('38,500원'));
