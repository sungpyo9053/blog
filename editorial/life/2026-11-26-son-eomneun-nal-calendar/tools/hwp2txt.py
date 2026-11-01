# HWP5 본문(BodyText/Section*) PARA_TEXT 레코드만 뽑는 최소 추출기 (olefile 필요)
import sys, zlib, struct, olefile
f = olefile.OleFileIO(sys.argv[1])
hdr = f.openstream('FileHeader').read()
compressed = hdr[36] & 1
secs = sorted([e for e in f.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
out = []
for e in secs:
    data = f.openstream(e).read()
    if compressed: data = zlib.decompress(data, -15)
    i = 0
    while i < len(data):
        h = struct.unpack('<I', data[i:i+4])[0]; i += 4
        tag, size = h & 0x3ff, (h >> 20) & 0xfff
        if size == 0xfff: size = struct.unpack('<I', data[i:i+4])[0]; i += 4
        rec = data[i:i+size]; i += size
        if tag == 67:
            t = rec.decode('utf-16le', 'ignore')
            s = ''.join(c for c in t if ord(c) >= 32 or c == '\t')
            out.append(s)
print('\n'.join(out))
