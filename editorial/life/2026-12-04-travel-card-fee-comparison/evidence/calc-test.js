// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
for (const lit of src.match(/'[^'\n]*'/g)) if (lit.indexOf('<') >= 0) throw new Error('< in string literal ' + lit);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity.length, h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq, h3faq); console.log('PASS FAQ', faq, '개, JSON-LD 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const C = window.travelFeeCalc;
const row = (res, name) => res.rows.find(r => r.name.indexOf(name) === 0);
// 1. 결제 100달러, 1달러=1,400원
let r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'pay', cnt: 0, prev: 0 });
assert.strictEqual(r.base, 140000);
for (const n of ['하나', '신한', 'KB', '토스뱅크', '트래블월렛']) assert.strictEqual(row(r, n).total, 140000, n);
assert.strictEqual(row(r, '하나').waived, Math.round(0.5 * 1400 + 1400)); // US$0.5 + 1% = 700 + 1,400
assert.strictEqual(row(r, '신한').waived, 1680); // 1.2%
assert.strictEqual(row(r, '토스뱅크').waived, 2100); // 1% + US$0.5
assert.strictEqual(row(r, '참고').fee, 1750); // 1% + 0.25%
assert.strictEqual(row(r, '참고').total, 141750);
console.log('PASS 결제 USD 100: 5개 카드 140,000원, 일반카드 141,750원, 면제액 하나 2,100 신한 1,680 토스 2,100');
// 2. ATM 100달러 첫 인출
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 0, prev: 0 });
assert.strictEqual(row(r, '하나').waived, 4200 + 1400); // US$3 + 1%
assert.strictEqual(row(r, '신한').waived, 5600);
assert.strictEqual(row(r, 'KB').fee, 0);
assert.strictEqual(row(r, '토스뱅크').fee, 0);
assert.strictEqual(row(r, '트래블월렛').fee, 0);
assert.ok(!row(r, '참고'));
console.log('PASS ATM USD 100 첫 인출: 전 카드 수수료 0, 일반카드 행 없음');
// 3. 트래블월렛 월 500달러 초과분 2%: 이미 450달러 + 100달러 -> 50달러 x 2% = 1달러 = 1,400원
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 2, prev: 450 });
assert.strictEqual(row(r, '트래블월렛').overUsd, 50);
assert.strictEqual(row(r, '트래블월렛').fee, 1400);
assert.strictEqual(row(r, '트래블월렛').total, 141400);
// 이미 600달러 넘은 상태 -> 전액 초과
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 3, prev: 600 });
assert.strictEqual(row(r, '트래블월렛').fee, 2800);
// 1회 400달러 한도 경고
r = C({ amt: 450, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 0, prev: 0 });
assert.ok(row(r, '트래블월렛').note.indexOf('400달러') >= 0);
console.log('PASS 트래블월렛: 450+100 -> 1,400원, 600+100 -> 2,800원, 1회 400달러 초과 경고');
// 4. 토스뱅크 월 5회 / US$700
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 4, prev: 400 });
assert.strictEqual(row(r, '토스뱅크').fee, 0); // 5번째, 500달러
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 5, prev: 400 });
assert.strictEqual(row(r, '토스뱅크').fee, null); // 6번째
r = C({ amt: 200, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 1, prev: 600 });
assert.strictEqual(row(r, '토스뱅크').fee, null); // 800달러
assert.strictEqual(row(r, '토스뱅크').total, null);
console.log('PASS 토스뱅크: 5번째 면제, 6번째·US$700 초과는 확인하지 못함');
// 5. KB 월 10회
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 9, prev: 0 });
assert.strictEqual(row(r, 'KB').fee, 0);
r = C({ amt: 100, cur: 'USD', rate: 1400, usd: 1400, mode: 'atm', cnt: 10, prev: 0 });
assert.strictEqual(row(r, 'KB').fee, null);
console.log('PASS KB: 10번째 면제, 11번째 확인하지 못함');
// 6. 엔화 10,000엔, 100엔=950원 -> 1엔 9.5원, 1달러 1,400원
r = C({ amt: 10000, cur: 'JPY', rate: 9.5, usd: 1400, mode: 'pay', cnt: 0, prev: 0 });
assert.strictEqual(r.base, 95000);
assert.strictEqual(row(r, '트래블월렛').total, 95000);
assert.strictEqual(r.amtUsd, 67.86);
console.log('PASS JPY 10,000엔 -> 95,000원(약 67.86달러), 트래블월렛 충전 0%');
// 7. 태국 바트: 트래블월렛 0.5~2.5% 범위
r = C({ amt: 1000, cur: 'THB', rate: 40, usd: 1400, mode: 'pay', cnt: 0, prev: 0 });
assert.strictEqual(r.base, 40000);
assert.strictEqual(row(r, '트래블월렛').totalMin, 40200);
assert.strictEqual(row(r, '트래블월렛').totalMax, 41000);
assert.ok(row(r, '토스뱅크').note.indexOf('17개 통화 환율') === 0);
assert.ok(row(r, 'KB').note.indexOf('확인하지 못했다') > 0);
console.log('PASS THB 1,000바트(1바트 40원 가정): 트래블월렛 40,200~41,000원, 토스 17개 통화 안, KB 지원 여부 미확인 표시');
// 8. 입력 오류
assert.ok(C({ amt: 0, cur: 'USD', rate: 1400, mode: 'pay' }).error);
assert.ok(C({ amt: 10, cur: 'USD', rate: 0, mode: 'pay' }).error);
assert.ok(C({ amt: 10, cur: 'EUR', rate: 1500, usd: 0, mode: 'pay' }).error);
console.log('PASS 금액 0, 환율 0, 달러 환율 누락 거부');
// 9. UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'tf-amt': '100', 'tf-cur': 'USD', 'tf-mode': 'pay', 'tf-rate': '1400', 'tf-usd': '1400', 'tf-cnt': '0', 'tf-prev': '0' };
const texts = [];
const mk = () => ({ style: {}, children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { texts.push(v); this._t = v; }, get textContent() { return this._t; } });
const els = {};
['tf-out', 'tf-rate-label', 'tf-usd-wrap', ...Object.keys(vals)].forEach(id => { els[id] = mk(); els[id].value = vals[id]; els[id].addEventListener = () => {}; Object.defineProperty(els[id], 'innerHTML', { set() { texts.length = 0; } }); });
global.document = { getElementById: id => els[id], createElement: () => mk() };
eval(src);
console.log('UI 기본값 출력:', texts.join(' | '));
assert.ok(texts.join().includes('140,000원'));
assert.ok(texts.join().includes('141,750원'));
