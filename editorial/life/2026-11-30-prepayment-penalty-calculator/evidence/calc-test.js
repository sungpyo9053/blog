// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
for (const ch of ['&', '<']) if (src.indexOf(ch) >= 0) throw new Error(ch + ' found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ JSON-LD', faq, '= h3', h3faq);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.prepayFeeCalc, R = window.prepayFeeRates;
const cases = [
  ['주담대 1억 0.75% 1년 후(30년 만기)', 1e8, 0.75, '2026-01-15', '2027-01-15', '2056-01-15', 3, { fee: 500228, denom: 1096, remain: 731, limited: false }],
  ['같은 대출 2년 후', 1e8, 0.75, '2026-01-15', '2028-01-15', '2056-01-15', 3, { remain: 366, fee: 250456 }],
  ['같은 대출 3년 되는 날 -> 0원', 1e8, 0.75, '2026-01-15', '2029-01-15', '2056-01-15', 3, { fee: 0, exempt: '적용기간 경과' }],
  ['3년 지난 뒤 -> 0원', 1e8, 0.75, '2026-01-15', '2030-06-01', '2056-01-15', 3, { fee: 0, exempt: '적용기간 경과' }],
  ['전세 2억 0.54% 2년 만기 1년 후', 2e8, 0.54, '2026-05-01', '2027-05-01', '2028-05-01', 3, { fee: 540738, denom: 731, remain: 366, limited: true }],
  ['신용 5천만 0.18% 1년 만기 6개월 후', 5e7, 0.18, '2026-03-01', '2026-09-01', '2027-03-01', 3, { fee: 44630, denom: 365, remain: 181 }],
  ['만기일 상환 -> 0원', 5e7, 0.18, '2026-03-01', '2027-03-01', '2027-03-01', 3, { fee: 0, exempt: '만기' }],
  ['실행 당일 상환 -> 수수료율 그대로', 1e8, 0.75, '2026-01-15', '2026-01-15', '', 3, { fee: 750000 }],
  ['수수료율 0% -> 0원', 1e8, 0, '2026-01-15', '2026-06-01', '', 3, { fee: 0, ok: true }],
];
for (const [name, a, r, s, p, m, y, exp] of cases) {
  const o = calc(a, r, s, p, m, y);
  for (const k of Object.keys(exp)) assert.strictEqual(o[k], exp[k], name + ' ' + k + '=' + o[k]);
  console.log('PASS', name, JSON.stringify(o));
}
assert.ok(!calc(1e8, 0.75, '2027-01-01', '2026-01-01', '', 3).ok); console.log('PASS 상환일이 실행일보다 빠르면 오류');
assert.ok(!calc(0, 0.75, '2026-01-01', '2026-06-01', '', 3).ok); console.log('PASS 금액 0 오류');
// 공시 데이터가 evidence JSON(은행연합회 원본 파싱)과 일치하는지
const keys = ['부동산 및 동산', '보증서 및 기타', '신용'];
for (const y of ['2026', '2025']) {
  const j = JSON.parse(fs.readFileSync(path.join(__dirname, 'kfb-prepay-' + y + '.json'), 'utf8'));
  let n = 0;
  for (const b of Object.keys(j)) keys.forEach((k, i) => ['fix', 'var'].forEach((f, q) => {
    const raw = j[b][k][f], v = R[y][b][i * 2 + q];
    assert.strictEqual(v, raw === '-' ? null : parseFloat(raw), y + ' ' + b + ' ' + k + ' ' + f); n++;
  }));
  console.log('PASS', y, '공시 수수료율', n, '칸 일치');
}
// 본문 표(2026)도 같은 값인지
const rows = [...html.split('<h2 id="rates">')[1].split('</tbody>')[0].matchAll(/<tr><td>([^<]+)<\/td>((?:<td>[^<]*<\/td>){6})<\/tr>/g)];
assert.strictEqual(rows.length, 19);
for (const [, b, cells] of rows) [...cells.matchAll(/<td>([^<]*)<\/td>/g)].forEach((c, i) => {
  const v = R[2026][b][i]; assert.strictEqual(c[1], v === null ? '-' : v.toFixed(2) + '%', b + i);
});
console.log('PASS 본문 2026 표 19행 x 6칸 일치');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'pp-amt': '100000000', 'pp-year': '2026', 'pp-bank': '', 'pp-type': '0', 'pp-kind': '0', 'pp-rate': '', 'pp-start': '2026-01-15', 'pp-repay': '2027-01-15', 'pp-mat': '2056-01-15', 'pp-yrs': '3', 'pp-ir': '4' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, style: {}, addEventListener() {}, set innerHTML(v) {}, appendChild() {} });
els['pp-out'] = { style: {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 수수료율:', vals['pp-rate'], '/ 출력:', outP.join(' | '));
assert.strictEqual(vals['pp-rate'], '0.75');
assert.ok(outP[0].includes('500,228원'));
