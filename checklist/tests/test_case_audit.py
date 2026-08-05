import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from case_audit import SCOPE_NOTE, _subsection_balance_text, audit_case, format_text

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "templates"))
from init_contest_case import initialize_case


AUDIT_SCRIPT = Path(__file__).resolve().parents[1] / "case_audit.py"


def _touch(case_dir: Path, relative: str, content: str = "{}\n") -> None:
    path = case_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _complete_optimization_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / "complete"
    initialize_case(case_dir, "fixture", 1)
    for relative in (
        "official_input/problem.pdf",
        "tests/test_model.py",
        "artifacts/results.json",
        "artifacts/baseline.json",
        "artifacts/primary.json",
        "artifacts/convergence.json",
        "artifacts/constraints.json",
        "artifacts/independent.json",
        "artifacts/seeds.json",
        "artifacts/result_table.csv",
    ):
        _touch(case_dir, relative)
    _touch(case_dir, "paper/paper.tex", r"\section{问题一：联合优化模型}")

    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["sources"] = [
        {"path": "official_input/problem.pdf", "kind": "official"}
    ]
    question = manifest["questions"][0]
    question.update(
        {
            "task_type": "optimization",
            "target_quantity": "总成本最小值",
            "constraint_audit": "artifacts/constraints.json",
        }
    )
    question["interpretation"] = {
        "ambiguities_reviewed": True,
        "ambiguities": [],
        "candidate_metrics": ["总成本"],
        "selected_metric": "总成本",
        "rationale": "与题目中的最小费用要求一致",
    }
    question["model"] = {
        "decision_variables": ["x"],
        "parameters": ["c"],
        "objective": "min c*x",
        "constraints": ["x >= 0"],
        "assumptions": ["单位成本在规划期内不变"],
        "discretized": False,
        "equation_code_map": [
            {
                "equation": "objective",
                "implementation": "src/compute.py:main",
                "test": "tests/test_model.py",
            }
        ],
    }
    question["solvers"] = {
        "baseline": {
            "method": "grid search",
            "entrypoint": "src/compute.py",
            "result_path": "artifacts/baseline.json",
        },
        "primary": {
            "method": "differential evolution",
            "entrypoint": "src/compute.py",
            "result_path": "artifacts/primary.json",
            "iterative": True,
            "stochastic": True,
            "seeds": [1, 2, 3],
            "convergence_trace": "artifacts/convergence.json",
        },
    }
    question["validations"] = [
        {
            "type": "independent_solver",
            "artifact": "artifacts/independent.json",
            "finding": "两种算法目标值相差 0.2%",
        },
        {
            "type": "multi_seed_stability",
            "artifact": "artifacts/seeds.json",
            "finding": "三次运行标准差小于 0.1",
        },
    ]
    question["paper"] = {
        "section": "问题一：联合优化模型",
        "evidence_displays": [
            {"type": "table", "artifact": "artifacts/result_table.csv"}
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_dir


def test_initialized_case_reports_actionable_warnings(tmp_path):
    case_dir = tmp_path / "incomplete"
    initialize_case(case_dir, "incomplete", 1)
    report = audit_case(case_dir)
    codes = {item["code"] for item in report["warnings"]}
    assert "inputs.sources" in codes
    assert "question.task_type" in codes
    assert "results.path" in codes


def test_complete_optimization_case_has_no_warnings(tmp_path):
    report = audit_case(_complete_optimization_case(tmp_path))
    assert report["warnings"] == []
    assert report["metrics"]["questions"] == 1
    assert report["metrics"]["skipped_questions"] == 0


def test_placeholder_values_still_count_as_unfilled(tmp_path):
    """骨架里的 <...> 占位符必须被判为未填写，不能伪装成已完成。"""
    case_dir = tmp_path / "placeholder"
    initialize_case(case_dir, "placeholder", 1)
    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    question = manifest["questions"][0]
    assert question["target_quantity"].startswith("<")

    # 只把任务类型填掉，其余保持出厂占位符，逐问检查才会真正跑起来。
    question["task_type"] = "optimization"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    codes = {item["code"] for item in audit_case(case_dir)["warnings"]}
    assert "question.target" in codes            # target_quantity 是占位符
    assert "interpretation.selected" in codes    # selected_metric 是占位符
    assert "solver.primary" in codes             # primary.method 是占位符
    assert "trace.equation" in codes             # equation_code_map 样例条目未填
    assert "paper.section" in codes              # 论文节标题是占位符


def test_unclassified_questions_are_counted_as_skipped(tmp_path):
    """未分类的问题会跳过后续全部检查，报告必须把跳过数说出来。"""
    case_dir = tmp_path / "skipped"
    initialize_case(case_dir, "skipped", 3)
    report = audit_case(case_dir)
    assert report["metrics"]["skipped_questions"] == 3
    assert "3 个问题因任务类型未分类" in format_text(report)


def test_report_states_that_the_audit_is_structural_only(tmp_path):
    """审计只查证据在不在，不查证据成不成立——这条边界必须写进输出。"""
    case_dir = tmp_path / "scope"
    initialize_case(case_dir, "scope", 1)
    report = audit_case(case_dir)
    assert report["scope"] == "structural"
    assert SCOPE_NOTE in format_text(report)
    assert "manual_verification.md" in SCOPE_NOTE


def test_blind_case_flags_corpus_reference(tmp_path):
    case_dir = tmp_path / "blind"
    initialize_case(case_dir, "blind", 1)
    manifest_path = case_dir / "case.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["sources"] = ["corpus/2025-A.md"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    codes = {item["code"] for item in audit_case(case_dir)["warnings"]}
    assert "inputs.corpus" in codes


def test_completeness_benchmark_is_reported_alongside_the_audit(tmp_path):
    case_dir = _complete_optimization_case(tmp_path)
    report = audit_case(case_dir)
    completeness = report["completeness"]
    assert completeness is not None
    labels = {item["label"] for item in completeness["items"]}
    assert {"正文图数", "附录占全文"} <= labels
    text = format_text(report)
    assert "完备性对标" in text
    # 基准出处必须写在输出里，否则读的人无从判断这些数字是实测还是拍脑袋
    assert "paper-structure.md" in text


def test_thin_paper_is_flagged_as_low_without_raising_the_warning_count(tmp_path):
    """体量不足只在对标分节里说，不污染 warning_count——这是 2025-B 演练暴露的设计要求。

    那次论文 6 张图、附录空白，审计仍报「0 个警告」；补对标是为了让人看见差距，
    而不是把「凑图表」变成通过审计的硬条件。
    """
    case_dir = _complete_optimization_case(tmp_path)
    baseline = audit_case(case_dir)
    assert baseline["warning_count"] == 0

    verdicts = {item["label"]: item["verdict"] for item in baseline["completeness"]["items"]}
    assert verdicts["正文图数"] == "偏低"          # fixture 论文一张图都没有
    assert verdicts["附录占全文"] == "偏低"        # 也没有 \appendix
    assert baseline["completeness"]["below_count"] > 0
    assert baseline["completeness"]["figures_exceed_tables"] is False
    # 关键断言：上面这些「偏低」一个都没有变成警告
    assert baseline["warning_count"] == 0


def test_completeness_does_not_gate_reference_count(tmp_path):
    """参考文献条数故意不设门槛：官方 14 篇实测 1-11 条，7 篇不足 5 条，D039 只有 1 条。

    见 analysis/paper-structure.md「参考文献少照样官方优秀」。给它设阈值会逼人凑引用。
    """
    case_dir = _complete_optimization_case(tmp_path)
    keys = {item["key"] for item in audit_case(case_dir)["completeness"]["items"]}
    assert not any("reference" in key or "bib" in key for key in keys)


def test_appendix_ratio_counts_code_pulled_in_at_compile_time(tmp_path):
    """\\lstinputlisting / \\codefile / \\input 引用的文件必须计入附录体量。

    回归测试：这些命令在 .tex 里只占一行，代码正文是编译期才读进来的。
    只数源码字符的话，用 templates/appendix_code.py 正确挂了全量代码的论文
    会被判成「附录是空的」——恰好把对的做法判成错的。实测这个 bug 让
    2025-B 演练接上附录后的占比只从 4.3% 涨到 7.8%，修正后是 68.2%。
    """
    from paper_completeness import measure

    (tmp_path / "big.py").write_text("x = 1\n" * 4000, encoding="utf-8")
    body = "\\begin{abstract}摘要\\end{abstract}\n\\section{模型的建立与求解}正文\n"

    thin = tmp_path / "thin.tex"
    thin.write_text(body + "\\appendix\n\\section{程序代码}\n见支撑材料。\n", encoding="utf-8")

    for command in ("\\lstinputlisting{big.py}",
                    "\\codefile{big.py}{Python}{src/big.py}"):
        fat = tmp_path / "fat.tex"
        fat.write_text(body + f"\\appendix\n\\section{{程序代码}}\n{command}\n", encoding="utf-8")
        assert measure(fat)["appendix_ratio"] > 0.9, command
    assert measure(thin)["appendix_ratio"] < 0.5


def test_missing_included_file_does_not_crash_the_audit(tmp_path):
    """路径写错时宁可少算，也不能让整个审计中断。"""
    from paper_completeness import measure

    tex = tmp_path / "broken.tex"
    tex.write_text("\\section{正文}文\n\\appendix\n\\lstinputlisting{nope.py}\n", encoding="utf-8")
    assert 0.0 <= measure(tex)["appendix_ratio"] <= 1.0


def test_completeness_medians_match_the_measured_corpus_document(tmp_path):
    """现算的中位数必须与 analysis/paper-structure.md 正文里写的一致。

    基准是从附表二的 14 行原始数据算出来的，如果哪天两边对不上，说明有人只改了一处。
    """
    from paper_completeness import BENCHMARKS

    documented = {
        "abstract_chars": 1026,
        "figures": 20.5,
        "tables": 9.0,
        "appendix_ratio": 0.499,
        "modeling_ratio": 0.788,
        "assumption_ratio": 0.009,
    }
    for key, expected in documented.items():
        got = BENCHMARKS[key]["median"]
        assert abs(got - expected) <= max(0.002, abs(expected) * 0.005), key


def test_evidence_utilisation_sorts_every_artifact_into_exactly_one_bucket(tmp_path):
    """算出来的证据分四桶：有图表 / 仅正文引用 / 已登记未展示 / 完全没登记。

    fixture 里 result_table.csv 登记为 evidence_display，constraints.json 只出现在
    constraint_audit，另加一个谁都没提的孤儿文件。
    """
    case_dir = _complete_optimization_case(tmp_path)
    _touch(case_dir, "artifacts/orphan.json")
    evidence = audit_case(case_dir)["evidence_use"]

    assert "result_table.csv" in evidence["shown_files"]      # evidence_displays 登记
    assert "constraints.json" in evidence["registered_not_shown"]  # 只在 constraint_audit
    assert "orphan.json" in evidence["unregistered"]          # 谁都没提

    buckets = ("shown_files", "cited_only", "registered_not_shown", "unregistered")
    classified = [name for key in buckets for name in evidence[key]]
    assert len(classified) == evidence["total"]               # 不重不漏
    assert len(set(classified)) == len(classified)


def test_evidence_utilisation_excludes_the_aggregate_results_file(tmp_path):
    """results.json 按定义总被引用，列进清单只是噪声。"""
    case_dir = _complete_optimization_case(tmp_path)
    evidence = audit_case(case_dir)["evidence_use"]
    assert "results.json" not in [item["file"] for item in evidence["items"]]


def test_a_figure_derived_from_an_artifact_counts_as_shown(tmp_path):
    """artifacts/convergence.json 生成的图叫 fig_convergence.png，这层对应关系
    没有任何地方结构化记录，只能靠文件名相含来搭桥。"""
    case_dir = _complete_optimization_case(tmp_path)
    before = audit_case(case_dir)["evidence_use"]
    assert "convergence.json" in before["registered_not_shown"]

    tex = case_dir / "paper/paper.tex"
    tex.write_text(tex.read_text(encoding="utf-8")
                   + "\n\\includegraphics[width=0.9\\textwidth]{fig_convergence.png}\n",
                   encoding="utf-8")
    after = audit_case(case_dir)["evidence_use"]
    assert "convergence.json" in after["shown_files"]
    assert after["shown"] == before["shown"] + 1


def test_a_bare_path_citation_is_not_counted_as_a_figure(tmp_path):
    """「详见 artifacts/constraints.json」只是引了个路径，不是图表。

    这两者必须分开，否则一份逐个罗列文件的「支撑文件/材料清单」会把所有证据都标成
    已展示，整个检查就废了——而那份清单恰恰是 2022 年后获奖论文的标配。
    """
    case_dir = _complete_optimization_case(tmp_path)
    tex = case_dir / "paper/paper.tex"
    tex.write_text(tex.read_text(encoding="utf-8")
                   + "\n约束残差详见 \\texttt{artifacts/constraints.json}。\n",
                   encoding="utf-8")
    evidence = audit_case(case_dir)["evidence_use"]
    assert "constraints.json" in evidence["cited_only"]
    assert "constraints.json" not in evidence["shown_files"]


def test_a_supporting_file_listing_does_not_inflate_the_shown_count(tmp_path):
    """回归：整份支撑文件清单把每个产物都点一遍，有图表的份数不应因此变化。"""
    case_dir = _complete_optimization_case(tmp_path)
    before = audit_case(case_dir)["evidence_use"]["shown"]
    listing = "\n".join(
        f"  \\item \\texttt{{artifacts/{p.name}}}"
        for p in sorted((case_dir / "artifacts").iterdir())
    )
    tex = case_dir / "paper/paper.tex"
    tex.write_text(tex.read_text(encoding="utf-8")
                   + f"\n\\section{{支撑文件/材料清单}}\n\\begin{{itemize}}\n{listing}\n\\end{{itemize}}\n",
                   encoding="utf-8")
    assert audit_case(case_dir)["evidence_use"]["shown"] == before


def test_unused_evidence_never_raises_the_warning_count(tmp_path):
    """回归断言：证据没露面只在独立分节里说，不污染 warning_count，也不让 --strict 失败。

    证据没露面完全可能是有意的——诊断类图本就该放支撑材料。工具不替人做这个决定。
    """
    case_dir = _complete_optimization_case(tmp_path)
    baseline = audit_case(case_dir)["warning_count"]
    for name in ("orphan_a.json", "orphan_b.json", "orphan_c.json"):
        _touch(case_dir, f"artifacts/{name}")
    report = audit_case(case_dir)
    assert len(report["evidence_use"]["unregistered"]) >= 3
    assert report["warning_count"] == baseline == 0

    text = format_text(report)
    assert "证据利用率" in text
    assert "orphan_a.json" in text


def test_evidence_section_is_absent_when_there_is_no_artifacts_directory(tmp_path):
    case_dir = tmp_path / "bare"
    initialize_case(case_dir, "bare", 1)
    assert audit_case(case_dir)["evidence_use"] is None


def _paper_with_subsections(case_dir: Path, blocks: list[tuple[str, dict]], tail: str = "") -> None:
    """写一份带 \\subsection/\\subsubsection 的论文；blocks 是 [(问题标题, {小节: 正文})]。"""
    parts = []
    for title, sections in blocks:
        parts.append(f"\\subsection{{{title}}}")
        for name, body in sections.items():
            parts.append(f"\\subsubsection{{{name}}}\n{body}")
    (case_dir / "paper/paper.tex").write_text("\n".join(parts) + tail, encoding="utf-8")


def test_subsection_balance_reports_the_ratio_between_sibling_sections(tmp_path):
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(case_dir, [
        ("问题一：联合优化模型", {"算法设计与求解": "短" * 10, "结果分析": "文" * 50}),
        ("问题二", {"算法设计与求解": "长" * 60, "结果分析": "文" * 55}),
    ])
    rows = {r["subsection"]: r for r in audit_case(case_dir)["subsection_balance"]["rows"]}
    assert rows["算法设计与求解"]["counts"] == [10, 60]
    assert rows["算法设计与求解"]["ratio"] == pytest.approx(6.0)
    # 倍数最大的排最前，方便一眼看到最该管的那个
    assert audit_case(case_dir)["subsection_balance"]["rows"][0]["subsection"] == "算法设计与求解"


def test_last_subsection_does_not_swallow_the_chapters_after_it(tmp_path):
    """回归：最后一个 \\subsubsection 必须在下一个上级标题处止住。

    不加这条约束时，问题三的「模型验证」会一路吃到文末，把「灵敏度分析」「模型评价」
    都算进自己的字数——实测把 253 字虚报成 1602 字。
    """
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(
        case_dir,
        [("问题一", {"模型验证": "验" * 20}), ("问题二", {"模型验证": "验" * 25})],
        tail="\n\\section{灵敏度分析}\n" + "尾" * 900 + "\n",
    )
    counts = audit_case(case_dir)["subsection_balance"]["rows"][0]["counts"]
    assert counts == [20, 25]


def test_subsection_appearing_only_once_has_no_sibling_to_compare(tmp_path):
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(case_dir, [
        ("问题一", {"模型建立": "甲" * 30, "独有小节": "乙" * 30}),
        ("问题二", {"模型建立": "丙" * 40}),
    ])
    names = {r["subsection"] for r in audit_case(case_dir)["subsection_balance"]["rows"]}
    assert "模型建立" in names
    assert "独有小节" not in names


def test_unfilled_skeleton_slots_are_counted(tmp_path):
    """骨架留下的 TODO 槽位没填完，要报出来。"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "templates"))
    from paper_skeleton import paper_skeleton

    case_dir = _complete_optimization_case(tmp_path)
    skeleton = paper_skeleton([{"id": "Q1", "title": "问题一", "task_type": "optimization"},
                               {"id": "Q2", "title": "问题二", "task_type": "optimization"}])
    (case_dir / "paper/paper.tex").write_text(skeleton, encoding="utf-8")
    balance = audit_case(case_dir)["subsection_balance"]
    assert balance["todo_slots"] == 28          # 两问 × 14 个必需元素
    assert balance["todo"][0]["section"] == "模型建立"


def test_single_question_paper_still_reports_its_unfilled_slots(tmp_path):
    """回归：一问的论文没有同名兄弟小节，但 14 个没填的槽位照样得报出来。

    先判断「有没有可比小节」再数 TODO 时，单问骨架会整个返回 None——
    审计报告里连一行都不出现，等于把最该提醒的场景漏掉了。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "templates"))
    from paper_skeleton import paper_skeleton

    case_dir = _complete_optimization_case(tmp_path)
    (case_dir / "paper/paper.tex").write_text(
        paper_skeleton([{"id": "Q1", "title": "问题一", "task_type": "optimization"}]),
        encoding="utf-8")
    balance = audit_case(case_dir)["subsection_balance"]
    assert balance is not None
    assert balance["rows"] == []                # 没有可比对象，这部分确实是空的
    assert balance["todo_slots"] == 14
    assert "14 处" in _subsection_balance_text(balance)


