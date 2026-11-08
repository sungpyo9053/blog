# /tmp 원본에서 evidence/*.txt 발췌본을 만든다: make_evidence.py SRC EVIDENCE
import sys, io, os, re, html, subprocess
S, E = sys.argv[1], sys.argv[2]
T = os.path.dirname(os.path.abspath(__file__))
def txt(p):
    s = io.open(p, encoding='utf-8', errors='replace').read()
    t = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', ' ', s, flags=re.S)))
    return re.sub(r'\s+', ' ', t)
def cut(t, a, b):
    i = t.find(a); j = t.find(b, i + len(a)) if b else len(t)
    return t[i:j].strip()
def hwp(p, tool):
    env = dict(os.environ, PYTHONPATH=os.path.join(S, 'py'))
    return subprocess.run([sys.executable, os.path.join(T, tool), p], capture_output=True, text=True, env=env, timeout=60).stdout
def w(name, url, note, body):
    with io.open(os.path.join(E, name), 'w', encoding='utf-8') as f:
        f.write(url + '\n' + note + '\n\n' + body.strip() + '\n')
N = '(curl 2026-11-08, 태그 제거 후 해당 구간 발췌)'
H = '국가법령정보센터 첨부 별표(HWP)를 표 셀 주소 기준 행 단위(tools/hwp2rows.py)와 본문 순서(tools/hwp2txt.py)로 추출. curl 2026-11-08.'
L = 'https://www.law.go.kr/LSW/ordinInfoP.do?ordinSeq='
t = txt(os.path.join(S, 's2.html'))
w('law-seoul-ordinance-articles.txt', L + '2171833', N, t[:t.find('제1장')] + '\n\n' + cut(t, '제6조(주차요금 및 가산금)', '제8조'))
w('law-seoul-byl1-fee.txt', L + '2171833', '서울특별시 주차장 설치 및 관리 조례 [별표1] 공영주차장 주차요금표(제6조제1항 관련). ' + H, hwp(os.path.join(S, 'byl1.bin'), 'hwp2rows.py'))
t = txt(os.path.join(S, 'p_rule.html'))
w('law-seoul-rule-note.txt', L + '1412112', N + ' 시행규칙 첨부는 별지 서식 5종뿐이고 요금 별표는 없다.', t[:400] + '\n\n첨부: ' + ' / '.join(re.findall(r'\[별지 제\d호서식\][^/]{0,40}', t)))
t = txt(os.path.join(S, 'p_songpa.html'))
w('law-songpa-ordinance-articles.txt', L + '2112383', N, t[:t.find('제1장')] + '\n\n' + cut(t, '제5조(주차요금 및 가산금)', '제6조(주차요금 미납'))
x = hwp(os.path.join(S, 'b_songpa.bin'), 'hwp2txt.py')
x = '\n'.join(l for l in x.splitlines() if l.strip())
w('law-songpa-byl-fee.txt', L + '2112383', '서울특별시 송파구 주차장 설치 및 관리 조례 [별표1]·[별표2] (첨부 원본 1MB HWP는 용량 때문에 텍스트만 보관). ' + H, x[:x.find('일반형 출입통로')] if '일반형 출입통로' in x else x)
for k, seq, a, b in [('gangnam', '2152155', None, None), ('busan', '2120413', '제3조(주차요금 및 가산금)', '제4조(주차요금의 징수방법'), ('incheon', '2177551', '제4조(주차요금 및 가산금)', '제5조(공영주차장의 관리)')]:
    t = txt(os.path.join(S, 'p_' + k + '.html'))
    if a: w('law-' + k + '-ordinance-articles.txt', L + seq, N, t[:t.find('제1장')] + '\n\n' + cut(t, a, b))
    else: w('law-' + k + '-ordinance-articles.txt', L + seq, N, t[:t.find('제1장')])
    w('law-' + k + '-byl1-fee.txt', L + seq, H, hwp(os.path.join(S, 'b_' + k + '.bin'), 'hwp2rows.py') + '\n---- 본문 순서 ----\n' + '\n'.join(l for l in hwp(os.path.join(S, 'b_' + k + '.bin'), 'hwp2txt.py').splitlines() if l.strip()))
t = txt(os.path.join(S, 'sisul_fee_dust2.html'))
w('sisul-parking-fee.txt', 'https://www.sisul.or.kr/open_content/parking/guidance/fee_dust2.jsp', N, cut(t, '요금결제 안내', '컨텐츠 담당자'))
t = txt(os.path.join(S, 'sisul_guide3.html'))
w('sisul-commuter-guide.txt', 'https://www.sisul.or.kr/open_content/parking/commuter/guide3.jsp', N, cut(t, '신청자격', '차량변경'))
t = txt(os.path.join(S, 'w_18d98a.html'))
w('parking-seoul-main.txt', 'https://parking.seoul.go.kr/', N, t)
t = txt(os.path.join(S, 'w_ff0cca.html'))
w('data-seoul-OA-13122.txt', 'https://data.seoul.go.kr/dataList/OA-13122/S/1/datasetView.do', N, cut(t, '서울시 공영주차장 안내 정보 공영', '관련 태그'))
t = txt(os.path.join(S, 'dg_std.html'))
w('data-go-kr-15012896.txt', 'https://www.data.go.kr/data/15012896/standard.do', N + ' 원본 HTML 2MB는 용량 때문에 발췌만 보관.', cut(t, '표준데이터 기본정보 전국', '관련법령'))
print('ok')
