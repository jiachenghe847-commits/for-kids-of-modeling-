"""Audit recorded computational repetitions and freshness."""
from __future__ import annotations
import json
from pathlib import Path
from .quality_common import issue, sha256, local_path

def audit_run(root, manifest=None):
    root = Path(root).resolve(); manifest = manifest or {}
    cfg = manifest.get("quality", {})
    rel = cfg.get("run_record_path", "artifacts/run-record.json")
    try: path = local_path(root, rel)
    except ValueError as exc: return [issue("run.path", str(exc))]
    if not path.is_file(): return [issue("run.missing", f"运行记录不存在：{rel}")]
    try: record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: return [issue("run.invalid", f"运行记录不可读：{exc}")]
    issues=[]; runs=record.get("runs", [])
    if not isinstance(runs,list) or len(runs)<2: issues.append(issue("run.repetitions", "至少需要两次成功重复运行"))
    if record.get("reproducible") is not True: issues.append(issue("run.reproducible", "运行记录未声明可复现"))
    result_rel=manifest.get("results_path", "artifacts/results.json")
    try: result=local_path(root,result_rel); current=sha256(result) if result.is_file() else None
    except ValueError: current=None
    hashes={r.get("results_sha256") for r in runs if isinstance(r,dict)}
    if current is None or (hashes and current not in hashes): issues.append(issue("run.stale", "当前结果文件与运行记录不一致"))
    if not record.get("isolated", False): issues.append(issue("run.isolation", "记录未证明运行环境已隔离", "needs_review"))
    return issues
