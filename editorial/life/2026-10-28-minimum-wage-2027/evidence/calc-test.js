// ko.html의 계산기 <script>를 그대로 뽑아 최소 DOM 스텁 위에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert.strictEqual(src.indexOf('&'), -1, '& found in script');
assert.strictEqual(src.indexOf('<'), -1, '< found in script');

const els = {};
const mk = (id, value) => (els[id] = {
  id, value, checked: false, style: {}, handlers: {}, kids: [],
  addEventListener(t, f) { this.handlers[t] = f; },
  set innerHTML(v) { this.kids = []; },
  appendChild(p) { this.kids.push(p.textContent); },
});
mk('wg-rate', '10700'); mk('wg-day', '8'); mk('wg-days', '5'); mk('wg-prob');
mk('wg-out'); mk('wg-26'); mk('wg-27');
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);

const out = () => els['wg-out'].kids.join(' | ') || els['wg-out'].textContent;
function run(rate, day, days, prob) {
  els['wg-rate'].value = String(rate); els['wg-day'].value = String(day);
  els['wg-days'].value = String(days); els['wg-prob'].checked = !!prob;
  els['wg-rate'].handlers.input();
  return out();
}
const cases = [
  ['기본값 2027 주40h -> 월 2,236,300(209h)', () => out(), ['주휴수당 85,600원 (8.0시간분)', '주급(근로+주휴) 513,600원', '월 환산 2,236,300원 (월 209시간)']],
  ['2026 주40h -> 노동포털 월 2,156,880', () => run(10320, 8, 5), ['월 환산 2,156,880원 (월 209시간)', '주휴수당 82,560원']],
  ['2027 3h x 5일 -> 표 값', () => run(10700, 3, 5), ['주휴수당 32,100원 (3.0시간분)', '주급(근로+주휴) 192,600원', '월 환산 834,600원 (월 78시간)']],
  ['2027 4h x 5일 -> 표 값', () => run(10700, 4, 5), ['주휴수당 42,800원', '월 환산 1,112,800원 (월 104시간)']],
  ['2027 6h x 5일 -> 표 값', () => run(10700, 6, 5), ['주휴수당 64,200원', '월 환산 1,669,200원 (월 156시간)']],
  ['수습 감액 2027 -> 9,630', () => run(10700, 8, 5, true), ['적용 시급 9,630원']],
  ['주 14h -> 주휴 없음', () => run(10700, 2, 7), ['주휴수당 없음 (주 15시간 미만)']],
  ['하루 10h x 5일 -> 40h 상한', () => run(10700, 10, 5), ['1주 소정근로시간 40시간 (하루 8시간까지만 계산)', '주휴수당 85,600원']],
  ['입력 오류 안내', () => (run('', 8, 5), els['wg-out'].textContent), ['숫자로 넣어 주세요']],
];
for (const [name, fn, expects] of cases) {
  const o = fn();
  for (const e of expects) assert.ok(o.includes(e), name + ' -> ' + o);
  console.log('PASS', name, '::', o);
}
els['wg-26'].handlers.click();
assert.strictEqual(String(els['wg-rate'].value), '10320');
console.log('PASS 2026 버튼 -> 시급 10320 ::', out());
