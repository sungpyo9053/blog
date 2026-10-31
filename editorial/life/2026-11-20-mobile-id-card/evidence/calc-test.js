// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검증
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.mobileIdCheck;
const cases = [
  ['주민등록증 QR -> 주민센터 무료', ['rrc', 'no', 'qr', 'first'], { route: 'qr', fee: 0, place: '가까운 읍·면·동 주민센터', revisit: true }],
  ['주민등록증 IC 교체 -> 1만원', ['rrc', 'no', 'ic', 'first'], { route: 'ic', fee: 10000, revisit: false }],
  ['운전면허 QR -> 시험장 1,000원', ['mdl', 'no', 'qr', 'first'], { route: 'qr', fee: 1000, place: '전국 운전면허시험장' }],
  ['운전면허 IC 교체 -> 15,000원', ['mdl', 'no', 'ic', 'first'], { route: 'ic', fee: 15000 }],
  ['보훈 QR 선택 -> QR 없음, IC 경로 무료', ['mnh', 'no', 'qr', 'first'], { route: 'ic', fee: 0 }],
  ['외국인 IC -> 35,000원', ['mfc', 'no', 'ic', 'first'], { route: 'ic', fee: 35000 }],
  ['외국인 QR -> 무료', ['mfc', 'no', 'qr', 'first'], { route: 'qr', fee: 0 }],
  ['장애인 QR -> 무료', ['mdc', 'no', 'qr', 'first'], { route: 'qr', fee: 0 }],
  ['IC 보유 -> 태그, 방법 무관 무료', ['mdl', 'yes', 'qr', 'first'], { route: 'tag', fee: 0, revisit: false }],
];
for (const [name, args, exp] of cases) {
  const r = c(...args);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ route: r.route, fee: r.fee, place: r.place }));
}
const j = (r) => r.need.join() + '|' + r.note.join() + '|' + r.feeText;
assert.ok(j(c('rrc', 'no', 'ic', 'first')).includes('21일'));
assert.ok(j(c('rrc', 'no', 'ic', 'first')).includes('2006년 11월 1일'));
assert.ok(j(c('rrc', 'no', 'qr', 'first')).includes('제24조의2제3항'));
assert.ok(j(c('mdl', 'no', 'ic', 'first')).includes('21,000원'));
assert.ok(j(c('mdl', 'no', 'qr', 'first')).includes('사진이 모바일용'));
assert.ok(j(c('mnh', 'no', 'qr', 'first')).includes('현장 QR 발급이 없다'));
assert.ok(j(c('mnh', 'no', 'ic', 'first')).includes('2028년 6월 4일'));
assert.ok(j(c('rrc', 'no', 'qr', 'phone')).includes('주민센터를 다시'));
assert.ok(j(c('mdl', 'no', 'qr', 'phone')).includes('운전면허시험장를 다시') || j(c('mdl', 'no', 'qr', 'phone')).includes('운전면허시험장'));
assert.ok(j(c('rrc', 'yes', 'ic', 'phone')).includes('다시 태그'));
assert.ok(c('rrc', 'no', 'qr', 'lost').note[0].includes('1688-0990'));
assert.ok(!j(c('rrc', 'no', 'qr', 'first')).includes('1688-0990'));
assert.ok(j(c('mdc', 'no', 'qr', 'first')).includes('3년'));
console.log('PASS 준비물·안내 문구 13건');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'mid-kind': 'rrc', 'mid-ic': 'no', 'mid-method': 'qr', 'mid-sit': 'first' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['mid-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('수수료 무료'));
assert.ok(outP.join().includes('주민센터'));
