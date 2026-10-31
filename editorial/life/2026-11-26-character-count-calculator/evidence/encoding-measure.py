# 한글 음절 11,172자를 EUC-KR(KS X 1001 완성형)·CP949·UTF-8로 인코딩해 바이트 수를 실측한다 (python3 -I encoding-measure.py)
def blen(s, enc):
    try: return len(s.encode(enc))
    except UnicodeEncodeError: return 'X'
syl = [chr(c) for c in range(0xAC00, 0xD7A4)]
print('한글 음절 총수:', len(syl))
print('EUC-KR 2바이트(완성형 코드 안):', sum(blen(c, 'euc-kr') == 2 for c in syl))
print('EUC-KR 8바이트(완성형 밖, 조합 확장 표기):', sum(blen(c, 'euc-kr') == 8 for c in syl))
print('CP949 2바이트:', sum(blen(c, 'cp949') == 2 for c in syl))
print('UTF-8 3바이트:', sum(blen(c, 'utf-8') == 3 for c in syl))
for s in ['가', 'A', '1', ' ', '\n', '.', '똠', '뷁', '😀', '한글 ABC']:
    print(repr(s), 'UTF-8', blen(s, 'utf-8'), 'EUC-KR', blen(s, 'euc-kr'), 'CP949', blen(s, 'cp949'), 'UTF-16 단위', len(s.encode('utf-16-le')) // 2)
