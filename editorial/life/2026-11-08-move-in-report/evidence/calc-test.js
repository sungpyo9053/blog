// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검증
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
assert.strictEqual(faq.mainEntity.length, (html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g) || []).length);
console.log('PASS 정적 검사(& < 빈 줄 0건, FAQ JSON-LD', faq.mainEntity.length, '개 = 본문 h3 수)');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.moveInCheck;
const iso = d => d.toISOString().slice(0, 10);
// 기한: 민법(초일 불산입) = +14, 안전(첫날 산입) = +13
let r = check('self', false, false, '2026-11-01', '');
assert.strictEqual(iso(r.civil), '2026-11-15'); assert.strictEqual(iso(r.safe), '2026-11-14'); assert.strictEqual(r.fine, null);
assert.ok(r.online); console.log('PASS 11/1 전입 -> 안전 11/14, 민법 11/15, 온라인 가능');
r = check('self', false, false, '2026-12-25', ''); assert.strictEqual(iso(r.civil), '2027-01-08'); console.log('PASS 연말 넘김 12/25 -> 2027-01-08');
r = check('self', false, false, '2028-02-20', ''); assert.strictEqual(iso(r.civil), '2028-03-05'); console.log('PASS 윤년 2028-02-20 -> 2028-03-05');
// 과태료 (시행령 별표 4 라목): 마감 2026-11-15 기준
const fines = [
  ['2026-11-15', 0], ['2026-11-16', 5000], ['2026-11-22', 5000], ['2026-11-23', 20000],
  ['2026-12-15', 20000], ['2026-12-16', 30000], ['2027-02-15', 30000], ['2027-02-16', 40000],
  ['2027-05-15', 40000], ['2027-05-16', 50000], ['2028-01-01', 50000], ['2026-11-03', 0],
];
for (const [rep, amt] of fines) {
  const f = check('self', false, false, '2026-11-01', rep).fine;
  assert.strictEqual(f.amount, amt, rep + ' ' + f.amount);
  console.log('PASS 신고일', rep, '-> 늦은 일수', f.late, '과태료', amt);
}
// 월말 클램프: 마감 1/31 + 1개월 = 2/28
const f = window.moveInFine(new Date(Date.UTC(2027, 0, 31)), new Date(Date.UTC(2027, 1, 28)));
assert.strictEqual(f.amount, 20000); console.log('PASS 마감 1/31 -> 2/28 신고는 1개월 이내 2만원');
// 상황별 경로
r = check('join', false, false, '2026-11-01', ''); assert.ok(r.online); assert.ok(r.items.join().includes('세대주의 확인')); assert.ok(r.notes.join().includes('8일'));
console.log('PASS 세대 합가 -> 온라인 가능, 세대주 확인·8일 자동취소 안내');
r = check('proxy', false, false, '2026-11-01', ''); assert.ok(!r.online); assert.ok(r.items.join().includes('위임장'));
console.log('PASS 대리 신고 -> 방문만, 위임장');
r = check('self', false, true, '2026-11-01', ''); assert.ok(!r.online); assert.ok(r.items.join().includes('출입국'));
console.log('PASS 재외국민·해외체류자 -> 방문만');
r = check('self', true, false, '2026-11-01', ''); assert.ok(r.items.join().includes('임대차계약서')); assert.ok(r.notes.join().includes('600원')); assert.ok(r.notes.join().includes('다음 날'));
console.log('PASS 임차인 -> 계약서·확정일자 600원·대항력 안내');
r = check('self', false, false, '', ''); assert.strictEqual(r.safe, null); console.log('PASS 날짜 없음 -> 기한 계산 생략');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'mv-case': 'join', 'mv-tenant': true, 'mv-abroad': false, 'mv-date': '2026-11-01', 'mv-report': '2026-11-20' };
const outP = [];
const mk = id => ({ value: vals[id], checked: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['mv-out', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => { const o = { style: {}, textContent: '' }; o.appendChild = c => { o.textContent += c.textContent; }; return o; } };
eval(src);
console.log('UI 출력:', outP.join(' | '));
assert.ok(outP.join().includes('2026년 11월 14일(토)')); assert.ok(outP.join().includes('5,000원'));
