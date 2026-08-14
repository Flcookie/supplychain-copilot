"""Update portfolio HTML text sections; preserve embedded screenshot base64 lines."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"

lines = HTML_PATH.read_text(encoding="utf-8").splitlines()

# Preserve lines that are huge base64 embeds
def is_embed_line(i: int, line: str) -> bool:
    return len(line) > 500


# Build updated content as line-range replacements (1-based inclusive)
REPLACEMENTS: dict[tuple[int, int], list[str]] = {}

# We'll find line numbers dynamically
def find_line(substr: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if substr in lines[i]:
            return i
    raise ValueError(f"not found: {substr}")


# --- Hero (279-301) ---
hero_start = find_line('<div class="hero">')
hero_end = find_line('<section class="section">', hero_start) - 1

hero_block = """    <div class="hero">
      <div class="badge">AI 产品｜端到端案例 · Ratti 供应商管理</div>
      <h1>Supplier Lifecycle Copilot</h1>
      <div class="subtitle">面向 Ratti 式供应商全生命周期管理的 AI 决策辅助：在同一入口完成<strong>准入清单</strong>、<strong>政策/ESG 问答</strong>、<strong>多指标 KPI 查询</strong>、<strong>风险复审与情景分析</strong>、<strong>Vendor Rating 解释</strong>；回答结构化呈现并可展开 <strong>SQL / 政策引用 / Router 追踪</strong>。</div>
      <div class="quick">
        <div class="quick-card">
          <div class="quick-num">100%</div>
          <div class="quick-label">Ratti 25 条路由评测（LLM 模式）</div>
        </div>
        <div class="quick-card">
          <div class="quick-num">6</div>
          <div class="quick-label">面试 Demo 场景模板</div>
        </div>
        <div class="quick-card">
          <div class="quick-num">9 表</div>
          <div class="quick-label">NL2SQL 白名单 · ratti_copilot_demo.db</div>
        </div>
        <div class="quick-card">
          <div class="quick-num">脱敏</div>
          <div class="quick-label">合成数据 · 无机密供应商记录</div>
        </div>
      </div>
    </div>""".splitlines()

# Section 01 core tasks (316-323)
tasks_start = find_line("<h3>核心任务</h3>")
tasks_end = find_line("</div>", tasks_start + 3)  # end of card - fragile

# Better: replace inner ul of core tasks card
for i in range(tasks_start, tasks_start + 15):
    if "<li>Policy_QA" in lines[i]:
        lines[i] = "            <li>Qualification：新供应商准入路径与文件清单</li>"
    elif "<li>KPI_Query" in lines[i]:
        lines[i] = "            <li>KPI_Query：纱线 OTD、缺陷率等多指标 NL2SQL</li>"
    elif "<li>Scenario" in lines[i]:
        lines[i] = "            <li>Risk / Rating：复审名单、情景推演、评分解释</li>"

# Section 02 jobs (347)
for i in range(len(lines)):
    if "政策问答、KPI查询、风险推演三类任务" in lines[i]:
        lines[i] = "          <div class=\"process-text\">准入清单、政策问答、KPI、风险、评分、复合问题六类任务。</div>"

# Section 03 data model intro + table (366-379)
data_desc = find_line("下表为面向企业化扩展")
lines[data_desc] = (
    '      <p class="desc">基于 Politecnico × Ratti 校企项目逻辑构建的<strong>脱敏合成库</strong> '
    '<code>ratti_copilot_demo.db</code>（9 表只读白名单）。下表为当前 PoC 已落地的核心对象；'
    '证据层统一标注 <code>anonymized Ratti demo database · ratti_copilot_demo.db</code>。</p>'
)

# Replace table tbody - find table after section 03
tbody_start = find_line("<tr><td>supplier_master</td>")
tbody_end = find_line("<tr><td>supplier_kpi_monthly</td>")

new_rows = [
    '          <tr><td>suppliers</td><td>供应商主数据</td><td>supplier_id, category_level_2, kraljic_quadrant, risk_level, qualification_status, next_review_date</td></tr>',
    '          <tr><td>category_rules</td><td>品类准入规则</td><td>category, qualification_path, required_documents</td></tr>',
    '          <tr><td>documents</td><td>合规证书</td><td>document_type, expiry_date, document_status</td></tr>',
    '          <tr><td>purchase_orders</td><td>采购订单</td><td>po_id, supplier_id, order_date, order_amount_eur</td></tr>',
    '          <tr><td>delivery_events</td><td>交付事件</td><td>on_time_flag, delay_days, delivery_date</td></tr>',
    '          <tr><td>quality_events</td><td>质量异常</td><td>defect_rate, severity, non_conformity_type</td></tr>',
    '          <tr><td>risk_events</td><td>风险事件</td><td>risk_score_1_25, event_type</td></tr>',
    '          <tr><td>esg_assessments</td><td>ESG 评估</td><td>esg_score, assessment_date</td></tr>',
    '          <tr><td>vendor_rating</td><td>供应商评分</td><td>rating_class, final_score, operational_score, risk_inverse_score</td></tr>',
]
lines[tbody_start : tbody_end + 1] = new_rows

# Section 04 metrics - add yarn multi-metric row
metrics_end_row = find_line("<tr><td>最近趋势</td>")
lines.insert(
    metrics_end_row + 1,
    '          <tr><td>纱线准时率+缺陷率（2025）</td><td>on_time_delivery_rate_pct + quality_defect_rate_pct</td><td>按供应商聚合 · 多指标同问</td><td>模板 SQL · 不触发误澄清</td></tr>',
)

# Section 05 - update SVG banner text only (small replacements)
for i in range(len(lines)):
    if "SupplyChain Copilot · LangGraph" in lines[i]:
        lines[i] = lines[i].replace(
            "SupplyChain Copilot · LangGraph 决策与降级",
            "Supplier Lifecycle Copilot · LangGraph",
        )
    if "policy · kpi · scenario" in lines[i]:
        lines[i] = lines[i].replace(
            "policy · kpi · scenario",
            "qualification · policy · kpi · risk · rating · hybrid",
        )
    if ">ScenarioNode<" in lines[i]:
        lines[i] = lines[i].replace("ScenarioNode", "RiskNode")
    if "What-if 推演" in lines[i]:
        lines[i] = lines[i].replace("What-if 推演", "复审 / 情景 / HITL")

# grid-3 under architecture (528-541)
arch_cards_start = find_line("<h3>政策问答</h3>", find_line("05 · Architecture"))
arch_cards = """      <div class="grid-3">
        <div class="card">
          <h3>供应商准入</h3>
          <p>规则引擎生成品类路径、Kraljic、必备文件与人工审批提示（Demo 1 首选）。</p>
        </div>
        <div class="card">
          <h3>政策 & KPI</h3>
          <p>RAG 检索 Ratti 政策；KPI 多指标模板 SQL + 结构化 Answer / Evidence / Limitations。</p>
        </div>
        <div class="card">
          <h3>风险 & 评分</h3>
          <p>本月复审 Strict/Relaxed 兜底；Vendor Rating 纠正用户前提并拆解得分驱动因素。</p>
        </div>
      </div>""".splitlines()
# find closing of grid after architecture section
g_start = find_line('<div class="grid-3">', find_line("05 · Architecture"))
g_end = find_line("</section>", g_start)
# only replace first grid-3 in section 05 - the one before section 06
lines[g_start:g_end] = arch_cards + ["    </section>"]
# fix duplicate section close - arch_cards shouldn't include section end
# Actually g_end was </section> - we need g_end to be line before </section>
g_end = find_line("    </section>", g_start)
lines[g_start:g_end] = arch_cards

# Section 06 intro (546-547)
for i in range(len(lines)):
    if "06 · Product Screens" in lines[i]:
        pass
    if i > 0 and "产品与可观测性截图" in lines[i]:
        lines[i] = "      <h2>产品界面（场景模板 + 分层证据）</h2>"
    if "Streamlit 主界面" in lines[i]:
        lines[i] = (
            '      <p class="desc">侧栏 <strong>6 个场景模板</strong>自动填入问题；'
            "回答区展示 <strong>当前任务 / Intent / 置信度</strong>；"
            "业务结论在上，<strong>证据与 Debug 默认折叠</strong>（SQL、Router JSON、引用文档）。</p>"
        )

# Section 07 evidence (612-635)
evidence_desc = find_line("将「结论 + 取数 + 路由」分层展示")
lines[evidence_desc] = (
    '      <p class="desc">三层信息架构：<strong>业务答案</strong>（Summary / Key Findings / Recommended Actions）→ '
    '<strong>Evidence</strong>（数据来源、SQL、行数、指标定义）→ '
    '<strong>Debug</strong>（Router JSON、引用、延迟）。与 Streamlit 折叠区一致。</p>'
)
mono_start = find_line("Intent: KPI_Query", evidence_desc)
mono_block = """      <div class="mono-block">Current Task: vendor_rating_explanation · Confidence: 0.97

