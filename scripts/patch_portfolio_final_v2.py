"""Final portfolio HTML sync with Supplier Lifecycle Copilot (v2)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "assets" / "portfolio" / "SupplyChain_AI产品经理作品集_总览.html"

REPLACEMENTS: list[tuple[str, str]] = [
    (
        "将<strong>供应商全生命周期</strong>五类任务收敛到同一 Copilot",
        "将<strong>供应商全生命周期</strong>六类任务收敛到同一 Copilot",
    ),
    (
        '<h3 style="margin:0;font-size:15px;">情景与风险推演</h3>',
        '<h3 style="margin:0;font-size:15px;">③ 风险复审 &amp; Vendor Rating</h3>',
    ),
    (
        "对「若某区域延误会怎样」一类问题给出影响摘要与行动建议，并可查看支撑取数。",
        "本月 review Strict/Relaxed 兜底；SUP012 评分解释并纠正用户前提。",
    ),
    (
        "<!-- Hub → three branches -->",
        "<!-- Hub → lifecycle branches (Qualification · Vendor Rating · Hybrid 同级分发) -->",
    ),
]

INSERT_AFTER = (
    '          <line x1="940" y1="586" x2="940" y2="614" stroke="#79b4ff" stroke-width="2.75" '
    'stroke-linecap="round" marker-end="url(#arrow)"/>'
)
INSERT_BLOCK = (
    '          <text x="520" y="602" class="flow-note">'
    "+ QualificationNode · VendorRatingNode · HybridNode"
    "</text>"
)

text = HTML_PATH.read_text(encoding="utf-8")
for old, new in REPLACEMENTS:
    if old not in text:
        print("WARN missing:", old[:70])
    else:
        text = text.replace(old, new, 1)

if INSERT_AFTER in text and "QualificationNode" not in text:
    text = text.replace(INSERT_AFTER, INSERT_AFTER + "\n" + INSERT_BLOCK, 1)

HTML_PATH.write_text(text, encoding="utf-8")
print("Patched:", HTML_PATH)
