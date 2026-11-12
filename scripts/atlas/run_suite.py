#!/usr/bin/env python3
"""Bounded pilot: direct-to-disk raw logs survive timeout, parsing or job failure."""
import json, os, pathlib, subprocess, sys, time
root=pathlib.Path(__file__).resolve().parents[2]
logs=pathlib.Path(os.environ['ATLAS_RUN_DIR']);py=sys.executable
launcher=[py,str(root/'scripts/atlas/launch.py')]
configs=[('serial',1,1),('mpi',1,1),('mpi',2,1),('mpi',4,1),('hybrid',1,4),('hybrid',2,2),('hybrid',4,1)]
mode=os.environ.get('ATLAS_EXPERIMENT_MODE','pilot')
if mode not in ('pilot','calibration'):raise SystemExit('Unknown experiment mode')
n,it,repeats=(1000000,50,5) if mode=='calibration' else (100000,10,3)
# Calibration: 7 configurations x (1 warmup + 5 measured) = 42 launches.
with (logs/(mode+'.jsonl')).open('x') as record:
    for version,p,t in configs:
        for rep in range(-1,repeats):
            stem='{}-p{}-t{}-r{}'.format(version,p,t,rep)
            cmd=launcher+['-n',str(p),str(root/'bin'/('kmeans_'+version)),
                '--n',str(n),'--d','16','--k','8','--iterations',str(it),'--seed','42','--fixed','--threads',str(t)]
            meta={'experiment':mode,'version':version,'ranks':p,'threads':t,'repeat':rep,'warmup':rep==-1,
                'command':cmd,'job_id':os.environ['PBS_JOBID'],'allocated_cores':int(os.environ['ATLAS_ALLOCATED_CORES']),
                'active_cores':p*t,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
            (logs/(stem+'.command.json')).write_text(json.dumps(meta,indent=2)+'\n')
            started=time.monotonic()
            with (logs/(stem+'.stdout')).open('x') as out,(logs/(stem+'.stderr')).open('x') as err:
                try:
                    proc=subprocess.run(cmd,stdout=out,stderr=err,timeout=60)
                    meta['returncode']=proc.returncode
                except subprocess.TimeoutExpired:
                    meta['error']='60-second invocation timeout';meta['returncode']=124
            meta['external_wall_s']=time.monotonic()-started
            if meta['returncode']==0:
                try: meta['measurement']=json.loads((logs/(stem+'.stdout')).read_text())
                except ValueError as e:meta['error']='Invalid JSON: '+str(e);meta['returncode']=125
            record.write(json.dumps(meta)+'\n');record.flush()
            if meta['returncode']:sys.exit('Pilot failed; stop job and inspect preserved raw files')
