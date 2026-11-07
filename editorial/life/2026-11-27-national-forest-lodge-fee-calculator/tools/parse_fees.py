# 국립자연휴양림 48곳 이용요금 페이지 → fees.tsv (forest, section, type, name, cap, offweek, peakwkend)
import re, sys, html, os
src, nat, out = sys.argv[1], sys.argv[2], sys.argv[3]
names = dict(l.rstrip('\n').split('\t') for l in open(nat, encoding='utf-8') if l.strip())
rows = []
def cells(tr):
    return [re.sub(r'\s+', ' ', html.unescape(re.sub(r'(?s)<[^>]+>', ' ', c))).strip() for c in re.findall(r'(?is)<t[hd][^>]*>(.*?)</t[hd]>', tr)]
for fid, nm in names.items():
    t = open(os.path.join(src, fid + '.html'), encoding='utf-8', errors='ignore').read()
    for ti, tb in enumerate(re.findall(r'(?is)<table.*?</table>', t)):
        cap = re.search(r'(?is)<caption>(.*?)</caption>', tb)
        capt = re.sub(r'(?s)<[^>]+>', ' ', cap.group(1)) if cap else ''
        sec = 'room' if '숙박' in capt else ('camp' if '야영' in capt else None)
        if not sec: continue
        typ = ''
        for tr in re.findall(r'(?is)<tr.*?</tr>', tb):
            c = cells(tr)
            if len(c) < 4 or not re.match(r'^[\d,]+$', c[-1].replace(' ', '')): continue
            p1, p2, capn = c[-2], c[-1], c[-3]
            name = c[-4]
            if sec == 'room' and len(c) >= 5 and re.search('숲속|휴양관|연립|수련장|캐빈|야영|오토|캠핑', c[-5]): typ = c[-5].replace(' ', '')
            rows.append([nm, sec, typ if sec == 'room' else '', name, capn, p1.replace(',', ''), p2.replace(',', '')])
with open(out, 'w', encoding='utf-8') as f:
    f.write('forest\tsection\ttype\tname\tcap\toffweek\tpeakwkend\n')
    for r in rows: f.write('\t'.join(r) + '\n')
print(len(rows))
