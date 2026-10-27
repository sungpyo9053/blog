const fs=require('fs');const html=fs.readFileSync(process.argv[2],'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
if(js.includes('&&'))throw 'has &&';
function el(){return{value:'',textContent:'',innerHTML:'',style:{},children:[],appendChild(c){this.children.push(c)},addEventListener(){}}}
const ids={'np-year':el(),'np-amt':el(),'np-out':el()};
global.document={getElementById:i=>ids[i],createElement:()=>el()};
eval(js);
// official NPS table (getOHAF0056M0): [from,to,normal,early]
const T=[[1930,1952,60,55],[1953,1956,61,56],[1957,1960,62,57],[1961,1964,63,58],[1965,1968,64,59],[1969,2010,65,60]];
const early=[70,76,82,88,94],n=0;let cnt=0;
const txt=c=>c.children.map(x=>x.textContent);
for(const [a,b,N,E] of T)for(let y=a;y<=b;y++){
 ids['np-year'].value=String(y);ids['np-amt'].value='100';
 // re-run: trigger by re-eval of run via change listener not stored; call eval again
 ids['np-out']=el();eval(js);const o=ids['np-out'];
 const head=o.children[0].textContent;
 if(!head.includes(`정상 수령 나이 ${N}세 → ${y+N}년`))throw y+' '+head;
 if(!head.includes(`조기노령연금은 ${E}세(${y+E}년)`))throw y+' early '+head;
 if(!head.includes(`연기는 ${N+5}세(${y+N+5}년)`))throw y+' delay '+head;
 const rows=o.children[1].children.slice(1).map(txt);
 for(let k=0;k<5;k++){if(rows[k][2]!==early[k]+'%')throw y+' rate '+rows[k];if(rows[k][1]!==`${E+k}세 (${y+E+k}년)`)throw y+' row '+rows[k]}
 const d=['107.2%','114.4%','121.6%','128.8%','136%'];
 for(let k=0;k<5;k++){if(rows[6+k][2]!==d[k])throw y+' d '+rows[6+k]}
 if(rows[0][3]!=='70만 원'||rows[10][3]!=='136만 원')throw y+' amt '+rows[0]+rows[10];
 cnt++}
console.log('OK',cnt,'birth years 1930-2010 match');
console.log(JSON.stringify(ids['np-out'].children[1].children.slice(1).map(txt)));
ids['np-year'].value='1899';ids['np-out']=el();eval(js);console.log(ids['np-out'].textContent);
