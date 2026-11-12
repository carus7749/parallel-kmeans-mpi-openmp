#!/usr/bin/env python3
"""Reproduce figures from verified Atlas JSONL; needs matplotlib and numpy."""
from pathlib import Path
import json, collections, statistics
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
FIG=ROOT/'figures'; FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
def load(folder,filename):
    rows=[json.loads(s) for s in (ROOT/'results'/folder/filename).read_text().splitlines()]
    assert all(x['returncode']==0 for x in rows)
    return [x for x in rows if not x['warmup']]
s=load('atlas-strong-1033995-analysis','full_strong.jsonl')
w=load('atlas-weak-1034060-analysis','full_weak.jsonl')
c=load('atlas-characteristics-1034070-analysis','full_characteristics.jsonl')
def group(rows,key):
    d=collections.defaultdict(list)
    for x in rows:d[key(x)].append(x)
    assert all(len(a)==5 for a in d.values())
    return d
def stats(xs,field='loop_s'):
    a=[x['measurement'][field] for x in xs];m=statistics.median(a)
    return m,m-min(a),max(a)-m
sg=group(s,lambda x:(x['version'],x['ranks'],x['threads']))
wg=group(w,lambda x:(x['version'],x['ranks'],x['threads']))
cg=group(c,lambda x:(x['measurement']['n'],x['measurement']['d'],x['measurement']['k'],x['version']))
base=stats(sg['serial',1,1])[0]
def save(fig,name):
    fig.tight_layout();fig.savefig(FIG/(name+'.png'),dpi=180);fig.savefig(FIG/(name+'.svg'));plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(10,3.4))
for v,t,label in [('mpi',1,'MPI (1 thread/rank)'),('hybrid',2,'Hybrid (2 threads/rank)')]:
    keys=sorted(k for k in sg if k[0]==v and k[2]==t);x=[k[1]*k[2] for k in keys];a=[stats(sg[k]) for k in keys]
    y=[base/z[0] for z in a];lo=[base/z[0]-base/(z[0]+z[2]) for z in a];hi=[base/(z[0]-z[1])-base/z[0] for z in a]
    axes[0].errorbar(x,y,yerr=[lo,hi],marker='o',capsize=3,label=label)
    axes[1].plot(x,[100*b/n for b,n in zip(y,x)],'o-',label=label)
axes[0].plot([1,12],[1,12],'--',color='gray',label='Ideal');axes[0].set_ylabel('Speedup vs serial loop median')
axes[1].axhline(100,ls='--',color='gray');axes[1].set_ylabel('Strong efficiency (%)')
for ax in axes:ax.set_xlabel('Active cores (ranks x threads)');ax.set_xticks([1,2,4,6,12]);ax.grid(alpha=.2)
axes[0].legend(fontsize=8);save(fig,'strong_scaling')
keys=[('mpi',12,1)]+[('hybrid',p,12//p) for p in (1,2,3,4,6,12)]
a=[stats(sg[k]) for k in keys];fig,ax=plt.subplots(figsize=(9,3.4));ax.bar(range(len(keys)),[z[0] for z in a],yerr=[[z[1] for z in a],[z[2] for z in a]],capsize=3,color=['#236b8e']+['#da8a38']*6)
ax.set_xticks(range(len(keys)),['MPI\n12 x 1']+[f'Hybrid\n{k[1]} x {k[2]}' for k in keys[1:]]);ax.set_ylabel('Loop time (s)');ax.set_title('Same 12 active cores; different rank/thread splits');save(fig,'rank_thread_split')
fig,axes=plt.subplots(1,2,figsize=(10,3.4))
for v,t,label in [('mpi',1,'MPI; baseline 1 core'),('hybrid',2,'Hybrid; baseline 2 cores')]:
    keys=sorted(k for k in wg if k[0]==v);x=[k[1]*k[2] for k in keys];a=[stats(wg[k]) for k in keys];b=a[0][0]
    axes[0].errorbar(x,[z[0] for z in a],yerr=[[z[1] for z in a],[z[2] for z in a]],marker='o',capsize=3,label=label)
    axes[1].plot(x,[100*b/z[0] for z in a],'o-',label=label)
axes[0].set_ylabel('Loop time (s)');axes[0].legend(fontsize=8);axes[1].set_ylabel('Family-normalized weak efficiency (%)');axes[1].axhline(100,ls='--',color='gray')
for ax in axes:ax.set_xlabel('Active cores (250,000 rows/core)');ax.set_xticks([1,2,4,6,12]);ax.grid(alpha=.2)
save(fig,'weak_scaling')
fig,axes=plt.subplots(1,3,figsize=(11,3.4))
for ax,dim,vals,label in zip(axes,[0,1,2],[[500000,1000000,2000000],[8,16,32],[4,8,16]],['N (million rows)','d (features)','K (clusters)']):
    for v in ['serial','mpi','hybrid']:
        arr=[]
        for value in vals:
            shape=[1000000,16,8];shape[dim]=value;arr.append(stats(cg[tuple(shape)+(v,)]))
        xx=[v/1e6 for v in vals] if dim==0 else vals
        ax.errorbar(xx,[z[0] for z in arr],yerr=[[z[1] for z in arr],[z[2] for z in arr]],capsize=3,marker='o',label={'serial':'Serial','mpi':'MPI 4 x 1','hybrid':'Hybrid 2 x 2'}[v])
    ax.set_xlabel(label);ax.set_ylabel('Loop time (s)');ax.grid(alpha=.2)
axes[0].legend(fontsize=8);save(fig,'input_characteristics')
fig,ax=plt.subplots(figsize=(9,3.4));keys=[('serial',1,1),('mpi',4,1),('mpi',12,1),('hybrid',6,2)]
xx=np.arange(len(keys));width=.25
for j,(field,label) in enumerate([('loop_s','Iteration loop'),('end_to_end_s','Application timer'),('external_wall_s','External invocation')]):
    a=[statistics.median(x[field] if field=='external_wall_s' else x['measurement'][field] for x in sg[k]) for k in keys]
    ax.bar(xx+(j-1)*width,a,width,label=label)
ax.set_xticks(xx,['Serial','MPI 4 x 1','MPI 12 x 1','Hybrid 6 x 2']);ax.set_ylabel('Median time (s)');ax.legend(fontsize=8);save(fig,'timing_scope')
print('Created five PNG/SVG figure pairs from 225 measured records.')
