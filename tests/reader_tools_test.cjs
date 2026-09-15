const assert = require('assert');
const {rest,retry,inventory} = require('../deploy/wordpress/huntlab-warm-editorial/assets/reader-tools.js');
const good={status:201,type:'application/json; charset=utf-8',body:'{"id":123,"status":"publish"}'};
assert.strictEqual(rest(good).ok,true);
assert.strictEqual(rest({...good,status:403}).ok,false);
assert.strictEqual(rest({...good,type:'text/html',body:'<html>login</html>'}).code,'type');
for(const body of ['null','[]','{"id":true}','{"id":-1}','{"id":0}','{"id":"123"}','{']) assert.strictEqual(rest({...good,body}).ok,false);
assert.strictEqual(rest({...good,expected:124}).code,'identity');
assert.strictEqual(rest({...good,body:'{"id":123,"status":"draft"}'}).code,'publication');
const now='2026-09-15T12:00:00Z';
assert.strictEqual(retry({retry:'120',now}).seconds,120);
assert.strictEqual(retry({retry:'Tue, 15 Sep 2026 12:00:07 GMT',now}).seconds,7);
assert.strictEqual(retry({retry:'Tue, 15 Sep 2026 11:00:07 GMT',now}).seconds,0);
for(const value of ['-1','1.2','NaN','tomorrow','Infinity','']) assert.strictEqual(retry({retry:value,now}).ok,false);
assert.strictEqual(retry({retry:'12',now:'2026-09-15T12:00:00'}).ok,false);
assert.strictEqual(inventory({total:3,perPage:2,ids:'1,2,3'}).ok,true);
assert.strictEqual(inventory({total:3,perPage:2,ids:'1,1,3'}).ok,false);
assert.strictEqual(inventory({total:119,perPage:100,ids:Array.from({length:100},(_,i)=>i+1).join(',')}).ok,false);
assert.strictEqual(inventory({total:0,perPage:100,ids:''}).ok,true);
assert.strictEqual(inventory({total:'',perPage:100,ids:''}).ok,false);
assert.strictEqual(inventory({total:1,perPage:100,ids:'NaN'}).ok,false);
console.log('Reader tools: response, retry and inventory edge cases passed');

// Exercise the actual DOM handler without a browser or third-party dependency.
const vm = require('vm'), fs = require('fs');
const handlers = {}, output = {textContent:'이전 성공 결과',dataset:{ok:'true'}};
const form = {addEventListener:(event,fn)=>{handlers[event]=fn;}, querySelector:()=>output};
const container = {
  querySelector:selector=>selector==='[name="now"]' ? {value:''} : {addEventListener:()=>{}},
  querySelectorAll:selector=>selector==='form[data-check]' ? [form] : []
};
vm.runInNewContext(fs.readFileSync(require.resolve('../deploy/wordpress/huntlab-warm-editorial/assets/reader-tools.js'),'utf8'), {
  document:{querySelectorAll:()=>[container]}, Date, FormData:class {}
});
handlers.input();
assert.strictEqual(output.dataset.ok,undefined);
assert.strictEqual(output.textContent,'입력이 바뀌었습니다. 다시 검사하세요.');
output.textContent=''; handlers.input(); assert.strictEqual(output.textContent,'');
console.log('Reader tools: edited inputs invalidate stale verdicts');
