# -*- coding: utf-8 -*-
# HTML/텍스트에서 태그를 걷어내고 패턴 주변 문장만 발췌: excerpt.py 원본 URL 출력파일 패턴...
import sys, re, io, html
src, url, out = sys.argv[1], sys.argv[2], sys.argv[3]
s = io.open(src, encoding='utf-8', errors='replace').read()
t = html.unescape(re.sub(r'<script.*?</script>|<style.*?</style>', ' ', s, flags=re.S))
t = re.sub(r'<[^>]+>', ' ', t); t = re.sub(r'\s+', ' ', t)
with io.open(out, 'w', encoding='utf-8') as f:
    f.write(url + '\n(curl 2026-11-08, 태그 제거 후 해당 구간 발췌)\n\n')
    for pat in sys.argv[4:]:
        for m in re.finditer(pat, t):
            f.write(m.group(0).strip() + '\n\n')
