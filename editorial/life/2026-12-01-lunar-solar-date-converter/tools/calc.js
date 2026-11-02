(function(){
var R='__R__';
var GAN='갑을병정무기경신임계',JI='자축인묘진사오미신유술해',HG='甲乙丙丁戊己庚辛壬癸',HJ='子丑寅卯辰巳午未申酉戌亥';
var ANI=['쥐','소','호랑이','토끼','용','뱀','말','양','원숭이','닭','개','돼지'],WD=['일','월','화','수','목','금','토'];
function dn(y,m,d){return Math.round(Date.UTC(y,m-1,d)/864e5)}
function ymd(x){var t=new Date(x*864e5);return {y:t.getUTCFullYear(),m:t.getUTCMonth()+1,d:t.getUTCDate(),wd:WD[t.getUTCDay()]}}
var MS=[],s=dn(1950,2,17),MIN=s,MAX=dn(2050,12,31);
R.split(',').forEach(function(r,i){var lp=parseInt(r.charAt(0),16),m=0,done=false;for(var k=1;r.length>k;k++){var leap=false;if(lp>0){if(m===lp){if(!done){leap=true;done=true}}}if(!leap)m++;var len=r.charAt(k)==='1'?30:29;MS.push({ly:1950+i,lm:m,leap:leap,s:s,len:len});s+=len}});
function gz(y){var g=(y-4)%10,j=(y-4)%12;return {ko:GAN.charAt(g)+JI.charAt(j),han:HG.charAt(g)+HJ.charAt(j),animal:ANI[j]}}
function toLunar(y,m,d){var x=dn(y,m,d);if(MIN>x)return null;if(x>MAX)return null;for(var i=MS.length-1;i>=0;i--){var o=MS[i];if(x>=o.s){var g=gz(o.ly);return {ly:o.ly,lm:o.lm,ld:x-o.s+1,leap:o.leap,len:o.len,wd:ymd(x).wd,gz:g.ko,han:g.han,animal:g.animal}}}return null}
function findMonth(ly,lm,leap){for(var i=0;MS.length>i;i++){var o=MS[i];if(o.ly===ly){if(o.lm===lm){if(o.leap===leap)return o}}}return null}
function toSolar(ly,lm,ld,leap){var o=findMonth(ly,lm,!!leap);if(!o){if(findMonth(ly,lm,false))return {err:'noleap'};return {err:'range'}}if(ld>o.len)return {err:'noday',len:o.len};var x=o.s+ld-1;if(x>MAX)return {err:'range'};var r=ymd(x);r.len=o.len;return r}
function birthday(lm,ld,leap,year){var out=[];for(var y=year;year+1>=y;y++){var note='',useLeap=!!leap;if(useLeap){if(!findMonth(y,lm,true)){useLeap=false;note='이해에는 윤'+lm+'월이 없어 평달 '+lm+'월로 계산'}}var r=toSolar(y,lm,ld,useLeap);if(r.err==='noday'){r=toSolar(y,lm,r.len,useLeap);note=(note?note+', ':'')+'이해 음력 '+lm+'월은 29일까지라 30일이 없음(29일 날짜)'}out.push({year:y,r:r,note:note})}return out}
function leapYears(a,b){var o=[];MS.forEach(function(x){if(x.leap){if(x.ly>=a){if(b>=x.ly)o.push(x.ly+'년 윤'+x.lm+'월')}}});return o}
window.lunarCalc={toLunar:toLunar,toSolar:toSolar,birthday:birthday,gz:gz,leapYears:leapYears,months:MS};
var $=function(i){return document.getElementById(i)};
if(!$('ls-out1'))return;
function line(box,t,b){var p=document.createElement('p');p.style.margin='0 0 6px';if(b)p.style.fontWeight='700';p.textContent=t;box.appendChild(p)}
function fmt(r){return r.y+'년 '+r.m+'월 '+r.d+'일('+r.wd+')'}
function num(id){return parseInt($(id).value,10)}
function run1(){var box=$('ls-out1');box.innerHTML='';var v=($('ls-sd').value||'').split('-');if(v.length!==3){line(box,'날짜를 선택해 주세요.');return}var L=toLunar(+v[0],+v[1],+v[2]);if(!L){line(box,'1950년 2월 17일부터 2050년 12월 31일까지만 계산합니다.');return}line(box,'양력 '+(+v[0])+'년 '+(+v[1])+'월 '+(+v[2])+'일('+L.wd+') = 음력 '+L.ly+'년 '+(L.leap?'윤':'')+L.lm+'월 '+L.ld+'일',true);line(box,L.leap?'윤달입니다. 같은 해에 평달 '+L.lm+'월이 따로 있습니다.':'평달입니다(윤달 아님).');line(box,'이 음력 달은 '+L.len+'일까지 있습니다('+(L.len===30?'큰달':'작은달')+').');line(box,'음력 '+L.ly+'년은 '+L.gz+'('+L.han+')년, '+L.animal+'띠 해입니다.')}
function run2(){var box=$('ls-out2');box.innerHTML='';var y=num('ls-ly'),m=num('ls-lm'),d=num('ls-ld'),lp=$('ls-leap').checked;if(isNaN(y)){line(box,'연도를 넣어 주세요.');return}if(isNaN(d)){line(box,'날짜를 넣어 주세요.');return}var r=toSolar(y,m,d,lp);if(r.err==='range'){line(box,'음력 1950년 1월 1일부터 2050년 11월 18일까지만 계산합니다.');return}if(r.err==='noleap'){line(box,y+'년에는 윤'+m+'월이 없습니다. 윤달 체크를 풀어 주세요.',true);var ly=leapYears(y,y);line(box,ly.length?'이해의 윤달: '+ly[0]:'이해에는 윤달이 없습니다.');return}if(r.err==='noday'){line(box,y+'년 음력 '+(lp?'윤':'')+m+'월은 '+r.len+'일까지라 '+d+'일이 없습니다.',true);return}var g=gz(y);line(box,'음력 '+y+'년 '+(lp?'윤':'')+m+'월 '+d+'일 = 양력 '+fmt(r),true);line(box,'이 음력 달은 '+r.len+'일까지 있습니다. '+y+'년은 '+g.ko+'('+g.han+')년, '+g.animal+'띠 해입니다.')}
function run3(){var box=$('ls-out3');box.innerHTML='';var m=num('ls-bm'),d=num('ls-bd'),y=num('ls-by'),lp=$('ls-bleap').checked;if(isNaN(y)){line(box,'기준 연도를 넣어 주세요.');return}if(isNaN(d)){line(box,'날짜를 넣어 주세요.');return}if(1950>y){line(box,'1950년부터 2049년까지 넣을 수 있습니다.');return}if(y>2049){line(box,'1950년부터 2049년까지 넣을 수 있습니다.');return}birthday(m,d,lp,y).forEach(function(b){if(b.r.err){line(box,b.year+'년: 계산 범위 밖입니다.');return}line(box,b.year+'년 음력 생일: 양력 '+fmt(b.r),true);if(b.note)line(box,'('+b.note+')')})}
var by=$('ls-by');if(by){var cy=new Date().getFullYear();if(cy>2049)cy=2049;if(1950>cy)cy=1950;by.value=cy}
['ls-sd'].forEach(function(i){$(i).addEventListener('input',run1);$(i).addEventListener('change',run1)});
['ls-ly','ls-lm','ls-ld','ls-leap'].forEach(function(i){$(i).addEventListener('input',run2);$(i).addEventListener('change',run2)});
['ls-bm','ls-bd','ls-by','ls-bleap'].forEach(function(i){$(i).addEventListener('input',run3);$(i).addEventListener('change',run3)});
run1();run2();run3()})();
