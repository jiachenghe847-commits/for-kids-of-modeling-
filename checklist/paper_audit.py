"""Check content/evidence locations and generated values, not scientific meaning."""
from __future__ import annotations

from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checklist.quality_common import issue, local_path, nonempty
from templates.result_bindings import render_bindings

ROLES = ("analysis", "model", "algorithm", "results", "validation", "interpretation")


def strip_comments(text):
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def read_tex(case_dir, path, stack=()):
    """Expand local input/include only; reject cycles and missing sections."""
    root, path = Path(case_dir).resolve(), Path(path).resolve()
    if not path.is_relative_to(root) or path in stack:
        raise ValueError(f"TeX 引用越界或循环：{path.name}")
    text = path.read_text(encoding="utf-8")
    def expand(match):
        relative = match.group(1)
        child = path.parent / relative
        if not child.suffix:
            child = child.with_suffix(".tex")
        return read_tex(root, child, (*stack, path))
    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", expand, strip_comments(text))


def audit_paper(case_dir, manifest):
    issues = []
    try:
        source = local_path(case_dir, manifest.get("paper", {}).get("tex_path"))
        raw = source.read_text(encoding="utf-8")
        text = read_tex(case_dir, source)
        if re.search(r"%\s*TODO\(", raw):
            issues.append(issue("paper.todo", "主文件仍有未完成的论文骨架槽位"))
    except (ValueError, OSError, RecursionError) as exc:
        return [issue("paper.source", str(exc))]
    labels = set(re.findall(r"\\label\s*\{([^}]+)\}", text))
    refs = set(re.findall(r"\\(?:ref|eqref|autoref)\s*\{([^}]+)\}", text))
    for missing in sorted(refs - labels):
        issues.append(issue("paper.reference", f"未定义交叉引用：{missing}"))
    evidence = {e.get("id"): e for e in manifest.get("evidence", []) if isinstance(e, dict)}
    questions = {q.get("id") for q in manifest.get("questions", []) if isinstance(q, dict)}
    for question in manifest.get("questions", []):
        qid = question.get("id")
        content = question.get("paper", {}).get("content", {})
        for role in ROLES:
            item = content.get(role, {})
            if (not isinstance(item, dict) or item.get("label") not in labels
                    or not nonempty(item.get("notes"))):
                issues.append(issue("paper.content", f"{qid}/{role}: 缺实际正文标签或内容说明"))
                continue
            ids = item.get("evidence_ids", [])
            if (not isinstance(ids, list) or any(e not in evidence for e in ids)
                    or (role in {"results", "validation"} and not ids)):
                issues.append(issue("paper.evidence", f"{qid}/{role}: 缺可定位证据"))
    claims = manifest.get("claims", [])
    if not isinstance(claims, list) or not claims:
        issues.append(issue("paper.claims", "缺少核心数值结果绑定"))
        return issues
    for claim in claims:
        cid = claim.get("id")
        ids = claim.get("evidence_ids", [])
        if (claim.get("question_id") not in questions or claim.get("label") not in labels
                or not ids or any(e not in evidence for e in ids)):
            issues.append(issue("paper.claim", f"{cid}: 缺小问、实际标签或证据映射"))
        if not isinstance(cid, str) or not re.search(r"\\ResultValue\s*\{" + re.escape(cid) + r"\}", text):
            issues.append(issue("paper.claim_unused", f"{cid}: 正文未使用该数值绑定"))
    try:
        expected = render_bindings(case_dir, manifest)
        binding = local_path(case_dir, manifest.get("paper", {}).get("bindings_path"))
        if not binding.is_file() or binding.read_text(encoding="utf-8") != expected:
            issues.append(issue("paper.bindings_stale", "数值绑定文件与当前结果不一致，请重新生成"))
        elif strip_comments(expected).strip() not in text:
            issues.append(issue("paper.bindings_unused", "正文未载入登记的数值绑定文件"))
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        issues.append(issue("paper.bindings_invalid", str(exc)))
    return issues
