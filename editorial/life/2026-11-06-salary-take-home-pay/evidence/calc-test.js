// node evidence/calc-test.js — ko.html의 <script>를 그대로 꺼내 실행하고, 간이세액표 전체를 별표 2 PDF 텍스트(annex2.txt)와 대조한다.
const fs=require('fs'),path=require('path'),assert=require('assert');
const dir=path.join(__dirname,'..');
const html=fs.readFileSync(process.argv[2]||path.join(dir,'ko.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
assert.strictEqual(scripts.length,1,'calculator script 1개');
assert.ok(!scripts[0].includes('&'),'script 안에 & 없음');
const el=()=>({value:'',checked:false,style:{},addEventListener(){},appendChild(){},set innerHTML(v){}});
global.window={};global.document={getElementById:el,createElement:el};
eval(scripts[0]);
const calc=window.salaryCalc,tt=window.salaryTableTax;
// 1) 별표 2 전 구간·전 가족수 대조
let n=0;
for(const ln of fs.readFileSync(path.join(__dirname,'annex2.txt'),'utf8').split('\n')){
  const m=ln.match(/^\s*([\d,]+)\s+([\d,]+)\s+((?:(?:[\d,]+|-)\s+){10}(?:[\d,]+|-))\s*$/);if(!m)continue;
  const lo=+m[1].replace(/,/g,'')*1000,hi=+m[2].replace(/,/g,'')*1000;
  const v=m[3].split(/\s+/).map(x=>x==='-'?0:+x.replace(/,/g,''));
  for(let f=1;f<=11;f++){assert.strictEqual(tt(lo,f),v[f-1],`${lo} f${f}`);assert.strictEqual(tt(hi-1,f),v[f-1],`${hi-1} f${f}`);n+=2}
}
assert.strictEqual(tt(769999,1),0);assert.strictEqual(tt(10000000,1),1507400);assert.strictEqual(tt(10000000,4),1170840);
console.log('간이세액표 대조:',n,'건 일치 (646구간 x 11가족 x 하한/상한-1원)');
const show=(name,r)=>console.log(name,JSON.stringify(r));
// 2) 사례
let r=calc(1060000,0,1,0,100);assert.strictEqual(r.np,50350);show('NPS 예시 기준소득월액 106만 -> 연금 50,350',r);
r=calc(3700000,200000,4,0,100);assert.strictEqual(r.taxable,3500000);assert.strictEqual(r.it,49340);
r=calc(3700000,200000,4,2,100);assert.strictEqual(r.it,3510);show('과세 350만·가족4·자녀2 (49,340-45,830)',r);
r=calc(3700000,200000,4,2,80);assert.strictEqual(r.it,2800);
r=calc(8000000,200000,1,0,100);assert.strictEqual(r.npBase,6590000);assert.strictEqual(r.np,313020);show('상한: 월 800만(과세 780만) 연금 기준 659만',r);
r=calc(15200000,200000,1,0,100);assert.strictEqual(r.taxable,15000000);
assert.strictEqual(r.it,Math.floor((1507400+1397000+1000000*0.98*0.38)/10)*10);show('1천만 초과: 과세 1,500만',r);
r=calc(200000,0,1,0,100);assert.strictEqual(r.npBase,410000);assert.strictEqual(r.np,19470);assert.strictEqual(r.hi,10080);assert.strictEqual(r.it,0);show('하한: 월 20만(연금 기준 41만, 건보 하한 20,160원의 절반)',r);
console.log('연봉 예시(가족1·자녀0·비과세 20만, 월=연봉/12):');
for(const y of [24000000,30000000,36000000,40000000,50000000,60000000,70000000,80000000,100000000]){const x=calc(Math.floor(y/12),200000,1,0,100);console.log(y/10000+'만',JSON.stringify(x))}
console.log('연봉 5천 가족별:');
for(const [f,k] of [[1,0],[2,0],[3,1],[4,2]]){const x=calc(Math.floor(50000000/12),200000,f,k,100);console.log(f,k,x.it,x.lt,x.net)}
console.log('ALL OK');
