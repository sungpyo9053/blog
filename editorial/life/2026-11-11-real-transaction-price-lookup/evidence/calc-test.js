// ko.html의 체크 도구·계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/^\s*$/m.test(src.replace(/^\n|\n$/g, ''))) throw new Error('blank line in script');
for (const m of src.match(/'(?:[^'\\]|\\.)*'/g)) if (m.indexOf('<') >= 0) throw new Error('< in string ' + m);
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld);
const h3faq = html.split('<h2 id="faq">')[1].split('<h2>')[0].match(/<h3>/g).length;
assert.strictEqual(faq.mainEntity.length, h3faq);
console.log('PASS JSON-LD 파싱, FAQ', h3faq, '개와 h3 수 일치');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const G = window.rtGuide, A = window.rtArea;
// 면적 계산
let r = A(84.97, 90000);
assert.ok(r.ok); assert.strictEqual(r.perM2, 1059.2); assert.strictEqual(r.per33, 3495); assert.strictEqual(r.pyeong, 25.7);
console.log('PASS 84.97㎡ 9억', JSON.stringify(r));
r = A(59.99, 60000); assert.strictEqual(r.per33, 3301); assert.strictEqual(r.pyeong, 18.2);
console.log('PASS 59.99㎡ 6억', JSON.stringify(r));
r = A(33, 33000); assert.strictEqual(r.perM2, 1000); assert.strictEqual(r.per33, 3300); assert.strictEqual(r.pyeong, 10);
console.log('PASS 33㎡ 3.3억 -> 3.3㎡당 3,300만원, 10평');
for (const [a, p] of [[0, 1000], [84, 0], [NaN, 1000], [-5, 1000], [84, NaN]]) assert.strictEqual(A(a, p).ok, false);
console.log('PASS 잘못된 입력 5건 거부');
// 경로 안내
r = G('apt', 'sale'); assert.ok(r.ok); assert.ok(r.path.includes('아파트 메뉴') && r.path.includes('매매 탭')); assert.ok(r.items.includes('해제여부')); assert.ok(r.notes.some(n => n.includes('등기일')));
console.log('PASS 아파트 매매:', r.path);
r = G('apt', 'rent'); assert.ok(r.ok); assert.ok(r.path.includes('전월세 탭')); assert.ok(r.notes.some(n => n.includes('6천만원')));
console.log('PASS 아파트 전월세:', r.items);
for (const t of ['villa', 'house', 'officetel']) { assert.ok(G(t, 'rent').ok); assert.ok(G(t, 'sale').ok); }
console.log('PASS 연립·단독·오피스텔 매매/전월세 모두 안내');
for (const t of ['presale', 'land', 'commercial', 'factory']) { const x = G(t, 'rent'); assert.strictEqual(x.ok, false); assert.ok(x.notes[0].includes('공개 대상이 아니다')); assert.ok(G(t, 'sale').ok); }
console.log('PASS 분양권·토지·상업·공장 전월세는 대상 아님 안내');
assert.ok(G('factory', 'sale').items.includes('확인하지 못했다'));
assert.ok(G('house', 'sale').items.includes('첫째 자리'));
assert.ok(G('presale', 'sale').notes[0].includes('2007년 6월 29일'));
r = G('bulk', 'sale'); assert.ok(r.path.includes('최대 1년')); assert.ok(r.notes.some(n => n.includes('10,000')));
console.log('PASS 대량 자료:', r.path);
assert.strictEqual(G('xxx', 'sale').ok, false);
// UI 렌더 확인 — 최소 DOM 스텁
const vals = { 'rt-type': 'land', 'rt-deal': 'sale', 'rt-area': '84.97', 'rt-price': '90000' };
const texts = { 'rt-guide': [], 'rt-calc': [] };
const mk = () => ({ style: {}, children: [], appendChild(c) { this.children.push(c); }, set textContent(v) { this._t = v; }, get textContent() { return this._t !== undefined ? this._t : this.children.map(c => c.textContent).join(' / '); } });
const el = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (texts[id]) texts[id].length = 0; }, appendChild(c) { texts[id].push(c.textContent); } });
const els = {}; Object.keys(vals).concat(['rt-guide', 'rt-calc']).forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: mk };
eval(src);
console.log('UI 토지 매매:', texts['rt-guide'].join(' | '));
console.log('UI 계산:', texts['rt-calc'].join(' | '));
assert.ok(texts['rt-calc'].join().includes('3,495만원'));
assert.ok(texts['rt-guide'].join().includes('토지 메뉴'));
console.log('ALL PASS');
