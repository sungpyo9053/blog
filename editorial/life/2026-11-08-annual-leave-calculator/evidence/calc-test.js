// ko.html의 계산기 <script>를 그대로 추출해 실행한다: node evidence/calc-test.js
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../ko.html','utf8');
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
assert(!code.includes('&'),'script must not contain &');
const ctx={window:{},Math,Date,String,Number};vm.runInNewContext(code,ctx);
const {calc,pay}=ctx.window.annualLeaveCalc;
const cases=[
 ['6개월차','2026-04-01','2026-10-28',{years:0,monthly:6,total:6}],
 ['11개월 전날','2025-11-08','2026-10-07',{years:0,monthly:10,total:10}],
 ['1년 정확히(365일째 퇴사)','2025-11-08','2026-11-07',{years:0,monthly:11,total:11}],
 ['1년+1일(366일째 재직)','2025-11-08','2026-11-08',{years:1,monthly:11,total:26,current:15}],
 ['1년 계약직 1/1~12/31','2025-01-01','2025-12-31',{years:0,monthly:11,total:11}],
 ['2년','2024-11-08','2026-11-08',{years:2,total:41,current:15}],
 ['3년','2023-11-08','2026-11-08',{years:3,total:57,current:16}],
 ['21년','2005-11-08','2026-11-08',{years:21,current:25}],
 ['26년(25 cap)','2000-01-01','2026-10-28',{years:26,current:25}],
 ['1월31일 입사 첫 발생','2026-01-31','2026-03-01',{monthly:1}],
 ['1월31일 입사 2/28 기준','2026-01-31','2026-02-28',{monthly:0}],
];
for(const [name,j,r,exp] of cases){const res=calc(j,r);for(const k in exp)assert.strictEqual(res[k],exp[k],name+' '+k+' '+res[k]);
 console.log('PASS',name,j,'->',r,'| 근속',res.years+'년','1년미만',res.monthly+'일','이번해',res.current+'일','누적',res.total+'일');}
assert.strictEqual(calc('2026-05-01','2026-04-30'),null);
assert.strictEqual(pay(96000,5),480000);assert.strictEqual(pay(96000,0.5),48000);assert.strictEqual(pay('',3),0);
console.log('PASS 기준일<입사일 -> null, 연차수당 96,000x5=480,000 / x0.5=48,000');
