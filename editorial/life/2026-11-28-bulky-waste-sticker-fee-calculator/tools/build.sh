#!/bin/sh
# ko.html 재생성: part1 + (data.js + part2.js 계산기) + part3a + 비교표(data.js에서 생성) + part3b + part4
cd "$(dirname "$0")"
timeout 120 node -e "
eval(require('fs').readFileSync('data.js','utf8'));
function f(v){return v===null?'규격 다름':(v===0?'무상·면제':v.toLocaleString('en-US')+'원')}
var o=['<figure class=\"wp-block-table\"><table><thead><tr><th>지역</th><th>장롱 90cm 1쪽</th><th>2인용 침대</th><th>3인용 소파</th><th>냉장고 500ℓ급</th><th>세탁기 10kg급</th></tr></thead><tbody>'];
for(var k in BW){var d=BW[k],v=d[4];o.push('<tr><td>'+d[0]+(d[1]==='서울'?'':'('+d[1]+')')+'</td><td>'+f(v[0])+'</td><td>'+f(v[1])+'</td><td>'+f(v[3])+'</td><td>'+f(v[6])+'</td><td>'+f(v[7])+'</td></tr>');}
o.push('</tbody></table></figure>');process.stdout.write(o.join('\n'));" > /tmp/bw-table.$$
{ cat part1.html; echo '(function(){'; cat data.js; cat part2.js; cat part3a.html; cat /tmp/bw-table.$$; echo; cat part3b.html; cat part4.html; } > ../ko.html
rm -f /tmp/bw-table.$$
