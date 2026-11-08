import json,sys,html,re
def strip(s):
    s=html.unescape(html.unescape(s or ''))
    s=re.sub(r'<br\s*/?>|</(p|li|tr|div|h\d)>','\n',s)
    s=re.sub(r'</t[dh]>',' | ',s)
    s=re.sub(r'<[^>]+>','',s)
    s=re.sub(r'[ \t\xa0]+',' ',s)
    return re.sub(r'\n\s*\n+','\n',s).strip()
d=json.load(open(sys.argv[1]))
items=d.get('list') or [d.get('data') or d]
for r in items:
    if not isinstance(r,dict): continue
    head=[str(r.get(k)) for k in ('bnftSeq','anlUtztnSeq','notiSeq','bnftDvNm','titl','prgrsBgnDtFmt','prgrsEndDtFmt','prgrsBgnDt','prgrsEndDt','lowstAmtFmt','amtSctnCntn','regDtm') if r.get(k)]
    print('=====',' | '.join(head))
    for k in ('cntn','cutnCntn','dtlCntn','bnftCntn','ntcCntn'):
        if r.get(k): print(strip(r[k]))
