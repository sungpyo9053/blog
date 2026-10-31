// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const m of src.match(/'[^'\n]*'/g) || []) if (m.indexOf('<') >= 0) throw new Error('raw < in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {}; global.document = { getElementById: () => null };
eval(src);
const C = window.shinglesCheck;
const base = { ref: '2026-11-19', immuno: 'no', prev: 'none', months: NaN, hist: 'no', region: 'other', income: 'general' };
const run = o => C(Object.assign({}, base, o));
const has = (r, s) => r.lines.concat(r.local).join('|').includes(s);
const cases = [
  ['45세 일반 -> 권장 안 함', { birth: '1981-05-01' }, r => r.status === 'not-recommended' && r.vaccines.length === 0],
  ['30세 면역저하 -> 재조합만', { birth: '1996-01-01', immuno: 'yes' }, r => r.status === 'target' && r.vaccines.join() === 'rzv'],
  ['17세 -> 대상 아님', { birth: '2009-06-01', immuno: 'yes' }, r => r.status === 'not-target'],
  ['만 50세 생일 당일 -> 두 백신', { birth: '1976-11-19' }, r => r.age === 50 && r.vaccines.join() === 'live,rzv'],
  ['생일 하루 전 49세', { birth: '1976-11-20' }, r => r.age === 49 && r.status === 'not-recommended'],
  ['60세 면역저하 -> 재조합만', { birth: '1966-03-01', immuno: 'yes' }, r => r.vaccines.join() === 'rzv'],
  ['재조합 1차 후 8개월 -> 2차만', { birth: '1960-01-01', prev: 'rzv1', months: 8 }, r => r.status === 'second-dose' && has(r, '2차만')],
  ['재조합 1차 후 1개월 -> 2개월 지나야', { birth: '1960-01-01', prev: 'rzv1', months: 1 }, r => has(r, '2개월이 지나야')],
  ['재조합 1차 후 4개월 -> 간격 안', { birth: '1960-01-01', prev: 'rzv1', months: 4 }, r => has(r, '권고 간격(2~6개월) 안')],
  ['재조합 2회 완료', { birth: '1960-01-01', prev: 'rzv2' }, r => r.status === 'done'],
  ['생백신 후 1개월 -> 2개월 이내 금지', { birth: '1950-01-01', prev: 'live', months: 1 }, r => has(r, '2개월 이내에는')],
  ['생백신 후 72개월 -> 5년 이상', { birth: '1960-01-01', prev: 'live', months: 72 }, r => has(r, '5년 이상')],
  ['78세, 생백신 60개월 전(73세 접종) -> 70세 이상 문구', { birth: '1948-01-01', prev: 'live', months: 60 }, r => has(r, '70세 이상에 맞았다면')],
  ['급성기', { birth: '1960-01-01', hist: 'acute' }, r => has(r, '급성기 증상이 있으면')],
  ['회복 6개월 미만', { birth: '1960-01-01', hist: 'recent' }, r => has(r, '6~12개월')],
  ['강남 일반 1961년생 -> 19,610원', { birth: '1961-12-31', region: 'gangnam' }, r => has(r, '19,610원')],
  ['강남 1962년생 -> 대상 아님', { birth: '1962-01-01', region: 'gangnam' }, r => has(r, '65세 이상(1961.12.31. 이전 출생)만')],
  ['강남 수급자 -> 생백신 무료', { birth: '1955-01-01', region: 'gangnam', income: 'basic' }, r => has(r, '생백신 무료')],
  ['광진 1951년생 -> 1회 무료', { birth: '1951-12-31', region: 'gwangjin' }, r => has(r, '75세 이상 1회 무료')],
  ['광진 1952년생 -> 대상 아님', { birth: '1952-01-01', region: 'gwangjin' }, r => has(r, '75세 이상(1951.12.31. 이전 출생)만')],
  ['성동 65세 -> 생백신 무료', { birth: '1961-01-01', region: 'seongdong' }, r => has(r, '생백신 1회 무료')],
  ['영등포 일반 -> 수급자만', { birth: '1955-01-01', region: 'ydp' }, r => has(r, '기초생활수급자(생계·의료급여)만')],
  ['영등포 차상위 -> 수급자만', { birth: '1955-01-01', region: 'ydp', income: 'near' }, r => has(r, '기초생활수급자(생계·의료급여)만')],
  ['영등포 수급자 -> 무료', { birth: '1955-01-01', region: 'ydp', income: 'basic' }, r => has(r, '생백신 1회 무료')],
  ['영등포 수급자 면역저하 -> 금기 제외', { birth: '1955-01-01', region: 'ydp', income: 'basic', immuno: 'yes' }, r => has(r, '금기자를 제외')],
  ['연수 차상위 -> 무료 + 90,000원', { birth: '1958-01-01', region: 'yeonsu', income: 'near' }, r => has(r, '생백신 무료') && has(r, '90,000원')],
  ['연수 일반 -> 19,610원', { birth: '1958-01-01', region: 'yeonsu' }, r => has(r, '19,610원')],
  ['과거 접종자 -> 지자체 제외', { birth: '1955-01-01', region: 'seongdong', prev: 'live', months: 30 }, r => has(r, '과거 대상포진 접종자')],
  ['그 밖 지역 -> 보건소 문의', { birth: '1955-01-01' }, r => has(r, '보건소에 문의')],
  ['생년월일 없음 -> 오류', { birth: '' }, r => !r.ok],
];
for (const [name, o, ok] of cases) { const r = run(o); assert.ok(ok(r), name + ' ' + JSON.stringify(r)); console.log('PASS', name); }
// UI 렌더(최소 DOM 스텁)
const vals = { 'hz-birth': '1958-04-02', 'hz-ref': '2026-11-19', 'hz-immuno': 'no', 'hz-prev': 'none', 'hz-months': '', 'hz-hist': 'no', 'hz-region': 'gangnam', 'hz-income': 'general' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['hz-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력(1958-04-02, 강남, 일반):\n  ' + outP.join('\n  '));
assert.ok(outP.join().includes('19,610원') && outP.join().includes('의료기관 상담'));
console.log('ALL PASS', cases.length + 1);
