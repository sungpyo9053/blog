import sys,zlib,struct
sys.path.insert(0,__file__.rsplit('/',1)[0]+'/pylib')
import olefile
f=olefile.OleFileIO(sys.argv[1])
hdr=f.openstream('FileHeader').read();comp=hdr[36]&1
out=[]
secs=sorted([e for e in f.listdir() if e[0]=='BodyText'],key=lambda e:int(e[1][7:]))
for s in secs:
    d=f.openstream(s).read()
    if comp:d=zlib.decompress(d,-15)
    i=0
    while i<len(d):
        h=struct.unpack('<I',d[i:i+4])[0];tag=h&0x3ff;sz=(h>>20)&0xfff;i+=4
        if sz==0xfff:sz=struct.unpack('<I',d[i:i+4])[0];i+=4
        if tag==67:
            t=d[i:i+sz].decode('utf-16le','ignore')
            t=''.join(c for c in t if ord(c)>=32 or c=='\n')
            out.append(t)
        i+=sz
print('\n'.join(out))
