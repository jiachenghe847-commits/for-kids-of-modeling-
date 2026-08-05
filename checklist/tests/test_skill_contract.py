from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_codex_and_claude_entries_share_quality_contract():
    codex = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (ROOT / ".claude/skills/cumcm-toolkit/SKILL.md").read_text(encoding="utf-8")
    required = (
        "official-only",
        "init_contest_case.py",
        "case.json",
        "case_audit.py",
        "方程到代码/测试映射",
        "分析 → 模型 → 算法 → 结果 → 验证 → 解释",
        "--strict",
        # 六段内容契约与模板四小节的映射，两边都要写清，否则照契约写的人会以为漏了两节
        "结果分析",
        # 审计的能力边界：0 个警告不是质量背书
        "只做结构检查",
        "manual_verification.md",
        # case.json 骨架里的尖括号占位符约定
        "<...>",
    )
    for marker in required:
        assert marker in codex
        assert marker in claude


def test_all_entry_docs_agree_on_which_audit_sections_exist():
    """三个不计入警告数的分节，四份入口文档必须都列全、数目一致。

    回归：新增「小节展开度」时只改了 README，AGENTS/SKILL/workflow 仍写「两个分节」
    且没提这一节——照文档写的人不会知道去看它。标记式断言查不出这种数目漂移，
    所以这里把数目和名字一起钉死。
    """
    docs = {
        name: (ROOT / name).read_text(encoding="utf-8")
        for name in ("AGENTS.md", ".claude/skills/cumcm-toolkit/SKILL.md",
                     "README.md", "analysis/modeling-workflow.md")
    }
    for name, text in docs.items():
        for section in ("完备性对标", "证据利用率", "小节展开度"):
            assert section in text, f"{name} 没提到「{section}」"
        assert "两个分节" not in text, f"{name} 还写着「两个分节」，分节已经有三个"


def test_case_skeleton_and_audit_agree_on_the_placeholder_convention():
    """init_contest_case.py 发占位符、case_audit.py 认占位符，两边不能各改各的。"""
    import sys

    sys.path.insert(0, str(ROOT / "templates"))
    sys.path.insert(0, str(ROOT / "checklist"))
    from case_audit import _blank
    from init_contest_case import question_card

    card = question_card(1)
    assert _blank(card["target_quantity"])
    assert _blank(card["solvers"]["primary"]["method"])
    assert _blank(card["paper"]["section"])


def test_shared_workflow_documents_evidence_requirements():
    workflow = (ROOT / "analysis/modeling-workflow.md").read_text(encoding="utf-8")
    for marker in (
        "资料隔离",
        "模型卡",
        "方程",
        "多种子",
        "逐约束",
        "独立验证",
        "论文内容契约",
    ):
        assert marker in workflow


def test_demo_is_not_described_as_depth_or_length_target():
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    demo_readme = (ROOT / "examples/示范论文/README.md").read_text(encoding="utf-8")
    assert "不是深度/篇幅范本" in root_readme
    assert "不是获奖深度或目标篇幅模板" in demo_readme
