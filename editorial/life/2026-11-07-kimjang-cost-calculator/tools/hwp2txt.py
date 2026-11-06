# HWP5 본문 텍스트 추출 (BodyText/Section* 의 PARA_TEXT 레코드). usage: hwp2txt.py file.hwp
import sys, zlib, struct
sys.path.insert(0, '/tmp/kj/lib')
import olefile
f = olefile.OleFileIO(sys.argv[1])
hdr = f.openstream('FileHeader').read()
compressed = struct.unpack('<I', hdr[36:40])[0] & 1
secs = sorted([e for e in f.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
out = []
for e in secs:
    d = f.openstream(e).read()
    if compressed: d = zlib.decompress(d, -15)
    i = 0
    while i < len(d):
        h = struct.unpack('<I', d[i:i+4])[0]; i += 4
        tag, size = h & 0x3ff, (h >> 20) & 0xfff
        if size == 0xfff: size = struct.unpack('<I', d[i:i+4])[0]; i += 4
        if tag == 67:
            raw = d[i:i+size]; s = []; j = 0
            while j < len(raw):
                c = struct.unpack('<H', raw[j:j+2])[0]
                if c in (1,2,3,11,12,14,15,16,17,18,21,22,23): j += 16; continue
                if c in (4,5,6,7,8,9,19,20): j += 16; s.append('\t' if c == 9 else ''); continue
                if c < 32: s.append('\n' if c in (10, 13) else ''); j += 2; continue
                s.append(chr(c)); j += 2
            out.append(''.join(s).strip())
        i += size
print('\n'.join(x for x in out if x))
