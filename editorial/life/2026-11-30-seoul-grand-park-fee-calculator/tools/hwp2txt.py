# HWP 5.x BodyText -> plain text (olefile)
import sys,zlib,struct
sys.path.insert(0,"/Users/sungpyo/im-not-ai/olefile-0.47-py2.py3-none-any.whl")
import olefile
f=olefile.OleFileIO(sys.argv[1])
hdr=f.openstream('FileHeader').read(); comp=hdr[36]&1
out=[]
for e in sorted([e for e in f.listdir() if e[0]=='BodyText'],key=lambda e:int(e[1][7:])):
    d=f.openstream(e).read()
    if comp: d=zlib.decompress(d,-15)
    i=0
    while i<len(d):
        h=struct.unpack('<I',d[i:i+4])[0]; t=h&0x3ff; n=(h>>20)&0xfff; i+=4
        if n==0xfff: n=struct.unpack('<I',d[i:i+4])[0]; i+=4
        if t==67:
            s=d[i:i+n].decode('utf-16le','replace'); r=[];j=0
            while j<len(s):
                c=ord(s[j])
                if c<32:
                    if c in (10,13): r.append('\n')
                    elif c==9: r.append('\t')
                    if c not in (0,10,13,24,25,26,27,28,29,30,31): j+=7
                else: r.append(s[j])
                j+=1
            out.append(''.join(r).strip())
        i+=n
print('\n'.join(x for x in out if x))
