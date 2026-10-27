// usage: node evidence/calc-test.js ko.html
const fs=require('fs');const html=fs.readFileSync(process.argv[2],'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
if(js.includes('&'))throw new Error('script contains &');
function el(){return{value:'0',textContent:'',innerHTML:'',style:{},children:[],appendChild(c){this.children.push(c)},addEventListener(){}}}
const ids={};['yt-g','yt-c','yt-d','yt-m','yt-t','yt-k','yt-kids','yt-out'].forEach(i=>ids[i]=el());
Object.assign(ids['yt-g'],{value:'5000'});
global.window={};global.document={getElementById:i=>ids[i],createElement:()=>el()};
eval(js);
const f=window.cardDeductionCalc,W=10000;
const cases=[
 // name, args(만원), kids, expected result(만원)
 ['25% 미달 → 0 (300만 원 부족)',[4000,500,200,0,0,0],0,0],
 ['25% 정확히 = 0',[4000,900,100,0,0,0],0,0],
 ['예시1 4천 신용위주',[4000,1500,300,0,60,0],0,189],
 ['예시2 5천 자녀2 한도초과+추가',[5000,1000,2000,300,100,100],2,590],
 ['한도 초과, 추가공제 재원 0',[5000,500,2500,0,0,0],0,300],
 ['예시3 8천(7천 초과) 자녀1',[8000,3500,500,200,150,0],1,415],
 ['8천 자녀0',[8000,3500,500,200,150,0],0,390],
 ['7천 초과 추가한도 200 cap',[10000,3000,3000,800,400,0],2,500],
 ['7천 이하 추가한도 300 cap',[7000,1750,3000,500,300,300],0,600],
 ['7천 초과 문화→신용 15%',[8000,2000,0,0,0,1000],0,150],
];
let ok=0;
for(const [n,a,k,exp] of cases){const r=f(...a.map(x=>x*W),k);const got=r.result/W;
 console.log((got===exp?'PASS':'FAIL'),n,'→',got+'만원','(한도전 '+r.ded/W+', 한도 '+r.limit/W+', 추가 '+r.extra/W+', 미달 '+r.short/W+')');
 if(got!==exp)process.exitCode=1;else ok++}
console.log(ok+'/'+cases.length+' passed; UI default output:',ids['yt-out'].children.map(c=>c.textContent).join(' | '));
