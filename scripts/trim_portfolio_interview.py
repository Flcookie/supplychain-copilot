"""Trim portfolio HTML for interview; keep Streamlit + LangSmith, remove unimplemented blocks."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"
OUT = HTML  # overwrite in place when unlocked; fallback below


def remove_block(text: str, start_marker: str, end_marker: str) -> str:
    i = text.find(start_marker)
    if i == -1:
        raise ValueError(f"start not found: {start_marker[:60]}")
    j = text.find(end_marker, i + len(start_marker))
    if j == -1:
        raise ValueError(f"end not found after: {start_marker[:60]}")
    return text[:i] + text[j:]


def main() -> None:
    s = HTML.read_text(encoding="utf-8")

    # Fake Supplier 360 card — not implemented
    s = remove_block(
        s,
        '        <div class="card" style="margin-top:10px; border:1px solid var(--line); padding:12px; background:#fff;">\n'
        '          <h3 style="margin:0 0 8px;font-size:15px;">技术栈与仓库</h3>',
        "\n      </div>\n    </section>\n\n    <section class=\"section\">\n"
        '      <div class="section-tag">07 · Evidence Drawer',
    )

    # Commercialization pricing — not relevant for interview portfolio
    s = remove_block(
        s,
        '        <div class="card">\n          <h3>若产品化可考虑的切入点</h3>',
        '        <div class="card">\n          <h3>主要风险与应对</h3>',
    )

    replacements = [
        (
            "典型政策查询从跨系统翻找约 15 分钟压缩到 30 秒响应，减少检索往返成本",
            "政策与 KPI 查询收敛为自然语言一步操作，减少跨系统检索往返",
        ),
        (
            "（9 表 + 7 份政策 chunk）",
            "（9 表 + 政策/合同/SOP 文档语料）",
        ),
        (
            "Supplier Lifecycle Copilot PoC：6 场景模板、9 表 NL2SQL、Ratti 政策 RAG、路由 100% 评测、产品化 UI。",
            "Supplier Lifecycle Copilot PoC：6 场景模板、9 表 NL2SQL、Ratti 政策 RAG、路由 100% 离线评测、Streamlit Demo + LangSmith 链路追踪。",
        ),
        (
            "顺序与取舍取决于客户访谈、漏斗数据与法务交付约束；路线图与前文架构示意图仅表达思考框架，不作为固定排期承诺。",
            "Phase 2/3 为延展方向，不作为本 PoC 交付范围。",
        ),
    ]
    for old, new in replacements:
        if old not in s:
            raise ValueError(f"missing replacement target: {old[:50]}")
        s = s.replace(old, new, 1)

    # Remove redundant Section 02 (duplicates Section 01)
    s = remove_block(
        s,
        '    <section class="section">\n'
        '      <div class="section-tag">02 · Scope & User Jobs</div>',
        '    </section>\n\n'
        '    <section class="section">\n'
        '      <div class="section-tag">03 · Data Model',
    )

    renumber = [
        ("03 · Data Model", "02 · Data Model"),
        ("04 · Metrics Layer", "03 · Metrics Layer"),
        ("05 · Architecture", "04 · Architecture"),
        ("06 · Product Screens", "05 · Product Screens"),
        ("07 · Evidence Drawer", "06 · Evidence Drawer"),
        ("08 · Results", "07 · Results"),
        ("09 · Robustness", "08 · Robustness"),
        ("10 · Edge Cases", "09 · Edge Cases"),
        ("11 · Roadmap", "10 · Roadmap"),
    ]
    for old, new in renumber:
        s = s.replace(old, new, 1)

    try:
        OUT.write_text(s, encoding="utf-8")
        print(f"OK — updated {OUT.name} ({len(s):,} chars)")
    except PermissionError:
        fallback = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_面试版.html"
        fallback.write_text(s, encoding="utf-8")
        print(f"WARN — {OUT.name} locked; wrote {fallback.name}")


if __name__ == "__main__":
    main()
