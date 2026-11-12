#!/usr/bin/env python3
"""Summarize raw successful measurements without inferring speedup baselines."""
import csv,json,statistics,sys
from collections import defaultdict
groups=defaultdict(list)
for path in sys.argv[1:]:
    for line in open(path):
        r=json.loads(line)
        if r['warmup'] or r['returncode']:continue
        m=r['measurement']
        key=(r['label'],r['experiment'],m['version'],m['n'],m['d'],m['k'],m['seed'],m['iterations'],m['ranks'],m['threads'])
        groups[key].append(m['loop_s'])
w=csv.writer(sys.stdout)
w.writerow(['label','experiment','version','n','d','k','seed','iterations','ranks','threads','repeats','median_loop_s','q1_loop_s','q3_loop_s'])
for key,values in sorted(groups.items()):
    q=statistics.quantiles(values,n=4,method='inclusive') if len(values)>1 else values*3
    w.writerow([*key,len(values),statistics.median(values),q[0],q[2]])
