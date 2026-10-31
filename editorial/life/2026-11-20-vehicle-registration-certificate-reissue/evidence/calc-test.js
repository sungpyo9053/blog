// ko.html의 확인기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('raw < found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const c = window.regCertCheck;
const has = (arr, s) => arr.some(x => x.includes(s));
const cases = [
  ['개인 본인 분실 온라인 -> 온라인 600원', ['lost', 'online', 'self', 'person', false], r => r.ok && r.route === 'online' && r.fee.startsWith('600원') && has(r.docs, '본인인증')],
  ['외국인 본인 훼손 온라인 -> 온라인', ['damaged', 'online', 'self', 'foreigner', false], r => r.ok && r.route === 'online'],
  ['기재란 부족 온라인 -> 면제', ['full', 'online', 'self', 'person', false], r => r.route === 'online' && r.fee.startsWith('면제')],
  ['법인 온라인 -> 불가, 방문 700원, 법인등기부등본', ['lost', 'online', 'self', 'corp', false], r => !r.ok && r.route === 'visit' && r.fee.startsWith('700원') && has(r.docs, '법인등기부등본')],
  ['사업자 온라인 -> 불가, 사업자등록증', ['lost', 'online', 'self', 'biz', false], r => !r.ok && r.route === 'visit' && has(r.docs, '사업자등록증')],
  ['대리 온라인 -> 불가, 위임장', ['lost', 'online', 'proxy', 'person', false], r => !r.ok && r.route === 'visit' && has(r.docs, '위임장') && has(r.docs, '대리인 신분증')],
  ['법인 대리 방문 -> 법인인감증명서', ['damaged', 'visit', 'proxy', 'corp', false], r => r.ok && has(r.docs, '법인인감증명서') && has(r.docs, '기존 자동차등록증')],
  ['개인 방문 분실 -> 700원, 원본 불요', ['lost', 'visit', 'self', 'person', false], r => r.ok && r.fee.startsWith('700원') && !has(r.docs, '기존 자동차등록증') && has(r.notes, '분실 사유')],
  ['방문 기재란 부족 -> 면제', ['full', 'visit', 'self', 'person', false], r => r.fee.startsWith('면제')],
  ['기재사항 변경 -> 변경등록 1,300원', ['change', 'online', 'self', 'person', false], r => r.route === 'change' && r.fee.includes('1,300원') && has(r.notes, '전입신고')],
  ['공동 소유 -> 위임장 예외 안내', ['lost', 'online', 'self', 'person', true], r => has(r.notes, '공동 소유')],
];
for (const [name, args, ok] of cases) {
  const r = c(...args);
  assert.ok(ok(r), name + ' ' + JSON.stringify(r));
  console.log('PASS', name, '|', r.route, '|', r.fee);
}
// UI 기본값 렌더 확인 — 최소 DOM 스텁
const vals = { 'rc-reason': 'lost', 'rc-method': 'online', 'rc-who': 'self', 'rc-owner': 'person' };
const outP = [];
const els = {};
Object.keys(vals).forEach(id => els[id] = { value: vals[id], addEventListener() {} });
els['rc-joint'] = { checked: false, addEventListener() {} };
els['rc-out'] = { set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } };
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP[0].includes('온라인 재발급 가능'));
