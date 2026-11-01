# 손없는날 74개를 KASI 음력→양력(/life/lunc) 역방향으로 다시 조회해 양력 날짜가 같은지 대조
import json, subprocess, time
rows=[json.loads(l) for l in open('evidence/kasi-solc-2026-12_2027-12.jsonl')]
son=[r for r in rows if r['LUNC_DD'][-1] in '09']
out=open('evidence/kasi-lunc-crosscheck.jsonl','w'); bad=0
for r in son:
    u=f"https://astro.kasi.re.kr/life/lunc?yyyy={r['LUNC_YYYY']}&mm={r['LUNC_MM']}&dd={r['LUNC_DD']}"
    j=json.loads(subprocess.run(['curl','-s','-m','20',u],capture_output=True,text=True).stdout)
    out.write(json.dumps(j,ensure_ascii=False)+'\n')
    p=[x for x in j if x['LUNC_LEAP_MM']=='평'][0]
    ok=(p['SOLC_YYYY'],p['SOLC_MM'],p['SOLC_DD'])==(r['SOLC_YYYY'],r['SOLC_MM'],r['SOLC_DD'])
    bad+=not ok
    time.sleep(0.2)
print('checked',len(son),'mismatch',bad)
