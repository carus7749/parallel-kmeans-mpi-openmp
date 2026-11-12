#!/usr/bin/env python3
"""Single-node formal experiments. All execution is inside a PBS allocation."""
import json
import math
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time


def matrix(mode):
    configs=[]
    def add(v,p,t,n=1000000,d=16,k=8):
        c=dict(version=v,ranks=p,threads=t,n=n,d=d,k=k,iterations=50,seed=42)
        if c not in configs:configs.append(c)
    if mode=='full_strong':
        add('serial',1,1)
        for p in (1,2,4,6,12):add('mpi',p,1)
        # Fixed two threads/rank hybrid strong-scaling series (baseline 2 cores).
        for p in (1,2,3,6):add('hybrid',p,2)
        # Full 12-active-core factorization sweep.
        for p in (1,2,3,4,6,12):add('hybrid',p,12//p)
    elif mode=='full_weak':
        # 250k rows/active core. Each family has its own smallest-core baseline.
        for p in (1,2,4,6,12):add('mpi',p,1,n=250000*p)
        for p in (1,2,3,6):add('hybrid',p,2,n=250000*p*2)
    elif mode=='full_characteristics':
        for n,d,k in [(1000000,16,8),(500000,16,8),(2000000,16,8),
                      (1000000,8,8),(1000000,32,8),
                      (1000000,16,4),(1000000,16,16)]:
            add('serial',1,1,n,d,k);add('mpi',4,1,n,d,k);add('hybrid',2,2,n,d,k)
    else:raise ValueError('Unknown suite: '+mode)
    return configs


def schedule(configs):
    rng=random.Random(5208)
    order=[]
    for rep in range(-1,5):
        indices=list(range(len(configs)));rng.shuffle(indices)
        order.extend((i,rep) for i in indices)
    return order


def main(mode):
    if not os.environ.get('PBS_JOBID'):raise SystemExit('PBS allocation required')
    root=Path(__file__).resolve().parents[2]
    logs=Path(os.environ['ATLAS_RUN_DIR'])
    configs=matrix(mode)
    budget=int(os.environ['ATLAS_CORE_BUDGET'])
    assert all(c['ranks']*c['threads']<=budget for c in configs)
    order=schedule(configs)
    (logs/'experiment-plan.json').write_text(json.dumps(dict(mode=mode,configs=configs,
        schedule=order,shuffle_seed=5208,repeats=5,warmups=1),indent=2)+'\n')
    launcher=[sys.executable,str(root/'scripts/atlas/launch.py')]

    def execute(stem,cmd):
        (logs/(stem+'.command.json')).write_text(json.dumps(cmd)+'\n')
        started=time.monotonic();rc=0;error=None
        with (logs/(stem+'.stdout')).open('x') as out,(logs/(stem+'.stderr')).open('x') as err:
            # Separate process group permits cleanup on timeout; never continue
            # benchmarking while a timed-out local launcher remains running.
            proc=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
            try:rc=proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                error='120-second timeout';rc=124
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    proc.wait()
        return rc,time.monotonic()-started,error

    # Validate placement for every distinct rank/thread pair in this matrix.
    for p,t in sorted(set((c['ranks'],c['threads']) for c in configs)):
        stem='affinity-p{}-t{}'.format(p,t)
        rc,_,_=execute(stem,launcher+['-n',str(p),str(root/'bin/affinity'),'--threads',str(t)])
        if rc or 'PASS physical-core affinity' not in (logs/(stem+'.stdout')).read_text():
            raise SystemExit('Affinity preflight failed: '+stem)

    # Verify all executable/rank/thread configurations on one common small input.
    small=['--n','103','--d','4','--k','5','--iterations','7','--fixed','--details']
    rc,_,_=execute('reference',launcher+['-n','1',str(root/'bin/kmeans_serial'),*small])
    if rc:raise SystemExit('Serial reference failed')
    reference=json.loads((logs/'reference.stdout').read_text())
    for v,p,t in sorted(set((c['version'],c['ranks'],c['threads']) for c in configs)):
        stem='validate-{}-p{}-t{}'.format(v,p,t)
        rc,_,_=execute(stem,launcher+['-n',str(p),str(root/'bin'/('kmeans_'+v)),*small,'--threads',str(t)])
        if rc:raise SystemExit('Numerical preflight launch failed: '+stem)
        out=json.loads((logs/(stem+'.stdout')).read_text())
        assert out['labels']==reference['labels'],stem+' labels mismatch'
        assert len(out['centers'])==len(reference['centers'])
        assert all(math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10) for a,b in zip(out['centers'],reference['centers'])),stem
        assert math.isclose(out['sse'],reference['sse'],rel_tol=1e-10,abs_tol=1e-9),stem
    (logs/'preflight-status.txt').write_text('PASS affinity and small numerical checks for all suite configurations\n')

    objectives={}
    with (logs/(mode+'.jsonl')).open('x') as record:
        for index,rep in order:
            c=configs[index];p,t=c['ranks'],c['threads']
            stem='config-{:02d}-repeat-{}'.format(index,rep)
            cmd=launcher+['-n',str(p),str(root/'bin'/('kmeans_'+c['version'])),'--fixed']
            for k in ('n','d','k','iterations','seed','threads'):cmd+=['--'+k,str(c[k])]
            meta=dict(experiment=mode,configuration=index,repeat=rep,warmup=rep==-1,
                version=c['version'],ranks=p,threads=t,command=cmd,
                job_id=os.environ['PBS_JOBID'],allocated_cores=int(os.environ['ATLAS_ALLOCATED_CORES']),
                active_cores=p*t,started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
            rc,wall,error=execute(stem,cmd)
            meta.update(returncode=rc,external_wall_s=wall)
            if error:meta['error']=error
            if rc==0:
                try:
                    m=json.loads((logs/(stem+'.stdout')).read_text());meta['measurement']=m
                    for k in ('version','n','d','k','iterations','seed','ranks','threads'):
                        if m[k]!=c[k]:raise ValueError('Unexpected output '+k)
                    if not m['fixed']:raise ValueError('Fixed iteration mode required')
                    for k in ('sse','loop_s','end_to_end_s'):
                        if not math.isfinite(m[k]) or m[k]<0:raise ValueError('Invalid '+k)
                    signature=tuple(c[k] for k in ('n','d','k','iterations','seed'))
                    old=objectives.setdefault(signature,m['sse'])
                    if not math.isclose(old,m['sse'],rel_tol=1e-9,abs_tol=1e-7):
                        raise ValueError('SSE mismatch on identical input; inspect numerical sensitivity')
                except (ValueError,KeyError) as exc:
                    meta.update(returncode=125,error=str(exc))
            record.write(json.dumps(meta)+'\n');record.flush()
            print(stem+' returncode='+str(meta['returncode']),flush=True)
            if meta['returncode']:raise SystemExit('Formal suite stopped; raw evidence preserved')
    (logs/'suite-status.txt').write_text('PASS {} completed invocations\n'.format(len(order)))

if __name__=='__main__':
    main(sys.argv[1])
