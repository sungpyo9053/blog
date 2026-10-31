// ko.html 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
if (/'[^'\n]*<[^'\n]*'/.test(src)) throw new Error('< inside string literal');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
JSON.parse(ld);
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const calc = window.idolbomCalc;
// 1) 성평등가족부 2026 요금표(시간당, 아이 1명, 평일 주간): [유형, 서비스, 구분, 정부지원, 본인부담]
const mogef = [
  ['ga','basic','pre',10872,1918],['ga','comp','pre',10872,5748],['ga','basic','school',10232,2558],['ga','comp','school',10232,6388],
  ['na','basic','pre',7674,5116],['na','comp','pre',7674,8946],['na','basic','school',6396,6394],['na','comp','school',6396,10224],
  ['da','basic','pre',3838,8952],['da','comp','pre',3838,12782],['da','basic','school',3198,9592],['da','comp','school',3198,13422],
  ['ra','basic','pre',1920,10870],['ra','comp','pre',1920,14700],['ra','basic','school',1280,11510],['ra','comp','school',1280,15340],
  ['ma','basic','pre',0,12790],['ma','comp','school',0,16620],['ga','infant','pre',10872,1918],['ra','infant','school',1920,10870],
];
for (const [t, s, sc, gov, own] of mogef) {
  const r = calc(t, s, sc, 1, false, 1, false, false);
  assert.strictEqual(r.hour.gov, gov, t + s + sc + ' gov ' + r.hour.gov);
  assert.strictEqual(r.hour.own, own, t + s + sc + ' own ' + r.hour.own);
}
console.log('PASS 성평등가족부 표 ' + mogef.length + '칸');
// 2) 아이돌봄 누리집 30분 요금표(아이 수별 아이 1명당 30분): 요금, [가A정부,가A본인,가B정부,가B본인, 나..., 다..., 라...]
const idol = {
  'basic,0': { 1: [6395, [5436,959,5116,1279, 3837,2558,3198,3197, 1919,4476,1599,4796, 960,5435,640,5755]],
               2: [4796, [4077,719,3837,959, 2878,1918,2398,2398, 1439,3357,1199,3597, 720,4076,480,4316]],
               3: [4263, [3624,639,3411,852, 2558,1705,2132,2131, 1279,2984,1066,3197, 640,3623,427,3836]] },
  'basic,1': { 1: [9590, [8152,1438,7672,1918, 5754,3836,4795,4795, 2877,6713,2398,7192, 1439,8151,959,8631]],
               2: [7192, [6114,1078,5754,1438, 4316,2876,3596,3596, 2158,5034,1798,5394, 1079,6113,720,6472]],
               3: [6393, [5435,958,5115,1278, 3836,2557,3197,3196, 1918,4475,1599,4794, 959,5434,640,5753]] },
  'comp,0':  { 1: [8310, [5436,2874,5116,3194, 3837,4473,3198,5112, 1919,6391,1599,6711, 960,7350,640,7670]],
               2: [6232, [4077,2155,3837,2395, 2878,3354,2398,3834, 1439,4793,1199,5033, 720,5512,480,5752]],
               3: [5540, [3624,1916,3411,2129, 2558,2982,2132,3408, 1279,4261,1066,4474, 640,4900,427,5113]] },
  'comp,1':  { 1: [12465, [8152,4313,7672,4793, 5754,6711,4795,7670, 2877,9588,2398,10067, 1439,11026,959,11506]],
               2: [9348, [6114,3234,5754,3594, 4316,5032,3596,5752, 2158,7190,1798,7550, 1079,8269,720,8628]],
               3: [8310, [5435,2875,5115,3195, 3836,4474,3197,5113, 1918,6392,1599,6711, 959,7351,640,7670]] },
};
let cells = 0;
for (const key of Object.keys(idol)) {
  const [svc, night] = key.split(',');
  for (const n of [1, 2, 3]) {
    const [fee30, arr] = idol[key][n];
    ['ga','na','da','ra'].forEach((t, ti) => ['pre','school'].forEach((sc, si) => {
      const r = calc(t, svc, sc, n, night === '1', 0.5, false, false);
      const g = arr[ti*4 + si*2], o = arr[ti*4 + si*2 + 1];
      assert.strictEqual(r.month.fee, fee30 * n, key + ' n' + n + ' fee');
      assert.strictEqual(r.month.gov, g * n, key + ' n' + n + t + sc + ' gov ' + r.month.gov / n + ' vs ' + g);
      assert.strictEqual(r.month.own, o * n, key + ' n' + n + t + sc + ' own');
      cells += 2;
    }));
  }
}
console.log('PASS 누리집 30분 요금표 ' + cells + '칸 (기본형·종합형 × 주간·야간휴일 × 아이 1~3명)');
// 3) 본문 예시: 가형 미취학 기본형 월 60시간
let r = calc('ga','basic','pre',1,false,60,false,false);
assert.strictEqual(r.month.own, 115080); assert.strictEqual(r.month.gov, 652320);
assert.strictEqual(calc('na','basic','pre',1,false,60,false,false).month.own, 306960);
assert.strictEqual(calc('ra','basic','pre',1,false,60,false,false).month.own, 652200);
console.log('PASS 본문 예시 월 60시간: 가형 115,080 / 나형 306,960 / 라형 652,200');
// 4) 한도: 월 80h = 연 960h 딱 맞음, 월 100h는 240h 초과, 취약가구 1,080h
r = calc('ga','basic','pre',1,false,80,false,false); assert.strictEqual(r.excess, 0); assert.strictEqual(r.yearOwn, 1918*960);
r = calc('ga','basic','pre',1,false,100,false,false); assert.strictEqual(r.excess, 240); assert.strictEqual(r.yearOwn, 1918*960 + 12790*240);
r = calc('ga','basic','pre',1,false,100,false,true); assert.strictEqual(r.limit, 1080); assert.strictEqual(r.excess, 120);
assert.strictEqual(r.hour.gov, 11512); // 가형 + 5% = 90%: ceil(6395*0.9)=5756 x2
console.log('PASS 연 960/1,080시간 한도, 가형 취약가구 90%');
// 5) 영아종일제 월 200시간 초과분 전액 부담, 다자녀 10%
r = calc('na','infant','school',1,false,220,false,false); assert.strictEqual(r.excess, 20); assert.strictEqual(r.month.own, 5116*200 + 12790*20);
r = calc('ga','basic','pre',2,false,10,true,false); assert.strictEqual(r.multiDisc, Math.round(719*2*10*2*0.1)); 
assert.strictEqual(calc('ma','basic','pre',2,false,10,true,false).multiDisc, undefined);
console.log('PASS 영아종일제 200시간 초과, 다자녀 10%(마형 제외)');
// 6) UI 기본값 렌더(나형·기본형·미취학·1명·주간·60시간)
const vals = { 'ic-type':'na','ic-svc':'basic','ic-school':'pre','ic-n':'1','ic-night':'0','ic-hours':'60' };
const outP = [];
const el = id => ({ value: vals[id], checked: false, style: {}, addEventListener() {}, set innerHTML(v) { outP.length = 0; }, appendChild(p) { outP.push(p.textContent); } });
const els = {}; ['ic-out','ic-multi','ic-vuln', ...Object.keys(vals)].forEach(id => els[id] = el(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 기본값 출력:', outP.join(' | '));
assert.ok(outP.join().includes('306,960원'));
