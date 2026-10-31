import zipfile,re,sys,html
z=zipfile.ZipFile(sys.argv[1]); out=[]
for n in sorted(z.namelist()):
  if re.match(r'Contents/section\d+\.xml',n):
    x=z.read(n).decode('utf-8')
    x=re.sub(r'</hp:p>','\n',x); out.append(html.unescape(re.sub(r'<[^>]+>','',x)))
print('\n'.join(out))
