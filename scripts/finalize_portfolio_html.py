"""Final portfolio HTML patches aligned with Supplier Lifecycle Copilot."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"

lines = HTML_PATH.read_text(encoding="utf-8").splitlines()

for i, line in enumerate(lines):
    if 'id="flowTitle">SupplyChain Copilot' in line:
        lines[i] = line.replace(
            "SupplyChain Copilot LangGraph 工作流",
            "Supplier Lifecycle Copilot LangGraph 工作流",
        )
    if 'id="flowDesc">' in line and "情景、KPI 或政策" in line:
        lines[i] = (
            '          <desc id="flowDesc">歧义 Gate → 置信度 Gate → 六类生命周期意图'
            "（准入 / 政策 / KPI / 风险 / 评分 / 复合）→ Answer；低置信走 Pinecone 兜底。</desc>"
        )
    if "情景与风险推演" in line and "<h3" in line:
        lines[i] = (
            '            <h3 style="margin:0;font-size:15px;">③ 风险复审 &amp; Vendor Rating</h3>'
        )
    if "若某区域延误会怎样" in line or "若某供应商延期" in line:
        lines[i] = (
            '            <p style="margin:6px 0 0; font-size:12px; color:#59708f;">'
            "本月 review Strict/Relaxed 兜底；SUP012 评分解释并纠正用户前提。</p>"
        )

# Replace Supplier 360 mock mono-block card with tech stack summary
start = None
for i, line in enumerate(lines):
    if "技术栈与仓库" in line and "<h3" in line:
        start = i - 1 if lines[i - 1].strip().startswith("<div class=\"card\"") else i
        break

if start is not None:
    end = start
    while end < len(lines) and not (
        lines[end].strip() == "</div>" and end > start + 5
    ):
        end += 1
    # Find closing of outer card (margin-top card)
    depth = 0
    for j in range(start, min(start + 30, len(lines))):
        if "<div" in lines[j]:
            depth += lines[j].count("<div") - lines[j].count("</div>")
        if "</div>" in lines[j]:
            depth -= lines[j].count("</div>")
            if j > start + 8 and depth <= 0:
                end = j
                break

    new_block = """        <div class="card" style="margin-top:10px; border:1px solid var(--line); padding:12px; background:#fff;">
          <h3 style="margin:0 0 8px;font-size:15px;">技术栈与仓库</h3>
          <p class="desc" style="margin:0 0 10px;"><strong>LangGraph</strong> 编排 · <strong>Pinecone</strong> 混合检索 · <strong>SQLite</strong> <code>ratti_copilot_demo.db</code>（9 表只读）· <strong>Streamlit</strong> 双语 UI · 评测 <code>eval/datasets/ratti_eval_25.json</code>。仓库：<a href="https://github.com/Flcookie/supplychain-copilot" style="color:var(--primary);">github.com/Flcookie/supplychain-copilot</a></p>
          <div class="mono-block">core/          → prompts, router_overrides, qualification_rules, demo_constants
graph/         → LangGraph nodes (qualification · policy · kpi · risk · rating · hybrid)
rag/           → Pinecone retriever (Ratti policies + legacy docs)
tools/         → kpi_sql_builder, SQL whitelist executor
app/ui.py      → 6 scenario templates · structured answer · collapsed Evidence/Debug
eval/          → ratti_eval_25 router eval · ratti_e2e_smoke KPI templates</div>
        </div>""".splitlines()
    lines[start : end + 1] = new_block

HTML_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Portfolio finalized:", HTML_PATH)
