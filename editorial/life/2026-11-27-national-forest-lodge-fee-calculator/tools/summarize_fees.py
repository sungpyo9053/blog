# national-48-fees.tsv → 시설 유형 × 최대인원별 (비수기 주중, 성수기·주말) 요금 빈도
import csv, collections, re, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8').readlines()[1:], delimiter='\t'))
def kind(x):
    t = x['type']
    if x['section'] == 'camp' or (re.search('야영|오토|반려|백패킹|캠핑', t + x['name']) and not re.search('숲속|휴양관|연립', t)):
        n = x['name'] + t
        return 'camp-' + ('캠핑카' if '캠핑카' in n else '캐빈' if '캐빈' in n else '오토캠핑' if '오토' in n else '데크' if '데크' in n else '기타')
    for k in ['휴양관', '연립', '숲속의집', '수련장', '캐빈']:
        if k in t: return k
    return '유형표기없음'
g = collections.defaultdict(collections.Counter); f = collections.defaultdict(set)
for x in rows:
    k = (kind(x), int(re.sub(r'\D', '', x['cap']) or 0))
    g[k][(int(x['offweek']), int(x['peakwkend']))] += 1; f[k].add(x['forest'])
print('유형\t최대인원\t시설수\t휴양림수\t(비수기주중,성수기·주말)=개수 상위')
for k in sorted(g):
    print(k[0], k[1], sum(g[k].values()), len(f[k]), ' '.join('%d/%d=%d' % (a, b, c) for (a, b), c in g[k].most_common(4)), sep='\t')
