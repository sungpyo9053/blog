# usage: show.py file.txt n "anchor1" "anchor2"...
import sys
t=open(sys.argv[1]).read(); n=int(sys.argv[2])
for a in sys.argv[3:]:
    j=t.find(a); print('=====',a); print(t[j:j+n] if j>=0 else 'NOTFOUND')
