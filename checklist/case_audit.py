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
    if interpretation.get("ambiguities") or len(metrics) > 1:
        _require_path(
            case_dir,
            interpretation.get("scenario_comparison"),
            warnings,
            "interpretation.scenario",
            "题意情景对照记录",
            qid,
        )

    model = question.get("model", {})
    if task_type == "optimization":
        if not model.get("decision_variables"):
            _warning(warnings, "model.variables", "优化问题缺少决策变量", qid)
        if _blank(model.get("objective")):
            _warning(warnings, "model.objective", "优化问题缺少目标函数", qid)
        if not model.get("constraints"):
            _warning(warnings, "model.constraints", "优化问题缺少约束条件", qid)
        policy = question.get("objective_policy")
        if isinstance(policy, dict):
            mode = policy.get("mode")
            if _blank(mode) or mode not in {"single", "lexicographic", "weighted"}:
                _warning(warnings, "objective_policy.mode", "优化目标政策必须明确为 single、lexicographic 或 weighted", qid)
            if mode in {"lexicographic", "weighted"} and not policy.get("stages"):
                _warning(warnings, "objective_policy.stages", "多目标政策缺少有序目标阶段及其定义", qid)
            if mode == "lexicographic" and policy.get("tolerances") and len(policy["tolerances"]) != len(policy.get("stages", [])):
                _warning(warnings, "objective_policy.tolerances", "字典序目标的 tolerances 必须与 stages 一一对应", qid)
            if policy.get("optimality_claim"):
                _require_path(
                    case_dir,
                    policy.get("solver_evidence"),
                    warnings,
                    "objective_policy.evidence",
                    "最优性求解证据",
                    qid,
                )
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


def _iter_manifest_strings(node: Any):
    """递归吐出 manifest 里所有字符串值，用于反查某个产物有没有被登记过。"""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _iter_manifest_strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _iter_manifest_strings(value)


def _display_artifacts(manifest: dict) -> set[str]:
    """收集所有登记为论文图表的产物路径（`paper.evidence_displays`）。"""
    out = set()
    for question in manifest.get("questions", []):
        if not isinstance(question, dict):
            continue
        for display in question.get("paper", {}).get("evidence_displays", []):
            value = display.get("artifact") if isinstance(display, dict) else display
            if isinstance(value, str) and value.strip():
                out.add(_file_part(value.strip()))
    return out


