// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('raw < in JS string');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld).mainEntity;
const h3 = html.split('<h2 id="faq">')[1].split('<script')[0].match(/<h3>([^<]+)<\/h3>/g).map(s => s.slice(4, -5));
assert.deepStrictEqual(faq.map(q => q.name), h3); console.log('PASS FAQ JSON-LD ' + faq.length + '개 = 본문 h3');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.funeralCostCalc;
const B = { base: 0, binso: 0, days: 0, meal: 0, guests: 0, etc: 0, cremFee: 0, publicCrem: true, burial: 0, basic: false, basic2: false, merit: false };
const cases = [
  ['기본값: 무빈소 중앙값 + 서울시립승화원 관내', { base: 2402000, cremFee: 120000 }, { hall: 2402000, crem: 120000, total: 2522000, pay: 2522000, dedFuneral: 5000000, dedTotal: 5000000 }],
  ['관외 100만원', { base: 2402000, cremFee: 1000000 }, { total: 3402000 }],
  ['빈소 1일 50만 x 2일 + 식사 1.5만 x 100명', { base: 5700000, binso: 500000, days: 2, meal: 15000, guests: 100, etc: 300000, cremFee: 120000 }, { binso: 1000000, meal: 1500000, hall: 8500000, total: 8620000, dedFuneral: 8620000 }],
  ['상속세 공제 상한 1천만 + 봉안 상한 500만', { base: 9000000, binso: 1000000, days: 3, cremFee: 1000000, burial: 7000000 }, { hall: 12000000, dedFuneral: 10000000, dedBurial: 5000000, dedTotal: 15000000 }],
  ['생계·의료급여 수급자: 공설 화장 면제 + 장제급여 80만', { base: 2402000, cremFee: 1000000, basic: true }, { crem: 0, total: 2402000, jangje: 800000, pay: 1602000 }],
  ['주거급여만: 화장료 면제 없음, 장제급여 80만', { base: 2402000, cremFee: 120000, basic2: true }, { crem: 120000, jangje: 800000, pay: 1722000 }],
  ['희생·공헌자: 공설 화장 면제, 장제급여 없음', { base: 3500000, cremFee: 160000, merit: true }, { crem: 0, jangje: 0, pay: 3500000 }],
  ['사설(직접 입력)은 수급자라도 화장료 면제 안 함', { base: 2402000, cremFee: 500000, publicCrem: false, basic: true }, { crem: 500000, jangje: 800000 }],
  ['인천 별빛당 95만+30만 = 125만', { base: 2402000, cremFee: 160000, burial: 1250000 }, { total: 3812000, dedBurial: 1250000 }],
  ['장제급여는 총액을 넘지 않음', { base: 300000, basic: true }, { jangje: 300000, pay: 0 }],
];
for (const [name, o, exp] of cases) {
  const r = calc(Object.assign({}, B, o));
  for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]);
  console.log('PASS', name, JSON.stringify(r));
}
// 화장장 데이터가 e하늘 원자료(evidence)와 같은지, 본문 표와 같은지
const raw = JSON.parse(fs.readFileSync(path.join(__dirname, 'ehaneul-crematoria-fees-20261107.txt'), 'utf8').split('\n').slice(1).join('\n'));
const MAP = { '용인 평온의 숲': '용인 평온의 숲(나래원)', '화성 함백산추모공원': '화성함백산추모공원(화장)', '세종 은하수공원': '은하수공원 해님의집(화장장)', '강릉 솔향하늘길': '솔향하늘길', '제주 양지공원': '양지공원', '원주추모공원': '원주추모공원 화장장' };
const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
const diffs = [];
for (const [name, region, inn, outt] of window.funeralCrem) {
  const f = raw.find(x => x.name === (MAP[name] || name));
  assert.ok(f, 'evidence에 없음 ' + name);
  const amts = f.fees.filter(x => x.sale === 'Y').map(x => x.facilityamt);
  assert.ok(amts.includes(inn) && amts.includes(outt), name + ' 요금 불일치');
  assert.ok(html.includes('<td>' + name + '</td><td>' + region + '</td><td>' + fmt(inn) + '</td><td>' + fmt(outt) + '</td>'), '표 ' + name);
  diffs.push(outt - inn);
}
console.log('PASS 화장장 ' + window.funeralCrem.length + '곳 e하늘 원자료·본문 표와 일치, 관외-관내 차이 ' + Math.min(...diffs) + '~' + Math.max(...diffs));
assert.strictEqual(Math.min(...diffs), 70000); assert.strictEqual(Math.max(...diffs), 950000);
// 패키지 통계 재계산
const pk = JSON.parse(fs.readFileSync(path.join(__dirname, 'ehaneul-funeral-packages-all-20261107.txt'), 'utf8').split('\n').slice(1).join('\n')).packages;
const med = a => { a = a.slice().sort((x, y) => x - y); const m = a.length >> 1; return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
const has = (p, n) => p.items.some(i => i.packageitemnm === n && i.packageitemprice > 0);
const grp = { mub: pk.filter(p => p.list.packagename.includes('무빈소')), fam: pk.filter(p => p.list.packagename.includes('가족장')), bothX: pk.filter(p => !has(p, '빈소') && !has(p, '식사')), binsoOnly: pk.filter(p => has(p, '빈소') && !has(p, '식사')), both: pk.filter(p => has(p, '빈소') && has(p, '식사')), all: pk };
const want = { mub: [36, 1138600, 2402000, 3500000], fam: [7, 2500000, 3500000, 6500000], bothX: [41, 762000, 2446000, 3900000], binsoOnly: [19, 1419000, 3046000, 6370000], both: [59, 1500000, 5700000, 9739000], all: [123, 762000, 3464000, 9739000] };
for (const k of Object.keys(want)) {
  const a = grp[k].map(p => p.list.discountamount);
  assert.deepStrictEqual([a.length, Math.min(...a), med(a), Math.max(...a)], want[k], k);
}
assert.deepStrictEqual(window.funeralPreset, [want.mub[2], want.fam[2], want.both[2]]);
console.log('PASS 패키지 통계 6개 구분·계산기 프리셋 원자료와 일치');
// UI 기본값 렌더 (최소 DOM 스텁)
const vals = { 'fc-type': '0', 'fc-base': '2402000', 'fc-binso': '0', 'fc-days': '0', 'fc-meal': '0', 'fc-guests': '0', 'fc-etc': '0', 'fc-crem': '0', 'fc-zone': '0', 'fc-cremfee': '120000', 'fc-burial': '0' };
const outP = [];
const el = id => ({ get value() { return vals[id]; }, set value(v) { vals[id] = String(v); }, checked: false, style: {}, addEventListener(t, f) { this['on' + t] = f; }, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['fc-out', 'fc-basic', 'fc-basic2', 'fc-merit', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('총 장례비용: 2,522,000원'));
vals['fc-zone'] = '1'; els['fc-zone'].onchange();
console.log('UI 관외 전환:', outP.join(' | '));
assert.strictEqual(vals['fc-cremfee'], '1000000'); assert.ok(outP.join().includes('3,402,000원'));
vals['fc-crem'] = '7'; els['fc-crem'].onchange(); assert.strictEqual(vals['fc-cremfee'], '480000');
vals['fc-type'] = '2'; els['fc-type'].onchange(); assert.strictEqual(vals['fc-base'], '5700000');
els['fc-basic'].checked = true; els['fc-basic'].onchange();
console.log('UI 부산 관외·빈소 포함·수급자:', outP.join(' | '));
assert.ok(outP.join().includes('총 장례비용: 5,700,000원') && outP.join().includes('유족 부담 4,900,000원'));
console.log('PASS UI');
