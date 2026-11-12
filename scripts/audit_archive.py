#!/usr/bin/env python3
"""Read-only validation of downloaded Atlas archive. Usage: python audit_archive.py ARCHIVE."""
from pathlib import Path
import sys,hashlib,json,collections,re
root=Path(__file__).resolve().parents[1];archive=Path(sys.argv[1]);jobs=[]
for d in sorted((archive/'atlas').iterdir()):
    if not d.is_dir():continue
    checked=0
    for name in ('source-sha256.txt','binary-sha256.txt','instrumented-test-sha256.txt'):
        f=d/name
        if not f.exists():continue
        for line in f.read_text().splitlines():
            digest,rel=line.split(None,1);rel=rel.strip().lstrip('*')
            actual=hashlib.sha256((d/'source'/rel).read_bytes()).hexdigest()
            if actual!=digest:
                if name=='source-sha256.txt' and rel=='tests/test_correctness.py' and (d/'instrumented-test-sha256.txt').exists():
                    assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest
                    continue
                raise AssertionError((str(d),rel,'SHA256 mismatch'))
            checked+=1
    for rel in ('src/main.cpp','include/kmeans.hpp','Makefile'):
        assert (root/rel).read_bytes()==(d/'source'/rel).read_bytes(),(d,rel)
    exit_code=int((d/'exit-code.txt').read_text());rows=0
    if d.name.startswith('full_') and exit_code==0:
        mode=d.name.split('.')[0];records=[json.loads(s) for s in (d/(mode+'.jsonl')).read_text().splitlines()]
        expected={'full_strong':90,'full_weak':54,'full_characteristics':126}[mode];assert len(records)==expected
        grouped=collections.defaultdict(list)
        for x in records:
            assert x['returncode']==0
            assert x['measurement']==json.loads((d/('config-%02d-repeat-%d.stdout'%(x['configuration'],x['repeat']))).read_text())
            grouped[x['configuration']].append(x['repeat'])
        assert all(sorted(a)==[-1,0,1,2,3,4] for a in grouped.values())
        rows=len(records)
    if d.name.startswith('correctness.'):
        assert 'PASS all 54 executable checks' in (d/'correctness.log').read_text()
        assert len(list(d.glob('test-*.exit-code')))==54
        assert all('PASS physical-core affinity' in f.read_text() for f in d.glob('affinity-*.stdout'))
    job='.'.join(d.name.split('.')[1:3])
    final=(archive/'submissions'/(job+'.final.txt')).read_text()
    assert re.search(r'job_state\s*=\s*F',final)
    assert int(re.search(r'Exit_status\s*=\s*(-?\d+)',final)[1])==exit_code
    jobs.append(dict(run=d.name,exit_code=exit_code,verified_hashes=checked,verified_formal_records=rows))
print(json.dumps(dict(jobs=jobs,submissions_directory_present=(archive/'submissions').is_dir()),indent=2))
