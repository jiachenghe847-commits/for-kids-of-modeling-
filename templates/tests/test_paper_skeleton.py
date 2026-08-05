import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paper_skeleton import (
    SUBSECTIONS,
    VALIDATION_BY_TYPE,
    missing_slots,
    paper_skeleton,
    question_skeleton,
)


def test_skeleton_has_all_four_subsections_in_template_order():
    tex = question_skeleton("Q1", "问题一：某模型")
    names = re.findall(r"\\subsubsection\{([^}]*)\}", tex)
    assert names == [name for name, _ in SUBSECTIONS]


def test_every_contract_element_gets_its_own_slot():
    """契约要求的每个元素都要有槽位——漏一个就等于默许它被静默跳过。"""
    tex = question_skeleton("Q1", "问题一")
    slots = missing_slots(tex)
    expected = sum(len(elements) for _, elements in SUBSECTIONS)
    assert len(slots) == expected
    assert {s["section"] for s in slots} == {name for name, _ in SUBSECTIONS}


def test_algorithm_section_covers_the_four_things_the_contract_asks_for():
    """算法小节的四要素是 2025-B 演练那 59 个字全缺的东西，必须逐项在场。"""
    elements = dict(SUBSECTIONS)["算法设计与求解"]
    joined = " ".join(elements)
    for keyword in ("输入输出", "步骤", "停止条件", "复杂度"):
        assert keyword in joined


def test_known_task_type_fills_in_the_minimum_validation_combination():
    tex = question_skeleton("Q2", "问题二", task_type="optimization")
    assert VALIDATION_BY_TYPE["optimization"] in tex


def test_unknown_task_type_degrades_to_a_bare_slot_without_failing():
    """题目分类本来就允许人工判断，给个不认识的类型不该炸。"""
    tex = question_skeleton("Q3", "问题三", task_type="不认识的类型")
    assert "\\subsubsection{模型验证}" in tex
    assert len(missing_slots(tex)) == sum(len(e) for _, e in SUBSECTIONS)


def test_todo_slots_are_latex_comments_so_they_never_reach_the_pdf():
    for line in question_skeleton("Q1", "问题一").splitlines():
        if "TODO(" in line:
            assert line.lstrip().startswith("%")


def test_filling_a_slot_removes_it_from_the_missing_list():
    tex = question_skeleton("Q1", "问题一")
    before = len(missing_slots(tex))
    target = missing_slots(tex)[0]
    pattern = re.compile(rf"^[ \t]*%[ \t]*TODO\({re.escape(target['section'])}/"
                         rf"{re.escape(target['element'])}\):.*$\n?", re.MULTILINE)
    filled = pattern.sub("设 $d$ 为厚度，单位 µm。\n", tex, count=1)
    assert len(missing_slots(filled)) == before - 1


def test_multi_question_skeleton_repeats_the_slots_per_question():
    tex = paper_skeleton([{"id": "Q1", "title": "一"}, {"id": "Q2", "title": "二"}])
    per_question = sum(len(e) for _, e in SUBSECTIONS)
    assert len(missing_slots(tex)) == 2 * per_question
    assert tex.count("\\subsection{") == 2


def test_slot_records_the_line_number_for_navigation():
    tex = paper_skeleton([{"id": "Q1", "title": "一"}])
    lines = [s["line"] for s in missing_slots(tex)]
    assert lines == sorted(lines)
    assert all(l >= 1 for l in lines)
