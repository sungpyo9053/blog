// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string literal ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.musicCalc;
const C = (n, o = {}) => Object.assign({ n, pc: false, off: false, ll: false, stu: false }, o);
const top = c => calc(c).list[0];
const cases = [
  ['1명 휴대폰만 -> 7,590원(멜론·FLO·벅스 동률)', C(1), r => { assert.strictEqual(r.list[0].total, 7590); assert.deepStrictEqual(r.list.slice(0, 3).map(x => x.svc).sort(), ['FLO', '멜론', '벅스'].sort()); }],
  ['1명 PC -> 8,690원', C(1, { pc: true }), r => assert.strictEqual(r.list[0].total, 8690)],
  ['1명 오프라인 -> 애플뮤직 8,900원', C(1, { off: true }), r => { assert.strictEqual(r.list[0].svc, '애플뮤직'); assert.strictEqual(r.list[0].total, 8900); }],
  ['1명 무손실 휴대폰 -> 벅스 7,590원', C(1, { ll: true }), r => { assert.strictEqual(r.list[0].svc, '벅스'); assert.strictEqual(r.list[0].total, 7590); }],
  ['1명 오프라인+무손실+PC -> 애플 8,900, 지니·FLO·멜론·유튜브 제외', C(1, { off: true, ll: true, pc: true }), r => { assert.strictEqual(r.list[0].total, 8900); assert.deepStrictEqual(r.none.sort(), ['FLO', '멜론', '유튜브 뮤직', '지니'].sort()); }],
  ['1명 대학생 오프라인 -> 스포티파이 학생 6,600원', C(1, { off: true, stu: true }), r => { assert.strictEqual(r.list[0].svc, '스포티파이'); assert.strictEqual(r.list[0].total, 6600); }],
  ['2명 대학생 체크 -> 학생 요금 미적용, 스포티파이 듀오 17,985원', C(2, { off: true, stu: true }), r => assert.strictEqual(r.list.find(x => x.svc === '스포티파이').total, 17985)],
  ['2명 오프라인 -> 애플 가족 13,500원(1인 6,750)', C(2, { off: true }), r => { assert.strictEqual(r.list[0].total, 13500); assert.strictEqual(r.list[0].per, 6750); }],
  ['2명 오프라인 -> 벅스 크루 21,010원', C(2, { off: true }), r => assert.strictEqual(r.list.find(x => x.svc === '벅스').total, 11990 + 9020)],
  ['4명 오프라인 -> 애플 13,500 / 스포티파이 35,970 / 벅스 39,050 / 멜론 47,960', C(4, { off: true }), r => {
    const g = s => r.list.find(x => x.svc === s).total;
    assert.strictEqual(g('애플뮤직'), 13500); assert.strictEqual(g('스포티파이'), 35970); assert.strictEqual(g('벅스'), 39050); assert.strictEqual(g('멜론'), 47960); assert.strictEqual(g('유튜브 뮤직'), 47960); }],
  ['3명 오프라인 -> 스포티파이 듀오+개인 29,975원', C(3, { off: true }), r => assert.strictEqual(r.list.find(x => x.svc === '스포티파이').total, 29975)],
  ['2명 휴대폰만 -> 애플 가족 13,500 < 벅스 크루 13,530', C(2), r => { assert.strictEqual(r.list[0].total, 13500); assert.strictEqual(r.list.find(x => x.svc === '벅스').total, 13530); }],
  ['5명 PC -> 벅스 크루4명+개인1명 = 8,690+3x6,490+8,690', C(5, { pc: true }), r => assert.strictEqual(r.list.find(x => x.svc === '벅스').total, 8690 + 3 * 6490 + 8690)],
  ['6명 오프라인 -> 애플 가족 1개 13,500원', C(6, { off: true }), r => assert.strictEqual(r.list[0].total, 13500)],
  ['멜론 오프라인+무손실 -> 조건 맞는 이용권 없음', C(1, { off: true, ll: true }), r => assert.ok(r.none.includes('멜론'))],
];
for (const [name, c, check] of cases) { const r = calc(c); check(r); console.log('PASS', name, '|', r.list.map(x => x.svc + ' ' + x.total).join(', '), r.none.length ? '| 없음: ' + r.none.join(',') : ''); }
// UI 기본값(1명, 조건 없음) 렌더 — 최소 DOM 스텁
const vals = { 'mu-n': { value: '1' }, 'mu-pc': { checked: false }, 'mu-off': { checked: false }, 'mu-ll': { checked: false }, 'mu-stu': { checked: false } };
const outP = [];
const els = { 'mu-out': { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } } };
for (const k of Object.keys(vals)) els[k] = Object.assign({ addEventListener() {} }, vals[k]);
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:\n' + outP.join('\n'));
assert.ok(outP[0].includes('7,590원'));
