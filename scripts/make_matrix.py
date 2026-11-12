#!/usr/bin/env python3
"""Create a proposed HPC matrix, not a scheduler script or job submission."""
import argparse,json
p=argparse.ArgumentParser()
p.add_argument('--cores',required=True,type=int,nargs='+',help='Verified allowed core counts')
p.add_argument('--n',type=int,default=100000)
p.add_argument('--d',type=int,default=16)
p.add_argument('--k',type=int,default=8)
p.add_argument('--iterations',type=int,default=20)
a=p.parse_args()
if min(a.cores)<1 or min(a.n,a.d,a.k,a.iterations)<1:p.error('positive values required')
configs=[]
def add(exp,v,n,d,k,r,t):
    configs.append(dict(experiment=exp,version=v,n=n,d=d,k=k,iterations=a.iterations,seed=42,ranks=r,threads=t))
add('strong','serial',a.n,a.d,a.k,1,1)
for c in sorted(set(a.cores)):
    add('strong','mpi',a.n,a.d,a.k,c,1)
    add('weak','mpi',a.n*c,a.d,a.k,c,1)
    # These are candidates only: factor pairs need placement validation on HPC.
    for t in (1,2,4,8):
        if c%t==0:
            add('configuration','hybrid',a.n,a.d,a.k,c//t,t)
            add('weak-hybrid','hybrid',a.n*c,a.d,a.k,c//t,t)
c=max(a.cores)
for n,d,k in [(a.n//2,a.d,a.k),(a.n*2,a.d,a.k),(a.n,a.d*2,a.k),(a.n,a.d,a.k*2)]:
    add('characteristics','mpi',n,d,k,c,1)
print(json.dumps(configs,indent=2))
