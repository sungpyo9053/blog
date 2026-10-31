/^--- CASE/ {name=$3; n=0; next}
/^CMD:/ {cmd=substr($0,6); next}
/^EXIT=/ {printf "\n## %s | %s | %s\n", name, $0, cmd; for(i=(n>3?n-2:1);i<=n;i++) print "   " substr(buf[i],1,300); n=0; next}
/^SINK:|^SERVER:/ {print "   " substr($0,1,330); next}
/^COUNT/ {print; next}
/^=== / {print; next}
{ if ($0 !~ /^\s*$/) buf[++n]=$0 }
