"""Single delivery gate composing all quality audits."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .quality_common import issue
from .case_audit import audit_case
from .evidence_audit import audit_evidence
from .paper_audit import audit_paper
from .figure_audit import audit_figures
from .run_audit import audit_run
from .review_audit import audit_review

def delivery_report(root, profile="reference-quality"):
    root=Path(root).resolve(); manifest_path=root/'case.json'; issues=[]; manifest={}
    try: manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception as exc: return {'status':'fail','profile':profile,'issues':[issue('case.invalid',str(exc))]}
    def add(scope, fn):
        try:
            raw = fn(root) if fn is audit_case else fn(root,manifest)
            items = raw.get('warnings',[]) if isinstance(raw,dict) else raw
            for item in items:
                item=dict(item); item['scope']=scope; issues.append(item)
        except Exception as exc: issues.append(issue(scope+'.error',str(exc)))
    add('structure', audit_case)
    add('evidence', audit_evidence)
    add('paper', audit_paper)
    add('figures', audit_figures)
    add('run', audit_run)
    pdf=manifest.get('paper',{}).get('pdf_path')
    if pdf:
        from .pdf_review import review_pdf
        try:
            result=review_pdf(root/pdf)
            for x in result.get('issues',[]): issues.append({'code':'pdf.'+x.get('code','issue'),'message':x.get('message',''),'status':x.get('status','fail'),'scope':'pdf'})
            pages=result.get('pages')
            if pages and manifest.get('quality',{}).get('reviews_path'): add('review', lambda r,m:audit_review(r,m,pages))
        except Exception as exc: issues.append(issue('pdf.error',str(exc)))
    status='fail' if any(x.get('status','fail')=='fail' for x in issues) else ('needs_review' if issues else 'pass')
    return {'status':status,'profile':profile,'issues':issues,'issue_count':len(issues)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('case_dir'); ap.add_argument('--profile',default='reference-quality'); ap.add_argument('--strict',action='store_true'); ap.add_argument('--json',action='store_true'); a=ap.parse_args()
    report=delivery_report(a.case_dir,a.profile)
    if a.json: print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(f"status: {report['status']} ({report['issue_count']} issues)")
        for x in report['issues']: print(f"[{x.get('status','fail')}] {x['code']}: {x['message']}")
    if not a.strict: return 0
    return 0 if report['status']=='pass' else (2 if report['status']=='needs_review' else 1)
if __name__=='__main__': raise SystemExit(main())
