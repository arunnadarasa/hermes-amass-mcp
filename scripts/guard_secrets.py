#!/usr/bin/env python3
"""Token guard — fail loudly if a secret pattern ever appears in this repo.
Same pattern as hermes-openai-jev / hermes-claude-jev's guard_secrets.py.
Run before every commit/push.
"""
import re
import sys
from pathlib import Path

PATTERNS = [
    r"(?i)AMASS_API_KEY\s*=\s*['\"]?amass_[A-Za-z0-9_\-]{10,}",
    r"(?i)MCP_AMASS_API_KEY\s*=\s*['\"]?amass_[A-Za-z0-9_\-]{10,}",
    r"amass_[A-Za-z0-9]{20,}",  # real keys: no underscores inside the random part, case-mixed
    r"(?i)bearer\s+amass_[A-Za-z0-9_\-]{10,}",
    r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,}",
]

BAD = 0
for p in sorted(Path(".").rglob("*")):
    if p.is_file() and p.suffix in (".md", ".yaml", ".yml", ".json", ".py", ".sh", ".txt"):
        try:
            t = p.read_text(errors="ignore")
        except Exception:
            continue
        for pat in PATTERNS:
            for m in re.finditer(pat, t):
                print(f"SECRET-LIKE: {p}: {m.group(0)[:40]}")
                BAD += 1
print("GUARD:", "FAIL" if BAD else "CLEAN")
sys.exit(1 if BAD else 0)
