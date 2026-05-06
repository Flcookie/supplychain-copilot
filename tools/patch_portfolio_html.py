"""Patch portfolio HTML: Data Model, Metrics, Evidence, Supplier 360; renumber sections."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "SupplyChain_AI产品经理作品集_总览.html"

DATA_MODEL = r"""
    <section class="section">
      <div class="section-tag">03 · Data Model｜采购数据对象设计</div>
      <h2>数据对象与可查询边界</h2>
      <p class="desc">下表为面向企业化扩展的数据对象设计，用于 NL2SQL 与企业指标口径对齐。<strong>当前 PoC</strong> 在 SQLite 中以 <code>suppliers</code> / <code>purchase_orders</code> 承载核心 KPI 路径，实体命名与下表中的 <code>supplier_master</code> / <code>purchase_order</code> 概念一致；其余对象表示目标模型与指标延展。</p>
      <table>
        <thead>
          <tr><th>数据对象</th><th>业务含义</th><th>核心字段</th></tr>
        </thead>
        <tbody>
          <tr><td>supplier_master</td><td>供应商主数据</td><td>supplier_id, supplier_name, category, country, status, risk_level</td></tr>
          <tr><td>purchase_order</td><td>采购订单</td><td>po_id, supplier_id, order_date, promised_date, amount</td></tr>
          <tr><td>delivery_record</td><td>交付记录</td><td>delivery_id, po_id, supplier_id, actual_date, delay_days</td></tr>
          <tr><td>quality_issue</td><td>质量异常</td><td>issue_id, supplier_id, issue_type, severity, defect_qty</td></tr>
          <tr><td>audit_record</td><td>审核记录</td><td>audit_id, supplier_id, audit_score, expiry_date</td></tr>
          <tr><td>risk_event</td><td>风险事件</td><td>event_id, supplier_id, event_type, impact_level, created_date</td></tr>
          <tr><td>supplier_kpi_monthly</td><td>月度 KPI 汇总</td><td>supplier_id, month, on_time_rate, defect_rate, avg_delay_days, risk_score</td></tr>
        </tbody>
      </table>
    </section>

    <section class="section">
      <div class="section-tag">04 · Metrics Layer｜指标口径与自然语言映射</div>
      <h2>自然语言 → 指标口径</h2>
      <p class="desc">说明用户问「表现怎么样」时系统指向哪些指标与默认时间窗；与仓库内 <code>data/metrics_dictionary.json</code> 及 KPI 前置结构化解析一致。</p>
      <table>
        <thead>
          <tr><th>用户自然语言</th><th>映射指标</th><th>口径说明</th><th>默认处理</th></tr>
        </thead>
        <tbody>
          <tr><td>交付表现怎么样</td><td>on_time_rate + avg_delay_days</td><td>准时交付率 + 平均延误天数</td><td>默认近 3 个月</td></tr>
          <tr><td>准时交付率</td><td>on_time_rate</td><td>准时交付订单数 / 总交付订单数</td><td>若缺时间则追问</td></tr>
          <tr><td>质量表现怎么样</td><td>defect_rate + quality_issue_count</td><td>缺陷率 + 质量异常数量</td><td>默认近 3 个月</td></tr>
          <tr><td>风险高不高</td><td>risk_score</td><td>交付、质量、审核、风险事件加权评分</td><td>展示风险原因</td></tr>
          <tr><td>最近趋势</td><td>recent_trend</td><td>按月查看 KPI 变化</td><td>默认近 3 个月</td></tr>
        </tbody>
      </table>
    </section>
"""

EVID = r"""
    <section class="section">
      <div class="section-tag">07 · Evidence Drawer｜回答依据展开区</div>
      <h2>可信与可审计输出</h2>
      <p class="desc">将「结论 + 取数 + 路由」分层展示，对应 Streamlit 中的执行证据与路由 JSON；面试时可强调：<strong>SQL 可验证、指标可追溯、Router 可复盘</strong>。</p>
      <div class="evidence-rows">
        <div class="card">
          <h3>Answer</h3>
          <p>自然语言结论（业务可读）</p>
        </div>
        <div class="card">
          <h3>Evidence</h3>
          <p>KPI：展示 SQL、数据范围与关键字段；政策：文档引用与段落定位。</p>
        </div>
        <div class="card">
          <h3>Trace</h3>
          <p>Intent、confidence、是否触发追问/兜底（可与 LangSmith 对齐）。</p>
        </div>
      </div>
      <div class="mono-block">Intent: KPI_Query
Metric: on_time_rate
Entity: Supplier A
Time Range: 2026-02 ~ 2026-04
SQL: SELECT month, on_time_rate FROM supplier_kpi_monthly WHERE supplier_id = ? ...
Data Source: supplier_kpi_monthly
Policy Citation: Supplier Evaluation Policy, Section 3.2</div>
    </section>

