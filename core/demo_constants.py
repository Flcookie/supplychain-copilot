"""Fixed demo parameters for reproducible SQL time windows and evidence labels."""

import os

RATTI_DATA_SNAPSHOT = "anonymized Ratti demo database · ratti_copilot_demo.db"

# Anchor calendar logic for certificate expiry / review-due queries (override via env).
DEMO_CURRENT_DATE = os.getenv("DEMO_CURRENT_DATE", "2025-12-01")
