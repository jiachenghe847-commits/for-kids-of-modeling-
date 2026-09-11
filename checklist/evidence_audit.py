"""Validate registered evidence data and freshness; never execute its producer."""
from __future__ import annotations

from pathlib import Path

try:
    from .quality_common import issue, local_path, nonempty, number, read_json, sha256
except ImportError:
    from quality_common import issue, local_path, nonempty, number, read_json, sha256


KINDS = {"validation", "constraints", "multi_seed", "convergence", "data", "sensitivity", "optimization"}


def _checks(data):
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("validation 必须有非空 checks")
    problems = []
    for row in checks:
        if not isinstance(row, dict) or not nonempty(row.get("name")) or not nonempty(row.get("unit")):
            raise ValueError("验证项缺 name/unit")
        observed, expected = number(row.get("observed")), number(row.get("expected"))
        atol, rtol = number(row.get("atol")), number(row.get("rtol", 0))
        if atol < 0 or rtol < 0:
            raise ValueError("验证容差不能为负")
        if abs(observed - expected) > atol + rtol * abs(expected):
            problems.append(issue("evidence.validation_failed", f"{row['name']} 超出登记容差"))
    return problems


def _constraints(data):
    rows = data.get("constraints")
    if not isinstance(rows, list) or not rows:
        raise ValueError("constraints 必须有非空约束列表")
    problems = []
    for row in rows:
        lhs, rhs, atol = number(row.get("lhs")), number(row.get("rhs")), number(row.get("atol"))
        if atol < 0 or not nonempty(row.get("unit")) or not nonempty(row.get("name")):
            raise ValueError("约束缺 name/unit 或容差无效")
        sense = row.get("sense")
        if sense not in {"<=", ">=", "=="}:
            raise ValueError("约束 sense 仅支持 <=、>=、==")
        residual = lhs - rhs if sense == "<=" else rhs - lhs if sense == ">=" else abs(lhs - rhs)
        if residual > atol:
            problems.append(issue("evidence.constraint_failed", f"约束 {row['name']} 违反量 {residual:g}"))
    return problems


def _kind_checks(kind, data):
    if kind == "validation":
        return _checks(data)
    if kind == "constraints":
        return _constraints(data)
    if kind == "optimization":
        required = ("solver", "termination_reason", "objective_sense", "incumbent_feasible",
                    "optimality_proven", "objective")
        if any(key not in data for key in required):
            raise ValueError("optimization 必须登记 solver、termination_reason、objective_sense、incumbent_feasible、optimality_proven 和 objective")
        if data.get("objective_sense") not in {"min", "max"}:
            raise ValueError("optimization objective_sense 仅支持 min 或 max")
        if not isinstance(data.get("solver"), str) or not data["solver"].strip():
            raise ValueError("optimization solver 不能为空")
        if not isinstance(data.get("termination_reason"), str) or not data["termination_reason"].strip():
            raise ValueError("optimization termination_reason 不能为空")
        if not isinstance(data.get("incumbent_feasible"), bool) or not isinstance(data.get("optimality_proven"), bool):
            raise ValueError("optimization 的 incumbent_feasible 和 optimality_proven 必须是布尔值")
        objective = number(data.get("objective"))
        if data.get("optimality_proven") and not data.get("incumbent_feasible"):
            raise ValueError("没有可行 incumbent 不能声明已证明最优")
        if data.get("claims_optimal", False) and not data.get("optimality_proven"):
            return [issue("evidence.optimality_claim", "限时或未闭合的求解结果不能声称最优")]
        if "relative_gap" in data:
            gap = number(data.get("relative_gap"))
            if gap < 0:
                raise ValueError("relative_gap 不能为负")
            if data.get("optimality_proven") and gap > 1e-9:
                return [issue("evidence.optimality_gap", "声明已证明最优但 relative_gap 仍大于 0")]
        for key in ("elapsed_seconds", "time_limit_seconds"):
            if key in data and number(data[key]) < 0:
                raise ValueError(f"{key} 不能为负")
        return []
    if kind == "multi_seed":
        runs = data.get("runs", [])
        if not isinstance(runs, list) or len(runs) < 3:
            return [issue("evidence.seeds", "随机算法至少需要 3 个不同固定种子")]
        seeds = [r.get("seed") for r in runs]
        if any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds):
            return [issue("evidence.seeds", "种子必须是互不相同的整数")]
        values = [number(r.get("value")) for r in runs]
        summary = data.get("summary")
        if summary is not None:
            expected = {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}
            if any(abs(number(summary.get(k)) - v) > 1e-9 * max(1, abs(v)) for k, v in expected.items()):
                return [issue("evidence.summary", "多种子汇总与原始结果不一致")]
    elif kind == "convergence":
        steps, values = data.get("iterations"), data.get("values")
        if (not isinstance(steps, list) or not isinstance(values, list) or len(steps) < 2
                or len(steps) != len(values) or not nonempty(data.get("termination_reason"))):
            return [issue("evidence.trace", "轨迹须含至少两步、等长数值及停止原因")]
        steps, values = [number(x) for x in steps], [number(x) for x in values]
        if any(b <= a for a, b in zip(steps, steps[1:])):
            return [issue("evidence.trace", "迭代序号必须严格递增")]
    else:
        rows = data.get("rows")
        if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) and r for r in rows):
            raise ValueError("data/sensitivity 必须有非空对象 rows")
        columns = data.get("columns")
        if not isinstance(columns, list) or not columns or not all(nonempty(c) for c in columns):
            raise ValueError("必须登记 columns")
        if any(not all(c in row for c in columns) for row in rows):
            raise ValueError("数据缺少登记的列")
    return []


