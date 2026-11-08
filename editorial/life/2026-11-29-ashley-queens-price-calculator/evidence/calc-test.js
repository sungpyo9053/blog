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
const h3faq = html.split('<h2 id="faq">')[1].split('<script type="application/ld+json">')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= 본문 h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.ashleyCalc;
const C = (a, t, e, p) => ({ adult: a, teen: t, elem: e, pre: p });
const cases = [
  ['일반 평일런치 성인2+초등1', ['normal', 'lunch', C(2, 0, 1, 0), 0, 0], 52700],
  ['일반 평일디너 성인2+초등1', ['normal', 'dinner', C(2, 0, 1, 0), 0, 0], 67700],
  ['일반 주말 성인2+초등1', ['normal', 'weekend', C(2, 0, 1, 0), 0, 0], 71700],
  ['일반 주말 성인2+초등1+미취학1', ['normal', 'weekend', C(2, 0, 1, 1), 0, 0], 79600],
  ['일반 평일디너 성인2+중학생1(성인가)', ['normal', 'dinner', C(2, 1, 0, 0), 0, 0], 77700],
  ['성수 평일디너 성인2+청소년1', ['seongsu', 'dinner', C(2, 1, 0, 0), 0, 0], 85700],
  ['성수 주말 성인1+청소년1+초등1+미취학1', ['seongsu', 'weekend', C(1, 1, 1, 1), 0, 0], 29900 + 27900 + 15900 + 7900],
  ['그릴 주말 성인2+초등2', ['grill', 'weekend', C(2, 0, 2, 0), 0, 0], 71600],
  ['그릴 평일디너 초등1', ['grill', 'dinner', C(0, 0, 1, 0), 0, 0], 12900],
  ['클럽데이 일반 평일디너 성인4', ['normal', 'dinner', C(4, 0, 0, 0), 4, 0], 79600],
  ['클럽데이 그릴 평일디너 성인1', ['grill', 'dinner', C(1, 0, 0, 0), 1, 0], 19900],
  ['클럽데이 성수 평일디너 성인1', ['seongsu', 'dinner', C(1, 0, 0, 0), 1, 0], 19900],
  ['클럽데이 일반 고등학생 포함', ['normal', 'dinner', C(1, 1, 0, 0), 2, 0], 39800],
  ['클럽데이 인원 초과는 성인 수까지', ['normal', 'dinner', C(1, 0, 1, 0), 3, 0], 19900 + 15900],
  ['클럽데이 주말엔 미반영', ['normal', 'weekend', C(2, 0, 0, 0), 2, 0], 55800],
  ['스테이크 2개 추가', ['normal', 'lunch', C(2, 0, 0, 0), 0, 2], 39800 + 31800],
  ['음수·빈값·문자 방어', ['normal', 'lunch', C(-2, '', 'x', 1), -1, -3], 7900],
];
for (const [name, args, total] of cases) {
  const r = calc(...args);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  console.log('PASS', name, r.total.toLocaleString('ko-KR') + '원', r.warn.length ? '(안내 ' + r.warn.length + ')' : '');
}
assert.strictEqual(calc('normal', 'weekend', C(2, 0, 0, 0), 2, 0).warn.length, 1);
assert.strictEqual(calc('seongsu', 'dinner', C(1, 1, 0, 0), 1, 0).warn.length, 1);
console.log('PASS 클럽데이 안내 문구');
const vals = { 'aq-store': 'normal', 'aq-slot': 'lunch', 'aq-adult': '2', 'aq-teen': '0', 'aq-elem': '1', 'aq-pre': '0', 'aq-infant': '1', 'aq-club': '0', 'aq-steak': '0' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['aq-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child ? p.child.textContent : '')); } };
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('52,700원'));
