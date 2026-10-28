// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.acquisitionTaxCalc;
// [이름, 가액, 주택수, 조정, 일시적2주택, 면적, 생애최초, 기대값]
const cases = [
  ['5억 1주택 84㎡', 5e8, 1, false, false, 84, 0, { rate: 0.01, acq: 5000000, edu: 500000, agri: 0, total: 5500000 }],
  ['6억 경계 = 1%', 6e8, 1, false, false, 84, 0, { rate: 0.01, acq: 6000000 }],
  ['7억 -> 1.67% (반올림)', 7e8, 1, false, false, 84, 0, { rate: 0.0167, acq: 11690000, edu: 1169000, total: 12859000 }],
  ['7.5억 -> 2%', 7.5e8, 1, false, false, 84, 0, { rate: 0.02, acq: 15000000 }],
  ['8억 -> 2.33%, 100㎡ 농특 0.2%', 8e8, 1, false, false, 100, 0, { rate: 0.0233, acq: 18640000, edu: 1864000, agri: 1600000, total: 22104000 }],
  ['9억 경계 = 3%', 9e8, 1, false, false, 84, 0, { rate: 0.03, acq: 27000000 }],
  ['10억 85㎡ 초과', 10e8, 1, false, false, 101, 0, { acq: 30000000, edu: 3000000, agri: 2000000, total: 35000000 }],
  ['85㎡ 정확히 -> 농특 비과세', 10e8, 1, false, false, 85, 0, { agri: 0 }],
  ['조정 2주택 8억 -> 8%', 8e8, 2, true, false, 84, 0, { lv: 1, acq: 64000000, edu: 3200000, agri: 0, total: 67200000 }],
  ['조정 2주택 8억 100㎡ -> 농특 0.6%', 8e8, 2, true, false, 100, 0, { agri: 4800000, total: 72000000 }],
  ['조정 일시적 2주택 -> 기본세율', 8e8, 2, true, true, 84, 0, { lv: 0, rate: 0.0233 }],
  ['비조정 2주택 -> 기본세율', 5e8, 2, false, false, 84, 0, { lv: 0, acq: 5000000 }],
  ['비조정 3주택 -> 8%', 5e8, 3, false, false, 84, 0, { lv: 1, acq: 40000000, edu: 2000000 }],
  ['조정 3주택 8억 100㎡ -> 12%, 농특 1.0%', 8e8, 3, true, false, 100, 0, { lv: 2, acq: 96000000, edu: 3200000, agri: 8000000, total: 107200000 }],
  ['비조정 4주택 -> 12%', 5e8, 4, false, false, 84, 0, { lv: 2, acq: 60000000 }],
  ['생애최초 3억 59㎡ 일반 -> 200만 감면', 3e8, 1, false, false, 59, 2, { cut: 2000000, acq: 1000000, edu: 300000, total: 1300000 }],
  ['생애최초 소형 2.5억 -> 전액 면제(300만 한도)', 2.5e8, 1, false, false, 59, 3, { cut: 2500000, acq: 0, edu: 250000 }],
  ['생애최초 7억 100㎡ -> 감면분 농특 20%', 7e8, 1, false, false, 100, 2, { cut: 2000000, acq: 9690000, agri: 1400000 + 400000 }],
  ['생애최초 12억 경계 적용', 12e8, 1, false, false, 84, 2, { firstOk: true, cut: 2000000 }],
  ['생애최초 12억 초과 미적용', 12.1e8, 1, false, false, 84, 2, { firstOk: false, cut: 0 }],
  ['생애최초 2주택이면 미적용', 5e8, 2, false, false, 84, 2, { firstOk: false, cut: 0 }],
];
for (const [name, v, h, adj, temp, area, first, exp] of cases) {
  const r = calc(v, h, adj, temp, area, first);
  for (const k of Object.keys(exp)) assert.ok(r[k] === exp[k] || Math.abs(r[k] - exp[k]) < 1e-9, name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값 검산 (85㎡ 이하 / 초과 합계)
const table = [[3, 3300000, 3900000], [5, 5500000, 6500000], [6, 6600000, 7800000], [7, 12859000, 14259000], [8, 20504000, 22104000], [9, 29700000, 31500000], [10, 33000000, 35000000], [12, 39600000, 42000000]];
for (const [e, a, b] of table) { assert.strictEqual(calc(e * 1e8, 1, false, false, 84, 0).total, a, e + '억'); assert.strictEqual(calc(e * 1e8, 1, false, false, 100, 0).total, b, e + '억 초과'); }
console.log('PASS 표 값 16개');
// UI 기본값(5억, 1주택, 84㎡) 렌더 확인 — 최소 DOM 스텁
const vals = { 'at-price': '50000', 'at-houses': '1', 'at-area': '84', 'at-first': '0' };
const checks = { 'at-adj': false, 'at-temp': false };
const outP = [];
const el = id => ({ value: vals[id], checked: checks[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['at-out', ...Object.keys(vals), ...Object.keys(checks)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('합계: 5,500,000원'));
