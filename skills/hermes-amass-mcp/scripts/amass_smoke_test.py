#!/usr/bin/env python3
"""Live, content-verified smoke test for the Amass REST API / MCP wiring.

A 200 with an empty data array is a FAIL, not a pass — same discipline as
the sibling hermes-openai-jev / hermes-claude-jev smoke tests. Reads
AMASS_API_KEY from the environment (source the target profile's .env
first); never prints the key.
"""
import json
import os
import ssl
import sys
import urllib.request
import urllib.error

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = None  # fall back to the interpreter's default trust store

BASE = "https://api.amass.tech/api/v1"


def _get(path: str):
    key = os.environ.get("AMASS_API_KEY")
    if not key:
        print("FAIL: AMASS_API_KEY not set in environment", file=sys.stderr)
        sys.exit(2)
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:
            headers = dict(resp.headers)
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, headers, body
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode("utf-8")) if e.fp else {}
        return e.code, dict(e.headers or {}), body


def check(name, condition, detail=""):
    condition = bool(condition)
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    return condition


def main():
    results = []

    # 1. BiomedCore
    status, _, body = _get("/cores/biomedcore/records?query=endometriosis&limit=2")
    data = body.get("data", [])
    ok = status == 200 and len(data) > 0 and data[0].get("title") and (data[0].get("pmid") or data[0].get("doi"))
    results.append(check(
        "BiomedCore search (real records, title + pmid/doi present)",
        ok,
        f"status={status} n={len(data)} title={data[0].get('title','')[:60] if data else None!r}",
    ))

    # 2. TrialCore
    status, _, body = _get("/cores/trialcore/records?query=endometriosis&limit=1")
    data = body.get("data", [])
    ok = status == 200 and len(data) > 0 and any(k in data[0] for k in ("nctId", "amassId"))
    results.append(check(
        "TrialCore search (real trial record)",
        ok,
        f"status={status} n={len(data)}",
    ))

    # 3. DrugCore
    status, _, body = _get("/cores/drugcore/records?query=dienogest&limit=1")
    data = body.get("data", [])
    ok = status == 200 and len(data) > 0 and "dienogest" in json.dumps(data[0]).lower()
    results.append(check(
        "DrugCore search (query term appears in matched record)",
        ok,
        f"status={status} n={len(data)}",
    ))

    # 4. Rate-limit headers present
    status, headers, _ = _get("/cores/genecore/records?query=BRCA1&limit=1")
    header_keys = {k.lower() for k in headers}
    ok = status == 200 and {"x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"} <= header_keys
    results.append(check(
        "Rate-limit headers present on response",
        ok,
        f"status={status}",
    ))

    # 5. Credits endpoint
    status, _, body = _get("/credits/api-credits")
    remaining = body.get("data", {}).get("remaining")
    ok = status == 200 and isinstance(remaining, (int, float))
    results.append(check(
        "Credits endpoint returns a numeric remaining balance",
        ok,
        f"status={status} remaining={remaining}",
    ))

    print()
    passed = sum(results)
    print(f"RESULT: {passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
