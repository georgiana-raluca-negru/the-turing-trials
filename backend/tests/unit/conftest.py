from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
LLM_ROOT = BACKEND_ROOT / "llm_functionality"

for path in (BACKEND_ROOT, LLM_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
