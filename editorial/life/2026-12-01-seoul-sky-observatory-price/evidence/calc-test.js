// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (src.indexOf('<') >= 0) throw new Error('raw < in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const h3faq = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>/g).length;
assert.strictEqual(faq.length, h3faq, 'FAQ JSON-LD count');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.seoulSkyCalc;
const C = (a, t, c, s) => ({ adult: a, teen: t, child: c, senior: s });
const cases = [
  // name, cnt, type, disc, total, regular
  ['부부+소인1 정가', C(2, 0, 1, 0), 'general', 'none', 95000, 95000],
  ['부부+소인1 다인권', C(2, 0, 1, 0), 'general', 'multi', 78000, 95000],
  ['부부+소인1 조조', C(2, 0, 1, 0), 'general', 'morning', 73500, 95000],
  ['부부+소인2 다인권', C(2, 0, 2, 0), 'general', 'multi', 102000, 124000],
  ['부부+소인2 송파', C(2, 0, 2, 0), 'general', 'songpa', 92000, 124000],
  ['부부+소인2 통신사 일반', C(2, 0, 2, 0), 'general', 'telco', 108300, 124000],
  ['부부+소인2 LG VIP콕', C(2, 0, 2, 0), 'general', 'lguVip', 105000, 124000],
  ['조부모2+손주1 경로만', C(0, 0, 1, 2), 'general', 'none', 80000, 87000],
  ['조부모2+손주1 다인권', C(0, 0, 1, 2), 'general', 'multi', 78000, 87000],
  ['커플 SO SWEET NIGHT', C(2, 0, 0, 0), 'general', 'night', 49000, 66000],
  ['어른3 SO SWEET NIGHT(2+1)', C(3, 0, 0, 0), 'general', 'night', 82000, 99000],
  ['커플 KT VVIP', C(2, 0, 0, 0), 'general', 'ktVvip', 33000, 66000],
  ['어른1+소인1 KT VVIP', C(1, 0, 1, 0), 'general', 'ktVvip', 29000, 62000],
  ['KT VVIP 1명(무료 없음)', C(1, 0, 0, 0), 'general', 'ktVvip', 33000, 33000],
  ['부부+학생1 학생우대', C(2, 1, 0, 0), 'general', 'student', 90500, 99000],
  ['장애인+동반1+1명', C(3, 0, 0, 0), 'general', 'welfare', 79200, 99000],
  ['문화누리 2명 한도 4명', C(2, 0, 2, 0), 'general', 'nuri', 109000, 124000],
  ['문화누리+가족관계증명서 4명', C(2, 0, 2, 0), 'general', 'nuriFamily', 96000, 124000],
  ['임신부 어른2', C(2, 0, 0, 0), 'general', 'pregnant', 56100, 66000],
  ['홈페이지 예약 2+1', C(2, 0, 1, 0), 'general', 'reserve', 90500, 95000],
  ['롯데월드카드 어른2', C(2, 0, 0, 0), 'general', 'lwcard', 33000, 66000],
  ['롯데월드카드 어른1+소인1', C(1, 0, 1, 0), 'general', 'lwcard', 45500, 62000],
  ['롯데멤버스 어른2', C(2, 0, 0, 0), 'general', 'lmembers', 49500, 66000],
  ['M포인트 어른2', C(2, 0, 0, 0), 'general', 'mpoint', 62000, 66000],
  ['경로 조조', C(0, 0, 0, 1), 'general', 'morning', 24500, 29000],
  ['어른5 다인권(4+1)', C(5, 0, 0, 0), 'general', 'multi', 135000, 165000],
  ['어른6 다인권(3+3)', C(6, 0, 0, 0), 'general', 'multi', 156000, 198000],
  ['Fast Pass 2+1', C(2, 0, 1, 0), 'fast', 'none', 186000, 186000],
  ['Fast Pass 할인 미적용', C(2, 0, 0, 0), 'fast', 'telco', 124000, 124000],
  ['패키지 2+1 우대가', C(2, 0, 1, 0), 'aqua', 'none', 148000, 180000],
  ['패키지 2+1 롯데월드카드', C(2, 0, 1, 0), 'aqua', 'lwcard', 128000, 180000],
  ['패키지 경로2', C(0, 0, 0, 2), 'aqua', 'none', 92000, 112000],
  ['스카이브릿지 2명', C(2, 0, 0, 0), 'bridge', 'none', 260000, 260000],
  ['스카이브릿지 단체 10명', C(10, 0, 0, 0), 'bridge', 'none', 1180000, 1300000],
  ['스카이브릿지 117층 2명', C(2, 0, 0, 0), 'bridge117', 'none', 212000, 212000],
  ['음수·빈값 방어', C(-3, '', 'x', null), 'general', 'none', 0, 0],
];
for (const [name, cnt, type, disc, total, regular] of cases) {
  const r = calc(cnt, type, disc);
  assert.strictEqual(r.total, total, name + ' total=' + r.total);
  assert.strictEqual(r.regular, regular, name + ' regular=' + r.regular);
  console.log('PASS', name, '총액', r.total.toLocaleString('ko-KR') + '원', '정가', r.regular.toLocaleString('ko-KR') + '원');
}
assert.strictEqual(calc(C(2, 0, 0, 0), 'fast', 'telco').applied, false);
console.log('PASS Fast Pass에 할인 고르면 applied=false');
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'ss-adult': '2', 'ss-teen': '0', 'ss-child': '1', 'ss-senior': '0', 'ss-infant': '0', 'ss-type': 'general', 'ss-disc': 'none' };
const outP = [];
const mk = id => ({ value: vals[id], addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent || (p.child && p.child.textContent)); } });
const els = {}; ['ss-out', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ appendChild(c) { this.child = c; this.textContent = c.textContent; } }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('95,000원'));
assert.ok(outP.join().includes('78,000원'));
// 스카이브릿지 + 소인 선택 시 경고
vals['ss-type'] = 'bridge'; Object.keys(vals).forEach(id => els[id].value = vals[id]);
eval(src);
console.log('스카이브릿지 출력:', outP.join(' | '));
assert.ok(outP.join().includes('동절기 운휴'));
assert.ok(outP.join().includes('140cm'));
console.log('ALL PASS');
