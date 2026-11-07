// ko.html 계산기 <script>를 그대로 뽑아 node에서 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert.ok(src.indexOf('&') === -1, '& in script');
assert.ok(src.indexOf('<') === -1, '< in script');
assert.ok(!/\n\s*\n/.test(src), 'blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
assert.ok(ld.indexOf('&') === -1 && ld.indexOf('<') === -1); JSON.parse(ld);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const calc = window.phCalc, inc = window.phIncome;
// 구로구 2026 표의 본인부담금(천원) — 가격-정부지원이 표 값과 같은지 전 칸 검산
const SELF = {
  A1: { ga: [73, 299, 671], tong: [163, 462, 893], ra: [276, 700, 1161] },
  A2: { ga: [119, 402, 834], tong: [299, 671, 1161], ra: [521, 1003, 1488] },
  A3: { ga: [90, 358, 774], tong: [269, 648, 1131], ra: [491, 960, 1429] },
  B1: { ga: [74, 391, 893], tong: [260, 698, 1228], ra: [558, 1143, 1712] },
  B2: { ga: [234, 794, 1407], tong: [479, 1107, 1781], ra: [844, 1574, 2343] },
  C1: { ga: [113, 937, 2696], tong: [561, 1872, 3745], ra: [1291, 2903, 5244] },
  C2: { ga: [130, 1084, 3120], tong: [649, 2166, 4333], ra: [1494, 3359, 6068] },
  D1: { ga: [122, 1008, 2901], tong: [604, 2014, 4030], ra: [1390, 3124, 5643] },
  D2: { ga: [175, 1451, 4180], tong: [870, 2902, 5806], ra: [2002, 4500, 8129] },
};
let n = 0;
for (const t in SELF) for (const tier in SELF[t]) SELF[t][tier].forEach((v, i) => { assert.strictEqual(calc(t, i, tier).self, v * 1000, t + tier + i); n++; });
console.log('PASS 본인부담금 표 ' + n + '칸 일치');
const r = calc('A1', 1, 'tong'); assert.deepStrictEqual(r, { days: 10, price: 1464000, gov: 1002000, self: 462000 });
console.log('PASS 단태아 첫째 표준 통합형', JSON.stringify(r));
console.log('PASS 삼태아 3명 연장 라형', JSON.stringify(calc('C2', 2, 'ra')));
// 성북구 맞벌이 예시: 30,000 x 0.5 + 40,000 = 55,000
assert.strictEqual(inc(3, 0, 30000, 40000, true).sum, 55000); console.log('PASS 맞벌이 감경 예시 55,000원');
assert.strictEqual(inc(3, 2, 30000, 40000, true).sum, 70000); console.log('PASS 혼합은 감경 없이 합산 70,000원');
assert.strictEqual(inc(3, 0, 290169, 0, false).under, true); assert.strictEqual(inc(3, 0, 290170, 0, false).under, false);
console.log('PASS 3인 직장 경계 290,169원 이하/초과');
// UI 기본값 렌더(최소 DOM 스텁)
const vals = { 'ph-type': 'A1', 'ph-period': '1', 'ph-tier': 'auto', 'ph-n': '3', 'ph-kind': '0', 'ph-mom': '120000', 'ph-dad': '150000', 'ph-local': '0' };
const out = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {}, options: [{}, {}, {}] });
els['ph-dual'] = { checked: true, addEventListener() {} };
els['ph-out'] = { set innerHTML(v) { out.length = 0; }, appendChild(p) { out.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값:', out.join(' | '));
assert.ok(out.join().includes('본인부담금 462,000원'));
els['ph-local'].value = '90'; els['ph-tier'].value = 'ga';
// 다시 실행: change 핸들러 대신 스크립트 재평가
eval(src);
console.log('UI 가형+90%:', out.join(' | '));
assert.ok(out.join().includes('실제 부담 29,900원'));
