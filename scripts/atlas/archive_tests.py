#!/usr/bin/env python3
"""Patch the job-local test copy to retain raw subprocess evidence, even on timeout."""
from pathlib import Path
p=Path('tests/test_correctness.py')
s=p.read_text()
needle='    p = subprocess.run(cmd, text=True, capture_output=True, timeout=60)'
replacement='''    evidence = Path(os.environ['ATLAS_RUN_DIR']) / ('test-%03d' % (CHECKS+1))
    Path(str(evidence)+'.command.json').write_text(json.dumps(cmd)+'\\n')
    with open(str(evidence)+'.stdout', 'x') as out, open(str(evidence)+'.stderr','x') as err:
        result = subprocess.run(cmd, stdout=out, stderr=err, timeout=60)
    p = subprocess.CompletedProcess(cmd,result.returncode,Path(str(evidence)+'.stdout').read_text(),Path(str(evidence)+'.stderr').read_text())
    Path(str(evidence)+'.exit-code').write_text(str(p.returncode)+'\\n')'''
assert s.count(needle)==1,'Test runner changed: review instrumentation before execution'
p.write_text(s.replace(needle,replacement))
