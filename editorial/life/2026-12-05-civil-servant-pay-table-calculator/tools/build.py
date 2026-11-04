# tools/ko.src.html + tables.json(extract.py 결과) -> ../ko.html
import json, os
H = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(H, 'tables.json')))
G = ['1급', '2급', '3급', '4급', '5급', '6급', '7급', '8급', '9급']
P = ['치안정감·소방정감', '치안감·소방감', '경무관·소방준감', '총경·소방정', '경정·소방령', '경감·소방경', '경위·소방위', '경사·소방장', '경장·소방교', '순경·소방사']
names = {'g': G, 'a': G, 'p': P, 't': ['교원']}
data = json.dumps({'tab': T, 'names': names}, ensure_ascii=False, separators=(',', ':'))
script = """<script>
(function(){
var D=@@D@@;
function jgRate(y){if(y>=10){return 0.5}if(y>=9){return 0.45}if(y>=8){return 0.4}if(y>=7){return 0.35}if(y>=6){return 0.3}if(y>=5){return 0.25}if(y>=2){return 0.2}return 0.1}
function jgAdd(y){if(y>=25){return 130000}if(y>=20){return 110000}if(y>=15){return 80000}if(y>=10){return 60000}if(y>=5){return 50000}return 30000}
function calc(type,grade,step,years){
var col=D.tab[type][grade];
if(!col){return null}
var pay=col[step-1];
if(!pay){return null}
var r={pay:pay,payYear:pay*12,jg:Math.round(pay*jgRate(years)),jgAddMonth:jgAdd(years),holiday:Math.round(pay*0.6),meal:160000};
r.total=r.payYear+r.jg*2+r.jgAddMonth*12+r.holiday*2+r.meal*12;
return r}
window.civilPayCalc=calc;
window.civilPayData=D;
var $=function(i){return document.getElementById(i)};
var out=$('cs-out');
if(!out){return}
function won(n){return n.toLocaleString('ko-KR')+'원'}
function opt(sel,list,keep){var old=sel.value;sel.innerHTML='';list.forEach(function(t,i){var o=document.createElement('option');o.value=String(i);o.textContent=t;sel.appendChild(o)});if(keep){if(old!==''){if(list.length>Number(old)){sel.value=old}}}}
function fillGrade(){var t=$('cs-type').value;opt($('cs-grade'),D.names[t],false);if(t==='g'){$('cs-grade').value='8'}if(t==='a'){$('cs-grade').value='8'}if(t==='p'){$('cs-grade').value='9'}$('cs-grade-row').style.display=t==='t'?'none':'';fillStep()}
function fillStep(){var t=$('cs-type').value,g=Number($('cs-grade').value)||0,n=D.tab[t][g].length,l=[];for(var i=1;n>=i;i++){l.push(i+'호봉')}opt($('cs-step'),l,true);run()}
function run(){
var t=$('cs-type').value,g=Number($('cs-grade').value)||0,s=Number($('cs-step').value)+1,y=parseFloat($('cs-years').value),L=[];
if(!(y>=0)){y=0}
var r=calc(t,g,s,y),label=t==='t'?'교원 '+s+'호봉':D.names[t][g]+' '+s+'호봉';
if(!r){L.push('해당 호봉이 없습니다.')}else{
L.push(label+' 월 봉급: '+won(r.pay));
L.push('봉급 12개월: '+won(r.payYear));
L.push('정근수당(1월·7월 각): '+won(r.jg)+' (월봉급액의 '+Math.round(jgRate(y)*100)+'%)');
L.push('정근수당 가산금: 월 '+won(r.jgAddMonth));
L.push('명절휴가비(설·추석 각): '+won(r.holiday));
L.push('정액급식비: 월 '+won(r.meal));
L.push('연간 합계(위 항목만): '+won(r.total));
}
out.innerHTML='';
L.forEach(function(x){var p=document.createElement('p');p.style.margin='0 0 6px';p.textContent=x;out.appendChild(p)})}
$('cs-type').addEventListener('change',fillGrade);
$('cs-grade').addEventListener('change',fillStep);
$('cs-step').addEventListener('change',run);
$('cs-years').addEventListener('input',run);
fillGrade()})();
</script>""".replace('@@D@@', data)
g = T['g']
rows = ['<table>', '<thead><tr><th>호봉</th>' + ''.join('<th>%s</th>' % x for x in G) + '</tr></thead>', '<tbody>']
for h in range(max(len(c) for c in g)):
    rows.append('<tr><td>%d</td>' % (h + 1) + ''.join('<td>%s</td>' % (format(c[h], ',') if h < len(c) else '') for c in g) + '</tr>')
rows += ['</tbody>', '</table>']
src = open(os.path.join(H, 'ko.src.html')).read()
html = src.replace('@@SCRIPT@@', script).replace('@@TABLE@@', '\n'.join(rows))
sc = script[script.index('>') + 1:]
assert '&' not in sc and '<' not in sc.replace('</script>', ''), 'bad char in script'
assert '\n\n' not in script
open(os.path.join(H, '..', 'ko.html'), 'w').write(html)
print('ko.html written', len(html))
