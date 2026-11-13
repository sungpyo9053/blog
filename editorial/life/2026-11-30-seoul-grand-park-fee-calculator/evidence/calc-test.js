// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
assert.ok(faq >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.grandparkCalc, pf = window.grandparkParkFee;
const N = (adult, teen, child, kid, baby, senior) => ({ adult, teen, child, kid, baby, senior });
const P3 = (a, t, c) => ({ adult: a, teen: t, child: c });
const Z = P3(0, 0, 0);
const base = { zoo: true, garden: false, multi: false, free: Z, climate: Z, train: 0, lift: 'none', car: 'none', pay: 'mobile', min: 0, cdisc: '0' };
const T = (o) => calc(Object.assign({}, base, o));
const cases = [
  ['기본값: 어른2+초등1+5세1, 동물원, 열차 왕복', { n: N(2, 0, 1, 1, 0, 0), train: 2 }, 26000],
  ['예시1: + 앱 정산 4시간', { n: N(2, 0, 1, 1, 0, 0), train: 2, car: 'normal', min: 240 }, 31000],
  ['예시2: 경로2+어린이1, 리프트 2회권', { n: N(0, 0, 1, 0, 0, 2), lift: '2' }, 34000],
  ['예시3: 다둥이 어른2+청소년1, 동물원+테마가든, 열차1, 정산기 3시간 50%', { n: N(2, 1, 0, 0, 0, 0), garden: true, multi: true, train: 1, car: 'normal', pay: 'onsite', min: 180, cdisc: '0.5' }, 8500],
  ['동물원+테마가든 어른1 청소년1 어린이1', { n: N(1, 1, 1, 0, 0, 0), garden: true }, 14500],
  ['무료대상 어른1 + 기후동행 어른1 + 정가 어른1', { n: N(3, 0, 0, 0, 0, 0), free: P3(1, 0, 0), climate: P3(1, 0, 0) }, 7500],
  ['무료 인원 초과 입력 방어', { n: N(1, 0, 0, 0, 0, 0), free: P3(3, 0, 0), climate: P3(2, 0, 0) }, 0],
  ['36개월 미만 열차 무료, 경로 열차 2,000원', { n: N(0, 0, 0, 0, 1, 1), zoo: false, train: 1 }, 2000],
  ['리프트 당일권 실버=어른 21,000원', { n: N(1, 0, 0, 0, 0, 1), zoo: false, lift: 'day' }, 42000],
  ['리프트 4구간 어른1', { n: N(1, 0, 0, 0, 0, 0), zoo: false, lift: '4' }, 32000],
  ['음수·빈값 방어', { n: N(-2, '', 'x', 0, 0, 0), train: -1 }, 0],
];
for (const [name, o, total] of cases) {
  const r = T(o);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원');
}
let r = T({ n: N(1, 0, 0, 0, 1, 0), lift: '1' });
assert.ok(r.notes.some(t => t.includes('확인하지 못했다')));
console.log('PASS 36개월 미만 리프트 확인 불가 안내');
r = T({ n: N(2, 0, 1, 1, 0, 1), lift: '1', train: 1 });
assert.strictEqual(r.pkg, 14500 * 2 + 8000 + 6200 + 8000);
console.log('PASS 운송패키지 참고값', r.pkg);
const pcases = [
  ['normal', 'mobile', 30, 0], ['normal', 'mobile', 31, 3000], ['normal', 'mobile', 120, 3000], ['normal', 'mobile', 121, 4000],
  ['normal', 'mobile', 150, 4000], ['normal', 'mobile', 180, 5000], ['normal', 'mobile', 600, 5000],
  ['normal', 'onsite', 120, 4000], ['normal', 'onsite', 150, 5500], ['normal', 'onsite', 180, 6000], ['normal', 'onsite', 900, 6000],
  ['large', 'mobile', 120, 6000], ['large', 'onsite', 240, 14000], ['large', 'onsite', 600, 14000], ['none', 'mobile', 600, 0],
];
for (const [car, pay, min, fee] of pcases) {
  assert.strictEqual(pf(car, pay, min), fee, car + pay + min);
}
console.log('PASS 주차요금', pcases.length, '건 (회차 30분 무료, 2시간 기본, 30분 단위 올림, 1일 최대)');
assert.strictEqual(T({ n: N(0, 0, 0, 0, 0, 0), zoo: false, car: 'normal', pay: 'onsite', min: 600, cdisc: '0.8' }).total, 1200);
console.log('PASS 주차 80% 감면 6,000원 -> 1,200원');
r = T({ n: N(0, 0, 0, 0, 0, 0), zoo: false, car: 'normal', min: 3000 });
assert.strictEqual(r.total, 5000); assert.ok(r.notes[0].includes('24시간'));
console.log('PASS 24시간 초과 안내');
const ids = ['gp-zoo', 'gp-garden', 'gp-multi', 'gp-adult', 'gp-teen', 'gp-child', 'gp-kid', 'gp-baby', 'gp-senior', 'gp-f-adult', 'gp-f-teen', 'gp-f-child', 'gp-c-adult', 'gp-c-teen', 'gp-c-child', 'gp-train', 'gp-lift', 'gp-car', 'gp-pay', 'gp-min', 'gp-cdisc'];
const els = {};
ids.forEach(id => {
  const m = html.match(new RegExp('id="' + id + '"[^>]*'));
  assert.ok(m, 'missing ' + id);
  const tag = m[0];
  const v = (tag.match(/value="([^"]*)"/) || [])[1];
  const sel = html.match(new RegExp('id="' + id + '"[^>]*>\\s*<option value="([^"]*)"'));
  els[id] = { value: v !== undefined ? v : (sel ? sel[1] : ''), checked: / checked/.test(tag), addEventListener() {} };
});
const outP = [];
els['gp-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('26,000원'));
console.log('FAQ JSON-LD 질문 수:', faq);
