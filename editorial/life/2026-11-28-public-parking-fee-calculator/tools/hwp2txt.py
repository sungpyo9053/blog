# HWP5 본문 텍스트 추출 (BodyText 레코드 HWPTAG_PARA_TEXT=67). 표 셀은 문단 순서대로 나온다.
import sys, zlib, struct, olefile
def hwp_text(path):
    f = olefile.OleFileIO(path)
    hdr = f.openstream('FileHeader').read()
    compressed = hdr[36] & 1
    out = []
    secs = sorted([e for e in f.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
    for s in secs:
        d = f.openstream('/'.join(s)).read()
        if compressed:
            d = zlib.decompress(d, -15)
        i = 0
        while i < len(d):
            h = struct.unpack('<I', d[i:i+4])[0]; i += 4
            tag, size = h & 0x3ff, (h >> 20) & 0xfff
            if size == 0xfff:
                size = struct.unpack('<I', d[i:i+4])[0]; i += 4
            if tag == 67:
                b = d[i:i+size]; t = []; j = 0
                while j < len(b):
                    c = struct.unpack('<H', b[j:j+2])[0]
                    if c in (1,2,3,4,5,6,7,8,9,11,12,14,15,16,17,18,19,20,21,22,23):
                        j += 16; continue
                    if c in (10, 13):
                        j += 2; continue
                    t.append(chr(c)); j += 2
                out.append(''.join(t))
            i += size
    return out
if __name__ == '__main__':
    print('\n'.join(hwp_text(sys.argv[1])))
