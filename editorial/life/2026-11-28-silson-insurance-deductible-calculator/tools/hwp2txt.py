import sys, zlib, struct, olefile
f = olefile.OleFileIO(sys.argv[1])
hdr = f.openstream('FileHeader').read()
comp = hdr[36] & 1
out = []
secs = sorted([e for e in f.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
for e in secs:
    d = f.openstream(e).read()
    if comp: d = zlib.decompress(d, -15)
    i = 0
    while i < len(d):
        h = struct.unpack('<I', d[i:i+4])[0]; i += 4
        tag = h & 0x3ff; size = (h >> 20) & 0xfff
        if size == 0xfff: size = struct.unpack('<I', d[i:i+4])[0]; i += 4
        if tag == 67:
            t = d[i:i+size].decode('utf-16le', 'ignore')
            t = ''.join(c for c in t if ord(c) >= 32 or c == '\t')
            out.append(t)
        i += size
print('\n'.join(out))
