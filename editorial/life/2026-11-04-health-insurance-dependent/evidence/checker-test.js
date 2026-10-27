const fs=require('fs'),vm=require('vm'),assert=require('assert');
const h=fs.readFileSync(process.argv[2],'utf8');
const js=h.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(!js.includes('&&'));
const c={};vm.createContext(c);vm.runInContext(js,c);
const b={rel:'asc',sibok:false,wage:0,pen:0,biz:0,fin:0,etc:0,reg:false,rent:false,dis:false,mar:false,sp:0,prop:0};
const T=[
['연금 2000 정확히',{pen:2000},'유지 가능성 높음'],
['연금 2001',{pen:2001},'탈락 가능성 높음'],
['사업 500 미등록',{biz:500},'유지 가능성 높음'],
['사업 501 미등록',{biz:501},'탈락 가능성 높음'],
['사업 100 등록',{biz:100,reg:true},'탈락 가능성 높음'],
['사업 100 등록 장애인',{biz:100,reg:true,dis:true},'유지 가능성 높음'],
['사업 100 미등록 주택임대',{biz:100,rent:true},'탈락 가능성 높음'],
['사업 100 주택임대 장애인',{biz:100,rent:true,dis:true},'유지 가능성 높음'],
['과표 54000 소득1900',{prop:54000,pen:1900},'유지 가능성 높음'],
['과표 54001 소득1000',{prop:54001,pen:1000},'유지 가능성 높음'],
['과표 54001 소득1001',{prop:54001,pen:1001},'탈락 가능성 높음'],
['과표 90000 소득1000',{prop:90000,pen:1000},'유지 가능성 높음'],
['과표 90001 소득0',{prop:90001},'탈락 가능성 높음'],
['형제 해당 18000',{rel:'sib',sibok:true,prop:18000},'유지 가능성 높음'],
['형제 해당 18001',{rel:'sib',sibok:true,prop:18001},'탈락 가능성 높음'],
['형제 비해당',{rel:'sib',sibok:false},'탈락 가능성 높음'],
['기혼 배우자 2001',{mar:true,sp:2001},'탈락 가능성 높음'],
['기혼 배우자 2000',{mar:true,sp:2000},'유지 가능성 높음'],
['미혼 sp무시',{mar:false,sp:5000},'유지 가능성 높음'],
['연금1500+이자800',{pen:1500,fin:800},'공단 확인 필요'],
['연금1500+이자1100',{pen:1500,fin:1100},'탈락 가능성 높음'],
['연금2100+이자500',{pen:2100,fin:500},'탈락 가능성 높음'],
['과표6억 연금900 이자200',{prop:60000,pen:900,fin:200},'공단 확인 필요'],
];
for(const [n,o,e] of T){const r=c.hlDepJudge(Object.assign({},b,o));console.log((r.verdict===e?'PASS':'FAIL'),n,'->',r.verdict,'|',r.fail.join(' / '));assert.strictEqual(r.verdict,e,n)}
console.log('all',T.length,'ok');
