// ko.html의 발급 경로 찾기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/'[^'\n]*</.test(src)) throw new Error('< inside string literal');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const route = window.hiqRoute;
const base = { who: 'self', device: 'pc', auth: 'simple', submit: 'paper', special: false };
const cases = [
  ['성인·PC·간편·종이 -> 홈페이지 프린트', {}, r => r.primary.includes('프린트') && r.items.join().includes('프린터')],
  ['성인·PC·공동인증서·전자 -> 홈페이지 전자증명서+최초 등록', { auth: 'cert', submit: 'digital' }, r => r.primary.includes('전자증명서') && r.items.join().includes('최초 1회 등록') && r.items.join().includes('전자문서지갑')],
  ['성인·PC·간편·팩스 -> 홈페이지 팩스+결과조회', { submit: 'fax' }, r => r.primary.includes('홈페이지') && r.primary.includes('팩스') && r.notes.join().includes('팩스 발송결과 조회')],
  ['성인·모바일·간편·종이 -> 앱 팩스(프린트 없음)', { device: 'mobile' }, r => r.primary.includes('건강보험25시') && r.notes.join().includes('프린트 발급이 없고')],
  ['성인·모바일·간편·전자 -> 앱 전자증명서', { device: 'mobile', submit: 'digital' }, r => r.primary.includes('앱') && r.primary.includes('전자증명서')],
  ['성인·모바일·공동인증서 -> PC 권장, 모바일웹 공동인증서 불가', { device: 'mobile', auth: 'cert' }, r => r.primary.includes('PC') && r.notes.join().includes('공동인증서를 쓸 수 없다')],
  ['성인·인증 없음 -> ARS 팩스+지사', { auth: 'none' }, r => r.primary.includes('디지털ARS') && r.alt.join().includes('지사')],
  ['65세 이상·인증 없음 -> 상담사 팩스', { auth: 'none', special: true }, r => r.primary.includes('상담사')],
  ['기기 없음 -> 전화·방문', { device: 'none' }, r => r.primary.includes('1577-1000')],
  ['14세 미만 자녀 -> 지사(법정대리인)+기본증명서', { who: 'child' }, r => r.primary.includes('지사') && r.items.join().includes('기본증명서')],
  ['14세 이상 미성년·인증 없음 -> 지사(청소년증)', { who: 'minor14', auth: 'none' }, r => r.primary.includes('지사') && r.items.join().includes('청소년증')],
  ['14세 이상 미성년·간편 -> 온라인 가능', { who: 'minor14' }, r => r.primary.includes('홈페이지') && r.notes.join().includes('만 14세 이상')],
  ['성인 대리 -> 확인하지 못했다', { who: 'proxy' }, r => r.notes.join().includes('확인하지 못했다')],
];
for (const [name, o, ok] of cases) {
  const r = route(Object.assign({}, base, o));
  assert.ok(r.notes[0].includes('수수료'), name + ' fee note');
  assert.ok(ok(r), name + ' ' + JSON.stringify(r));
  console.log('PASS', name, '=>', r.primary);
}
// UI 기본값 렌더 — 최소 DOM 스텁
const vals = { 'hiq-who': 'self', 'hiq-device': 'pc', 'hiq-auth': 'simple', 'hiq-submit': 'paper' };
const outP = [];
const mk = () => ({ style: {}, children: [], textContent: '', appendChild(c) { this.children.push(c) } });
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['hiq-special'] = { checked: false, addEventListener() {} };
els['hiq-out'] = { set innerHTML(v) { outP.length = 0 }, appendChild(p) { outP.push(p.children.map(c => c.textContent).join('')) } };
global.document = { getElementById: id => els[id], createElement: mk, createTextNode: t => ({ textContent: t }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('프린트 발급'));
