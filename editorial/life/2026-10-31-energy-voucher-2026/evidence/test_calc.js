const fs=require('fs');const h=fs.readFileSync(process.argv[2],'utf8');
const js=h.split('<script>')[1].split('</script>')[0];
const m=js.match(/var T=[^;]+;/)[0]+js.slice(js.indexOf('function calc'),js.indexOf('function run'));
const {T,S,calc}=new Function(m.replace(/^var /,'var ')+';return {T,S,calc}')();
// table as published in the HTML
const rows=[...h.matchAll(/<tr><td>(\d)인[^<]*<\/td><td>([\d,]+)원<\/td><td>([\d,]+)원<\/td><\/tr>/g)];
let n=0,ok=0;const num=s=>+s.replace(/,/g,'');
for(const r of rows){const k=+r[1],tot=num(r[2]),sub=num(r[3]);
 const cases=[[calc(true,true,false,k,false,0),{ok:1,total:tot,left:tot}],
 [calc(true,true,false,k,false,30000),{ok:1,total:tot,left:tot-30000}],
 [calc(true,true,false,k,false,9999999),{ok:1,total:tot,left:0}],
 [calc(true,true,false,k,true,0),{ok:1,total:sub,left:0}],
 [calc(false,true,false,k,false,0),{ok:0}],[calc(true,false,false,k,false,0),{ok:0}],[calc(true,true,true,k,false,0),{ok:0}]];
 for(const [a,e] of cases){n++;let good=true;for(const key in e)if(a[key]!==e[key])good=false;if(good)ok++;else console.log('FAIL',k,a,e)}}
console.log('rows',rows.length,'cases',n,'pass',ok);
