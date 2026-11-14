// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g) || []) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
assert.strictEqual(faq.mainEntity.length, (html.match(/<h2 id="faq">[\s\S]*?<script type/)[0].match(/<h3>/g) || []).length);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const C = window.hpvCalc;
const base = { first: '2026-11-15', sex: 'f', income: 'general', vac: 'g4', price: '' };
const run = o => C(Object.assign({}, base, o));
const has = (r, s) => r.lines.join('|').includes(s);
const cases = [
  ['2014년생 여아 12세 가다실 -> 무료 2회 0원', { birth: '2014-03-01' }, r => r.free && r.doses === 2 && r.total === 0],
  ['2008년생 여성 18세 가다실 -> 무료 3회', { birth: '2008-02-01' }, r => r.free && r.doses === 3 && r.age === 18],
  ['2011년생 여아, 15세 생일 당일 첫 접종 -> 3회', { birth: '2011-11-15' }, r => r.age === 15 && r.doses === 3 && r.free],
  ['15세 생일 전날 -> 2회', { birth: '2011-11-16' }, r => r.age === 14 && r.doses === 2],
  ['14세 가다실 -> 허가 9~13 참고 문구', { birth: '2012-01-01' }, r => r.age === 14 && has(r, '만 9~13세')],
  ['무료 여아가 가다실9 선택 -> 본인 부담', { birth: '2013-05-01', vac: 'g9', price: '200000' }, r => !r.free && r.total === 400000 && has(r, '전액 본인 부담')],
  ['2014년생 남아 2026.6 -> 무료 2회', { birth: '2014-07-01', sex: 'm', first: '2026-06-01' }, r => r.free && r.doses === 2 && r.group === 'boy'],
  ['2014년생 남아 2026.5.5 첫 접종 -> 시행일 전', { birth: '2014-01-01', sex: 'm', first: '2026-05-05' }, r => !r.free && has(r, '시행일(2026.5.6.) 이전')],
  ['2014년생 남아 2026.5.6 -> 무료', { birth: '2014-01-01', sex: 'm', first: '2026-05-06' }, r => r.free],
  ['2013년생 남아 -> 무료 아님, 가격 계산', { birth: '2013-01-01', sex: 'm', price: '150000' }, r => !r.free && r.doses === 2 && r.total === 300000],
  ['2015년생 남아 -> 2027 예정 문구', { birth: '2015-01-01', sex: 'm' }, r => !r.free && has(r, '2027년 신규 지원 예정')],
  ['2000년생 저소득 여성 -> 무료 3회', { birth: '2000-06-01', income: 'low' }, r => r.free && r.doses === 3 && r.group === 'low'],
  ['2000년생 일반 여성 -> 저소득만', { birth: '2000-06-01' }, r => !r.free && r.group === 'need-low'],
  ['1998년생 저소득 여성 -> 대상 아님', { birth: '1998-12-31', income: 'low' }, r => !r.free && r.group === ''],
  ['30세 여성 가다실 -> 허가 밖', { birth: '1996-01-01' }, r => r.doses === 0 && has(r, '허가 연령 밖')],
  ['30세 여성 가다실9 -> 3회 × 가격', { birth: '1996-01-01', vac: 'g9', price: '210000' }, r => r.doses === 3 && r.total === 630000 && has(r, '630,000원')],
  ['45세 여성 가다실9 -> 3회', { birth: '1981-01-01', vac: 'g9' }, r => r.age === 45 && r.doses === 3],
  ['46세 여성 가다실9 -> 허가 밖', { birth: '1980-01-01', vac: 'g9' }, r => r.doses === 0],
  ['27세 남성 가다실9 -> 허가 밖', { birth: '1999-01-01', sex: 'm', vac: 'g9' }, r => r.age === 27 && r.doses === 0],
  ['26세 남성 가다실9 -> 3회', { birth: '2000-01-01', sex: 'm', vac: 'g9' }, r => r.age === 26 && r.doses === 3],
  ['25세 서바릭스 -> 3회, 26세 -> 밖', { birth: '2001-01-01', vac: 'cv2' }, r => r.age === 25 && r.doses === 3 && has(r, '0, 1, 6개월')],
  ['26세 서바릭스 -> 허가 밖', { birth: '2000-01-01', vac: 'cv2' }, r => r.doses === 0],
  ['8세 -> 허가 밖', { birth: '2018-01-01' }, r => r.doses === 0 && has(r, '9세 미만')],
  ['가격 미입력 -> 안내', { birth: '1990-01-01', vac: 'g9' }, r => r.total === null && has(r, '확인하지 못했')],
  ['2027년 첫 접종 -> 2026 기준 주의', { birth: '2014-01-01', sex: 'm', first: '2027-03-01' }, r => r.free && has(r, '2027년 대상은 확인하지 못했')],
  ['생년월일 없음 -> 오류', { birth: '' }, r => !r.ok],
  ['생년월일이 접종일보다 늦음 -> 오류', { birth: '2027-01-01' }, r => !r.ok],
];
for (const [name, o, ok] of cases) { const r = run(o); assert.ok(ok(r), name + ' ' + JSON.stringify(r)); console.log('PASS', name); }
// UI 렌더(최소 DOM 스텁)
const vals = { 'hp-birth': '2010-04-02', 'hp-first': '2026-11-15', 'hp-sex': 'f', 'hp-income': 'general', 'hp-vac': 'g9', 'hp-price': '200000' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hp-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(2010-04-02 여성, 가다실9, 1회 200,000원 입력):\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('600,000원') && outP.join().includes('전액 본인 부담'));
console.log('ALL PASS', cases.length + 1);
