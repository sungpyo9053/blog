// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
for (const m of src.match(/'(?:[^'\\\n]|\\.)*'/g) || []) if (m.includes('<')) throw new Error('raw < in string literal ' + m);
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const J = window.nesJudge;
const base = { year: 2026, age: 30, mil: 0, size: 1, income: 0, own: 0, prop: 0, exp: true, ui: 'none', kid: 0, old: 0, dis: 0 };
const cases = [
  ['1인 30세 150만 경험O -> 요건심사형 360만', { income: 1500000 }, { t1: '요건심사형', total: 3600000, success: true, t2: '청년' }],
  ['1인 60% 경계 1,538,543 -> 요건심사형', { income: 1538543 }, { t1: '요건심사형', lim60: 1538543 }],
  ['4인 45세 380만 재산3억 자녀2 -> 월80만 480만', { size: 4, age: 45, income: 3800000, prop: 300000000, kid: 2 }, { t1: '요건심사형', family: 200000, total: 4800000, t2: '중장년' }],
  ['4인 45세 400만 -> Ⅰ 불가, Ⅱ 중장년, 성공수당X', { size: 4, age: 45, income: 4000000 }, { t1: '', t2: '중장년', success: false }],
  ['4인 45세 700만 -> Ⅱ 불가(특정계층만)', { size: 4, age: 45, income: 7000000 }, { t1: '', t2: '' }],
  ['3인 28세 600만 재산4.5억 경험X -> 청년특례, 성공X', { size: 3, age: 28, income: 6000000, prop: 450000000, exp: false }, { t1: '선발형(청년특례)', total: 3600000, success: false }],
  ['3인 28세 300만 재산4.5억 경험X -> 청년특례, 성공O', { size: 3, age: 28, income: 3000000, prop: 450000000, exp: false }, { t1: '선발형(청년특례)', success: true }],
  ['45세 경험X 재산3억 -> 선발형(비경활)', { age: 45, income: 1000000, prop: 300000000, exp: false }, { t1: '선발형(비경제활동)' }],
  ['45세 재산4.5억 -> Ⅰ 불가', { age: 45, income: 1000000, prop: 450000000 }, { t1: '', t2: '중장년' }],
  ['30세 재산4.5억 경험O -> 요건심사형(청년 5억)', { income: 1000000, prop: 450000000 }, { t1: '요건심사형' }],
  ['구직급여 종료 6개월 이내 -> Ⅰ 차단, 수당 0', { income: 1000000, ui: '6m' }, { t1Block: 'ui', total: 0, t2: '청년', success: true }],
  ['본인소득 160만 -> Ⅰ 차단', { size: 2, income: 1600000, own: 1600000 }, { t1Block: 'own', total: 0 }],
  ['가족수당 상한: 자녀3+부모2 -> 월100만 600만', { size: 6, age: 50, income: 3000000, kid: 3, old: 2 }, { family: 400000, total: 6000000 }],
  ['중증장애 미성년 1인 중복 -> 20만', { size: 2, income: 2000000, kid: 1, dis: 1 }, { family: 200000, total: 4800000 }],
  ['나이 70 -> 불가', { age: 70 }, { ageOk: false, t1: '', t2: '' }],
  ['나이 14 -> 불가', { age: 14 }, { ageOk: false }],
  ['37세 병역3년 -> 청년', { age: 37, mil: 3, income: 1000000 }, { youth: true, t2: '청년' }],
  ['38세 병역3년 -> 중장년', { age: 38, mil: 3, income: 1000000 }, { youth: false, t2: '중장년' }],
  ['35세 병역0 -> 중장년', { age: 35, income: 1000000 }, { youth: false }],
  ['2027 1인 160만 -> 60% 1,641,625 이하라 요건심사형', { year: 2027, income: 1600000 }, { t1: '요건심사형', lim60: 1641625 }],
];
for (const [name, inp, exp] of cases) {
  const r = J(Object.assign({}, base, inp));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 본문 표 값 검산 (2026, 1~6인)
const t60 = [1538543, 2519575, 3215422, 3896843, 4534031, 5133571], t120 = [3077086, 5039150, 6430843, 7793686, 9068063, 10267142];
for (let n = 1; n <= 6; n++) { const r = J(Object.assign({}, base, { size: n })); assert.strictEqual(r.lim60, t60[n - 1]); assert.strictEqual(r.lim120, t120[n - 1]); }
assert.strictEqual(J(Object.assign({}, base, { year: 2027, size: 4 })).lim60, 4157931);
console.log('PASS 표 값 13개');
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'nes-year': '2026', 'nes-age': '29', 'nes-mil': '0', 'nes-size': '1', 'nes-inc': '120', 'nes-own': '0', 'nes-prop': '5000', 'nes-exp': '1', 'nes-ui': 'none', 'nes-kid': '0', 'nes-old': '0', 'nes-dis': '0' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = { 'nes-out': el('nes-out') }; Object.keys(vals).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('3,600,000원'));
