// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
if (/\n\s*\n/.test(ld)) throw new Error('blank line in JSON-LD');
const faq = JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.jongbuTaxCalc;
let n = 0;
const ok = (name, got, exp) => { assert.strictEqual(got, exp, name + ' got ' + got + ' exp ' + exp); n++; console.log('PASS', name, got); };
// 1) 본문 예시 3개 = 계산기 출력 (재산세 공제는 대략값 = ptax null)
const e1 = calc(2000000000, 2, true, 68, 12, null);
ok('예1 과세표준', e1.base, 480000000); ok('예1 세율세액', e1.gross, 2760000); ok('예1 재산세공제', e1.ptax, 864000);
ok('예1 산출', e1.after, 1896000); ok('예1 공제율', e1.creditRate, 70); ok('예1 세액공제', e1.credit, 1327200);
ok('예1 종부세', e1.jongbu, 568800); ok('예1 농특세', e1.nong, 113760); ok('예1 합계', e1.total, 682560);
const e2 = calc(1500000000, 2, false, 50, 3, null);
ok('예2 과세표준', e2.base, 360000000); ok('예2 세율세액', e2.gross, 1920000); ok('예2 재산세공제', e2.ptax, 864000);
ok('예2 종부세', e2.jongbu, 1056000); ok('예2 농특세', e2.nong, 211200); ok('예2 합계', e2.total, 1267200);
const e3 = calc(3000000000, 3, false, 50, 3, null);
ok('예3 과세표준', e3.base, 1260000000); ok('예3 세율세액', e3.gross, 10800000); ok('예3 재산세공제', e3.ptax, 3024000);
ok('예3 종부세', e3.jongbu, 7776000); ok('예3 농특세', e3.nong, 1555200); ok('예3 합계', e3.total, 9331200); ok('예3 분납', e3.installment, 3888000);
ok('예3 비교 2주택 30억', calc(3000000000, 2, false, 50, 3, null).gross, 10380000);
// 본문에 예시 숫자가 그대로 있는지
for (const s of ['682,560원', '1,267,200원', '9,331,200원', '3,888,000원', '10,380,000원', '568,800원', '1,327,200원']) { assert.ok(html.includes(s), s); n++; console.log('PASS 본문 포함', s); }
// 2) 세율 구간 경계 (법 제9조제1항 표의 누적액) — 과세표준 직접: 공시가격 = 9억 + 과표/0.6
const at = (base, houses) => calc(900000000 + base / 0.6, houses, false, 0, 0, 0).gross;
const B2 = [[3e8, 1500000], [6e8, 3600000], [12e8, 9600000], [25e8, 26500000], [50e8, 64000000], [94e8, 152000000]];
const B3 = [[3e8, 1500000], [6e8, 3600000], [12e8, 9600000], [25e8, 35600000], [50e8, 110600000], [94e8, 286600000]];
for (const [b, t] of B2) ok('2주택 이하 경계 ' + b / 1e8 + '억', at(b, 2), t);
for (const [b, t] of B3) ok('3주택 이상 경계 ' + b / 1e8 + '억', at(b, 3), t);
ok('2주택 94억 초과 1억 -> 2.7%', at(95e8, 2), 152000000 + 2700000);
ok('3주택 94억 초과 1억 -> 5.0%', at(95e8, 3), 286600000 + 5000000);
ok('3억 초과 1천만 -> 0.7%', at(3.1e8, 2), 1500000 + 70000);
// 3) 공제금액 이하 0원
ok('1주택 12억 -> 과표 0', calc(1200000000, 2, true, 70, 20, null).total, 0);
ok('1주택 11억 -> 0', calc(1100000000, 2, true, 70, 20, null).total, 0);
ok('일반 9억 -> 0', calc(900000000, 2, false, 0, 0, null).total, 0);
ok('일반 9억 -> 과표 0', calc(900000000, 3, false, 0, 0, null).base, 0);
ok('1주택 12억 1원 초과 과표 0', calc(1200000001, 2, true, 0, 0, null).base, 0);
// 4) 1세대 1주택 공제율·합산 한도 80%
ok('72세 16년 -> 90%가 80%로', calc(2000000000, 2, true, 72, 16, null).creditRate, 80);
ok('70세 15년 -> 80', calc(2000000000, 2, true, 70, 15, null).creditRate, 80);
ok('65세 10년 -> 70', calc(2000000000, 2, true, 65, 10, null).creditRate, 70);
ok('60세 5년 -> 40', calc(2000000000, 2, true, 60, 5, null).creditRate, 40);
ok('59세 4년 -> 0', calc(2000000000, 2, true, 59, 4, null).creditRate, 0);
ok('64세 9년 -> 40', calc(2000000000, 2, true, 64, 9, null).creditRate, 40);
ok('80% 한도 종부세 = 산출의 20%', (() => { const r = calc(2000000000, 2, true, 75, 20, null); return r.jongbu === r.after - Math.floor(r.after * 0.8); })(), true);
ok('1주택 아님 -> 공제 0', calc(2000000000, 2, false, 75, 20, null).creditRate, 0);
ok('3주택 + 1주택 선택 -> 일반 처리 공제 9억', calc(2000000000, 3, true, 75, 20, null).deduct, 900000000);
// 5) 재산세 공제 입력값 사용·상한
ok('재산세 입력값 사용', calc(2000000000, 2, true, 68, 12, 500000).after, 2260000);
ok('재산세 입력 0', calc(1500000000, 2, false, 0, 0, 0).jongbu, 1920000);
ok('재산세 입력이 세액보다 크면 0', calc(1500000000, 2, false, 0, 0, 9e9).jongbu, 0);
// 6) 분납 금액 (시행령 제16조)
const fakeInst = j => (j > 5000000 ? Math.floor(j / 2) : (j > 2500000 ? j - 2500000 : 0));
for (const p of [1.8e9, 2.0e9, 2.5e9, 3.0e9]) { const r = calc(p, 2, false, 0, 0, 0); ok('분납 ' + p / 1e8 + '억 종부세 ' + r.jongbu, r.installment, fakeInst(r.jongbu)); }
// 7) FAQ JSON-LD 답변 = HTML 답변
const qa = [...html.matchAll(/<h3>([^<]*)<\/h3>\n<p>([^<]*)<\/p>/g)].filter(m => m[1].endsWith('?'));
assert.strictEqual(qa.length, faq.mainEntity.length); n++;
qa.forEach((m, i) => { assert.strictEqual(faq.mainEntity[i].acceptedAnswer.text, m[2], 'FAQ ' + i); n++; console.log('PASS FAQ 일치', m[1]); });
// 8) UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'jb-price': '2000000000', 'jb-houses': '2', 'jb-one': 'yes', 'jb-age': '68', 'jb-years': '12', 'jb-ptax': '' };
const outP = [];
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['jb-out', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('682,560원')); n++;
assert.ok(outP.join().includes('대략값')); n++;
console.log('ALL PASS', n, 'checks');
