import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from appendix_code import appendix_section, collect_sources


def _make_tree(root: Path) -> Path:
    src = root / "src"
    (src / "sub").mkdir(parents=True)
    (src / "model.py").write_text("# 中文注释：σ = std(Δ²y)/√6\nX = 1\n", encoding="utf-8")
    (src / "sub" / "solve.m").write_text("% MATLAB\nx = 1;\n", encoding="utf-8")
    (src / "notes.txt").write_text("不该被收进来\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "model.py").write_text("cached\n", encoding="utf-8")
    return src


def test_collect_sources_skips_noise_and_is_sorted(tmp_path):
    src = _make_tree(tmp_path)
    names = [p.name for p in collect_sources(src)]
    assert names == sorted(names)          # 排序稳定，论文才能逐字节复现
    assert "model.py" in names
    assert "solve.m" in names
    assert "notes.txt" not in names        # 非源码扩展名
    assert all("__pycache__" not in str(p) for p in collect_sources(src))


def test_missing_source_dir_fails_loudly(tmp_path):
    with pytest.raises(FileNotFoundError):
        collect_sources(tmp_path / "nope")


def test_include_path_is_relative_to_the_tex_file_not_the_cwd(tmp_path):
    """\\lstinputlisting 是编译期读文件，路径必须相对 .tex 所在目录。

    paper/ 与 src/ 平级是最常见的布局，此时读取路径应当是 ../src/...
    """
    src = _make_tree(tmp_path)
    tex_dir = tmp_path / "paper"
    tex_dir.mkdir()
    text = appendix_section(src, tex_dir=tex_dir)
    assert "\\codefile{../src/model.py}{Python}{src/model.py}" in text


def test_display_name_stays_short_even_when_include_path_is_long(tmp_path):
    """显示名按源码目录算，不能把一长串 ../ 灌进小节标题。"""
    src = _make_tree(tmp_path)
    tex_dir = tmp_path / "a" / "b" / "c" / "paper"
    tex_dir.mkdir(parents=True)
    text = appendix_section(src, tex_dir=tex_dir)
    assert "\\subsection{\\texttt{src/model.py}}" in text
    assert "\\subsection{\\texttt{../" not in text


def test_language_is_mapped_per_extension(tmp_path):
    src = _make_tree(tmp_path)
    text = appendix_section(src, tex_dir=tmp_path)
    assert "{Python}{src/model.py}" in text
    assert "{Matlab}{src/sub/solve.m}" in text


def test_output_is_deterministic(tmp_path):
    src = _make_tree(tmp_path)
    assert appendix_section(src, tex_dir=tmp_path) == appendix_section(src, tex_dir=tmp_path)


def test_underscore_in_filename_is_escaped_in_the_subsection_title(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "make_figures.py").write_text("pass\n", encoding="utf-8")
    text = appendix_section(src, tex_dir=tmp_path)
    assert "\\subsection{\\texttt{src/make\\_figures.py}}" in text
    # \codefile 内部用 \detokenize，路径原样传，不能被转义
    assert "\\codefile{src/make_figures.py}" in text
