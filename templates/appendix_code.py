"""把源码目录渲染成论文附录的「程序代码」一节。

**为什么要有这个**：官方 2023 年 14 篇优秀论文实测，附录占全文 27.6%~72.1%（中位 49.9%），
内容以全量代码为主（见 `analysis/paper-structure.md`）。2025 B 题演练的论文在这一节只写了
「见支撑材料 src/ 目录」，附录占比接近 0——16 页对 67~72 页的差距，一多半出在这里。
代码本来就写好了，不放进附录纯属白丢。

**用法**：在论文生成器里调用 `appendix_section(...)`，把返回的 LaTeX 片段拼进 .tex；
排版依赖 `templates/cumcm-paper.sty` 里的 `\\codefile` 宏与 `cumcmcode` 样式。

```python
from appendix_code import appendix_section
tex += appendix_section(src_dir="../src", tex_dir="paper", title="程序代码")
```

**注意**：`\\lstinputlisting` 是编译期读文件，所以路径必须是**相对 .tex 文件所在目录**的，
不是相对生成器的工作目录。`tex_dir` 参数就是为此存在的。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# 扩展名 → listings 的 language 名。listings 不认识的语言用空串，退化成纯等宽排版。
LANGUAGES = {
    ".py": "Python",
    ".m": "Matlab",
    ".r": "R",
    ".R": "R",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C",
    ".java": "Java",
    ".jl": "Julia",
    ".sql": "SQL",
    ".sh": "bash",
}
DEFAULT_PATTERNS = ("*.py", "*.m", "*.r", "*.R", "*.jl", "*.c", "*.cpp", "*.java")
# 附录要的是自己写的模型代码，不是环境垃圾
EXCLUDE_DIRS = {"__pycache__", ".venv", ".git", ".pytest_cache", "node_modules"}


def collect_sources(src_dir: str | Path, patterns: tuple[str, ...] = DEFAULT_PATTERNS) -> list[Path]:
    """按扩展名收集源码文件，路径排序保证输出稳定（论文要逐字节可复现）。"""
    src_dir = Path(src_dir)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"源码目录不存在：{src_dir}")
    found: set[Path] = set()
    for pattern in patterns:
        for path in src_dir.rglob(pattern):
            if path.is_file() and not (set(path.parts) & EXCLUDE_DIRS):
                found.add(path)
    return sorted(found)


def _language(path: Path) -> str:
    return LANGUAGES.get(path.suffix, "")


def _escape(text: str) -> str:
    """把路径里的 LaTeX 特殊字符转义，用于 caption 之外的普通文本。"""
    for char in ("\\", "_", "%", "&", "#", "$", "{", "}"):
        text = text.replace(char, "\\" + char)
    return text


def appendix_section(
    src_dir: str | Path,
    tex_dir: str | Path = ".",
    title: str = "程序代码",
    intro: str | None = None,
    patterns: tuple[str, ...] = DEFAULT_PATTERNS,
) -> str:
    """生成 ``\\section{程序代码}`` 加逐文件的 ``\\codefile`` 清单。

    参数
    ----
    src_dir : 源码目录（相对当前工作目录或绝对路径）
    tex_dir : .tex 文件所在目录——``\\lstinputlisting`` 的路径按它来算
    intro   : 小节开头的说明段；传 None 用默认文案

    返回的字符串可直接拼进 .tex。文件按路径排序，因此同样的输入产出同样的字节。
    """
    sources = collect_sources(src_dir, patterns)
    tex_dir = Path(tex_dir).resolve()

    lines = [f"\\section{{{title}}}", ""]
    if intro is None:
        total = sum(p.stat().st_size for p in sources)
        intro = (
            f"本节列出全部 {len(sources)} 个源码文件（共 {total / 1024:.1f} KB），"
            "与支撑材料中的文件逐字节一致，可直接运行复现正文全部结果。"
        )
    if intro:
        lines += [intro, ""]

    root = Path(src_dir).resolve()
    for path in sources:
        # 读取路径按 .tex 所在目录算（\lstinputlisting 是编译期读文件），
        # 显示名按源码目录算——前者可能是一长串 ../，不该出现在小节标题里。
        include = Path(os.path.relpath(path.resolve(), tex_dir)).as_posix()
        display = f"{root.name}/{path.resolve().relative_to(root).as_posix()}"
        lines.append(f"\\subsection{{\\texttt{{{_escape(display)}}}}}")
        lines.append(f"\\codefile{{{include}}}{{{_language(path)}}}{{{display}}}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="把源码目录渲染成论文附录的程序代码一节")
    parser.add_argument("src_dir", type=Path, help="源码目录")
    parser.add_argument("--tex-dir", type=Path, default=Path("."), help=".tex 文件所在目录")
    parser.add_argument("--title", default="程序代码")
    parser.add_argument("-o", "--output", type=Path, help="写入文件；不给就打到标准输出")
    args = parser.parse_args()
    text = appendix_section(args.src_dir, args.tex_dir, args.title)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"已写入 {args.output}（{len(text)} 字符）")
    else:
        print(text)


if __name__ == "__main__":
    main()