def audit_evidence(case_dir: str | Path, manifest: dict) -> list[dict]:
    issues, seen = [], set()
    entries = manifest.get("evidence")
    if not isinstance(entries, list) or not entries:
        return [issue("evidence.empty", "尚无内容级证据登记")]
    questions = {q.get("id") for q in manifest.get("questions", []) if isinstance(q, dict)}
    for entry in entries:
        eid = entry.get("id") if isinstance(entry, dict) else None
        try:
            if not nonempty(eid) or eid in seen:
                raise ValueError("证据 id 为空或重复")
            seen.add(eid)
            if entry.get("question_id") not in questions:
                raise ValueError("证据 question_id 未登记")
            kind = entry.get("kind")
            if kind not in KINDS:
                issues.append(issue("evidence.kind", f"{eid}: 未知证据类型 {kind}"))
                continue
            path = local_path(case_dir, entry.get("path"))
            producer = local_path(case_dir, entry.get("producer"))
            if not path.is_file() or not producer.is_file():
                raise ValueError("证据或生成器文件不存在")
            hashes = entry.get("input_hashes")
            if not isinstance(hashes, dict) or not hashes:
                raise ValueError("缺少输入哈希清单")
            targets = [(path, entry.get("sha256")), (producer, entry.get("producer_sha256"))]
            targets += [(local_path(case_dir, p), h) for p, h in hashes.items()]
            if any(not p.is_file() or sha256(p) != digest for p, digest in targets):
                issues.append(issue("evidence.stale", f"{eid}: 输入、生成器或证据哈希不一致"))
            data = read_json(path)
            if not isinstance(data, dict) or not data:
                raise ValueError("证据必须是非空 JSON 对象")
            units = entry.get("units")
            if (not isinstance(units, dict) or not units or not all(nonempty(v) for v in units.values())
                    or data.get("units") != units):
                issues.append(issue("evidence.units", f"{eid}: 数据与登记单位不一致（无量纲写 1）"))
            for problem in _kind_checks(kind, data):
                problem["message"] = f"{eid}: {problem['message']}"
                issues.append(problem)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            issues.append(issue("evidence.invalid", f"{eid}: {exc}"))
    return issues
