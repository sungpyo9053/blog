// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.bulkyWasteCalc, BWD = window.BW;
assert.strictEqual(Object.keys(BWD).length, 26);
// 1) 별표에서 직접 읽은 값 대조 (evidence/law-*.txt 행)
const spot = [
  ['gangnam', 0, 10000], ['gangnam', 1, 15000], ['gangnam', 6, 8000],
  ['jongno', 0, 15000], ['dongjak', 0, 15000], ['suwon', 0, 6000],
  ['seocho', 1, 23000], ['dobong', 1, 12000], ['nowon', 1, 12000],
  ['seongdong', 3, 5000], ['yangcheon', 0, 10000], ['yangcheon', 3, 8000], ['seodaemun', 3, 15000], ['eunpyeong', 3, 15000],
  ['mapo', 0, 13500], ['mapo', 3, 12000], ['changwon', 6, 10000], ['gangbuk', 7, 10000],
];
for (const [k, i, v] of spot) { assert.strictEqual(BWD[k][4][i], v, k + ' ' + i); }
console.log('PASS 별표 대조', spot.length, '건');
// 2) 본문 예시: 강남 장롱1+침대1+소파1+냉장고1
let r = calc('gangnam', [1, 1, 0, 1, 0, 0, 1, 0], true);
assert.strictEqual(r.total, 32000); console.log('PASS 강남 기본값(가전 무상)', r.total);
r = calc('gangnam', [1, 1, 0, 1, 0, 0, 1, 0], false);
assert.strictEqual(r.total, 40000); console.log('PASS 강남 기본값(가전 조례 금액)', r.total);
// 3) 본문 이삿짐 예시: 장롱3+침대+소파+식탁
for (const [k, v] of [['gangnam', 57000], ['mapo', 71500], ['dobong', 62000]]) {
  r = calc(k, [3, 1, 0, 1, 1, 0, 0, 0], true); assert.strictEqual(r.total, v, k); console.log('PASS 이삿짐', BWD[k][0], r.total);
}
// 4) 규격 기준이 달라 합계에서 빠지는 경우
r = calc('gwanak', [0, 0, 0, 2, 0, 0, 0, 0], false);
assert.strictEqual(r.total, 0); assert.strictEqual(r.missing.length, 1); console.log('PASS 관악 소파 합계 제외:', r.missing[0]);
r = calc('gangdong', [0, 0, 0, 0, 0, 1, 0, 0], false); assert.strictEqual(r.missing.length, 1); console.log('PASS 강동 책상 합계 제외');
// 5) 조례상 무상·면제 가전
r = calc('dobong', [0, 0, 0, 0, 0, 0, 1, 1], false); assert.strictEqual(r.total, 0); console.log('PASS 도봉 냉장고·세탁기 면제 0원');
r = calc('seodaemun', [0, 0, 0, 0, 0, 0, 2, 0], true); assert.strictEqual(r.total, 0); assert.ok(r.lines[0][3].includes('30,000원') && !/NaN/.test(r.lines[0][3])); console.log('PASS 서대문 냉장고 2대 무상방문수거 0원 (조례 기준 30,000원)');
// 6) 음수·소수·빈칸 방어
r = calc('guro', [-2, '1.7', '', 0, 0, 0, 0, 0], false); assert.strictEqual(r.total, 15000); console.log('PASS 음수·소수·빈칸 처리', r.total);
assert.strictEqual(calc('nope', [], false), null);
// 7) 본문 비교표 숫자가 데이터와 같은지
const fmt = v => v === null ? '규격 다름' : (v === 0 ? '무상·면제' : v.toLocaleString('en-US') + '원');
for (const k of Object.keys(BWD)) {
  const d = BWD[k], v = d[4], name = d[0] + (d[1] === '서울' ? '' : '(' + d[1] + ')');
  const row = '<tr><td>' + name + '</td><td>' + [v[0], v[1], v[3], v[6], v[7]].map(fmt).join('</td><td>') + '</td></tr>';
  assert.ok(html.includes(row), 'table row ' + k);
}
console.log('PASS 비교표 26행 일치');
// 8) UI 렌더(최소 DOM 스텁)
const els = {}, outP = [];
function mk(id) { return { id, value: '', checked: true, style: {}, children: [], addEventListener() {}, appendChild(c) { this.children.push(c); if (id === 'bw-items') { (c.children || []).forEach(l => (l.children || []).forEach(x => { if (x.id) els[x.id] = x; })); } if (id === 'bw-out') outP.push(c.textContent); }, set innerHTML(v) { if (id === 'bw-out') outP.length = 0; } }; }
['bw-gu', 'bw-items', 'bw-free', 'bw-out'].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => mk(''), createTextNode: t => ({ textContent: t }) };
els['bw-gu'].appendChild = function (og) { (og.children || []).forEach(o => { if (o.selected) this.value = o.value; }); };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP[0].includes('강남구 합계: 32,000원'));
console.log('ALL PASS');
