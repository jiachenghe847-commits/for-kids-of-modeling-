"""把论文产出与获奖论文的实测分布对标。

**为什么需要这个工具**：2025 B 题演练产出的论文只有 16 页——正文 7754 字、6 张图、
附录空白——而 `analysis/paper-structure.md` 里早就写着正文 1.2~1.3 万字、图中位 20.5 张、
附录占全文中位 49.9%。基准一直在仓库里，`case_audit.py` 也一直在数图表，但两者从来没有
碰过面，于是那篇论文以「0 个警告」通过了审计。这个模块补的就是碰面这一步。

**基准的来源**：全部取自 `analysis/paper-structure.md`「官方优秀论文对照（2023，n=14）」
一节与「附表二」，是组委会评选的优秀论文经 pdftotext 字符级实测得到的分布，不是经验估计。
改动这些数字之前请先回去改那份实测文档——顺序反了就等于把实测退化成拍脑袋。

**这里故意不检查的**：参考文献条数。`analysis/paper-structure.md` 的官方样本已经否定了
「至少 5 条」这个流传很广的说法——14 篇实测 1~11 条（中位 4.5），7 篇不足 5 条，D039 只有
1 条照样入选官方优秀论文。给它设门槛会逼着队伍凑引用，是负作用。

**边界**：这里量的是体量，不是质量。图够多不等于图有用。达标只说明论文的形态落在获奖论文
的分布里，内容是否站得住仍然要走 `checklist/manual_verification.md`。
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


# `analysis/paper-structure.md`「附表二」的 14 篇官方优秀论文逐篇实测值，原样誊录。
# 直接放原始数据而不是放预先算好的区间，有两个原因：一是中位数、四分位都能由它现算出来，
# 印出来的基准与文档必然自洽；二是以后附表二增补样本时，这里只需同步表格。
# 列序：摘要字数、图、表、附录占全文%、建模求解占正文%、模型假设占正文%
OFFICIAL_2023: dict[str, tuple] = {
    #        摘要   图  表  附录%  建模%  假设%
    "A092": (1035, 36,  8, 31.1, 83.3, 0.4),
    "A127": (1225, 21, 15, 52.3, 78.4, 1.1),
    "A165": (1032, 11,  9, 47.5, 68.1, 1.5),
    "A175": (1197, 11, 10, 35.9, 84.8, 1.0),
    "B226": (962,  27,  5, 44.0, 80.9, 0.8),
    "B311": (827,  13,  5, 52.8, 58.7, 2.1),
    "B477": (861,  24,  4, 72.1, 71.7, 0.9),
    "C050": (1051, 15, 17, 39.6, 77.4, 0.6),
    "C126": (654,   8,  9, 71.6, 90.9, 0.4),
    "C228": (976,  20, 10, 65.0, 69.7, 0.7),
    "C235": (868,  28, 11, 57.2, 83.3, 1.4),
    "D039": (1037,  5,  7, 27.6, 76.1, 1.3),
    "E032": (1019, 32,  7, 43.1, 80.5, 1.3),
    "E176": (1276, 41, 14, 58.5, 78.8, 0.8),
}
_COLUMNS = ("abstract_chars", "figures", "tables",
            "appendix_ratio", "modeling_ratio", "assumption_ratio")
_PERCENT_COLUMNS = {"appendix_ratio", "modeling_ratio", "assumption_ratio"}

_LABELS = {
    "abstract_chars": "摘要字数",
    "body_chars": "正文字符数",
    "figures": "正文图数",
    "tables": "正文表数",
    "appendix_ratio": "附录占全文",
    "modeling_ratio": "建模求解占正文",
    "assumption_ratio": "模型假设占正文",
}


def _quartiles(values: list[float]) -> tuple[float, float, float]:
    """返回 (Q1, 中位数, Q3)，用 stdlib 的 inclusive 口径。

    区间取四分位而不是最小-最大值：官方 14 篇里 D039 只有 5 张图照样入选，
    拿最小值当下界的话，一篇 6 张图的论文会被判成「达标」——那正好掩盖了要抓的问题。
    四分位说的是「落在半数获奖论文的常见区间之外」，这才是有信息量的判断。
    """
    q1, q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, q2, q3


def _build_benchmarks() -> dict[str, dict]:
    rows = list(OFFICIAL_2023.values())
    benchmarks: dict[str, dict] = {}
    for i, key in enumerate(_COLUMNS):
        raw = [row[i] for row in rows]
        scale = 100.0 if key in _PERCENT_COLUMNS else 1.0
        q1, median, q3 = _quartiles([v / scale for v in raw])
        benchmarks[key] = {
            "low": q1, "high": q3, "median": median,
            "label": _LABELS[key],
            "percent": key in _PERCENT_COLUMNS,
            "source": f"官方 2023 n=14 的四分位（analysis/paper-structure.md 附表二）",
        }
    # 跨年代均值不是单篇区间，且 TeX 汉字与 PDF 字母数字口径不同。
    # 此项只报告观测值；正式比较由 pdf_metrics 同口径完成。
    benchmarks["body_chars"] = {
        "low": None, "high": None, "median": None,
        "label": _LABELS["body_chars"], "percent": False,
        "source": "analysis/paper-structure.md 年代差异一节：正文字符数均值稳定在 1.2-1.3 万",
    }
    return benchmarks


BENCHMARKS: dict[str, dict] = _build_benchmarks()
# 输出顺序：先体量后结构，与论文本身的阅读顺序一致
_ORDER = ("abstract_chars", "body_chars", "figures", "tables",
          "appendix_ratio", "modeling_ratio", "assumption_ratio")

# 章节归类：按标题关键词把 \section 分到统计口径里。标题命名是自由的
# （paper-structure.md 记录了「内容命名章标题」这种合法变体），所以用关键词而非精确匹配。
_MODELING_KEYWORDS = ("模型的建立", "模型建立", "建立与求解", "问题一", "问题二", "问题三",
                      "问题四", "问题五", "模型的分析")
_ASSUMPTION_KEYWORDS = ("模型假设", "基本假设", "假设")

_CJK = re.compile(r"[㐀-鿿]")
_SECTION = re.compile(r"\\section\*?\{([^}]*)\}")


def _cjk_count(text: str) -> int:
    return len(_CJK.findall(text))


def _strip_comments(text: str) -> str:
    """去掉 LaTeX 行注释，避免注释里的中文被算进正文字数。"""
    return re.sub(r"(?<!\\)%.*", "", text)


def _split_body_appendix(text: str) -> tuple[str, str]:
    """以 \\appendix 为界切开正文与附录；没有 \\appendix 时附录为空。"""
    match = re.search(r"\\appendix\b", text)
    if not match:
        return text, ""
    return text[: match.start()], text[match.start():]


# 编译期才把外部文件读进来的命令：\lstinputlisting[..]{路径}、\codefile{路径}{..}{..}、
# \input{路径}、\include{路径}。只看 .tex 源码会把这些当成一行命令，严重低估附录体量——
# 而「用 \lstinputlisting 挂全量代码」恰恰是 templates/appendix_code.py 推荐的写法，
# 不跟进这些引用的话，工具会告诉用户「你的附录是空的」，正好把对的做法判成错的。
_INCLUDES = re.compile(
    r"\\(?:lstinputlisting|verbatiminput|VerbatimInput)\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}"
    r"|\\codefile\s*\{([^}]+)\}"
    r"|\\(?:input|include)\s*\{([^}]+)\}"
)


def _expanded_length(fragment: str, base_dir: Path, _seen: set | None = None) -> int:
    """片段的有效长度：自身字符数 + 所有被引用文件的字符数（递归展开 \\input）。

    读不到的文件按 0 计——路径写错时宁可少算也不要报错中断审计。
    """
    _seen = set() if _seen is None else _seen
    total = len(fragment)
    for match in _INCLUDES.finditer(fragment):
        raw = next(g for g in match.groups() if g is not None).strip()
        candidates = [base_dir / raw]
        if not Path(raw).suffix:                      # \input{appx} 省略 .tex 后缀
            candidates.append(base_dir / f"{raw}.tex")
        for path in candidates:
            resolved = path.resolve()
            if resolved in _seen or not path.is_file():
                continue
            _seen.add(resolved)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                break
            # 被 \input 进来的还可能继续引用别的文件，递归展开
            total += _expanded_length(content, path.parent, _seen)
            break
    return total


def _expand_tex_inputs(fragment: str, base_dir: Path, seen: set[Path] | None = None) -> str:
    """Inline local TeX inputs before counting body sections, figures, and tables."""
    seen = set() if seen is None else seen
    def replace(match: re.Match) -> str:
        raw = match.group(1).strip()
        candidates = [base_dir / raw]
        if not Path(raw).suffix:
            candidates.append(base_dir / f"{raw}.tex")
        for path in candidates:
            resolved = path.resolve()
            if path.is_file() and resolved not in seen:
                seen.add(resolved)
                return _expand_tex_inputs(path.read_text(encoding="utf-8", errors="replace"), path.parent, seen)
        return match.group(0)
    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", replace, fragment)


def _abstract_chars(text: str) -> int:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
    return _cjk_count(match.group(1)) if match else 0


def _section_chars(body: str) -> list[tuple[str, int]]:
    """返回 [(节标题, 该节 CJK 字符数)]，按 \\section 切分。"""
    marks = list(_SECTION.finditer(body))
    out = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out.append((mark.group(1), _cjk_count(body[mark.end():end])))
    return out


def _classify_ratio(sections: list[tuple[str, int]], keywords: tuple[str, ...], total: int) -> float:
    if total <= 0:
        return 0.0
    hit = sum(n for title, n in sections if any(k in title for k in keywords))
    return hit / total


def measure(tex_path: str | Path) -> dict:
    """读一份 .tex，量出对标需要的原始指标。

    ``\\lstinputlisting`` / ``\\codefile`` / ``\\input`` 引用的外部文件会被展开计入长度，
    否则挂全量代码的附录会被误判成空的（见 ``_expanded_length``）。
    """
    tex_path = Path(tex_path)
    text = _strip_comments(_expand_tex_inputs(tex_path.read_text(encoding="utf-8"), tex_path.parent))
    body, appendix = _split_body_appendix(text)

    body_chars = _cjk_count(body)
    appendix_chars = _cjk_count(appendix)
    # 附录以代码为主，CJK 计数会严重低估它的体量，因此附录占比按字符长度算，
    # 与 paper-structure.md「附录占全文」按提取文本计的口径一致。
    base_dir = tex_path.parent
    body_len = _expanded_length(body, base_dir)
    appendix_len = _expanded_length(appendix, base_dir)
    total_len = body_len + appendix_len

    sections = _section_chars(body)
    return {
        "abstract_chars": _abstract_chars(body),
        "body_chars": body_chars,
        "figures": len(re.findall(r"\\begin\{figure\*?\}", body)),
        "tables": len(re.findall(r"\\begin\{table\*?\}", body)),
        "appendix_ratio": appendix_len / total_len if total_len else 0.0,
        "modeling_ratio": _classify_ratio(sections, _MODELING_KEYWORDS, body_chars),
        "assumption_ratio": _classify_ratio(sections, _ASSUMPTION_KEYWORDS, body_chars),
        "appendix_chars": appendix_chars,
        "sections": [{"title": t, "cjk": n} for t, n in sections],
    }


def _verdict(value: float, bench: dict) -> str:
    if value < bench["low"]:
        return "偏低"
    if value > bench["high"]:
        return "偏高"
    return "达标"


def _fmt(value: float, bench: dict) -> str:
    return f"{value * 100:.1f}%" if bench.get("percent") else f"{value:g}"


def completeness_report(tex_path: str | Path) -> dict:
    """把一份论文的体量指标与官方优秀论文的实测分布逐项对照。

    返回的 ``items`` 每项含 value / median / band / verdict / source，
    ``figures_exceed_tables`` 是一条派生判据：官方 2023 样本 11/14 篇图多于表，
    图成为第一公民；表比图多不算错，但值得回头看看有没有能画的结果被写成了表。
    """
    raw = measure(tex_path)
    items = []
    for key in _ORDER:
        bench = BENCHMARKS[key]
        value = raw[key]
        if bench["low"] is None:
            items.append({"key": key, "label": bench["label"], "value": value,
                          "display": str(value), "median": None, "band": None,
                          "band_display": "口径不同，需 PDF 对标", "median_display": "—",
                          "verdict": "仅测量", "source": bench["source"]})
            continue
        items.append({
            "key": key,
            "label": bench["label"],
            "value": value,
            "display": _fmt(value, bench),
            "median": bench["median"],
            "band": [bench["low"], bench["high"]],
            "band_display": f"{_fmt(bench['low'], bench)}~{_fmt(bench['high'], bench)}",
            "median_display": _fmt(bench["median"], bench),
            "verdict": _verdict(value, bench),
            "source": bench["source"],
        })
    below = [i["label"] for i in items if i["verdict"] == "偏低"]
    return {
        "baseline": "analysis/paper-structure.md 官方优秀论文对照（2023，n=14）",
        "items": items,
        "figures_exceed_tables": raw["figures"] > raw["tables"],
        "below_count": len(below),
        "below": below,
        "measured": {k: v for k, v in raw.items() if k != "sections"},
        "sections": raw["sections"],
    }


def format_text(report: dict) -> str:
    lines = [
        "完备性对标（基准：" + report["baseline"] + "）",
        f"  {'指标':<12}{'本文':>10}{'中位':>10}  {'区间':<18}{'判定'}",
    ]
    for item in report["items"]:
        lines.append(
            f"  {item['label']:<12}{item['display']:>10}{item['median_display']:>10}  "
            f"{item['band_display']:<18}{item['verdict']}"
        )
    lines.append(
        "  图 vs 表      " + ("图多于表，与官方主流一致（11/14 篇）"
                              if report["figures_exceed_tables"]
                              else "表多于图，与官方主流相反（官方 11/14 篇图多于表）")
    )
    if report["below_count"]:
        lines.append("  偏低项：" + "、".join(report["below"]))
    lines.append("  注：此处量的是体量不是质量，达标不代表内容站得住；不检查参考文献条数（官方样本已否定「至少 5 条」）")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="把论文体量与获奖论文实测分布对标")
    parser.add_argument("tex_path", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if not args.tex_path.is_file():
        print(f"找不到论文源文件：{args.tex_path}")
        raise SystemExit(2)
    report = completeness_report(args.tex_path)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else format_text(report))


if __name__ == "__main__":
    main()
