// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/^\s*$/m.test(src.replace(/^\n|\n$/g, ''))) throw new Error('blank line in script');
for (const m of src.matchAll(/'[^'\n]*'/g)) if (m[0].includes('<')) throw new Error('< in string ' + m[0]);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const { calc, pct, conv43, need } = window.gpaCalc;
const near = (a, b, n) => assert.ok(Math.abs(a - b) < 1e-9, n + ': ' + a + ' != ' + b);
let pass = 0;
const ok = (name, fn) => { fn(); pass++; console.log('PASS', name); };
const R = (c, g, m) => ({ credit: c, grade: g, major: !!m });
const ex = [R(3, 'A+'), R(3, 'A0', 1), R(3, 'B+', 1), R(2, 'B0'), R(3, 'C+', 1), R(1, 'P')];
ok('본문 예시 4.5: 49.5/14 -> 3.54 반올림, 3.53 절사', () => { const r = calc(ex, '4.5'); near(r.points, 49.5, 'pts'); near(r.graded, 14, 'cr'); near(r.avgRound, 3.54, 'r'); near(r.avgTrunc, 3.53, 't'); near(r.pf, 1, 'pf'); });
ok('전공 평점 30/9 -> 3.33', () => { const r = calc(ex, '4.5'); near(r.majorCredits, 9, 'mc'); near(r.majorRound, 3.33, 'mr'); });
ok('NP 3학점 추가해도 평균 불변', () => { near(calc(ex.concat([R(3, 'NP')]), '4.5').avgRound, 3.54, 'np'); });
ok('F는 분모 포함: A+3 + F3 -> 2.25', () => { near(calc([R(3, 'A+'), R(3, 'F')], '4.5').avg, 2.25, 'f'); });
ok('4.3 만점: A+3 A-3 B0 3 -> 3.67 / 3.66', () => { const r = calc([R(3, 'A+'), R(3, 'A-'), R(3, 'B0')], '4.3'); near(r.avgRound, 3.67, 'r'); near(r.avgTrunc, 3.66, 't'); });
ok('4.5 체계에 없는 A- 는 미선택 처리', () => { const r = calc([R(3, 'A-'), R(3, 'A0')], '4.5'); near(r.avg, 4, 'a'); assert.strictEqual(r.skipped, 1); });
ok('P만 있으면 평균 없음', () => { assert.strictEqual(calc([R(2, 'P')], '4.5').avg, null); });
ok('학점 0·빈칸 과목 무시', () => { near(calc([R(0, 'F'), R('', 'F'), R(3, 'B+')], '4.5').avg, 3.5, 'z'); });
ok('이전 누적 60학점 3.40 + 이번 학기 합산', () => { const r = calc([R(3, 'A+')], '4.5', 60, 3.4); near(r.graded, 63, 'g'); near(r.points, 204 + 13.5, 'p'); });
ok('서울대 별표2: 4.3=100, 4.0=97, 3.0=87, 0.1=58, 0=0, 비고 예 3.25=89.5, 4.27=99.7', () => {
  [[4.3, 100], [4, 97], [3, 87], [0.1, 58], [0, 0], [3.25, 89.5], [4.27, 99.7], [3.8, 95]].forEach(([a, b]) => near(pct('snu', a), b, 'snu ' + a));
  assert.strictEqual(pct('snu', 0.05), null); assert.strictEqual(pct('snu', 4.4), null); });
ok('서울대 Grade_table.pdf 0.01 단위 전수 대조', () => {
  const t = fs.readFileSync(path.join(__dirname, 'snu-Grade_table-4.3.txt'), 'utf8').trim().split('\n').slice(2);
  let n = 0; t.forEach(l => { const [a, b] = l.trim().split(/\s+/).map(Number); if (isNaN(a)) return; near(pct('snu', a), b, 'tbl ' + a); n++; });
  assert.ok(n >= 400, 'rows ' + n); console.log('  rows checked:', n); });
ok('경북대 실점수 환산표: 4.3=100, 4.25=99, 4.2=98, 4.0=96, 0.1=57, 예 4.26=99.2, 4.24=98.8, 3.25=88.5', () => {
  [[4.3, 100], [4.25, 99], [4.2, 98], [4, 96], [3.3, 89], [1.1, 67], [0.1, 57], [0, 0], [4.26, 99.2], [4.24, 98.8], [3.25, 88.5]].forEach(([a, b]) => near(pct('knu', a), b, 'knu ' + a)); });
ok('인하대 x10+55: 4.5=100, 4.0=95, 3.5=90, 3.0=85, 4.3=98', () => { [[4.5, 100], [4, 95], [3.5, 90], [3, 85], [4.3, 98], [3.8, 93]].forEach(([a, b]) => near(pct('inha', a), b, 'inha ' + a)); });
ok('미확인 학교(부산대)는 계산 안 함', () => { assert.strictEqual(pct('pnu', 4), null); });
ok('서울대 별표2 만점 환산: 4.3->4.5/4.0, 4.25->4.45, 4.0->4.2, 3.5->3.7, 0->0', () => {
  near(conv43(4.3).to45, 4.5, 'a'); near(conv43(4.3).to40, 4, 'b'); near(conv43(4.25).to45, 4.45, 'c'); near(conv43(4.25).to40, 4, 'c2');
  near(conv43(4).to45, 4.2, 'd'); near(conv43(3.5).to45, 3.7, 'e'); near(conv43(3.9).to40, 3.9, 'f'); near(conv43(0).to45, 0, 'g'); assert.strictEqual(conv43(0.05).to45, null); });
ok('목표: 60학점 3.40 -> 3.60, 다음 18학점 -> 4.27', () => { const n = need(204, 60, 3.6, 18, 4.5); assert.strictEqual(n.status, 'ok'); near(n.ceil, 4.27, 'n'); });
ok('목표 3.80 -> 5.13 불가능', () => { const n = need(204, 60, 3.8, 18, 4.5); assert.strictEqual(n.status, 'impossible'); near(n.ceil, 5.14, 'c'); });
ok('4.3 만점에서 4.27 필요 -> 가능, 4.31 필요 -> 불가능', () => { assert.strictEqual(need(204, 60, 3.6, 18, 4.3).status, 'ok'); assert.strictEqual(need(200, 60, 3.6, 18, 4.3).status, 'impossible'); });
ok('목표가 현재보다 낮으면 done', () => { assert.strictEqual(need(204, 60, 2.5, 18, 4.5).status, 'done'); });
ok('다음 학기 학점 0 -> null', () => { assert.strictEqual(need(204, 60, 3.6, 0, 4.5), null); });
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'gp-scale': '4.5', 'gp-prevc': '', 'gp-preva': '', 'gp-target': '3.8', 'gp-next': '18', 'gp-direct': '' };
const outP = [];
function mk(tag) {
  const e = { tagName: tag, children: [], style: {}, value: '', checked: false, attrs: {}, addEventListener() {}, setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); if (c.parent === undefined) c.parent = this; if (this.id === 'gp-out') outP.push(c.textContent); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); },
    set innerHTML(v) { this.children = []; if (this.id === 'gp-out') outP.length = 0; } };
  Object.defineProperty(e, 'value', { get() { if (this.tagName === 'select') { return this._v === undefined ? '' : this._v; } return this._v === undefined ? '' : this._v; }, set(v) { this._v = String(v); } });
  e.querySelector = function (q) { return all(this).find(x => match(x, q)); };
  e.querySelectorAll = function (q) { return all(this).filter(x => match(x, q)); };
  return e;
}
function all(n) { let r = []; (n.children || []).forEach(c => { r.push(c); r = r.concat(all(c)); }); return r; }
function match(x, q) { if (q === '.gp-row') return x.className === 'gp-row'; if (q === 'select') return x.tagName === 'select'; const m = q.match(/input\[type=(\w+)\]/); return m ? x.tagName === 'input' && x.type === m[1] : false; }
const els = {};
Object.keys(vals).concat(['gp-out', 'gp-rows', 'gp-add']).forEach(id => { const e = mk(id === 'gp-scale' ? 'select' : 'div'); e.id = id; if (vals[id] !== undefined) e.value = vals[id]; els[id] = e; });
global.document = { getElementById: id => els[id], createElement: t => mk(t), createTextNode: t => ({ textContent: t }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('3.54 (반올림) / 3.53 (절사)'));
assert.ok(outP.join().includes('전공 평점: 3.33'));
assert.ok(outP.join().includes('인하대 식 90.4점'));
assert.ok(outP.join().includes('4.01 이상'));
pass++;
console.log('PASS UI 기본값 렌더');
console.log('TOTAL PASS', pass);
