# 코레일 KTX 운임표(2026. 9. 1. 기준).xls -> 주요 구간 발췌 + 계산기용 JSON
# usage: PYTHONPATH=<xlrd> python3 extract_fares.py kfare.xls out.txt
import sys, json, xlrd
SRC = 'https://www.korail.com/file/cubedata/COMMON/jfile/202610/21/202610211a15d850ef5260.xls (코레일 열차운임/시간표 게시판 bdIdx=25328 "KTX 운임표(2026. 9. 1. 기준)", 2026-10-21 수정본)'
# (sheet name prefix, 출발, [도착...], 경유 표시)
PICK = [
 ('1.서울~(경주)~부산', '서울', ['천안아산', '오송', '대전', '김천구미', '동대구', '경주', '울산', '부산'], ''),
 ('2.서울~(구포)~부산', '서울', ['밀양', '구포', '부산'], '구포 경유'),
 ('4.서울~진주', '서울', ['창원중앙', '마산', '진주'], ''),
 ('5.서울~포항', '서울', ['포항'], ''),
 ('6.용산~(공주)~목포', '서울', ['광주송정', '목포'], ''),
 ('6.용산~(공주)~목포', '용산', ['익산', '정읍', '광주송정', '목포'], ''),
 ('10.용산~(공주)~여수엑스포', '용산', ['전주', '남원', '순천', '여수엑스포'], ''),
 ('19.서울~청량리~강릉,동해', '서울', ['평창', '강릉', '정동진'], ''),
 ('19.서울~청량리~강릉,동해', '청량리', ['강릉'], ''),
 ('20.서울~부전', '청량리', ['안동', '태화강', '부전'], ''),
 ('12. 수서~부산', '수서', ['대전', '동대구', '부산'], ''),
 ('14. 수서~목포', '수서', ['광주송정', '목포'], ''),
]
b = xlrd.open_workbook(sys.argv[1])
names = {s.name: s for s in b.sheets()}
out, data = ['source: ' + SRC, '열: 구간 | 일반실 운임 | 특실(또는 우등실) 운임 + 요금 = 계'], []
for sheet, a, ds, via in PICK:
    s = names[sheet]
    out.append('## sheet: ' + sheet + ' (열 수 %d)' % s.ncols)
    hdr = [c.value for c in s.row(4)] + [c.value for c in s.row(5)]
    out.append('   header: ' + ' | '.join(str(h) for h in hdr if h))
    for r in range(s.nrows):
        v = [c.value for c in s.row(r)]
        if v[1] != a or v[2] not in ds or not isinstance(v[3], float): continue
        gen = int(v[3])
        if s.ncols == 10: fa, fee, tot = int(v[7]), int(v[8]), int(v[9])     # 일반 | 우등(운임·요금·계) | 특실(운임·요금·계)
        else: fa, fee, tot = int(v[4]), int(v[5]), int(v[6])                # 일반 | 특실 또는 우등실(운임·요금·계)
        out.append('%s-%s 일반실 %d / 특실·우등실 운임 %d + 요금 %d = %d   raw=%s' % (a, v[2], gen, fa, fee, tot, v[1:]))
        assert fa == gen and fa + fee == tot
        data.append([a + '→' + v[2] + (' (' + via + ')' if via else ''), gen, fee])
open(sys.argv[2], 'w').write('\n'.join(out) + '\n\nJSON ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
print(len(data))
