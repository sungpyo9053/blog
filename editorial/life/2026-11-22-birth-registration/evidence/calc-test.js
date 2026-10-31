// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.birthRegCheck;
const iso = d => d.toISOString().slice(0, 10);
const cases = [
  // [이름, 출생일, 예정일, 방법, 장소, 기대]
  ['본문 예: 11.22생 12.15 신고', '2026-11-22', '2026-12-15', 'online', 'hospital', { deadline: '2026-12-21', extended: '2026-12-21', daysLeft: 6, late: false, fine: 0 }],
  ['마감 당일 신고', '2026-11-22', '2026-12-21', 'dong', 'hospital', { daysLeft: 0, late: false, fine: 0 }],
  ['1.31생: 2월 말일 마감, 일요일+3·1절 -> 3.2', '2027-01-31', '2027-02-20', 'online', 'hospital', { deadline: '2027-02-28', extended: '2027-03-02' }],
  ['3.1생: 월초 기산 -> 3.31', '2026-03-01', '2026-03-10', 'dong', 'hospital', { deadline: '2026-03-31' }],
  ['윤년 1.30생 -> 2.29', '2028-01-30', '2028-02-01', 'dong', 'hospital', { deadline: '2028-02-29' }],
  ['12월생 연도 넘김', '2026-12-15', '2027-01-02', 'dong', 'hospital', { deadline: '2027-01-14' }],
  ['1일 지연 -> 1만', '2026-11-22', '2026-12-22', 'dong', 'hospital', { late: true, lateDays: 1, fine: 10000 }],
  ['6일 지연 -> 1만', '2026-11-22', '2026-12-27', 'dong', 'hospital', { lateDays: 6, fine: 10000 }],
  ['7일 지연 -> 2만', '2026-11-22', '2026-12-28', 'dong', 'hospital', { lateDays: 7, fine: 20000 }],
  ['1개월 직전 -> 2만', '2026-11-22', '2027-01-20', 'dong', 'hospital', { fine: 20000 }],
  ['1개월 -> 3만', '2026-11-22', '2027-01-21', 'dong', 'hospital', { fine: 30000 }],
  ['3개월 -> 4만', '2026-11-22', '2027-03-21', 'dong', 'hospital', { fine: 40000 }],
  ['6개월 -> 5만', '2026-11-22', '2027-06-21', 'dong', 'hospital', { fine: 50000 }],
  ['1년 -> 상한 5만', '2026-11-22', '2027-12-01', 'dong', 'hospital', { fine: 50000 }],
  ['60일: 1.1생 -> 3.1', '2026-01-01', '2026-01-20', 'dong', 'hospital', { sixty: '2026-03-01', sixtyOk: true }],
];
for (const [name, b, p, m, pl, exp] of cases) {
  const r = check(b, p, m, pl);
  for (const k of Object.keys(exp)) {
    const v = r[k] instanceof Date ? iso(r[k]) : r[k];
    assert.strictEqual(v, exp[k], name + ' ' + k + '=' + v);
  }
  console.log('PASS', name, JSON.stringify({ deadline: iso(r.deadline), extended: iso(r.extended), daysLeft: r.daysLeft, lateDays: r.lateDays, fine: r.fine }));
}
// 오류 입력
assert.ok(check('', '2026-12-01', 'online', 'hospital').error);
assert.ok(check('2026-11-22', '2026-11-01', 'online', 'hospital').error);
console.log('PASS 입력 오류 2건');
// 방법·장소별 준비물 분기
const on = check('2026-11-22', '2026-12-01', 'online', 'hospital');
assert.ok(on.docs.join().includes('인증서')); assert.ok(on.svc[0].includes('정부24'));
const onOut = check('2026-11-22', '2026-12-01', 'online', 'outside');
assert.ok(onOut.notes[0].includes('방문 신고')); assert.ok(onOut.docs.join().includes('119'));
const off = check('2026-11-22', '2026-12-01', 'office', 'hospital');
assert.ok(off.docs.join().includes('출생신고서')); assert.ok(off.svc[0].includes('시청·구청'));
console.log('PASS 분기 3건');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'br-birth': '2026-11-22', 'br-plan': '2026-12-15', 'br-method': 'online', 'br-place': 'hospital' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['br-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2026년 12월 21일(월)'));
assert.ok(outP.join().includes('6일 남았다'));
// 주말 연장 구간 안 신고 — 보수적으로 과태료 표시 + 연장 안내 플래그
global.document = { getElementById: () => null }; eval(src);
const ext = window.birthRegCheck('2027-01-31', '2027-03-02', 'dong', 'hospital');
assert.strictEqual(ext.late, true); assert.strictEqual(ext.inExt, true); assert.strictEqual(ext.fine, 10000);
console.log('PASS 연장 구간 3.2 신고: inExt=true, 보수적 표시 1만');
