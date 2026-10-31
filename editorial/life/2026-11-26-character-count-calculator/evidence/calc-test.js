// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
// 문자열 리터럴 안의 '<' 검사
for (const m of src.match(/'(?:[^'\\]|\\.)*'/g) || []) if (m.includes('<')) throw new Error('raw < in string: ' + m);
if (src.includes('<')) throw new Error('raw < anywhere in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= 본문 h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.charCountCalc, check = window.charCountCheck;
const H1000 = '가'.repeat(1000), H500 = '한'.repeat(500);
const cases = [
  ['빈 문자열', '', { chars: 0, noSpace: 0, lines: 0, words: 0, utf8: 0, euckr: 0, sheets: 0 }],
  ['가', '가', { chars: 1, utf8: 3, euckr: 2 }],
  ['A', 'A', { chars: 1, utf8: 1, euckr: 1 }],
  ['예문1', '안녕하세요. 반갑습니다.', { chars: 13, noSpace: 12, spaces: 1, words: 2, utf8: 33, euckr: 23 }],
  ['예문2', '저는 2026년 하반기 공채에 지원합니다.', { chars: 23, noSpace: 19, spaces: 4, words: 5, utf8: 51, euckr: 37 }],
  ['한글 1,000자', H1000, { chars: 1000, utf8: 3000, euckr: 2000, sheets: 5 }],
  ['1,001자 -> 원고지 6매', H1000 + '.', { sheets: 6 }],
  ['500자 -> 원고지 3매', H500, { sheets: 3 }],
  ['이모지', '😀', { chars: 1, utf16: 2, utf8: 4, euckr: 2 }],
  ['완성형 밖 글자 똠', '똠', { chars: 1, utf8: 3, euckr: 2 }],
  ['CRLF 줄바꿈', 'a\r\nb', { chars: 3, charsNoNewline: 2, newlines: 1, lines: 2, noSpace: 2 }],
  ['빈 줄 포함', '가\n\n나', { lines: 3, newlines: 2, chars: 4, noSpace: 2, words: 2 }],
  ['탭·전각공백', '가\t나　다', { spaces: 2, noSpace: 3 }],
];
for (const [name, text, exp] of cases) {
  const r = calc(text);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// UTF-8 값을 Node Buffer와 대조
for (const [, t] of cases) assert.strictEqual(calc(t).utf8, Buffer.byteLength(t.replace(/\r\n?/g, '\n'), 'utf8'));
console.log('PASS UTF-8 바이트 = Buffer.byteLength');
// TextEncoder 없을 때 수동 계산 경로도 같은 값
const TE = global.TextEncoder; delete global.TextEncoder; eval(src);
for (const [, t] of cases) assert.strictEqual(window.charCountCalc(t).utf8, Buffer.byteLength(t.replace(/\r\n?/g, '\n'), 'utf8'));
global.TextEncoder = TE; console.log('PASS TextEncoder 없는 경로');
// 바이트 제한 표: 한글만 n바이트에 들어가는 최대 글자
for (const [lim, e2, e3] of [[500, 250, 166], [1000, 500, 333], [2000, 1000, 666], [3000, 1500, 1000], [4000, 2000, 1333]]) {
  assert.ok(!check(calc('가'.repeat(e2)), lim, 'euckr').over); assert.ok(check(calc('가'.repeat(e2 + 1)), lim, 'euckr').over);
  assert.ok(!check(calc('가'.repeat(e3)), lim, 'utf8').over); assert.ok(check(calc('가'.repeat(e3 + 1)), lim, 'utf8').over);
}
console.log('PASS 바이트 제한 표 5행');
const k = check(calc('저는 2026년 하반기 공채에 지원합니다.'), 30, 'chars');
assert.deepStrictEqual(k, { value: 23, remain: 7, over: false }); console.log('PASS 제한 체크', JSON.stringify(k));
// UI 렌더 — 최소 DOM 스텁, 예문 버튼 클릭
const vals = { 'cc-text': '', 'cc-limit': '30', 'cc-unit': 'chars' };
const outP = [], handlers = {};
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener(e, f) { handlers[id + ':' + e] = f; }, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['cc-out', 'cc-sample', 'cc-clear', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
handlers['cc-sample:click']();
console.log('UI 예문 출력:', outP.join(' | '));
assert.ok(outP[0].startsWith('공백 포함: 40자 (줄바꿈 제외 39자)'));
assert.ok(outP.join().includes('10자 초과했습니다'));
vals['cc-unit'] = 'utf8'; vals['cc-limit'] = '100'; handlers['cc-unit:change']();
console.log('UI UTF-8 100바이트 제한:', outP[outP.length - 1]);
assert.ok(outP[outP.length - 1].includes('8바이트 남았습니다'));
console.log('ALL PASS');
