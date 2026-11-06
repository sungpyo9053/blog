import zipfile,re,sys,csv
z=zipfile.ZipFile(sys.argv[1]);ss=[]
if 'xl/sharedStrings.xml' in z.namelist():
  x=z.read('xl/sharedStrings.xml').decode()
  for si in re.findall(r'<si>(.*?)</si>',x,re.S): ss.append(''.join(re.findall(r'<t[^>]*>(.*?)</t>',si,re.S)))
sheets=sorted(n for n in z.namelist() if n.startswith('xl/worksheets/sheet'))
w=csv.writer(sys.stdout)
for sh in sheets:
  x=z.read(sh).decode(); print('##',sh)
  for row in re.findall(r'<row[^>]*>(.*?)</row>',x,re.S):
    out={}
    for c in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)',row,re.S):
      col,attr,body=c.groups();v=re.search(r'<v>(.*?)</v>',body or '');v=v.group(1) if v else ''
      if 't="s"' in attr and v: v=ss[int(v)]
      elif 't="inlineStr"' in attr: v=''.join(re.findall(r'<t[^>]*>(.*?)</t>',body))
      out[col]=v
    w.writerow([out.get(k,'') for k in 'ABCDEFGHI'])
