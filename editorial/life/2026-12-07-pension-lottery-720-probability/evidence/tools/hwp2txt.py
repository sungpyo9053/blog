# minimal HWP5 text extractor: python3 -I hwp2txt.py file.hwp (needs olefile on PYTHONPATH)
import sys, zlib, struct
sys.path.insert(0, '/tmp/pt720/lib')
import olefile
ole = olefile.OleFileIO(sys.argv[1])
hdr = ole.openstream('FileHeader').read()
compressed = struct.unpack('<I', hdr[36:40])[0] & 1
out = []
secs = sorted([e for e in ole.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
for e in secs:
    d = ole.openstream(e).read()
    if compressed:
        d = zlib.decompress(d, -15)
    i = 0
    while i < len(d):
        h = struct.unpack('<I', d[i:i+4])[0]; i += 4
        tag, size = h & 0x3ff, (h >> 20) & 0xfff
        if size == 0xfff:
            size = struct.unpack('<I', d[i:i+4])[0]; i += 4
        if tag == 67:
            b = d[i:i+size]; s = []; j = 0
            while j < len(b):
                c = struct.unpack('<H', b[j:j+2])[0]
                if c < 32:
                    if c in (0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31):
                        j += 2
                    else:
                        j += 16
                    if c == 9: s.append('\t')
                    continue
                s.append(chr(c)); j += 2
            out.append(''.join(s))
        i += size
sys.stdout.buffer.write('\n'.join(out).encode('utf-8','replace'))