def _evidence_utilisation(case_dir: Path, manifest: dict, tex_path: Path | None) -> dict | None:
    """反过来问一句：算出来的证据，有几份真在论文里露过面。

    现有检查都是「登记的路径存不存在」，方向是从 case.json 出发的；它查不出
    `artifacts/` 里躺着一堆算完却从没被用过的东西。2025-B 演练实测 10 份证据只露面 4 份——
    这些不是需要新做的分析，是已经花掉机器时间、只差一张图的结果。

    分三桶：论文已展示 / 已登记但没展示 / 完全没登记。后两桶合起来就是行动清单。

    **刻意不计入警告数**：证据没露面完全可能是有意的——诊断类、过程类的图本就该放支撑材料
    而不是塞进正文（见 `analysis/figure-guide.md`）。工具不替人做这个决定，
    只负责让「算了但忘了用」看得见。

    只查文件级，不去猜 `results.json` 内部某个结果块有没有配图——那需要语义判断，
    静态工具做不了，硬做只会产生假信号。
    """
    results_path = manifest.get("results_path")
    artifacts_dir = None
    if isinstance(results_path, str) and results_path.strip():
        candidate = case_dir / _file_part(results_path.strip())
        if candidate.parent.is_dir():
            artifacts_dir = candidate.parent
    if artifacts_dir is None:
        fallback = case_dir / "artifacts"
        artifacts_dir = fallback if fallback.is_dir() else None
    if artifacts_dir is None:
        return None

    # 聚合结果文件按定义总被引用，列进去只是噪声
    aggregate = (case_dir / _file_part(results_path.strip())).resolve() \
        if isinstance(results_path, str) and results_path.strip() else None
    files = sorted(
        p for p in artifacts_dir.iterdir()
        if p.is_file() and (aggregate is None or p.resolve() != aggregate)
    )
    if not files:
        return None

    displays = _display_artifacts(manifest)
    display_names = {Path(d).name for d in displays}
    registered_text = [_file_part(s) for s in _iter_manifest_strings(manifest)]
    tex_text = tex_path.read_text(encoding="utf-8") if tex_path and tex_path.is_file() else ""
    # 插图的文件名单独拎出来：artifacts/convergence.json 生成的图叫 fig_convergence.png，
    # 这层对应关系没有任何地方结构化记录，只能靠文件名相含来搭桥。
    included_figures = re.findall(r"\\includegraphics[^{]*\{([^}]*)\}", tex_text)

    items, shown, cited_only, registered_not_shown, unregistered = [], [], [], [], []
    for path in files:
        relative = path.relative_to(case_dir).as_posix()
        in_displays = relative in displays or path.name in display_names
        as_figure = any(path.stem in fig for fig in included_figures)
        # 只在正文里被点了个路径名（如「详见 artifacts/constraints.json」）不算有图表。
        # 这条必须与上面两条分开，否则一份逐个罗列文件的「支撑文件清单」会把所有证据
        # 都标成已展示，整个检查就废了。
        cited = bool(tex_text) and path.stem in tex_text and not as_figure
        is_shown = in_displays or as_figure
        is_registered = any(path.name in text for text in registered_text)

        how = ("evidence_displays" if in_displays else
               "配图" if as_figure else
               "仅正文引用" if cited else "—")
        items.append({"file": path.name, "shown": is_shown, "cited": cited,
                      "registered": is_registered, "how": how})
        if is_shown:
            shown.append(path.name)
        elif cited:
            cited_only.append(path.name)
        elif is_registered:
            registered_not_shown.append(path.name)
        else:
            unregistered.append(path.name)

    return {
        "artifacts_dir": artifacts_dir.relative_to(case_dir).as_posix(),
        "total": len(files),
        "shown": len(shown),
        "shown_ratio": len(shown) / len(files),
        "shown_files": shown,
        "cited_only": cited_only,
        "registered_not_shown": registered_not_shown,
        "unregistered": unregistered,
        "items": items,
    }


_SUBSUB = re.compile(r"\\subsubsection\*?\{([^}]*)\}")
# 小节的结束边界：下一个 \subsubsection，或任何上级标题——最后一个小节不加这条约束
# 就会一路吃到文末，把后面的独立章节都算进自己的字数里。
_ANY_HEADING = re.compile(r"\\(?:sub)?(?:sub)?section\*?\{|\\appendix\b|\\end\{document\}")
_TODO_SLOT = re.compile(r"^[ \t]*%[ \t]*TODO\(([^/]+)/([^)]*)\):", re.MULTILINE)


