import re
from pathlib import Path


_IDENTITY_LABELS = re.compile(
    r"学校名称|所在学校|队员姓名|参赛(?:队)?编号|参赛队号|指导教师"
)
_AI_TOOL_NAMES = re.compile(
    r"Codex|ChatGPT|Claude|Gemini|Copilot|文心一言|通义千问|豆包|DeepSeek",
    re.IGNORECASE,
)
_AI_ORGANIZATIONS = re.compile(
    r"OpenAI|Anthropic|Google|Microsoft|百度|阿里|字节跳动|深度求索|DeepSeek",
    re.IGNORECASE,
)


def _strip_comments(text: str) -> str:
    """去掉 LaTeX 注释，避免注释里的模板提示被当成正文。"""
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def _has_nonempty_command(text: str, command: str) -> bool:
    match = re.search(rf"\\{command}\s*\{{(.*?)\}}", text, re.DOTALL)
    return bool(match and match.group(1).strip())


def _check_ai_disclosure(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text)
    no_ai = bool(re.search(r"本参赛队未使用任何(?:生成式)?AI工具", compact, re.IGNORECASE))
    has_heading = bool(re.search(r"AI工具使用声明", compact, re.IGNORECASE))
    used_ai = has_heading and bool(re.search(r"使用|借助", compact)) and bool(_AI_TOOL_NAMES.search(text))

    if no_ai:
        return []
    if not used_ai:
        return ["缺少 AI 工具使用声明（已使用则披露；未使用则明确声明）"]

    bibliography = re.search(
        r"\\begin\{thebibliography\}(.*?)\\end\{thebibliography\}", text, re.DOTALL
    )
    bibliography_text = bibliography.group(1) if bibliography else ""
    has_tool_reference = bool(_AI_TOOL_NAMES.search(bibliography_text))
    has_date = bool(re.search(r"20\d{2}[-年/.]\d{1,2}", bibliography_text))
    has_version = bool(
        re.search(
            r"\b\d+(?:\.\d+)+\b|GPT-\d|Claude\s+\d|Gemini\s+\d|版本|型号",
            bibliography_text,
            re.IGNORECASE,
        )
    )
    has_organization = bool(_AI_ORGANIZATIONS.search(bibliography_text))
    if not (has_tool_reference and has_version and has_organization and has_date):
        return ["已声明使用 AI，但参考文献中缺少工具名称、版本/型号、机构或使用日期"]
    return []


def check_tex(path: str) -> dict:
    text = _strip_comments(Path(path).read_text(encoding="utf-8"))
    issues = []

    if "\\begin{abstract}" not in text:
        issues.append("缺少 abstract 环境（摘要）")

    for environment, label in (("figure", "图注"), ("table", "表注")):
        pattern = rf"\\begin\{{{environment}\*?\}}(.*?)\\end\{{{environment}\*?\}}"
        for match in re.finditer(pattern, text, re.DOTALL):
            if "\\caption" not in match.group(1):
                issues.append(f"存在 {environment} 环境缺少 \\caption（{label}）")

    if _has_nonempty_command(text, "author"):
        issues.append("\\author 不为空，可能暴露队员身份")
    if _has_nonempty_command(text, "institute"):
        issues.append("\\institute 不为空，可能暴露学校信息")
    if re.search(r"pdfauthor\s*=\s*\{?\s*[^},\s]", text, re.IGNORECASE):
        issues.append("PDF 元数据 pdfauthor 不为空，可能暴露队员身份")
    if _IDENTITY_LABELS.search(text):
        issues.append("正文中存在学校/队员/参赛编号等明确身份字段")

    issues.extend(_check_ai_disclosure(text))

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
