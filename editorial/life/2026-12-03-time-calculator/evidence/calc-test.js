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
const T = window.timeCalc;
const eq = (name, got, exp) => { for (const k of Object.keys(exp)) assert.deepStrictEqual(got[k], exp[k], name + ' ' + k + '=' + JSON.stringify(got[k])); console.log('PASS', name, JSON.stringify(got)); };
// 1. 시각 차이
eq('23:30->01:15 자정 넘김', T.diff('23:30', '01:15', 0), { span: 105, next: true, work: 105, night: 105 });
eq('09:00->18:00 휴게 60', T.diff('09:00', '18:00', 60), { span: 540, next: false, work: 480, night: 0, legal: 60, short: false, over8: 0 });
eq('09:00->17:30 휴게 30 -> 제54조 부족', T.diff('09:00', '17:30', 30), { work: 480, legal: 60, short: true });
eq('09:00->13:00 휴게 0 -> 4h 30분 필요', T.diff('09:00', '13:00', 0), { work: 240, legal: 30, short: true });
eq('22:00->07:00 휴게 60', T.diff('22:00', '07:00', 60), { span: 540, next: true, work: 480, night: 480 });
eq('20:00->05:00', T.diff('20:00', '05:00', 0), { span: 540, night: 420 });
eq('18:00->23:00 야간 1h', T.diff('18:00', '23:00', 0), { night: 60 });
eq('05:00->14:00 야간 1h', T.diff('05:00', '14:00', 0), { night: 60 });
eq('20:00->08:00 12h 야간 8h, 8h 초과 4h', T.diff('20:00', '08:00', 0), { span: 720, night: 480, over8: 240 });
eq('같은 시각 -> 0', T.diff('09:00', '09:00', 0), { span: 0, next: false });
assert.ok(T.diff('09:00', '18:00', -10).error); console.log('PASS 음수 휴게 거부');
assert.ok(T.diff('25:00', '18:00', 0).error); assert.ok(T.diff('09:60', '18:00', 0).error); console.log('PASS 잘못된 시각 거부(25:00, 9:60)');
assert.ok(T.diff('09:00', '10:00', 90).error); console.log('PASS 휴게가 전체보다 긴 경우 거부');
// 파서: 59분 넘김 정규화, 음수 거부, 여러 형식
assert.strictEqual(T.pDur('1:75'), 135); assert.strictEqual(T.hm(T.pDur('1:75')), '2시간 15분');
assert.strictEqual(T.pDur('0:90'), 90); assert.strictEqual(T.hm(90), '1시간 30분'); assert.strictEqual(T.colon(70 + 9 * 60), '10:10');
console.log('PASS 59분 넘김 정규화 1:75=2시간 15분, 0:90=1시간 30분, 9:70=10:10');
for (const bad of ['-1:00', '-30', '-0.5', 'abc', '', '1시간 -5분']) assert.ok(isNaN(T.pDur(bad)), bad);
console.log('PASS 음수·잘못된 입력 거부');
assert.strictEqual(T.pDur('1시간 20분'), 80); assert.strictEqual(T.pDur('45분'), 45); assert.strictEqual(T.pDur('2시간'), 120); assert.strictEqual(T.pDur('7.5'), 450);
console.log('PASS 1시간 20분·45분·2시간·7.5 파싱');
// 2. 다중 줄 합산
eq('기본 다섯 줄 합계', T.sum(['8:30', '9:00', '7:45', '8:15', '9:10'], ''), { count: 5, total: 2560, over40: 160, over52: false, bad: [] });
assert.strictEqual(T.dec(2560), 42.67); assert.strictEqual(T.hm(2560), '42시간 40분');
eq('형식 섞기 + 빈 줄', T.sum(['1시간 30분', '', '45분', '0.5', '22:00~02:30'], ''), { count: 4, total: 90 + 45 + 30 + 270 });
eq('음수 줄은 제외하고 번호 표시', T.sum(['8:00', '-2:00', '8:00', 'x'], ''), { count: 2, total: 960, bad: [2, 4] });
eq('뺄 시간 2:30', T.sum(['8:50', '1:20'], '2:30'), { add: 610, sub: 150, total: 460 });
assert.strictEqual(T.colon(460), '7:40');
eq('주 6일 9시간 = 54h -> 52h 초과', T.sum(['9:00', '9:00', '9:00', '9:00', '9:00', '9:00'], ''), { total: 3240, over40: 840, over52: true });
assert.ok(T.sum(['8:00'], '-1:00').error); console.log('PASS 음수 뺄 시간 거부');
// 3. 도착 시각
eq('22:30 + 3:45 -> 다음 날 02:15', T.add('22:30', '3:45', 1), { clock: '02:15', day: 1 });
eq('23:30 + 2:00 -> 다음 날 01:30', T.add('23:30', '2:00', 1), { clock: '01:30', day: 1 });
eq('00:30 - 1:00 -> 전날 23:30', T.add('00:30', '1:00', -1), { clock: '23:30', day: -1 });
eq('08:00 + 49:00 -> 2일 뒤 09:00', T.add('08:00', '49:00', 1), { clock: '09:00', day: 2 });
eq('10:00 + 0:90 -> 11:30', T.add('10:00', '0:90', 1), { clock: '11:30', day: 0 });
assert.ok(T.add('10:00', '-1:00', 1).error); console.log('PASS 음수 경과시간 거부');
// 4. 소수 시간
assert.strictEqual(T.decToMin('0.25'), 15); assert.strictEqual(T.decToMin('7.5'), 450); assert.strictEqual(T.decToMin('7.3'), 438); assert.strictEqual(T.decToMin('1.01'), 61);
assert.ok(isNaN(T.decToMin('-1')));
assert.strictEqual(T.dec(440), 7.33); assert.strictEqual(T.dec(105), 1.75); assert.strictEqual(T.dec(15), 0.25);
console.log('PASS 소수 환산 0.25h=15분, 7.5h=450분, 7.3h=7시간 18분, 7:20=7.33h');
// 본문 환산표 검산
const rows = [[5, 0.08], [6, 0.1], [10, 0.17], [15, 0.25], [20, 0.33], [25, 0.42], [30, 0.5], [35, 0.58], [40, 0.67], [45, 0.75], [48, 0.8], [50, 0.83], [55, 0.92], [60, 1]];
rows.forEach(([m, d]) => assert.strictEqual(T.dec(m), d, m + '분')); console.log('PASS 환산표', rows.length, '칸');
// UI 렌더 확인 — 최소 DOM 스텁
function render(vals) {
  const outs = {}; let handler = null;
  const el = id => ({ value: vals[id], style: {}, addEventListener(t, f) { handler = f; }, set innerHTML(v) { outs[id] = []; }, appendChild(p) { outs[id].push(p.textContent); } });
  const els = {}; ['tc-o1', 'tc-o2', 'tc-o3', 'tc-o4', ...Object.keys(vals)].forEach(id => els[id] = el(id));
  global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
  eval(src);
  // 페이지 로드 시 스크립트가 2번 칸 기본값을 채우므로, 사용자가 다시 입력한 상황을 input 이벤트로 재현
  if (vals['tc-list']) { els['tc-list'].value = vals['tc-list']; handler(); }
  return outs;
}
let o = render({ 'tc-s': '09:00', 'tc-e': '18:00', 'tc-b': '60', 'tc-list': '', 'tc-sub': '', 'tc-c': '22:30', 'tc-op': '1', 'tc-d': '3:45', 'tc-dh': '7.5', 'tc-hm': '7:20' });
for (const k of ['tc-o1', 'tc-o2', 'tc-o3', 'tc-o4']) console.log('UI 기본값', k + ':', o[k].join(' | '));
assert.ok(o['tc-o1'].join().includes('8시간 (소수 8시간 · 480분)'));
assert.ok(o['tc-o2'].join().includes('42:40 = 42시간 40분'));
assert.ok(o['tc-o3'].join().includes('다음 날 02:15'));
assert.ok(o['tc-o4'].join().includes('7시간 30분') && o['tc-o4'].join().includes('7.33시간'));
o = render({ 'tc-s': '23:30', 'tc-e': '01:15', 'tc-b': '0', 'tc-list': '1:75\n-3:00\n8:00', 'tc-sub': '', 'tc-c': '00:30', 'tc-op': '-1', 'tc-d': '1:00', 'tc-dh': '1.01', 'tc-hm': '-1:00' });
for (const k of ['tc-o1', 'tc-o2', 'tc-o3', 'tc-o4']) console.log('UI 경계값', k + ':', o[k].join(' | '));
assert.ok(o['tc-o1'].join().includes('1시간 45분 (자정을 넘겨'));
assert.ok(o['tc-o2'][0].includes('2번째 줄'));
assert.ok(o['tc-o3'].join().includes('전날 23:30'));
assert.ok(o['tc-o4'].join().includes('반올림') && o['tc-o4'].join().includes('음수 불가'));
console.log('ALL PASS');
