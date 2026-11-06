# Minimal HWP5 text extractor: OLE compound file -> BodyText/Section* (zlib) -> PARA_TEXT records
import struct, sys, zlib
d = open(sys.argv[1], 'rb').read()
ss = 1 << struct.unpack_from('<H', d, 30)[0]; mss = 1 << struct.unpack_from('<H', d, 32)[0]
nfat, dirst, _, minicut, mfst, nmf, difst, ndif = struct.unpack_from('<IIIIIIII', d, 44)
difat = list(struct.unpack_from('<109I', d, 76))
s = difst
while s < 0xFFFFFFFA:
    blk = struct.unpack_from('<%dI' % (ss // 4), d, 512 + s * ss); difat += blk[:-1]; s = blk[-1]
fat = []
for sec in difat[:nfat]: fat += struct.unpack_from('<%dI' % (ss // 4), d, 512 + sec * ss)
def chain(s, t):
    out = []
    while s < 0xFFFFFFFA: out.append(s); s = t[s]
    return out
def read(s): return b''.join(d[512 + x * ss:512 + (x + 1) * ss] for x in chain(s, fat))
dirs = read(dirst); ents = []
for i in range(0, len(dirs), 128):
    e = dirs[i:i + 128]; nl = struct.unpack_from('<H', e, 64)[0]
    ents.append((e[:max(nl - 2, 0)].decode('utf-16le'), e[66], struct.unpack_from('<I', e, 116)[0], struct.unpack_from('<I', e, 120)[0]))
root = ents[0]; ministream = read(root[2])
mfat = list(struct.unpack_from('<%dI' % (nmf * ss // 4), read(mfst))) if nmf else []
def stream(name):
    for n, t, st, sz in ents:
        if n == name:
            if sz < minicut: return b''.join(ministream[x * mss:(x + 1) * mss] for x in chain(st, mfat))[:sz]
            return read(st)[:sz]
hdr = stream('FileHeader'); comp = struct.unpack_from('<I', hdr, 36)[0] & 1
for k in range(100):
    raw = stream('Section%d' % k)
    if raw is None: break
    if comp: raw = zlib.decompress(raw, -15)
    p = 0
    while p < len(raw):
        h = struct.unpack_from('<I', raw, p)[0]; tag = h & 0x3FF; sz = h >> 20; p += 4
        if sz == 0xFFF: sz = struct.unpack_from('<I', raw, p)[0]; p += 4
        if tag == 67:
            b = raw[p:p + sz]; out = []; i = 0
            while i < len(b):
                c = struct.unpack_from('<H', b, i)[0]
                if c in (1,2,3,4,5,6,7,8,9,11,12,14,15,16,17,18,19,20,21,22,23): i += 16; continue
                if c == 10 or c == 13: out.append('\n')
                elif c >= 32: out.append(chr(c))
                i += 2
            print(''.join(out).strip())
        p += sz
