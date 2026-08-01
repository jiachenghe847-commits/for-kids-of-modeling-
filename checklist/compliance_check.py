import re
from pathlib import Path


def check_tex(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    issues = []

    if "\\begin{abstract}" not in text:
        issues.append("缺少 abstract 环境（摘要）")

    for match in re.finditer(r"\\begin\{figure\}(.*?)\\end\{figure\}", text, re.DOTALL):
        if "\\caption" not in match.group(1):
            issues.append("存在 figure 环境缺少 \\caption（图注）")

    for match in re.finditer(r"\\begin\{table\}(.*?)\\end\{table\}", text, re.DOTALL):
        if "\\caption" not in match.group(1):
            issues.append("存在 table 环境缺少 \\caption（表注）")

    return {"issues": issues}


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("用法：python checklist/compliance_check.py <论文.tex>")
        sys.exit(2)
    if not Path(sys.argv[1]).is_file():
        print(f"文件不存在：{sys.argv[1]}")
        sys.exit(2)

    result = check_tex(sys.argv[1])
    if result["issues"]:
        print("发现问题：")
        for issue in result["issues"]:
            print(f"  - {issue}")
        sys.exit(1)
    print("未发现问题")
