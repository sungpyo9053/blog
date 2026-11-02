// ko.html 계산기 <script>를 그대로 뽑아 node에서 실행하고 KASI 조회 결과와 대조
const fs = require('fs'), path = require('path'), assert = require('assert');
const E = f => path.join(__dirname, f);
const html = fs.readFileSync(E('../ko.html'), 'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
for (const s of scripts) { if (s.indexOf('&') >= 0) throw new Error('& in script'); if (/\n\s*\n/.test(s)) throw new Error('blank line in script'); if (s.indexOf('<') >= 0) throw new Error('< in script'); }
console.log('script bytes', Buffer.byteLength(scripts[0]));
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faqN = JSON.parse(ld).mainEntity.length; assert.ok(faqN >= 6);
global.window = {}; global.document = { getElementById: () => null };
eval(scripts[0]);
const C = window.lunarCalc;
const key = (y, m, d) => y + '-' + m + '-' + d;
// 1) 내장 표 전수: KASI /life/lunc 매월 1일 조회 1,212회 응답(1,248개 달)과 시작일·길이·세차
const rows = fs.readFileSync(E('kasi-lunc-month-starts-1950-2050.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
let n = 0;
for (const q of rows) for (const x of q.r) {
  const leap = x.LUNC_LEAP_MM === '윤';
  const r = C.toSolar(+x.LUNC_YYYY, +x.LUNC_MM, 1, leap);
  assert.strictEqual(key(r.y, r.m, r.d), key(+x.SOLC_YYYY, +x.SOLC_MM, +x.SOLC_DD), q.q + (leap ? ' 윤' : ''));
  assert.strictEqual(r.len, +x.LUNC_EN_DD); assert.strictEqual(r.wd, x.SOLC_WEEK);
  const L = C.toLunar(r.y, r.m, r.d); assert.strictEqual(L.leap, leap); assert.strictEqual(L.gz + '(' + L.han + ')', x.LUNC_PRCN);
  n++;
}
assert.strictEqual(n, 1248); assert.strictEqual(C.months.length, 1248);
console.log('PASS KASI 매월 초하루 1,248개 달 시작일·길이·요일·윤달·세차 일치');
// 2) 개별 대조 — 기대값은 evidence/kasi-solc-spotcheck.jsonl·kasi-lunc-spotcheck.jsonl(KASI 응답)에서 옮겨 적음
const solc = [ // 양력 -> 음력 [y,m,d, ly,lm,ld,윤,달길이,세차]
  [1950,2,17, 1950,1,1,0,30,'경인'], [1970,1,1, 1969,11,24,0,30,'기유'], [1984,12,22, 1984,11,1,0,30,'갑자'],
  [1988,9,17, 1988,8,7,0,30,'무진'], [2000,1,1, 1999,11,25,0,30,'기묘'], [2020,1,25, 2020,1,1,0,30,'경자'],
  [2020,5,23, 2020,4,1,1,29,'경자'], [2020,6,20, 2020,4,29,1,29,'경자'], [2020,10,1, 2020,8,15,0,30,'경자'],
  [2023,1,22, 2023,1,1,0,29,'계묘'], [2023,3,22, 2023,2,1,1,29,'계묘'], [2023,4,19, 2023,2,29,1,29,'계묘'],
  [2023,9,29, 2023,8,15,0,30,'계묘'], [2025,1,29, 2025,1,1,0,30,'을사'], [2025,7,25, 2025,6,1,1,29,'을사'],
  [2025,8,22, 2025,6,29,1,29,'을사'], [2025,10,6, 2025,8,15,0,29,'을사'], [2026,2,17, 2026,1,1,0,30,'병오'],
  [2026,9,25, 2026,8,15,0,30,'병오'], [2026,11,2, 2026,9,23,0,29,'병오'], [2026,12,1, 2026,10,23,0,30,'병오'],
  [2027,2,7, 2027,1,1,0,29,'정미'], [2027,9,15, 2027,8,15,0,29,'정미'], [2028,2,9, 2028,1,14,0,29,'무신'],
  [2033,12,22, 2033,11,1,1,29,'계축'], [2044,9,1, 2044,7,10,1,29,'갑자'], [2050,12,31, 2050,11,18,0,30,'경오'],
];
const sj = fs.readFileSync(E('kasi-solc-spotcheck.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
assert.strictEqual(sj.length, solc.length);
solc.forEach((c, i) => {
  const L = C.toLunar(c[0], c[1], c[2]), k = sj[i];
  assert.deepStrictEqual([L.ly, L.lm, L.ld, L.leap ? 1 : 0, L.len, L.gz], c.slice(3), c.join('-'));
  assert.deepStrictEqual(c.slice(0, 9).map(String), [+k.SOLC_YYYY, +k.SOLC_MM, +k.SOLC_DD, +k.LUNC_YYYY, +k.LUNC_MM, +k.LUNC_DD, k.LUNC_LEAP_MM === '윤' ? 1 : 0, +k.LUNC_EN_DD, k.LUNC_PRCN.slice(0, 2)].map(String), 'spot file ' + i);
});
console.log('PASS 양력->음력 개별', solc.length, '건 (설날·추석·윤달 2020/2023/2025 포함)');
const lunc = [ // 음력 -> 양력 [ly,lm,ld, 평달 결과, 윤달 결과 or null]
  [1990,5,15,'1990-6-7','1990-7-7'], [2001,4,10,'2001-5-3','2001-6-1'], [2020,4,15,'2020-5-7','2020-6-6'],
  [2023,2,29,'2023-3-20','2023-4-19'], [2025,6,6,'2025-6-30','2025-7-30'], [2026,1,1,'2026-2-17',null],
  [2026,8,15,'2026-9-25',null], [2027,1,15,'2027-2-21',null], [2028,5,5,'2028-5-28','2028-6-27'],
  [2033,11,1,'2033-11-22','2033-12-22'], [2033,11,30,'2033-12-21',null],
];
const lj = fs.readFileSync(E('kasi-lunc-spotcheck.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
lunc.forEach((c, i) => {
  const a = C.toSolar(c[0], c[1], c[2], false); assert.strictEqual(key(a.y, a.m, a.d), c[3]);
  const b = C.toSolar(c[0], c[1], c[2], true);
  if (c[4]) assert.strictEqual(key(b.y, b.m, b.d), c[4]); else assert.ok(b.err, c.join());
  const got = lj[i].r.map(r => key(+r.SOLC_YYYY, +r.SOLC_MM, +r.SOLC_DD));
  assert.deepStrictEqual(got, [c[3], c[4]].filter(Boolean), 'spot file ' + lj[i].q);
});
console.log('PASS 음력->양력 개별', lunc.length, '건 (평달·윤달 쌍)');
// 3) 오류·경계
assert.strictEqual(C.toSolar(2026, 2, 30, false).err, 'noday'); // KASI lunc 2026-02-30 -> [] (kasi-lunc-2026-02-30.json)
assert.strictEqual(C.toSolar(2026, 4, 1, true).err, 'noleap');
assert.strictEqual(C.toSolar(2050, 12, 1, false).err, 'range');
assert.strictEqual(C.toSolar(2050, 11, 19, false).err, 'range');
assert.strictEqual(C.toLunar(1950, 2, 16), null); assert.strictEqual(C.toLunar(2051, 1, 1), null);
console.log('PASS 없는 날짜·없는 윤달·범위 밖');
// 4) 달력자료(월력요항 형식) 2021~2028 표와 대조
let cd = 0;
for (let y = 2021; 2028 >= y; y++) {
  const t = fs.readFileSync(E('calendarData/kasi-calendar-data-' + y + '.txt'), 'utf8').replace(/\s+/g, ' ');
  const sec = t.slice(t.indexOf('음력(' + y), t.indexOf('(음력 : 대'));
  const re = /(윤 )?(\d{1,2}) 1 (대|소) (?:\S+ )?\S+ (\d{4}) (\d{1,2}) (\d{1,2})/g; let m, k = 0;
  while ((m = re.exec(sec))) {
    const r = C.toSolar(y, +m[2], 1, !!m[1]);
    // 2021년 달력자료의 음력 12월 행은 양력 연도가 "2021 1 3"으로 적혀 있다(앞 달 11월 1일 2021-12-4 + 30일 = 2022-1-3, KASI lunc 조회도 2022-01-03). 연도 오기로 보고 이 한 행만 연도를 고쳐 대조한다.
    if (y === 2021) { if (m[2] === '12') { assert.strictEqual(m[4], '2021'); m[4] = '2022'; } }
    assert.strictEqual(key(r.y, r.m, r.d), key(+m[4], +m[5], +m[6]), y + ' ' + m[0]);
    assert.strictEqual(r.len, m[3] === '대' ? 30 : 29); k++; cd++;
  }
  assert.ok(k >= 12, y + ' rows ' + k);
}
console.log('PASS 달력자료 2021~2028 음력 표', cd, '개 달 일치');
// 5) 본문 표 값
const fmt = r => r.m + '-' + r.d;
assert.deepStrictEqual([2026,2027,2028,2029,2030,2031,2032,2033,2034,2035].map(y => fmt(C.toSolar(y,1,1)) + '/' + fmt(C.toSolar(y,8,15))),
  ['2-17/9-25','2-7/9-15','1-27/10-3','2-13/9-22','2-3/9-12','1-23/10-1','2-11/9-19','1-31/9-8','2-19/9-27','2-8/9-16']);
assert.strictEqual(C.leapYears(1950, 2050).length, 37);
assert.strictEqual(C.leapYears(2001, 2050).join(), '2001년 윤4월,2004년 윤2월,2006년 윤7월,2009년 윤5월,2012년 윤3월,2014년 윤9월,2017년 윤5월,2020년 윤4월,2023년 윤2월,2025년 윤6월,2028년 윤5월,2031년 윤3월,2033년 윤11월,2036년 윤6월,2039년 윤5월,2042년 윤2월,2044년 윤7월,2047년 윤5월,2050년 윤3월');
assert.deepStrictEqual([[1,15],[5,5],[7,7],[4,8]].map(c => fmt(C.toSolar(2027, c[0], c[1]))), ['2-21','6-9','8-8','5-13']); // 우주항공청 보도자료·달력자료 2027
assert.strictEqual(fmt(C.toSolar(2026, 12, 30)), '2-6');
console.log('PASS 설날·추석 2026~2035, 윤달 목록, 2027 대보름·단오·칠석·부처님오신날');
// 6) 음력 생일
const b = C.birthday(8, 15, false, 2026); assert.deepStrictEqual(b.map(x => x.year + ':' + fmt(x.r)), ['2026:9-25', '2027:9-15']);
const bl = C.birthday(4, 15, true, 2026); assert.strictEqual(fmt(bl[0].r), '5-31'); assert.ok(bl[0].note.includes('윤4월이 없어'));
const b30 = C.birthday(2, 30, false, 2026); assert.strictEqual(fmt(b30[0].r), '4-16'); assert.ok(b30[0].note.includes('30일이 없음'));
console.log('PASS 음력 생일(평달·윤달·30일)');
// 7) UI 렌더 (최소 DOM 스텁)
function mk(v) { return { value: v, checked: false, style: {}, kids: [], addEventListener() {}, set innerHTML(x) { this.kids = []; }, appendChild(p) { this.kids.push(p.textContent); } }; }
const els = { 'ls-sd': mk('2026-12-01'), 'ls-out1': mk(), 'ls-ly': mk('2027'), 'ls-lm': mk('1'), 'ls-ld': mk('1'), 'ls-leap': mk(), 'ls-out2': mk(), 'ls-bm': mk('8'), 'ls-bd': mk('15'), 'ls-bleap': mk(), 'ls-by': mk('2026'), 'ls-out3': mk() };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(scripts[0]);
console.log('UI 양력->음력:', els['ls-out1'].kids.join(' | '));
console.log('UI 음력->양력:', els['ls-out2'].kids.join(' | '));
console.log('UI 음력 생일:', els['ls-out3'].kids.join(' | '));
assert.ok(els['ls-out1'].kids[0].includes('음력 2026년 10월 23일'));
assert.ok(els['ls-out2'].kids[0].includes('2027년 2월 7일(일)'));
console.log('ALL PASS');
