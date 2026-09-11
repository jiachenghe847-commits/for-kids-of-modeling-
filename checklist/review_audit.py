"""Audit independent visual/content review records."""
from __future__ import annotations
import json
from pathlib import Path
from .quality_common import issue, sha256, local_path

RUBRIC=("model","algorithm","validation","figures","organization")
def snapshot_files(root):
    root=Path(root).resolve(); out={}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts and ".venv" not in p.parts and "reviews" not in p.parts:
            out[str(p.relative_to(root))]=sha256(p)
    return out

def audit_review(root, manifest, page_count):
    root=Path(root).resolve(); cfg=manifest.get("quality",{}); rel=cfg.get("reviews_path","reviews/review.json")
    try: path=local_path(root,rel)
    except ValueError as exc: return [issue("review.path",str(exc))]
    if not path.is_file(): return [issue("review.missing",f"评审记录不存在：{rel}")]
    try: rec=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: return [issue("review.invalid",str(exc))]
    if rec.get("status") != "complete": return [issue("review.pending","评审尚未完成")]
    issues=[]
    if rec.get("snapshot") != snapshot_files(root): issues.append(issue("review.stale","评审后文件已发生变化"))
    if set(rec.get("pages_reviewed",[])) != set(range(1,page_count+1)): issues.append(issue("review.pages","未覆盖全部页面"))
    expected={str(x.get("id")) for x in manifest.get("figures",[]) if isinstance(x,dict) and x.get("id")}
    if expected and expected-set(map(str,rec.get("figures_reviewed",[]))): issues.append(issue("review.figures","未覆盖全部图件"))
    scores=rec.get("scores",{})
    if any(k not in scores or not scores[k].get("reason") or scores[k].get("score") is None for k in RUBRIC): issues.append(issue("review.scores","五项评审维度均需评分、依据和定位"))
    return issues
