# HWP5/HWPX 표를 행 단위로 출력: "T표번호 R행: 셀|셀|..." (셀 주소 기준이라 2단 표도 섞이지 않는다)
import sys, zlib, struct, re, html, zipfile, glob
def rows_hwp(path):
    import olefile
    f = olefile.OleFileIO(path)
    comp = f.openstream('FileHeader').read()[36] & 1
    secs = sorted([e for e in f.listdir() if e[0] == 'BodyText'], key=lambda e: int(e[1][7:]))
    cells = []; t = -1; cur = None; cell_level = None
    for s in secs:
        d = f.openstream('/'.join(s)).read()
        if comp: d = zlib.decompress(d, -15)
        i = 0
        while i < len(d):
            h = struct.unpack('<I', d[i:i+4])[0]; i += 4
            tag, lvl, size = h & 0x3ff, (h >> 10) & 0x3ff, (h >> 20) & 0xfff
            if size == 0xfff: size = struct.unpack('<I', d[i:i+4])[0]; i += 4
            b = d[i:i+size]
            if tag == 77: t += 1; cur = None; cell_level = None  # HWPTAG_TABLE
            elif tag == 72 and t >= 0 and len(b) >= 16:          # LIST_HEADER (셀)
                col, row = struct.unpack('<HH', b[8:12])
                cur = [t, row, col, []]; cells.append(cur); cell_level = lvl
            elif tag == 67:
                txt = []; j = 0
                while j < len(b):
                    c = struct.unpack('<H', b[j:j+2])[0]
                    if c in (1,2,3,4,5,6,7,8,9,11,12,14,15,16,17,18,19,20,21,22,23): j += 16; continue
                    if c not in (10, 13): txt.append(chr(c))
                    j += 2
                s2 = ''.join(txt).strip()
                if cur is not None and cell_level is not None and lvl > cell_level: cur[3].append(s2)
                elif cur is not None and lvl == cell_level: cur[3].append(s2)
                else: cells.append([-1, 0, 0, [s2]]); cur = None
            i += size
    return cells
def rows_hwpx(path):
    z = zipfile.ZipFile(path); cells = []; t = -1
    for n in sorted(x for x in z.namelist() if re.match(r'Contents/section\d+\.xml', x)):
        s = z.read(n).decode('utf-8')
        for m in re.finditer(r'<hp:tbl[ >]|<hp:tc[ >].*?</hp:tc>', s, re.S):
            g = m.group(0)
            if g.startswith('<hp:tbl'): t += 1; continue
            a = re.search(r'<hp:cellAddr colAddr="(\d+)" rowAddr="(\d+)"', g)
            txt = ' '.join(html.unescape(''.join(re.findall(r'<hp:t>([^<]*)</hp:t>', p))) for p in re.findall(r'<hp:p[ >].*?</hp:p>', g, re.S))
            cells.append([t, int(a.group(2)), int(a.group(1)), [txt]])
    return cells
p = sys.argv[1]
cells = rows_hwpx(p) if zipfile.is_zipfile(p) else rows_hwp(p)
out = {}
for t, r, c, tx in cells:
    if t < 0: continue
    out.setdefault((t, r), {})[c] = ' '.join(x for x in tx if x)
for (t, r) in sorted(out):
    row = out[(t, r)]
    print('T%d R%d: ' % (t, r) + ' | '.join('%d=%s' % (c, row[c]) for c in sorted(row)))
