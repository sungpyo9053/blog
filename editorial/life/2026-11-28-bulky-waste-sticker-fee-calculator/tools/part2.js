var ITEMS=['장롱 1쪽(폭 90cm)','2인용 침대(매트리스+틀)','2인용 매트리스만','3인용 소파','4인용 나무 식탁(의자 별도)','한쪽 서랍 책상','냉장고 500ℓ급','세탁기 10kg급'];
function won(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,',')+'원'}
function calc(key,qty,freeAppl){
var d=BW[key];if(!d){return null}
var r={name:d[0],src:d[2],total:0,lines:[],missing:[],note:d[6]};
for(var i=0;i!==8;i++){
var q=Math.floor(Number(qty[i])||0);if(q>0){
var fee=d[4][i],lab=d[5][i];
if(fee===null){r.missing.push(ITEMS[i]+': '+lab)}
else if(i>5){if(freeAppl){r.lines.push([ITEMS[i],q,0,'폐가전 무상방문수거, 조례 기준으로는 '+(fee===0?'무상·면제':won(fee*q))])}else{r.lines.push([ITEMS[i],q,fee*q,'별표: '+lab]);r.total+=fee*q}}
else{r.lines.push([ITEMS[i],q,fee*q,'별표: '+lab]);r.total+=fee*q}
}}
return r}
window.bulkyWasteCalc=calc;window.BW=BW;
var sel=document.getElementById('bw-gu');if(!sel){return}
var groups={'서울':'서울특별시','경기':'경기도','경남':'경상남도'};
Object.keys(groups).forEach(function(g){var og=document.createElement('optgroup');og.label=groups[g];Object.keys(BW).forEach(function(k){if(BW[k][1]===g){var o=document.createElement('option');o.value=k;o.textContent=BW[k][0];if(k==='gangnam'){o.selected=true}og.appendChild(o)}});sel.appendChild(og)});
var box=document.getElementById('bw-items');
var def=[1,1,0,1,0,0,1,0];
ITEMS.forEach(function(t,i){var p=document.createElement('p');p.style.margin='0 0 6px';var l=document.createElement('label');l.textContent=t+' ';var inp=document.createElement('input');inp.type='number';inp.min='0';inp.step='1';inp.value=String(def[i]);inp.id='bw-q'+i;inp.style.width='70px';l.appendChild(inp);l.appendChild(document.createTextNode(' 개'));p.appendChild(l);box.appendChild(p);inp.addEventListener('input',run)});
var free=document.getElementById('bw-free'),out=document.getElementById('bw-out');
function para(txt,bold){var p=document.createElement('p');p.style.margin='4px 0';if(bold){p.style.fontWeight='700'}p.textContent=txt;out.appendChild(p)}
function run(){
var q=[];for(var i=0;i!==8;i++){var e=document.getElementById('bw-q'+i);q.push(e?e.value:0)}
var r=calc(sel.value,q,free.checked);out.innerHTML='';if(!r){return}
para(r.name+' 합계: '+won(r.total),true);
r.lines.forEach(function(x){para(x[0]+' '+x[1]+'개 = '+won(x[2])+' ('+x[3]+')')});
r.missing.forEach(function(x){para('합계 제외 - '+x)});
if(r.note){para('참고: '+r.note)}
para('근거: '+r.name+' '+r.src+'(국가법령정보센터). 구청 신청 화면의 품목·금액이 다르면 그쪽이 우선이다.')}
sel.addEventListener('change',run);free.addEventListener('change',run);run();
})();
</script>
