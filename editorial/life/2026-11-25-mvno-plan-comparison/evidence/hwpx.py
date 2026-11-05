import zipfile,re,sys,html
z=zipfile.ZipFile(sys.argv[1]); out=[]
for n in sorted(x for x in z.namelist() if re.match(r'Contents/section\d+\.xml',x)):
    t=z.read(n).decode('utf-8')
    for p in re.findall(r'<hp:p\b[\s\S]*?</hp:p>',t):
        s=''.join(re.sub(r'<[^>]+>','',x) for x in re.findall(r'<hp:t>([\s\S]*?)</hp:t>',p))
        if s.strip(): out.append(html.unescape(s))
print('\n'.join(out))
