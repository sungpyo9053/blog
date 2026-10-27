First run (res_*.txt, out.txt) used tcpdump -w and was discarded: every config showed the same packet count because the capture buffer was not flushed. res2_* use /sys/class/net counters.
