// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { ktxR100: r100, ktxCalc: calc, ktxRefund: refund, ktxData: R } = window;
// 원 단위: 50원까지 버림, 50원 초과 올림 (약관 제8조)
assert.strictEqual(r100(38080), 38100); assert.strictEqual(r100(6250), 6200); assert.strictEqual(r100(6251), 6300); assert.strictEqual(r100(32640), 32600);
console.log('PASS 100원 단위 처리 4건');
// 운임표 발췌와 계산기 데이터 일치
const ex = JSON.parse(fs.readFileSync(path.join(__dirname, 'korail-ktx-fare-20260901-excerpt.txt'), 'utf8').split('JSON ')[1]);
assert.strictEqual(ex.length, R.length);
ex.forEach((e, i) => { assert.strictEqual(R[i][0], e[0]); assert.strictEqual(R[i][1], e[1]); assert.strictEqual(R[i][2], e[2]); });
console.log('PASS 운임표 발췌 ' + R.length + '구간 = 계산기 데이터');
const BUSAN = 7, GN = 26, YJ = 21;
const one = (route, type, o) => calc(Object.assign({ route, first: false, wkend: false, sp: 30, n: { [type]: 1 }, rt: false }, o || {})).total;
const cases = [
  ['서울→부산 일반 어른', one(BUSAN, 'adult'), 54400],
  ['서울→부산 특실 어른', one(BUSAN, 'adult', { first: true }), 78900],
  ['서울→부산 어린이 일반', one(BUSAN, 'child'), 27200],
  ['서울→부산 어린이 특실(요금 할인 없음)', one(BUSAN, 'child', { first: true }), 51700],
  ['서울→부산 유아 좌석 75%', one(BUSAN, 'infant'), 13600],
  ['서울→부산 경로 평일', one(BUSAN, 'senior'), 38100],
  ['서울→부산 경로 특실 평일', one(BUSAN, 'senior', { first: true }), 62600],
  ['서울→부산 경로 주말 = 할인 없음', one(BUSAN, 'senior', { wkend: true }), 54400],
  ['서울→부산 경증장애인 주말 = 할인 없음', one(BUSAN, 'dis2', { wkend: true }), 54400],
  ['서울→부산 중증장애인 주말 50%', one(BUSAN, 'dis1', { wkend: true }), 27200],
  ['서울→부산 국가유공자 50%', one(BUSAN, 'merit'), 27200],
  ['서울→부산 청소년 드림 40% 입력 -> 30%로 제한', one(BUSAN, 'teen', { sp: 40 }), 38100],
  ['서울→부산 힘내라 청춘 40%', one(BUSAN, 'youth', { sp: 40 }), 32600],
  ['서울→부산 다자녀 3자녀 어른 50%', one(BUSAN, 'multi3'), 27200],
  ['서울→부산 다자녀 2자녀 특실 = 할인 없음', one(BUSAN, 'multi2', { first: true }), 78900],
  ['서울→부산 맘편한 일반 40%', one(BUSAN, 'mom'), 32600],
  ['서울→부산 맘편한 특실 = 요금 면제', one(BUSAN, 'mom', { first: true }), 54400],
  ['서울→강릉 우등실 어른', one(GN, 'adult', { first: true }), 33100],
  ['용산→전주 어린이', one(YJ, 'child'), 15800],
];
for (const [name, got, exp] of cases) { assert.strictEqual(got, exp, name + ' got ' + got); console.log('PASS', name, got); }
// 가족: 어른2 어린이1 유아좌석1 왕복
const fam = calc({ route: BUSAN, first: false, wkend: false, sp: 30, n: { adult: 2, child: 1, infant: 1 }, rt: true });
assert.strictEqual(fam.oneWay, 54400 * 2 + 27200 + 13600); assert.strictEqual(fam.total, fam.oneWay * 2); assert.strictEqual(fam.tickets, 8);
console.log('PASS 가족 왕복', JSON.stringify({ oneWay: fam.oneWay, total: fam.total, tickets: fam.tickets }));
// 반환 위약금 (약관 제14조)
const rf = [
  ['월~목 2일 전 무료', refund(54400, false, 0).fee, 0],
  ['월~목 3시간 이내 5%', refund(54400, false, 3).fee, 2700],
  ['금~일 2일 전 최저 400원', refund(54400, true, 0).fee, 400],
  ['금~일 1일 전 5%', refund(54400, true, 1).fee, 2700],
  ['금~일 3시간 전까지 10%', refund(54400, true, 2).fee, 5400],
  ['금~일 3시간 이내 20%', refund(54400, true, 3).fee, 10900],
  ['월~목 출발 후 20분 15%', refund(54400, false, 4).fee, 8200],
  ['금~일 출발 후 20분 30%', refund(54400, true, 4).fee, 16300],
  ['20~60분 40%', refund(54400, false, 5).fee, 21800],
  ['60분~도착 70%', refund(54400, true, 6).fee, 38100],
  ['도착 후 100%', refund(54400, false, 7).fee, 54400],
];
for (const [name, got, exp] of rf) { assert.strictEqual(got, exp, name + ' got ' + got); console.log('PASS 위약금', name, got); }
// UI 기본값 렌더 (서울→부산, 일반실, 월~목, 어른 1, 3시간 이내 반환)
const vals = { 'kt-route': '7', 'kt-cls': '0', 'kt-day': '0', 'kt-sp': '30', 'kt-when': '3' };
const outP = [];
const mk = id => ({ id, value: vals[id] !== undefined ? vals[id] : (id === 'kt-n-adult' ? '1' : '0'), checked: false, style: {}, addEventListener() {}, appendChild(p) { if (id === 'kt-out') outP.push(p.textContent); }, set innerHTML(v) { if (id === 'kt-out') outP.length = 0; } });
const els = {};
global.document = { getElementById: id => els[id] || (els[id] = mk(id)), createElement: () => ({ style: {}, appendChild() {}, addEventListener() {} }), createTextNode: t => t };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('총 운임: 54,400원'));
assert.ok(outP.join().includes('위약금: 2,700원'));
console.log('ALL PASS');
