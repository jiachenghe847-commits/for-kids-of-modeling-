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
    )
    for marker in required:
        assert marker in codex
        assert marker in claude


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
