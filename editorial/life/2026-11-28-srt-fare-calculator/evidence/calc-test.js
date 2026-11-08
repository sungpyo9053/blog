// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g) || []) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const S = window.srtFare;
// 1) 계산기 데이터 = 운임표 요약(evidence/srail-fare-20260901-summary.txt) JSON
const sum = fs.readFileSync(path.join(__dirname, 'srail-fare-20260901-summary.txt'), 'utf8');
assert.deepStrictEqual(S.F, JSON.parse(sum.split('\nJSON ')[1]));
console.log('PASS 계산기 운임 데이터 = 운임표 추출본');
// 2) 본문 표의 수서 출발 금액이 데이터와 같은지 (일반실 열)
const gen = {};
for (const l of Object.keys(S.F)) for (const [d, g, s] of S.F[l]['수서']) gen[d] = gen[d] || [g, s];
let n = 0;
const fares = html.split('<h2 id="fares">')[1].split('<h2 id="route">')[0];
for (const m of fares.matchAll(/<tr><td>([^<]+)<\/td><td>([\d,]+)<\/td>(?:<td>([\d,]+)<\/td>)?<td>([\d,]+)<\/td><\/tr>/g)) {
  const d = m[1], g = +m[2].replace(/,/g, ''), tot = +m[4].replace(/,/g, '');
  assert.ok(gen[d], 'no data ' + d);
  assert.strictEqual(g, gen[d][0], d + ' 일반실'); assert.strictEqual(tot, gen[d][1], d + ' 특실');
  if (m[3]) assert.strictEqual(+m[3].replace(/,/g, ''), gen[d][1] - gen[d][0], d + ' 특실요금');
  n++;
}
console.log('PASS 본문 운임표 ' + n + '행');
// 3) 운임·합계
const base = { line: 'gb', from: '수서', to: '부산', seat: 'gen', trip: 1, adult: 1, dcn: 0, dcr: 0, infant: 0, day: 'wk', when: 'd2' };
const T = o => S.total(Object.assign({}, base, o));
const cases = [
  ['수서→부산 일반실 1인', {}, { sum: 52900, refundFee: 0 }],
  ['수서→부산 특실 1인', { seat: 'spc' }, { sum: 76700 }],
  ['구포 경유 수서→부산 일반실', { line: 'gp' }, { sum: 47800 }],
  ['수서→광주송정 왕복 2인', { line: 'hn', to: '광주송정', trip: 2, adult: 2 }, { sum: 40900 * 4 }],
  ['할인 50% 1명 + 어른 1명, 특실(요금 할인 없음)', { seat: 'spc', dcn: 1, dcr: 50 }, { dc: 26450 + 23800, sum: 76700 + 50250 }],
  ['유아 2명·어른 1명 -> 1명 무임, 1명 확인 불가', { infant: 2 }, { freeInfant: 1, extraInfant: 1, sum: 52900 }],
  ['토요일 3시간 전까지 10%', { day: 'we', when: 'h3' }, { refundFee: 5290, refund: 47610 }],
  ['화요일 3시간 전까지 무료', { when: 'h3' }, { refundFee: 0 }],
  ['화요일 3시간 이내 5%', { when: 'h0' }, { refundFee: 2645 }],
  ['월~목 출발 후 20분 15%', { when: 'a20' }, { refundFee: 7935 }],
  ['금~일 출발 후 20분 30%', { day: 'we', when: 'a20' }, { refundFee: 15870 }],
  ['금~일 2일 전까지 최저 400원', { day: 'we', when: 'd2' }, { refundFee: 400 }],
  ['수서→동탄 7,500 금 1일 전 5%=375 -> 400', { to: '동탄', day: 'we', when: 'd1' }, { refundFee: 400 }],
  ['도착 후 100%', { when: 'done' }, { refundFee: 52900, refund: 0 }],
  ['2인 금~일 2일 전 -> 400 x 2', { adult: 2, day: 'we', when: 'd2' }, { refundFee: 800 }],
];
for (const [name, o, exp] of cases) {
  const r = T(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify({ sum: r.sum, dc: r.dc, refundFee: r.refundFee, refund: r.refund, freeInfant: r.freeInfant }));
}
// 4) 서울 출발 비교표의 수서 열 = 데이터
const seoul = html.split('<h2 id="seoul">')[1].split('</table>')[0];
for (const m of seoul.matchAll(/<tr><td>([^<]+)<\/td><td>([\d,]+)<\/td><td>([\d,]+)<\/td><td>([\d,]+)<\/td><\/tr>/g)) {
  const a = +m[2].replace(/,/g, ''), b = +m[3].replace(/,/g, ''), d = +m[4].replace(/,/g, '');
  assert.strictEqual(b - a, d, m[1] + ' 차이');
  const key = m[1] === '부산(경주 경유)' ? ['gb', '부산'] : m[1] === '부산(구포 경유)' ? ['gp', '부산'] : [null, m[1]];
  const v = key[0] ? S.fare(key[0], '수서', key[1]).gen : gen[key[1]][0];
  assert.strictEqual(a, v, m[1] + ' 수서');
}
console.log('PASS 서울 출발 비교표 수서 열·차이');
// 5) UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'srt-line': 'gb', 'srt-from': '수서', 'srt-to': '', 'srt-seat': 'gen', 'srt-trip': '1', 'srt-adult': '1', 'srt-infant': '0', 'srt-dcn': '0', 'srt-dcr': '0', 'srt-day': 'wk', 'srt-when': 'd2' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = v; }, style: {}, addEventListener() {}, set innerHTML(v) { if (id === 'srt-out') outP.length = 0; }, appendChild(p) { if (id === 'srt-out') outP.push(p.textContent); } });
const els = {}; ['srt-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('52,900원'));
