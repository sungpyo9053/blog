// ko.html의 달력·연차 계산기 <script>를 그대로 뽑아 node에서 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>\n([\s\S]*?)<\/script>/)[1];
assert.ok(src.indexOf('&') === -1, '& in script'); assert.ok(src.indexOf('<') === -1, '< in script'); assert.ok(!/\n\s*\n/.test(src), 'blank line in script');
global.window = {}; eval(src); const c = window.calData;
// 1) 월력요항 공휴일 표(우주항공청 2026.6.29.)와 대조
const official = ['01-01','02-06','02-07','02-08','02-09','03-01','05-01','05-03','05-05','05-13','06-06','07-17','07-19','08-15','08-16','09-14','09-15','09-16','10-03','10-04','10-09','10-11','12-25','12-27'].map(s => '2027-' + s);
assert.deepStrictEqual(Object.keys(c.H).sort(), official); console.log('PASS 공휴일 24일 = 월력요항 표');
// 2) 개수: 월력요항 72일·119일, 평일 공휴일 15일 (Python 검산과 동일)
const k = c.counts(); console.log('counts', JSON.stringify(k));
assert.strictEqual(k.red, 72); assert.strictEqual(k.offDays, 119); assert.strictEqual(k.weekdayHol, 15); assert.strictEqual(k.workDays, 246); assert.strictEqual(k.sun, 52); assert.strictEqual(k.sat, 52);
console.log('PASS 72일 / 119일 / 평일 공휴일 15일');
// 3) 본문에 적은 조합
const find = (n, s, e) => c.plans(n).find(p => c.key(p.s) === s && c.key(p.e) === e);
const cases = [[1,'2027-09-11','2027-09-16',6],[1,'2027-02-05','2027-02-09',5],[1,'2027-05-01','2027-05-05',5],[1,'2027-05-13','2027-05-16',4],[2,'2027-09-11','2027-09-19',9],[3,'2027-09-10','2027-09-19',10],[3,'2027-02-06','2027-02-14',9],[3,'2027-05-01','2027-05-09',9],[4,'2027-09-09','2027-09-19',11],[5,'2027-09-08','2027-09-19',12],[7,'2027-05-01','2027-05-16',16],[4,'2027-12-25','2028-01-02',9]];
for (const [n, s, e, len] of cases) { const p = find(n, s, e); assert.ok(p, s + '~' + e); assert.strictEqual(p.len, len); assert.strictEqual(p.k, n); console.log('PASS', c.desc(p)); }
// 4) 최적 배분(DP)을 전체 후보 완전탐색과 대조 (n=1..6), 본문 값 확인
function brute(n) { const ps = c.plans(n).sort((a, b) => a.s - b.s); const memo = new Map();
  function f(i, b, last) { if (i === ps.length) return 0; const key = i + ',' + b + ',' + last; if (memo.has(key)) return memo.get(key);
    let v = f(i + 1, b, last); const p = ps[i]; if (p.k <= b && p.s > last) v = Math.max(v, p.len + f(i + 1, b - p.k, p.e)); memo.set(key, v); return v; }
  return f(0, n, -1); }
for (let n = 1; n <= 6; n++) { const a = c.alloc(n), bf = brute(n); assert.strictEqual(a.days, bf, 'n=' + n); assert.ok(a.used <= n); console.log('PASS alloc n=' + n, '쉬는 날 합계', a.days, '= 완전탐색', bf); }
assert.strictEqual(c.alloc(2).days, 11); assert.strictEqual(c.alloc(5).days, 24);
assert.deepStrictEqual(c.alloc(5).plans.map(p => p.leave.map(c.key)).flat(), ['2027-01-04','2027-02-05','2027-02-26','2027-05-04','2027-09-13']);
console.log('PASS 본문 배분 예(2일 11일, 5일 24일)');
// 5) UI 렌더 — 최소 DOM 스텁으로 기본값(3일) 실행
const els = {}, mk = () => { const o = { style: {}, children: [], textContent: '', innerHTML: '', title: '', className: '', addEventListener(t, f) { this.h = f; }, appendChild(x) { this.children.push(x); return x; }, scrollIntoView() {} }; return o; };
['cal-grid','cal-count','cal-n','cal-run','cal-out'].forEach(id => els[id] = mk()); els['cal-n'].value = '3';
global.document = { getElementById: id => els[id], createElement: () => mk() };
eval(src);
assert.strictEqual(els['cal-grid'].children.length, 12); console.log('UI', els['cal-count'].textContent);
const out = els['cal-out'].children; console.log('UI 첫 결과:', out[0].innerHTML.replace(/\\x3c|<[^>]+>/g, ''), '/', out[1].children.map(li => li.textContent).join(' | '));
assert.ok(out[0].innerHTML.includes('쉬는 날 합계 16일'));
els['cal-n'].value = '0'; els['cal-run'].h(); assert.ok(els['cal-out'].textContent.includes('1~15')); console.log('PASS 입력 검증(0일)');
