"""Native Windows build acceptance using saved independent Python reference costs."""
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'frozen'))
import _rollout_cpp as native

def main():
    fixtures=json.loads((ROOT/'native-fixtures.json').read_text())
    assert native.source_sha256==fixtures['source_sha256']['rollout_cpp.cpp']
    largest=0.;expected_scores=[];actual_scores=[]
    for row in fixtures['cases']:
        result=native.evaluate(*row['args'],time.monotonic()+60)
        assert result is not None
        expected=row['expected']
        for field in ('mean_s','max_s'):
            residual=abs(result[field]-expected[field]);largest=max(largest,residual)
            assert residual<1e-6,(field,residual)
        for a,b in zip(result['components_s'],expected['components_s']):assert abs(a-b)<1e-6
        expected_scores.append(expected['mean_s']);actual_scores.append(result['mean_s'])
    for i in range(0,len(expected_scores),3):
        assert min(range(3),key=lambda j:expected_scores[i+j])==min(range(3),key=lambda j:actual_scores[i+j])
    report=dict(status='passed',cases=len(fixtures['cases']),max_residual_s=largest,source_sha256=native.source_sha256,
                network_requests=0,scope='Same-world costs and candidate choices against stored Python reference')
    (ROOT/'native-check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