def test_empty_subsections_serialise_as_valid_json(tmp_path):
    """回归：空节的「差几倍」必须是 null，不能是 float('inf')。

    json.dumps 把 inf 写成 Infinity，那是 Python 的扩展、不是合法 JSON，
    严格解析器（jq、Go、多数前端）直接报错——`--format json` 就没法给别的工具吃。
    """
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(case_dir, [
        ("问题一", {"模型建立": "", "结果分析": "文" * 30}),
        ("问题二", {"模型建立": "甲" * 40, "结果分析": "文" * 30}),
    ])
    balance = audit_case(case_dir)["subsection_balance"]
    rows = {r["subsection"]: r for r in balance["rows"]}
    assert rows["模型建立"]["ratio"] is None
    assert balance["rows"][0]["subsection"] == "模型建立"   # 空节排最前

    def reject(constant):                        # json.loads 默认会放行 Infinity
        raise AssertionError(f"输出了非法 JSON 常量：{constant}")
    json.loads(json.dumps(balance, ensure_ascii=False), parse_constant=reject)

    text = _subsection_balance_text(balance)
    assert "最短那节是空的" in text
    assert "inf" not in text


def test_all_empty_siblings_are_not_reported_as_infinitely_lopsided(tmp_path):
    """两节都是 0 字不是「相差无穷倍」，是两节都还没写——措辞要说对。"""
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(case_dir, [
        ("问题一", {"模型验证": ""}),
        ("问题二", {"模型验证": ""}),
    ])
    balance = audit_case(case_dir)["subsection_balance"]
    assert balance["rows"][0]["counts"] == [0, 0]
    assert "都还是空的" in _subsection_balance_text(balance)


def test_lopsided_subsections_never_raise_the_warning_count(tmp_path):
    """回归：展开度只在独立分节里陈述事实，不污染 warning_count，也不让 --strict 失败。"""
    case_dir = _complete_optimization_case(tmp_path)
    _paper_with_subsections(case_dir, [
        ("问题一：联合优化模型", {"算法设计与求解": "短"}),
        ("问题二", {"算法设计与求解": "长" * 500}),
    ])
    report = audit_case(case_dir)
    assert report["subsection_balance"]["rows"][0]["ratio"] >= 100
    assert report["warning_count"] == 0
    assert "小节展开度" in format_text(report)


def test_cli_warns_without_blocking_and_strict_blocks(tmp_path):
    case_dir = tmp_path / "cli"
    initialize_case(case_dir, "cli", 1)
    normal = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(case_dir)], capture_output=True, text=True
    )
    strict = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), str(case_dir), "--strict"],
        capture_output=True,
        text=True,
    )
    assert normal.returncode == 0
    assert "警告" in normal.stdout
    assert strict.returncode == 1