Answer Summary
SUP012 received rating B (not C). Final score 77.3; weak OTD 63.6%; strong ESG 86.4.

Evidence
- Data: anonymized Ratti demo database · ratti_copilot_demo.db
- SQL: SELECT ... FROM vendor_rating JOIN suppliers WHERE supplier_id = 'SUP012'
- Rows: 1 · Demo as-of: 2025-12-01

Limitations
Synthetic demo data; buyer validation required before status changes.</div>"""
lines[mono_start] = mono_block

# Section 08 results table
for i in range(len(lines)):
    if "<td>65%</td>" in lines[i] and "意图分类" in lines[i - 2]:
        lines[i] = "            <td>24%（LLM 裸路由）</td>"
    if "90%+</b>" in lines[i] and "意图分类" in "".join(lines[max(0, i - 3) : i]):
        lines[i] = '            <td><b style="color:var(--primary)">100%</b></td>'
        lines[i + 1] = "            <td>Ratti 25 条 lifecycle 评测 · eval/ratti_eval_25.json</td>"
    if "歧义判断是否准确" in lines[i]:
        pass
    if "<td>50%</td>" in lines[i]:
        lines[i] = "            <td>92%（baseline）</td>"
    if "<td><b style=\"color:var(--primary)\">80%</b></td>" in lines[i]:
        lines[i] = '            <td><b style="color:var(--primary)">96%</b></td>'

# Update results desc
for i in range(len(lines)):
    if "基于 RATTI SPA 供应商管理项目实际观察构建的模拟数据集" in lines[i]:
        lines[i] = (
            '      <p class="desc">数据为<strong>基于 Ratti 流程逻辑脱敏合成的演示库</strong>（9 表 + 7 份政策 chunk），'
            "评测集 <code>eval/datasets/ratti_eval_25.json</code> 覆盖准入、KPI、风险、评分、政策、复合问法；"
            "下表为路由优化前后对比（LLM 模式）。</p>"
        )

# Section 09 robustness - add multi-metric and relaxed risk
rob_start = find_line("<li><strong>歧义或未指明的对象", find_line("09 · Robustness"))
lines.insert(
    rob_start + 3,
    "        <li><strong>风险复审无严格匹配：</strong>输出 Strict Match + Relaxed Check + Recommended Actions，避免 Demo「查不到」。</li>",
)
lines.insert(
    rob_start + 4,
    "        <li><strong>多指标 KPI：</strong>同问 OTD+缺陷率时归一化 parse，不误标 need_clarification。</li>",
)

# Section 10 - add qualification and rating edge cases
edge_start = find_line("10 · Edge Cases")
# replace grid content - find grid-4 after edge
eg = find_line('<div class="grid-4">', edge_start)
eg_end = find_line("</section>", eg)
new_edge = """      <div class="grid-4">
        <div class="process-card">
          <div class="process-head">Demo 1</div>
          <div class="process-title">新纱线供应商准入</div>
          <div class="process-text">输出品类、Kraljic、准入路径、必备文件、人工审批 — 最贴 Ratti 主线。</div>
        </div>
        <div class="process-card">
          <div class="process-head">多指标 KPI</div>
          <div class="process-title">OTD + 缺陷率</div>
          <div class="process-text">2025 纱线供应商多指标同问 · 模板 SQL · 标明 demo 样本局限。</div>
        </div>
        <div class="process-card">
          <div class="process-head">风险兜底</div>
          <div class="process-title">本月无 due review</div>
          <div class="process-text">固定 DEMO_CURRENT_DATE=2025-12-01 · 严格匹配为空时给 Relaxed 名单。</div>
        </div>
        <div class="process-card">
          <div class="process-head">评分解释</div>
          <div class="process-title">纠正错误前提</div>
          <div class="process-text">用户说 SUP012 是 C → 系统纠正为 B 并拆解得分驱动与建议动作。</div>
        </div>
      </div>""".splitlines()
lines[eg:eg_end] = new_edge

# Section 11 Phase 1
for i in range(len(lines)):
    if "Phase 1（当前）" in lines[i]:
        idx = i + 1
        if "<p>" in lines[idx]:
            lines[idx] = "          <p>Supplier Lifecycle Copilot PoC：6 场景模板、9 表 NL2SQL、Ratti 政策 RAG、路由 100% 评测、产品化 UI。</p>"

# Title tag
lines[5] = "  <title>Supplier Lifecycle Copilot | Ratti 采购 AI 产品案例</title>"

# Apply hero replacement
lines[hero_start:hero_end + 1] = hero_block

HTML_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("Updated", HTML_PATH)
