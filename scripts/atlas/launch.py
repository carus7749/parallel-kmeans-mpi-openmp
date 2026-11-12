#!/usr/bin/env python3
"""Single-node PBS-only OpenMPI launcher with per-configuration core binding."""
import json, os, pathlib, socket, sys

def command(args, env):
    if not env.get('PBS_JOBID') or not env.get('PBS_NODEFILE'):
        raise ValueError('Refusing launch outside PBS')
    hosts=pathlib.Path(env['PBS_NODEFILE']).read_text().split()
    if not hosts or len(set(hosts))!=1:
        raise ValueError('This pilot launcher supports exactly one allocated host')
    if hosts[0].split('.')[0] != socket.gethostname().split('.')[0]:
        raise ValueError('Job shell is not on the allocated compute host')
    if len(args)<3 or args[0]!='-n':raise ValueError('Expected -n P executable [arguments]')
    p=int(args[1]); app=args[2:]; t=1
    for i,a in enumerate(app):
        if a=='--threads':t=int(app[i+1])
    budget=int(env['ATLAS_CORE_BUDGET'])
    allocated=int(env['ATLAS_ALLOCATED_CORES'])
    if budget>allocated or allocated>len(hosts):raise ValueError('Invalid allocation/active cap')
    if p<1 or t<1 or p*t>budget or p>len(hosts):raise ValueError('Rank/thread request exceeds allocation')
    # PBS reserves 12 rank slots; the pilot intentionally activates at most four cores.
    launcher=env['ATLAS_MPI']+'/bin/mpirun'
    return [launcher,'-n',str(p),'--hostfile',env['PBS_NODEFILE'],
            '--map-by','slot:PE='+str(t),'--bind-to','core','--nooversubscribe',
            '--report-bindings',*app],t

if __name__=='__main__':
    try:
        cmd,t=command(sys.argv[1:],os.environ)
        os.environ['OMP_NUM_THREADS']=str(t)
        os.environ['OMP_DYNAMIC']='FALSE';os.environ['OMP_PLACES']='cores';os.environ['OMP_PROC_BIND']='close'
        print('ATLAS_LAUNCH '+json.dumps(cmd),file=sys.stderr,flush=True)
        os.execv(cmd[0],cmd)
    except (ValueError,KeyError,IndexError,OSError) as e:
        sys.exit('Atlas launcher refused: '+str(e))
