"""Further simplify portfolio HTML for interview — keep hero, flow, screenshots, key metrics."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_面试版.html"
if not SRC.exists():
    SRC = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"
OUT = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_面试版.html"
OUT_ORIG = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"


def remove_block(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i == -1:
        raise ValueError(f"start not found: {start[:70]}")
    j = text.find(end, i + len(start))
    if j == -1:
        raise ValueError(f"end not found after: {start[:70]}")
    return text[:i] + text[j:]


def main() -> None:
    s = SRC.read_text(encoding="utf-8")

    # Fix stray closing tag from prior trim
    s = s.replace("    </section>\n\n    </section>\n\n    <section", "    </section>\n\n    <section", 1)

    # 01 — drop role/task/value cards; one short paragraph
    s = remove_block(
        s,
        '      <div class="grid-3">\n        <div class="card">\n          <h3>用户角色</h3>',
        "    </section>\n\n    <section class=\"section\">\n      <div class=\"section-tag\">02 · Data Model",
    )
    s = s.replace(
        "适合 AI 产品经理面试 Demo。</p>",
        "回答带 SQL / 政策引用 / LangSmith 链路追踪，可现场 Demo。</p>",
        1,
    )

    # Remove data model + metrics (too granular for PM portfolio)
    s = remove_block(
        s,
        '    <section class="section">\n      <div class="section-tag">02 · Data Model',
        '    <section class="section">\n      <div class="section-tag">04 · Architecture',
    )

    # Architecture — drop three intent summary cards under the diagram
    s = remove_block(
        s,
        '      <div class="grid-3">\n        <div class="card">\n          <h3>供应商准入</h3>',
        '    </section>\n\n    <section class="section">\n      <div class="section-tag">05 · Product Screens',
    )

    # Renumber architecture tag before screenshots
    s = s.replace("04 · Architecture & Workflow", "02 · Architecture", 1)
    s = s.replace("05 · Product Screens", "03 · Product Screens", 1)

    # Screens — shorter intro
    s = s.replace(
        '      <p class="desc">侧栏 <strong>6 个场景模板</strong>自动填入问题；回答区展示 <strong>当前任务 / Intent / 置信度</strong>；业务结论在上，<strong>证据与 Debug 默认折叠</strong>（SQL、Router JSON、引用文档）。以下为界面截图（流程见 §05）。</p>',
        '      <p class="desc">Streamlit 侧栏 <strong>6 个场景模板</strong>一键填入；结论在上，证据与 LangSmith trace 可展开复核。</p>',
        1,
    )

    # Remove evidence drawer (redundant with screenshot ④)
    s = remove_block(
        s,
        '    <section class="section">\n      <div class="section-tag">06 · Evidence Drawer',
        '    <section class="section">\n      <div class="section-tag">07 · Results',
    )

    # Simplify results table — keep 2 headline metrics only
    s = remove_block(
        s,
        '          <tr>\n            <td>追问触发占比</td>',
        "        </tbody>\n      </table>\n",
    )
    s = s.replace(
        '      <p class="desc">数据为<strong>基于 Ratti 流程逻辑脱敏合成的演示库</strong>（9 表 + 政策/合同/SOP 文档语料），评测集 <code>eval/datasets/ratti_eval_25.json</code> 覆盖准入、KPI、风险、评分、政策、复合问法；下表为路由优化前后对比（LLM 模式）。</p>',
        '      <p class="desc">离线评测集 25 条（准入 / KPI / 风险 / 评分 / 政策 / 复合问法），路由规则迭代前后对比如下。</p>',
        1,
    )
    s = s.replace(
        '      <p class="desc" style="margin-top:10px;">当前为概念验证阶段，通过离线固定问句集验证路由机制的可迭代性；下一阶段目标是接入真实数据源获取线上指标。</p>\n    </section>',
        "    </section>",
        1,
    )
    s = s.replace("07 · Results", "04 · Results", 1)

    # Remove robustness, edge cases, roadmap entirely
    s = remove_block(
        s,
        '    <section class="section">\n      <div class="section-tag">08 · Robustness',
        "  </div>\n</body>",
    )

    # Hero — tighten subtitle
    s = s.replace(
        '<div class="subtitle">面向 Ratti 式供应商全生命周期管理的 AI 决策辅助：在同一入口完成<strong>准入清单</strong>、<strong>政策/ESG 问答</strong>、<strong>多指标 KPI 查询</strong>、<strong>风险复审与情景分析</strong>、<strong>Vendor Rating 解释</strong>；回答结构化呈现并可展开 <strong>SQL / 政策引用 / Router 追踪</strong>。</div>',
        '<div class="subtitle">Ratti 供应商全生命周期 Copilot：准入 · 政策 · KPI · 风险 · 评分，同一入口自然语言问答；Streamlit Demo + LangGraph 路由 + LangSmith 追踪。</div>',
        1,
    )

    for target in (OUT, OUT_ORIG):
        try:
            target.write_text(s, encoding="utf-8")
            print(f"OK — {target.name} ({len(s):,} chars, ~{s.count(chr(10))+1} lines)")
            break
        except PermissionError:
            continue
    else:
        raise SystemExit("All targets locked")


if __name__ == "__main__":
    main()