"""

S360 = r"""
        <div class="card" style="margin-top:10px; border:1px solid var(--line); padding:12px; background:#fff;">
          <h3 style="margin:0 0 8px;font-size:15px;">Supplier 360｜供应商绩效摘要（示意）</h3>
          <p class="desc" style="margin:0 0 10px;">静态版面示例：突出「智能 BI + 分析摘要」，PoC 未单独做该页路由。</p>
          <div class="mono-block">Supplier A

KPI Overview
- On-time Delivery Rate: 87%
- Avg Delay Days: 2.4 days
- Defect Rate: 1.8%
- Risk Score: 72 / 100
- Audit Status: Valid, 42 days before expiry

AI Summary
过去 3 个月 Supplier A 的交付稳定性下降，主要由 4 月延误订单增加导致。
质量缺陷率保持低位，但风险分因交付延误与审核临近过期而上升。
建议采购经理优先跟进交付计划，并确认下一轮审核安排。

Evidence
- SQL: SELECT ... FROM purchase_orders JOIN suppliers ...
- Data Range: 2026-02 ~ 2026-04
- Policy Citation: Supplier Evaluation Policy - Section 3.2</div>
        </div>
"""


def main() -> None:
    s = HTML.read_text(encoding="utf-8")
    if "03 · Data Model" in s:
        print("Already patched (Data Model present); abort")
        return

    mark1 = (
        '      <p class="desc" style="margin-top:10px;"><strong>P0 能力：</strong>'
        "按意图分发到政策检索 / KPI 查询 / 情景分析；不完整问题先追问不盲答；"
        "置信不足时宽泛检索兜底；答案必须带引用段落或结构化查询摘要，便于复核。</p>\n"
        "    </section>\n\n"
        '    <section class="section">\n'
        '      <div class="section-tag">03 · Architecture</div>'
    )
    repl1 = (
        '      <p class="desc" style="margin-top:10px;"><strong>P0 能力：</strong>'
        "按意图分发到政策检索 / KPI 查询 / 情景分析；不完整问题先追问不盲答；"
        "置信不足时宽泛检索兜底；答案必须带引用段落或结构化查询摘要，便于复核。</p>\n"
        "    </section>\n"
        + DATA_MODEL
        + '\n    <section class="section">\n'
        '      <div class="section-tag">05 · Architecture & Workflow</div>'
    )
    if mark1 not in s:
        raise SystemExit("Anchor P0/Architecture not found")
    s = s.replace(mark1, repl1, 1)

    s = s.replace("02 · Scope</div>", "02 · Scope & User Jobs</div>", 1)
    s = s.replace("04 · Product Screens</div>", "06 · Product Screens</div>", 1)
    s = s.replace("05 · Results</div>", "08 · Results</div>", 1)
    s = s.replace("06 · Robustness</div>", "09 · Robustness</div>", 1)
    s = s.replace("07 · Edge Cases</div>", "10 · Edge Cases</div>", 1)
    s = s.replace("08 · Roadmap</div>", "11 · Roadmap</div>", 1)

    mark2 = (
        "    </section>\n\n"
        '    <section class="section">\n'
        '      <div class="section-tag">08 · Results</div>'
    )
    repl2 = (
        "    </section>\n"
        + EVID
        + '    <section class="section">\n'
        '      <div class="section-tag">08 · Results</div>'
    )
    if mark2 not in s:
        raise SystemExit("Anchor before Results not found")
    s = s.replace(mark2, repl2, 1)

    lang = "链路追踪（LangSmith）"
    i = s.find(lang)
    if i == -1:
        raise SystemExit("LangSmith heading not found")
    fig = s.find("</figure>", i)
    shot_close = s.find("\n      </div>\n    </section>", fig)
    if shot_close == -1:
        raise SystemExit("shot-grid close not found")
    s = s[:shot_close] + S360 + s[shot_close:]

    css_marker = "    @media print {\n"
    css_insert = """    .mono-block {
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11px;
      line-height: 1.45;
      background: #0a0e17;
      color: #c9d7e8;
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid #263247;
      overflow-x: auto;
      margin-top: 8px;
      white-space: pre-wrap;
    }
    .evidence-rows {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 10px;
    }

"""
    if ".mono-block {" not in s:
        s = s.replace(css_marker, css_insert + css_marker, 1)

    mq = "      .grid-3, .grid-4, .grid-2 { grid-template-columns: 1fr; }\n"
    ext = "      .grid-3, .grid-4, .grid-2 { grid-template-columns: 1fr; }\n      .evidence-rows { grid-template-columns: 1fr; }\n"
    if mq in s and "evidence-rows { grid-template-columns: 1fr }" not in s.replace(" ", ""):
        s = s.replace(mq, ext, 1)

    HTML.write_text(s, encoding="utf-8")
    print("OK", HTML)


if __name__ == "__main__":
    main()
