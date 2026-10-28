// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.parentalLeaveCalc;
const pays = r => r.rows.map(x => x.pay / 10000);
const cases = [
  // [이름, wage, months, spouse, six, single, disabled, 기대 총액, 기대 월별(만원)]
  ['정책브리핑: 12개월 상한 적용 총 2,310만원', 4000000, 12, 0, false, false, false, 23100000, [250,250,250,200,200,200,160,160,160,160,160,160]],
  ['상한 경계: 통상임금 250만원', 2500000, 12, 0, false, false, false, 23100000, null],
  ['중간: 180만원 -> 1~6개월 180, 7개월~ 144', 1800000, 12, 0, false, false, false, 1800000*6 + 1440000*6, [180,180,180,180,180,180,144,144,144,144,144,144]],
  ['하한: 60만원 -> 전 구간 70만원', 600000, 12, 0, false, false, false, 8400000, [70,70,70,70,70,70,70,70,70,70,70,70]],
  ['하한: 80만원 -> 7개월~ 64만원이 70만원으로', 800000, 8, 0, false, false, false, 800000*6 + 700000*2, [80,80,80,80,80,80,70,70]],
  ['6+6 부모 각 6개월, 450만원 이상 -> 첫 6개월 2,000만원', 5000000, 6, 6, true, false, false, 20000000, [250,250,300,350,400,450]],
  ['6+6 12개월(7개월~ 일반 160)', 5000000, 12, 6, true, false, false, 20000000 + 1600000*6, null],
  ['6+6 공통 3개월(내 6, 배우자 3)', 5000000, 6, 3, true, false, false, 2500000*2 + 3000000 + 2000000*3, [250,250,300,200,200,200]],
  ['6+6 통상임금 280만원: 3개월째 상한 300 미만이라 280', 2800000, 3, 3, true, false, false, 2500000*2 + 2800000, [250,250,280]],
  ['6+6 체크했지만 배우자 0 -> 일반', 5000000, 3, 0, true, false, false, 7500000, [250,250,250]],
  ['한부모: 첫 3개월 상한 300', 5000000, 4, 0, false, true, false, 3000000*3 + 2000000, [300,300,300,200]],
  ['기간: 배우자 0이면 18개월 입력해도 12개월', 4000000, 18, 0, false, false, false, 23100000, null],
  ['기간: 배우자 3개월이면 18개월', 4000000, 18, 3, false, false, false, 23100000 + 1600000*6, null],
  ['기간: 장애아동 부모 18개월', 4000000, 18, 0, false, false, true, 23100000 + 1600000*6, null],
];
for (const [name, w, m, s, six, sg, dis, total, monthly] of cases) {
  const r = calc(w, m, s, six, sg, dis);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  if (monthly) assert.deepStrictEqual(pays(r), monthly, name + ' monthly=' + pays(r));
  console.log('PASS', name, '| 개월', r.months, '| 총', r.total.toLocaleString('ko-KR'), '| 월별(만원)', pays(r).join(','));
}
// UI 기본값(300만원, 12개월) 렌더 확인 — 최소 DOM 스텁
const vals = { 'pl-wage': '3000000', 'pl-months': '12', 'pl-spouse': '0' };
const checks = { 'pl-six': false, 'pl-single': false, 'pl-disabled': false };
const texts = [];
const mk = () => ({ style: {}, children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { this._t = v; }, get textContent() { return this._t; } });
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
Object.keys(checks).forEach(id => els[id] = { checked: checks[id], addEventListener() {} });
els['pl-out'] = { set innerHTML(v) { texts.length = 0; }, appendChild(c) { texts.push(c); } };
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
const flat = n => (n._t !== undefined ? [n._t] : []).concat(...(n.children || []).map(flat));
const out = texts.map(n => flat(n).join(' ')).join(' | ');
console.log('UI 기본값 출력:', out.slice(0, 300), '...');
assert.ok(out.includes('23,100,000원'));
console.log('PASS UI');
