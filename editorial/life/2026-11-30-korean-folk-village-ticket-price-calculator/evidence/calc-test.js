// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const bodyQ = [...html.split('<h2 id="faq">')[1].matchAll(/<h3>(.*?)<\/h3>/g)].map(m => m[1]);
assert.deepStrictEqual(faq.map(q => q.name), bodyQ);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.folkVillageCalc;
const C = (a, c, s) => ({ adult: a, child: c, senior: s });
const D = (a, c) => ({ adult: a, child: c });
const Z = D(0, 0);
const cases = [
  ['주말 종일 성인2+아동1', ['wkend', 'none', C(2, 1, 0), Z, 0], 110000, 0],
  ['주중 종일 성인2+아동1', ['wkday', 'none', C(2, 1, 0), Z, 0], 104000, 0],
  ['12월 주말 오후2시 성인2+아동1', ['pw2', 'none', C(2, 1, 0), Z, 0], 73000, 0],
  ['11월 주말 오후4시 성인1+아동1', ['pa4', 'none', C(1, 1, 0), Z, 0], 56000, 0],
  ['여름 야간6시 성인2', ['ps6', 'none', C(2, 0, 0), Z, 0], 56000, 0],
  ['주말 성인3+아동1', ['wkend', 'none', C(3, 1, 0), Z, 0], 149000, 0],
  ['주말 경로2+아동1', ['wkend', 'none', C(0, 1, 2), Z, 0], 96000, 0],
  ['장애인 본인 아동요금+보호자', ['wkend', 'childrate', C(1, 0, 0), D(1, 0), 0], 71000, 0],
  ['열린관광지 2명', ['wkend', 'open', Z, D(2, 0), 0], 36000, 0],
  ['병사 무료+친구', ['wkend', 'free', C(1, 0, 0), D(1, 0), 0], 39000, 0],
  ['문화누리 대인2+소인2', ['wkend', 'nuri', Z, D(2, 2), 0], 92000, 0],
  ['경기도민 주중 4명', ['wkday', 'gg', Z, D(3, 1), 0], 84000, 0],
  ['고정우대 오후권 미적용', ['pa2', 'mf', Z, D(1, 0), 0], 0, 1],
  ['아동요금 우대 오후권', ['pa2', 'childrate', Z, D(1, 0), 0], 28000, 0],
  ['음수·빈값 방어', ['wkend', 'none', C(-3, '', 'x'), Z, -2], 0, 0],
];
for (const [name, args, total, unknown] of cases) {
  const r = calc(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.unknown.length, unknown, name + ' unknown=' + r.unknown.length);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.unknown.join(','));
}
const be = (base, who, v) => { const c = C(who === 'a' ? 1 : 0, who === 'c' ? 1 : 0, 0); return calc(base, 'none', c, Z, v); };
assert.ok(be('wkend', 'a', 5).annualTotal > be('wkend', 'a', 5).dayTotal);
assert.ok(be('wkend', 'a', 6).dayTotal > be('wkend', 'a', 6).annualTotal);
assert.ok(be('wkend', 'c', 4).annualTotal > be('wkend', 'c', 4).dayTotal);
assert.ok(be('wkend', 'c', 5).dayTotal > be('wkend', 'c', 5).annualTotal);
assert.ok(be('wkday', 'a', 4).annualWk > be('wkday', 'a', 4).dayTotal);
assert.ok(be('wkday', 'a', 5).dayTotal > be('wkday', 'a', 5).annualWk);
assert.ok(be('wkday', 'c', 4).annualWk > be('wkday', 'c', 4).dayTotal);
assert.ok(be('wkday', 'c', 5).dayTotal > be('wkday', 'c', 5).annualWk);
console.log('PASS 본전: 주말 성인 6회째, 주말 아동 5회째, 주중 성인·아동 5회째');
assert.strictEqual(calc('wkend', 'gg', Z, D(5, 0), 0).warn.length, 1);
assert.strictEqual(calc('wkend', 'open', Z, D(2, 0), 0).warn.length, 0);
assert.strictEqual(calc('wkend', 'none', C(0, 0, 1), Z, 0).warn.length, 1);
console.log('PASS 인원 상한·경로 안내 경고');
const vals = { 'kf-base': 'wkend', 'kf-disc': 'none', 'kf-adult': '2', 'kf-child': '1', 'kf-senior': '0', 'kf-infant': '1', 'kf-d-adult': '0', 'kf-d-child': '0', 'kf-visits': '1' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['kf-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('110,000원'));
