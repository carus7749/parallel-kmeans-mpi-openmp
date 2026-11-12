#!/usr/bin/env python3
"""Independent dependency-free reference and executable integration tests."""
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = shlex.split(os.environ.get('MPIEXEC', 'mpirun'))
CHECKS = 0

def run(version, args, ranks=1, threads=1, success=True):
    global CHECKS
    cmd = [str(ROOT/'bin'/('kmeans_'+version)), *map(str,args), '--threads', str(threads)]
    if version != 'serial': cmd = [*LAUNCH, '-n', str(ranks), *cmd]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
    CHECKS += 1
    if not success:
        assert p.returncode != 0, (cmd,p.stdout)
        return
    assert p.returncode == 0, (cmd,p.stderr)
    return json.loads(p.stdout)

def reference(rows, centers, iterations, tol=0, fixed=True):
    centers=[list(c) for c in centers]
    k,d=len(centers),len(rows[0])
    def assign():
        return [min(range(k),key=lambda c:sum((a-b)**2 for a,b in zip(x,centers[c]))) for x in rows]
    for it in range(iterations):
        labels=assign()
        updated=[]
        for c in range(k):
            points=[x for x,l in zip(rows,labels) if l==c]
            updated.append([sum(x[j] for x in points)/len(points) for j in range(d)] if points else centers[c][:])
        shift=max(math.dist(a,b) for a,b in zip(centers,updated))
        centers=updated
        if not fixed and shift<=tol: break
    labels=assign()
    sse=sum(sum((a-b)**2 for a,b in zip(x,centers[l])) for x,l in zip(rows,labels))
    return {'centers':[v for c in centers for v in c], 'labels':labels,'sse':sse,'iterations':it+1}

def compare(a,b):
    for x,y in zip(a['centers'],b['centers']): assert math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-10),(a,b)
    assert len(a['centers'])==len(b['centers'])
    assert a['labels']==b['labels'],(a,b)
    assert math.isclose(a['sse'],b['sse'],rel_tol=1e-10,abs_tol=1e-9),(a,b)
    assert a['iterations']==b['iterations'],(a,b)

configs=[('serial',1,1),('mpi',1,1),('mpi',3,1),('hybrid',2,2),('hybrid',3,1)]
cases=[
    ('one_step',[[0.],[2.],[9.],[11.]],[[0.],[9.]],1,True),
    ('uneven',[[0.,0.],[1.,0.],[0.,1.],[9.,9.],[10.,9.],[9.,10.],[11.,10.]],[[0.,0.],[9.,9.]],10,False),
    ('empty_cluster',[[0.],[0.],[10.],[10.]],[[0.],[0.],[10.]],3,True),
    ('identical',[[2.,2.]]*5,[[2.,2.],[2.,2.]],8,False),
    ('k_one',[[0.,2.],[2.,4.],[4.,6.]],[[0.,2.]],4,True),
    ('k_n',[[1.],[4.]],[[1.],[4.]],5,False),
    ('tie',[[0.],[1.],[2.]],[[0.],[2.]],1,True),
]
with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    for name,rows,centers,it,fixed in cases:
        data=td/'data.txt'; init=td/'init.txt'
        data.write_text('\n'.join(' '.join(map(str,x)) for x in rows))
        init.write_text('\n'.join(' '.join(map(str,x)) for x in centers))
        args=['--n',len(rows),'--d',len(rows[0]),'--k',len(centers),'--iterations',it,'--tol',0,'--details','--input',data,'--init',init]
        if fixed:args+=['--fixed']
        expected=reference(rows,centers,it,fixed=fixed)
        for version,p,t in configs:
            out=run(version,args,p,t);compare(out,expected)
            assert out['initial_centers']==[v for c in centers for v in c]
        print('PASS',name,flush=True)
    args=['--n',103,'--d',4,'--k',5,'--iterations',7,'--fixed','--details']
    base=run('serial',args)
    compare(base,run('serial',args))
    for version,p,t in configs[1:]:
        out=run(version,args,p,t);compare(out,base)
        assert out['initial_centers']==base['initial_centers']
    print('PASS seeded synthetic partition invariance',flush=True)
    for args in [['--n',0],['--n',2,'--k',3],['--d',0],['--iterations',0],['--n','-1'],['--tol','nan'],['--tol','1junk'],['--threads',0],['--d','2147483648'],['--n','2147483648'],['--unknown',1]]:
        # Threads are tested separately because run appends its own value.
        if args[0]=='--threads': continue
        run('serial',args,success=False)
    run('serial',[],threads=0,success=False)
    data=td/'bad.txt';data.write_text('1 2 nan')
    run('serial',['--n',3,'--d',1,'--k',1,'--input',data],success=False)
    run('mpi',['--input',td/'missing'],ranks=2,success=False)
print(f'PASS all {CHECKS} executable checks')
