// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const check = window.seniorJobCheck;
const base = { birth: 1961, year: 2027, pension: 'basic', chasang: false, livelihood: false, work: false, ltc: 'none', two: false, fin: false, wish: 'all' };
const st = (o) => Object.fromEntries(check(Object.assign({}, base, o)).map(r => [r.key, r.status]));
const cases = [
  ['1961년생 2027년(66세) 기초연금 -> 전부 가능', {}, { public: 'ok', capacity: 'ok', community: 'ok', employ: 'ok', intern: 'ok' }],
  ['66세 연금 없음 -> 공익 불가, 역량 가능', { pension: 'none' }, { public: 'no', capacity: 'ok', community: 'ok' }],
  ['66세 직역연금 -> 공익 가능', { pension: 'jikyeok' }, { public: 'ok' }],
  ['1965년생 2027년(62세) 연금 없음 -> 공익 불가, 역량 조건부, 공동체 가능', { birth: 1965, pension: 'none' }, { public: 'no', capacity: 'cond', community: 'ok', employ: 'ok' }],
  ['62세 차상위 -> 공익 조건부', { birth: 1965, pension: 'none', chasang: true }, { public: 'cond' }],
  ['1968년생 2027년(59세) -> 전부 불가', { birth: 1968 }, { public: 'no', capacity: 'no', community: 'no', employ: 'no', intern: 'no' }],
  ['경계: 1962년생 2027년 = 65세 -> 공익 가능', { birth: 1962 }, { public: 'ok' }],
  ['경계: 1967년생 2027년 = 60세 -> 공동체 가능', { birth: 1967, pension: 'none' }, { community: 'ok', capacity: 'cond', public: 'no' }],
  ['생계급여 -> 공익·역량·공동체 불가, 취업형은 가능', { livelihood: true }, { public: 'no', capacity: 'no', community: 'no', employ: 'ok', intern: 'ok' }],
  ['직장가입자 -> 3유형 불가', { work: true }, { public: 'no', capacity: 'no', community: 'no' }],
  ['장기요양 1~5등급 -> 불가', { ltc: 'grade' }, { public: 'no', capacity: 'no', community: 'no' }],
  ['인지지원등급 -> 조건부', { ltc: 'cognitive' }, { public: 'cond', capacity: 'cond', community: 'cond' }],
  ['인지지원 + 연금 없음 -> 공익 불가 유지', { ltc: 'cognitive', pension: 'none' }, { public: 'no' }],
  ['일자리사업 2개 이상 -> 3유형 불가', { two: true }, { public: 'no', capacity: 'no', community: 'no', employ: 'ok' }],
  ['재정지원 일자리 참여 중 -> 취업알선·인턴십 불가', { fin: true }, { employ: 'no', intern: 'no', public: 'ok' }],
];
for (const [name, o, exp] of cases) {
  const r = st(o);
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
const one = check(Object.assign({}, base, { wish: 'public' }));
assert.strictEqual(one.length, 1); assert.ok(one[0].pay.includes('29만 원')); assert.ok(one[0].when.includes('확인하지 못했다'));
const y26 = check(Object.assign({}, base, { year: 2026, wish: 'capacity' }))[0];
assert.strictEqual(y26.age, 65); assert.ok(y26.pay.includes('76.1만 원')); assert.ok(y26.when.includes('끝났고'));
assert.strictEqual(check(Object.assign({}, base, { wish: 'intern' }))[0].when, '연중 선발');
console.log('PASS 희망 유형 필터·활동비·모집 시기 문구');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'sj-birth': '1961', 'sj-year': '2027', 'sj-pension': 'basic', 'sj-ltc': 'none', 'sj-wish': 'all' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['sj-out', 'sj-chasang', 'sj-livelihood', 'sj-work', 'sj-two', 'sj-fin', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('[신청 가능] 공익활동형'));
assert.ok(outP.join().includes('66세'));
