"""审计一个国赛工作目录的建模证据链。

**能力边界**：本工具做的是结构检查——字段填没填、登记的文件在不在。它不打开
证据文件、不读内容、不判断结论是否成立。`ambiguities_reviewed` 写 `true` 就算
审过了；`validations` 里登记一条独立验证，只要那个文件存在（哪怕内容是 `{}`）
就算数。因此「0 个警告」只说明证据可定位，不代表证据成立，内容真伪必须走
`checklist/manual_verification.md`。

警告默认只提示不阻断：命令正常退出，队伍仍可在时间盒内产出草稿。加 `--strict`
才把同一批警告变成非零退出码，作为显式质量门槛。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:  # 直接跑脚本时 checklist/ 已在 sys.path 上；从仓库根目录当包导入时走下面这条
    from paper_completeness import completeness_report
    from paper_completeness import format_text as _completeness_text
except ImportError:  # pragma: no cover
    from checklist.paper_completeness import completeness_report
    from checklist.paper_completeness import format_text as _completeness_text


SCOPE = "structural"
SCOPE_NOTE = (
    "本工具只检查证据是否存在且可定位，不判断证据是否成立；"
    "内容真伪见 checklist/manual_verification.md"
)

# 完备性对标（论文体量 vs 获奖论文实测分布）刻意**不**计入 warning_count，也不影响
# --strict 的退出码，理由有两条：
#   一、篇幅达标和研究质量是两件事。把「图不够多」和「缺独立验证」堆进同一个计数里，
#      会让人以为凑几张图就能提质量；
#   二、现有「0 个警告」的语义是「证据链结构完整」，掺进体量指标就变味了。
# 它以独立分节呈现，看得见但不阻断。基准与口径见 checklist/paper_completeness.py。

TASK_TYPES = {"direct", "mechanism", "simulation", "optimization", "prediction", "evaluation"}
INDEPENDENT_VALIDATIONS = {
    "analytic_check",
    "independent_calculation",
    "analytic_case",
    "independent_implementation",
    "independent_solver",
    "reduced_exact",
    "bound_comparison",
    "benchmark",
    "cross_validation",
    "holdout",
    "normalization_sensitivity",
}


class AuditConfigurationError(ValueError):
    pass


def _blank(value: Any) -> bool:
    if value is None or value == "" or value == [] or value == {}:
        return True
    return isinstance(value, str) and value.strip().startswith("<")


def _warning(warnings: list[dict], code: str, message: str, question: str | None = None) -> None:
    item = {"code": code, "message": message}
    if question:
        item["question"] = question
    warnings.append(item)


def _source_value(source: Any) -> str:
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        return str(source.get("path") or source.get("url") or "")
    return ""


def _file_part(value: str) -> str:
    value = value.split("#", 1)[0]
    if ".py:" in value:
        value = value.split(":", 1)[0]
    return value


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _path_exists(case_dir: Path, value: Any) -> bool:
    if not isinstance(value, str) or _blank(value):
        return False
    path_text = _file_part(value)
    if _is_url(path_text):
        return True
    path = Path(path_text)
    return (path if path.is_absolute() else case_dir / path).exists()


def _require_path(
    case_dir: Path,
    value: Any,
    warnings: list[dict],
    code: str,
    label: str,
    question: str | None = None,
) -> None:
    if _blank(value):
        _warning(warnings, code, f"缺少{label}", question)
    elif not _path_exists(case_dir, value):
        _warning(warnings, code, f"{label}不存在：{value}", question)


def _validation_types(question: dict) -> set[str]:
    return {
        item.get("type", "")
        for item in question.get("validations", [])
        if isinstance(item, dict)
    }


def _require_validation(
    types: set[str],
    accepted: set[str],
    warnings: list[dict],
    code: str,
    label: str,
    question: str,
) -> None:
    if not types.intersection(accepted):
        _warning(warnings, code, f"缺少{label}；可用类型：{', '.join(sorted(accepted))}", question)


def _audit_question(case_dir: Path, question: dict, warnings: list[dict]) -> bool:
    """审计一问，返回 True 表示因任务类型未分类而跳过了后续全部检查。

    未分类时无法确定该用哪套验证判据，只能早返回；但跳过这件事必须在报告里
    说出来，否则「只有 2 个警告」会被误读成快做完了。
    """
    qid = str(question.get("id") or "未编号问题")
    task_type = question.get("task_type")
    if task_type not in TASK_TYPES:
        _warning(warnings, "question.task_type", f"任务类型未分类或无效：{task_type!r}", qid)
        return True

    if _blank(question.get("target_quantity")):
        _warning(warnings, "question.target", "缺少目标量或待求量的明确数学定义", qid)

    interpretation = question.get("interpretation", {})
    if not interpretation.get("ambiguities_reviewed"):
        _warning(warnings, "interpretation.review", "尚未完成题意歧义审计", qid)
    metrics = interpretation.get("candidate_metrics", [])
    if not metrics:
        _warning(warnings, "interpretation.metrics", "至少需要记录一个候选评价指标", qid)
    if _blank(interpretation.get("selected_metric")):
        _warning(warnings, "interpretation.selected", "缺少最终采用的指标口径", qid)
    if _blank(interpretation.get("rationale")):
        _warning(warnings, "interpretation.rationale", "缺少指标口径的选择依据", qid)

    model = question.get("model", {})
    if task_type == "optimization":
        if not model.get("decision_variables"):
            _warning(warnings, "model.variables", "优化问题缺少决策变量", qid)
        if _blank(model.get("objective")):
            _warning(warnings, "model.objective", "优化问题缺少目标函数", qid)
        if not model.get("constraints"):
            _warning(warnings, "model.constraints", "优化问题缺少约束条件", qid)
    if not model.get("assumptions"):
        _warning(warnings, "model.assumptions", "未记录模型假设或适用边界", qid)

    equation_map = model.get("equation_code_map", [])
    if not equation_map:
        _warning(warnings, "trace.equations", "缺少核心方程到代码和测试的映射", qid)
    for index, item in enumerate(equation_map, start=1):
        if not isinstance(item, dict) or _blank(item.get("equation")):
            _warning(warnings, "trace.equation", f"第 {index} 条映射缺少方程标识", qid)
            continue
        _require_path(case_dir, item.get("implementation"), warnings, "trace.implementation", "方程实现", qid)
        _require_path(case_dir, item.get("test"), warnings, "trace.test", "方程测试", qid)

    solvers = question.get("solvers", {})
    baseline = solvers.get("baseline", {})
    primary = solvers.get("primary", {})
    if task_type in {"optimization", "prediction", "evaluation"}:
        if _blank(baseline.get("method")):
            _warning(warnings, "solver.baseline", "缺少基线方法", qid)
        _require_path(case_dir, baseline.get("entrypoint"), warnings, "solver.baseline_entry", "基线入口", qid)
        _require_path(case_dir, baseline.get("result_path"), warnings, "solver.baseline_result", "基线结果", qid)
    if _blank(primary.get("method")):
        _warning(warnings, "solver.primary", "缺少主求解方法", qid)
    _require_path(case_dir, primary.get("entrypoint"), warnings, "solver.primary_entry", "主求解入口", qid)
    _require_path(case_dir, primary.get("result_path"), warnings, "solver.primary_result", "主求解结果", qid)

    if primary.get("stochastic") and len(primary.get("seeds", [])) < 3:
        _warning(warnings, "solver.seeds", "随机算法至少需要 3 个固定种子的重复运行记录", qid)
    if primary.get("iterative"):
        _require_path(
            case_dir,
            primary.get("convergence_trace"),
            warnings,
            "solver.convergence",
            "收敛轨迹",
            qid,
        )

    decomposition = question.get("decomposition", {})
    if decomposition.get("used"):
        if _blank(decomposition.get("method")) or _blank(decomposition.get("rationale")):
            _warning(warnings, "decomposition.rationale", "分解/贪心方法缺少方法说明或理论依据", qid)
        _require_path(
            case_dir,
            decomposition.get("joint_benchmark"),
            warnings,
            "decomposition.benchmark",
            "缩小规模联合优化对照",
            qid,
        )

    if task_type == "optimization":
        _require_path(
            case_dir,
            question.get("constraint_audit"),
            warnings,
            "validation.constraints",
            "逐约束可行性报告",
            qid,
        )

    validations = question.get("validations", [])
    types = _validation_types(question)
    if not validations:
        _warning(warnings, "validation.none", "没有任何模型验证记录", qid)
    elif not types.intersection(INDEPENDENT_VALIDATIONS):
        _warning(warnings, "validation.independent", "缺少与主求解路径相对独立的验证", qid)
    for index, item in enumerate(validations, start=1):
        if not isinstance(item, dict):
            _warning(warnings, "validation.record", f"第 {index} 条验证记录格式错误", qid)
            continue
        if _blank(item.get("type")):
            _warning(warnings, "validation.type", f"第 {index} 条验证缺少类型", qid)
        if _blank(item.get("finding")):
            _warning(warnings, "validation.finding", f"第 {index} 条验证缺少结论", qid)
        _require_path(case_dir, item.get("artifact"), warnings, "validation.artifact", "验证产物", qid)

    if len(metrics) > 1 and "formulation_sensitivity" not in types:
        _warning(warnings, "interpretation.sensitivity", "多个候选指标缺少口径敏感性比较", qid)
    if task_type == "direct":
        _require_validation(types, {"analytic_check", "independent_calculation"}, warnings, "validation.direct", "独立计算复核", qid)
    elif task_type in {"mechanism", "simulation"}:
        _require_validation(types, {"dimensional_check"}, warnings, "validation.dimension", "量纲检查", qid)
        _require_validation(types, {"analytic_case", "independent_implementation"}, warnings, "validation.mechanism", "解析特例或独立实现", qid)
        if model.get("discretized"):
            _require_validation(types, {"discretization_convergence"}, warnings, "validation.discretization", "离散精度收敛检验", qid)
    elif task_type == "optimization":
        _require_validation(types, {"independent_solver", "reduced_exact", "bound_comparison"}, warnings, "validation.optimization", "第二算法、缩小规模精确解或界比较", qid)
        if primary.get("stochastic"):
            _require_validation(types, {"multi_seed_stability"}, warnings, "validation.stochastic", "多种子稳定性分析", qid)
    elif task_type == "prediction":
        _require_validation(types, {"benchmark"}, warnings, "validation.benchmark", "基准模型比较", qid)
        _require_validation(types, {"cross_validation", "holdout"}, warnings, "validation.predictive", "交叉验证或留出验证", qid)
        _require_validation(types, {"residual_analysis"}, warnings, "validation.residual", "残差分析", qid)
    elif task_type == "evaluation":
        _require_validation(types, {"normalization_sensitivity"}, warnings, "validation.normalization", "标准化或赋权敏感性分析", qid)
        _require_validation(types, {"rank_stability"}, warnings, "validation.ranking", "排序稳定性分析", qid)

    paper = question.get("paper", {})
    if _blank(paper.get("section")):
        _warning(warnings, "paper.section", "缺少对应论文节标题", qid)
    displays = paper.get("evidence_displays", [])
    if not displays:
        _warning(warnings, "paper.evidence", "论文中未登记结果图或结果表", qid)
    for display in displays:
        value = display.get("artifact") if isinstance(display, dict) else display
        _require_path(case_dir, value, warnings, "paper.evidence_path", "论文证据图表", qid)
    return False


def _paper_metrics(tex_path: Path) -> dict:
    text = tex_path.read_text(encoding="utf-8")
    return {
        "cjk_characters": len(re.findall(r"[\u3400-\u9fff]", text)),
        "equations": len(re.findall(r"\\begin\{(?:equation|align)\*?\}", text)),
        "figures": len(re.findall(r"\\begin\{figure\*?\}", text)),
        "tables": len(re.findall(r"\\begin\{table\*?\}", text)),
    }


def audit_case(case_dir: str | Path) -> dict:
    case_dir = Path(case_dir).resolve()
    manifest_path = case_dir / "case.json"
    if not manifest_path.is_file():
        raise AuditConfigurationError(f"missing manifest: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise AuditConfigurationError(f"cannot read {manifest_path}: {exc}") from exc

    warnings: list[dict] = []
    if manifest.get("schema_version") != 1:
        _warning(warnings, "schema.version", "case.json 的 schema_version 必须为 1")
    if _blank(manifest.get("case_id")):
        _warning(warnings, "case.id", "缺少 case_id")

    inputs = manifest.get("inputs", {})
    sources = inputs.get("sources", [])
    if not sources:
        _warning(warnings, "inputs.sources", "尚未登记官方题目或附件来源")
    for source in sources:
        value = _source_value(source)
        _require_path(case_dir, value, warnings, "inputs.missing", "输入文件")
        kind = source.get("kind") if isinstance(source, dict) else None
        if inputs.get("mode") == "official-only" and kind not in (None, "official"):
            _warning(warnings, "inputs.kind", f"official-only 模式出现非官方来源：{value}")

    external = inputs.get("external_references", [])
    corpus_pattern = re.compile(r"(?:^|[/\\])(?:corpus|建模)(?:[/\\]|$)", re.IGNORECASE)
    if manifest.get("phase") == "blind" and inputs.get("mode") == "official-only" and external:
        _warning(warnings, "inputs.external", "盲测 official-only 阶段不应使用外部题解或参考方案")
    for source in [*sources, *external]:
        value = _source_value(source)
        if manifest.get("phase") == "blind" and corpus_pattern.search(value):
            _warning(warnings, "inputs.corpus", f"盲测阶段引用了语料库路径：{value}")

    questions = manifest.get("questions", [])
    if not questions:
        _warning(warnings, "questions.none", "case.json 中没有子问题")
    skipped = 0
    for question in questions:
        if not isinstance(question, dict):
            _warning(warnings, "question.record", "子问题记录必须是对象")
            continue
        if _audit_question(case_dir, question, warnings):
            skipped += 1

    results_path = manifest.get("results_path")
    _require_path(case_dir, results_path, warnings, "results.path", "统一结果文件")
    paper = manifest.get("paper", {})
    _require_path(case_dir, paper.get("generator"), warnings, "paper.generator", "论文生成器")
    if paper.get("generated_from") != results_path:
        _warning(warnings, "paper.trace", "论文生成器的数据源必须与 results_path 一致")

    metrics = {"questions": len(questions), "skipped_questions": skipped}
    completeness = None
    tex_value = paper.get("tex_path")
    if _path_exists(case_dir, tex_value):
        tex_path = Path(tex_value)
        if not tex_path.is_absolute():
            tex_path = case_dir / tex_path
        metrics.update(_paper_metrics(tex_path))
        completeness = completeness_report(tex_path)
        tex_text = tex_path.read_text(encoding="utf-8")
        for question in questions:
            section = question.get("paper", {}).get("section", "")
            if section and section not in tex_text:
                _warning(warnings, "paper.section_missing", f"论文中未找到登记节标题：{section}", question.get("id"))
    else:
        _warning(warnings, "paper.tex", f"论文源文件不存在：{tex_value}")

    return {
        "case_id": manifest.get("case_id"),
        "scope": SCOPE,
        "warning_count": len(warnings),
        "warnings": warnings,
        "metrics": metrics,
        # 见文件头部注释：体量对标独立于警告计数
        "completeness": completeness,
    }


def format_text(report: dict) -> str:
    lines = [f"研究质量审计：{report['warning_count']} 个警告"]
    for item in report["warnings"]:
        prefix = f"[{item['question']}] " if item.get("question") else ""
        lines.append(f"- {item['code']}: {prefix}{item['message']}")
    metrics = report.get("metrics", {})
    skipped = metrics.get("skipped_questions", 0)
    if skipped:
        lines.append(f"注意：{skipped} 个问题因任务类型未分类，跳过了后续全部检查")
    lines.append("指标：" + "，".join(f"{key}={value}" for key, value in metrics.items()))
    lines.append(f"范围：{SCOPE_NOTE}")
    completeness = report.get("completeness")
    if completeness:
        lines.append("")
        lines.append(_completeness_text(completeness))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="审计国赛工作目录的建模证据链（结构检查）")
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = audit_case(args.case_dir)
    except AuditConfigurationError as exc:
        print(f"审计失败：{exc}")
        raise SystemExit(2) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else format_text(report))
    raise SystemExit(1 if args.strict and report["warning_count"] else 0)


if __name__ == "__main__":
    main()