def _subsection_balance(tex_path: Path | None) -> dict | None:
    """同名小节在各问之间的字数是否量级相当。

    这是小节层面唯一站得住的判断，因为**它不需要外部基线**——拿论文自己作参照。
    小节级的语料基线做不出来：从 corpus/official-2023 的 14 篇提取件自动切章，
    与 analysis/paper-structure.md 已实测的占比交叉验证只有 2/14 吻合
    （pdftotext 把公式打散成了像标题的短行）。编一个阈值比不给更糟，所以这里
    只报事实：最短多少、最长多少、差几倍。

    2025-B 演练上，「算法设计与求解」三问分别是 59 / 346 / 117 字，相差 5.9 倍——
    翻开最短那个会发现里面写的是推导，不是算法，内容放错了小节。
    """
    if tex_path is None or not tex_path.is_file():
        return None
    raw = tex_path.read_text(encoding="utf-8")
    # TODO 槽位本身就是 LaTeX 注释，必须在剥注释之前数。它跟「有没有同名小节可比」
    # 是两件事：单问论文没有任何可比对象，但 14 个没填的槽位照样得报出来。
    todo = [{"section": m.group(1).strip(), "element": m.group(2).strip()}
            for m in _TODO_SLOT.finditer(raw)]

    text = re.sub(r"(?<!\\)%.*", "", raw)
    groups: dict[str, list[int]] = {}
    for mark in _SUBSUB.finditer(text):
        following = _ANY_HEADING.search(text, mark.end())
        end = following.start() if following else len(text)
        chars = len(re.findall(r"[㐀-鿿]", text[mark.end():end]))
        groups.setdefault(mark.group(1), []).append(chars)

    rows = []
    for name, counts in groups.items():
        if len(counts) < 2:      # 只出现一次的小节没有可比对象
            continue
        lo, hi = min(counts), max(counts)
        rows.append({
            "subsection": name,
            "counts": counts,
            "min": lo,
            "max": hi,
            # 最短那节是空的时候「差几倍」没有定义。不要写 float("inf")：
            # json.dumps 会吐出 Infinity，那不是合法 JSON，严格解析器读不了。
            "ratio": (hi / lo) if lo else None,
        })
    if not rows and not todo:
        return None
    # ratio 为 None 的排最前——有空节比差几倍更该先看。
    rows.sort(key=lambda r: (r["ratio"] is None, r["ratio"] or 0.0), reverse=True)
    return {"rows": rows, "todo_slots": len(todo), "todo": todo[:12]}


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
    if manifest.get("schema_version") not in (1, 2):
        _warning(warnings, "schema.version", "case.json 的 schema_version 必须为 1 或 2")
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
    tex_path = None
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
        # 见文件头部注释：下面两项都独立于警告计数
        "completeness": completeness,
        "evidence_use": _evidence_utilisation(case_dir, manifest, tex_path),
        "subsection_balance": _subsection_balance(tex_path),
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
    evidence = report.get("evidence_use")
    if evidence:
        lines.append("")
        lines.append(_evidence_use_text(evidence))
    balance = report.get("subsection_balance")
    if balance:
        lines.append("")
        lines.append(_subsection_balance_text(balance))
    return "\n".join(lines)


def _subsection_balance_text(report: dict) -> str:
    lines = ["小节展开度（同名小节在各问之间的汉字数，用论文自己作参照，无外部基线）"]
    for row in report["rows"]:
        counts = "/".join(str(c) for c in row["counts"])
        if row["ratio"] is None:
            tail = ("这些小节都还是空的" if row["max"] == 0
                    else f"最长 {row['max']}，但最短那节是空的")
        else:
            tail = f"最短 {row['min']}，最长 {row['max']}，相差 {row['ratio']:.1f} 倍"
        lines.append(f"  {row['subsection']:<14}{counts:<20}{tail}")
    if not report["rows"]:
        lines.append("  没有同名小节可比（只有一问，或各小节标题都不重名）")
    if report["todo_slots"]:
        lines.append(f"  骨架 TODO 槽位未填：{report['todo_slots']} 处"
                     f"（如 {report['todo'][0]['section']}/{report['todo'][0]['element']}）")
    lines.append("  注：不计入警告数。差几倍是事实不是判定——最短的那个往往不是漏写，"
                 "而是内容放错了小节，展开模式见 analysis/exposition-guide.md")
    return "\n".join(lines)


def _evidence_use_text(report: dict) -> str:
    total, shown = report["total"], report["shown"]
    lines = [
        f"证据利用率：{report['artifacts_dir']}/ 下 {total} 份证据，"
        f"{shown} 份有图或表（{report['shown_ratio'] * 100:.0f}%）"
    ]
    if report["cited_only"]:
        lines.append("  仅正文引用了路径、没有图表：" + "、".join(report["cited_only"]))
    if report["registered_not_shown"]:
        lines.append("  已登记但论文没展示：" + "、".join(report["registered_not_shown"]))
    if report["unregistered"]:
        lines.append("  未登记：" + "、".join(report["unregistered"]))
    if shown < total:
        lines.append("  以上都是已经算出来、只差一张图或一张表的东西——凑图数先从这里找")
    lines.append("  注：不计入警告数。诊断类、过程类证据本就该放支撑材料而不塞进正文，工具不替你决定")
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
