# stdlib xlsx -> rows dump (sheet index arg)
import zipfile,re,sys,xml.etree.ElementTree as ET
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
z=zipfile.ZipFile(sys.argv[1])
ss=[]
if 'xl/sharedStrings.xml' in z.namelist():
    for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns):
        ss.append(''.join(t.text or '' for t in si.iter('{%s}t'%ns['m'])))
root=ET.fromstring(z.read('xl/worksheets/sheet%s.xml'%sys.argv[2]))
for row in root.iter('{%s}row'%ns['m']):
    out=[]
    for c in row.findall('m:c',ns):
        v=c.find('m:v',ns); t=c.get('t')
        if v is None:
            is_=c.find('m:is',ns)
            val=''.join(x.text or '' for x in is_.iter('{%s}t'%ns['m'])) if is_ is not None else ''
        else:
            val=ss[int(v.text)] if t=='s' else v.text
        if val!='': out.append(re.sub(r'[A-Z]+','',c.get('r'))+':'+c.get('r').rstrip('0123456789')+'='+val)
    if out: print(' '.join(out))
