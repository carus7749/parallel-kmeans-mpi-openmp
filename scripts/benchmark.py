#!/usr/bin/env python3
"""Run an explicitly supplied experiment matrix; never submits remote jobs."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess

p=argparse.ArgumentParser()
p.add_argument('--matrix',required=True)
p.add_argument('--output',required=True,help='New JSONL file; existing files are never overwritten')
p.add_argument('--core-budget',required=True,type=int,help='Allocated physical CPU cores, not guessed host count')
p.add_argument('--repeats',type=int,default=5)
p.add_argument('--label',required=True,help='e.g. local-smoke or atlas-verified-node-type')
a=p.parse_args()
if a.core_budget<1 or a.repeats<1:p.error('positive budget/repeats required')
root=Path(__file__).resolve().parents[1]
matrix=json.loads(Path(a.matrix).read_text())
for cfg in matrix:
    if cfg['ranks']*cfg['threads']>a.core_budget: raise SystemExit('Configuration exceeds declared core budget')
    if cfg['version'] not in ('serial','mpi','hybrid'):raise SystemExit('Unknown version')
    if cfg['version']=='serial' and (cfg['ranks']!=1 or cfg['threads']!=1):raise SystemExit('Invalid serial resources')
    if min(cfg['ranks'],cfg['threads'])<1:raise SystemExit('Invalid resources')
launcher=shlex.split(os.environ.get('MPIEXEC','mpirun'))
env=os.environ.copy();env.setdefault('OMP_PLACES','cores');env.setdefault('OMP_PROC_BIND','close');env['OMP_DYNAMIC']='FALSE'
with open(a.output,'x') as out:
    for index,cfg in enumerate(matrix):
        cmd=[str(root/'bin'/('kmeans_'+cfg['version'])),'--fixed']
        for key in ('n','d','k','iterations','seed','threads'):cmd += ['--'+key,str(cfg[key])]
        if cfg['version']!='serial':cmd=launcher+['-n',str(cfg['ranks'])]+cmd
        for repeat in range(-1,a.repeats):
            started=datetime.datetime.now(datetime.timezone.utc).isoformat()
            result=subprocess.run(cmd,env=env,text=True,capture_output=True,timeout=3600)
            record={'label':a.label,'configuration':index,'experiment':cfg.get('experiment','unspecified'),
                    'repeat':repeat,'warmup':repeat==-1,'timestamp_utc':started,
                    'hostname':platform.node(),'platform':platform.platform(),'command':cmd,
                    'core_budget':a.core_budget,'omp_places':env['OMP_PLACES'],
                    'omp_proc_bind':env['OMP_PROC_BIND'],'returncode':result.returncode,
                    'stdout':result.stdout,'stderr':result.stderr}
            if result.returncode==0:record['measurement']=json.loads(result.stdout)
            out.write(json.dumps(record)+'\n');out.flush()
            if result.returncode:raise SystemExit('Benchmark failed; raw output preserved')
