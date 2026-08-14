from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"
lines = p.read_text(encoding="utf-8").splitlines()

replacements = {
    "KPI 查询": (
        "            <h3 style=\"margin:0;font-size:15px;\">① 供应商准入清单</h3>",
        "            <p style=\"margin:6px 0 0; font-size:12px; color:#59708f;\">新纱线供应商 → 品类 / Kraljic / 准入路径 / 必备文件 / 人工审批（Demo 1）。</p>",
    ),
    "政策问答": (
        "            <h3 style=\"margin:0;font-size:15px;\">② 多指标 KPI 查询</h3>",
        "            <p style=\"margin:6px 0 0; font-size:12px; color:#59708f;\">2025 纱线 OTD + 缺陷率 · 结构化 Summary / Evidence / Limitations · 折叠 Debug。</p>",
    ),
    "情景与风险分析": (
        "            <h3 style=\"margin:0;font-size:15px;\">③ 风险复审 & Vendor Rating</h3>",
        "            <p style=\"margin:6px 0 0; font-size:12px; color:#59708f;\">本月 review Strict/Relaxed 兜底；SUP012 评分解释并纠正用户前提。</p>",
    ),
    "链路追踪（LangSmith）": (
        "            <h3 style=\"margin:0;font-size:15px;\">④ 路由与证据（Streamlit）</h3>",
        "            <p style=\"margin:6px 0 0; font-size:12px; color:#59708f;\">Current task + Intent + 置信度；证据 / Debug 分层折叠（可对接 LangSmith trace）。</p>",
    ),
}

for i, line in enumerate(lines):
    for key, (h3, para) in replacements.items():
        if key in line and "<h3" in line:
            lines[i] = h3
            if i + 1 < len(lines) and "<p style" in lines[i + 1]:
                lines[i + 1] = para
            break

for i, line in enumerate(lines):
    if "Supplier 360" in line and "<h3" in line:
        lines[i] = "          <h3 style=\"margin:0 0 8px;font-size:15px;\">技术栈与仓库</h3>"
    if "静态看板示意" in line or "突出「连接 BI" in line:
        lines[i] = (
            "          <p class=\"desc\" style=\"margin:0 0 10px;\">"
            "<strong>LangGraph</strong> 编排 · <strong>Pinecone</strong> 混合检索 · "
            "<strong>SQLite</strong> <code>ratti_copilot_demo.db</code> · "
            "<strong>Streamlit</strong> 双语 UI · 评测 <code>eval/datasets/ratti_eval_25.json</code>。"
            " GitHub: <code>github.com/Flcookie/supplychain-copilot</code></p>"
        )

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("captions patched")
