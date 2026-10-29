// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^']*'/g)) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const fine = window.carInsFine, grade = window.carInsGrade, label = window.carInsLabel;
// 과태료: 시행령 별표 5 (2026.9.15. 개정)
const fc = [
  ['비사업용 둘다 1일', 'car', 'both', 1, 15000],
  ['비사업용 둘다 10일', 'car', 'both', 10, 15000],
  ['비사업용 대인 11일 = 1만+4천', 'car', 'd', 11, 14000],
  ['비사업용 둘다 30일', 'car', 'both', 30, 90000 + 45000],
  ['비사업용 대인 157일 = 598,000', 'car', 'd', 157, 598000],
  ['비사업용 대인 158일 상한 60만', 'car', 'd', 158, 600000],
  ['비사업용 대물 1년 상한 30만', 'car', 'p', 365, 300000],
  ['사업용 대인 30일 = 3만+20*8천', 'biz', 'd', 30, 190000],
  ['사업용 대인 1년 상한 100만', 'biz', 'd', 365, 1000000],
  ['사업용 대물 30일 = 5천+20*2천', 'biz', 'p', 30, 45000],
  ['이륜 대인 20일 = 6천+10*1,200', 'bike', 'd', 20, 18000],
  ['이륜 둘다 1년 = 20만+10만', 'bike', 'both', 365, 300000],
  ['이륜 대물 20일 = 3천+10*600', 'bike', 'p', 20, 9000],
  ['0일 = 0', 'car', 'both', 0, 0],
];
for (const [n, t, c, d, exp] of fc) {
  const r = fine(t, c, d);
  assert.strictEqual(r.total, exp, n + ' total=' + r.total);
  console.log('PASS', n, JSON.stringify(r));
}
// 등급: 보험개발원 사고점수 (가)(나) 규칙
const z = { s4: 0, s3: 0, s2: 0, s1: 0, self: 0, pover: 0, punder: 0 };
const gc = [
  ['물적 이하 1건 0.5점 -> 유지', 11, { punder: 1 }, 0.5, 11, '11Z'],
  ['물적 이하 2건 1점 -> 1등급 할증', 11, { punder: 2 }, 1, 10, '10Z'],
  ['물적 초과 1건 -> 1등급', 15, { pover: 1 }, 1, 14, '14Z'],
  ['부상 2~7급 1건 3점 11Z -> 8Z', 11, { s3: 1 }, 3, 8, '8Z'],
  ['사망 4점 + 물적이하 0.5 = 4.5점 15Z -> 10F', 15, { s4: 1, punder: 1 }, 4.5, 10.5, '10F'],
  ['3Z에서 4점 -> 최고할증 1Z', 3, { s4: 1 }, 4, 1, '1Z'],
  ['18F(18.5)에서 자손 1점 -> 17F', 18.5, { self: 1 }, 1, 17.5, '17F'],
];
for (const [n, prev, cnt, pts, next, lab] of gc) {
  const r = grade(prev, Object.assign({}, z, cnt));
  assert.strictEqual(r.points, pts, n + ' pts'); assert.strictEqual(r.next, next, n + ' next'); assert.strictEqual(label(r.next), lab, n + ' label');
  console.log('PASS', n, JSON.stringify(r), label(r.next));
}
// 상황 4종 데이터
for (const k of ['new', 'renew', 'accident', 'change']) {
  const s = window.carInsSit[k];
  assert.ok(s.steps.length >= 3 && s.docs.length >= 2 && s.route && s.warn.length >= 1, k);
}
console.log('PASS 상황 4종 데이터');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'ci-sit': 'renew', 'ci-prev': '11', 'ci-s4': '0', 'ci-s3': '0', 'ci-s2': '0', 'ci-s1': '0', 'ci-self': '0', 'ci-pover': '0', 'ci-punder': '1', 'ci-type': 'car', 'ci-cover': 'both', 'ci-days': '30' };
const outs = {};
const mk = tag => { const e = { tag, style: {}, kids: [], textContent: '', appendChild(c) { this.kids.push(c); } }; return e; };
const el = id => ({ value: vals[id], style: {}, kids: [], addEventListener() {}, set innerHTML(v) { this.kids = []; }, appendChild(c) { this.kids.push(c); } });
const els = {}; ['ci-out', 'ci-grade-out', 'ci-fine-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
const flat = n => (n.textContent || '') + ' ' + (n.kids || []).map(flat).join(' ');
const sitTxt = els['ci-out'].kids.map(flat).join(' | ');
const gTxt = els['ci-grade-out'].kids.map(flat).join(' | ');
const fTxt = els['ci-fine-out'].kids.map(flat).join(' | ');
console.log('UI 상황(갱신):', sitTxt.replace(/\s+/g, ' ').slice(0, 160) + '...');
console.log('UI 등급:', gTxt.replace(/\s+/g, ' '));
console.log('UI 과태료:', fTxt.replace(/\s+/g, ' '));
assert.ok(sitTxt.includes('보험다모아 갱신 조회'));
assert.ok(gTxt.includes('11Z'));
assert.ok(fTxt.includes('135,000원'));
console.log('ALL PASS');
