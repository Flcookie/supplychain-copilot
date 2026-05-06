"""One-off: inline assets/portfolio PNGs as data URIs into the portfolio HTML."""
from __future__ import annotations

import base64
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = ROOT / "SupplyChain_AI产品经理作品集_总览.html"
PORT = ROOT / "assets" / "portfolio"

FILES = [
    "ui-streamlit-conversation-zh.png",
    "ui-streamlit-policy-qa-en.png",
    "ui-streamlit-scenario-analysis-en.png",
    "obs-langsmith-trace-studio.png",
]


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    for name in FILES:
        rel = f"assets/portfolio/{name}"
        path = PORT / name
        if rel not in html:
            raise SystemExit(f"Missing src reference: {rel}")
        raw = path.read_bytes()
        b64 = base64.standard_b64encode(raw).decode("ascii")
        uri = f"data:image/png;base64,{b64}"
        html = html.replace(f'src="{rel}"', f'src="{uri}"', 1)
    HTML.write_text(html, encoding="utf-8")
    print("Embedded", len(FILES), "images into", HTML.name)


if __name__ == "__main__":
    main()
