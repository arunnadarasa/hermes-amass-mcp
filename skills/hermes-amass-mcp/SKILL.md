---
name: hermes-amass-mcp
description: "Wire Amass (biomedical/trials/drug/gene/patent) MCP into Hermes."
version: 1.0.0
---

# Hermes Amass MCP

Wires the Amass life-sciences data platform (https://amass.tech) into Hermes
as a remote HTTP MCP server, giving the agent 14 first-class tools across
six "Cores": biomedical literature, clinical trials, FDA/EMA regulatory
authorizations, drugs/molecules, genes, and patents (preview). Verified live
2026-10-02 against `api.amass.tech/api/v1` and `mcp.amass.tech/mcp`.

## 1. What Amass provides

Six Cores, each with a `search` + `get`-by-id pattern, cross-linked:

| Core | Records | Status |
|---|---|---|
| BiomedCore | 43M+ PubMed/PMC citations + conference abstracts | Available |
| TrialCore | 1.2M+ trials (ClinicalTrials.gov + WHO ICTRP) | Available |
| DrugCore | 22K+ harmonized drugs/molecules (ChEMBL) | Available |
| RegulatoryCore | FDA + EMA authorizations, unified schema | Available |
| GeneCore | 43K+ genes (HGNC + NCBI Gene) | Available |
| PatentCore | Patent publications, full text, CPC/IPC | Preview |

Records link across Cores (a drug → its trials → its literature → its
regulatory authorizations), and BiomedCore records carry citation counts,
JuFo journal-quality tier, retraction status, and MeSH terms — genuinely
useful filters for evidence triage, not just keyword search.

## 2. Wiring into Hermes (remote HTTP MCP, header auth)

### Key storage
- Amass issues a plain API key (`amass_...`), not OAuth-only — despite the
  marketing site (`amass.tech/mcp`) pushing the one-click OAuth connector
  flow for Claude/ChatGPT, the platform docs
  (`platform.amass.tech/documentation/getting-started/overview`) describe a
  standard Bearer-token REST API. **Prefer header auth over OAuth**: it's
  non-interactive, works headless, and the same key also powers direct REST
  calls (useful for a pre-wiring smoke test before trusting the MCP layer).
- Store as `AMASS_API_KEY` (your own copy) AND `MCP_AMASS_API_KEY` (the name
  Hermes's `hermes mcp add --auth header` convention expects —
  `MCP_<NAME_UPPER>_API_KEY`, confirmed in `hermes_cli/mcp_config.py`
  `_env_key_for_server`) in every profile's `.env` that needs it. Each
  Hermes profile has its OWN `.env` — a key in the default profile's `.env`
  does NOT propagate to `profiles/<name>/.env`.
- Copy without ever printing the value:
  ```bash
  for f in ~/.hermes/.env ~/.hermes/profiles/<name>/.env; do
    val=$(grep "^AMASS_API_KEY=" "$f" | cut -d= -f2-)
    [ -n "$val" ] && echo "MCP_AMASS_API_KEY=$val" >> "$f"
  done
  ```
- Verify no broken-paste (same trap as every other key-wiring skill):
  `set -a; . <profile>/.env; set +a; echo ${#MCP_AMASS_API_KEY}` must print
  silently. A `command not found` means the key leaked into chat/tool
  output — rotate it at platform.amass.tech/api-keys.

### Add the MCP server

```
hermes mcp add amass --url https://mcp.amass.tech/mcp --auth header --connect-timeout 90
```

- This is an **interactive** flow (two yes/no prompts: "Does this server
  require authentication?" and "Enable all N tools?"). From a non-TTY
  shell, pipe exactly two `Y`s — `printf 'Y\nY\n' | hermes mcp add ...` — a
  single piped `Y` only answers the first prompt and the add is silently
  cancelled at the second ("Enable all 14 tools?"). Neither prompt is a
  password/token prompt, so piping `Y` twice is safe here — it is NOT the
  same as the "never pipe more than the auth answer" trap, which applies
  only when a getpass-style token prompt could read the next stdin line as
  the secret.
- With `MCP_AMASS_API_KEY` already in `.env`, the add flow detects it
  ("✓ MCP_AMASS_API_KEY: already configured") and skips any token prompt
  entirely — no secret ever crosses stdin or chat.
- Result: `config.yaml` gets only the template
  `Authorization: Bearer ${MCP_AMASS_API_KEY}` — the raw key never lands in
  config. Tools register as `mcp_amass_*` (14 tools: `search_amass_*` ×6
  and `get_amass_*` ×6, plus `get_amass_regulatorycore_document_section`
  and `send_feedback`).
- Config is shared across profiles in this install (default + researcher
  read the same `config.yaml`), so one `hermes mcp add` wires every profile
  at once — confirm this isn't true for your install before assuming it.

### Verify

```
hermes mcp test amass
```

Checks connection + auth + tool discovery in one shot (~1.5s on a healthy
key). **MCP tools need a new session to appear — no hot reload.** `hermes
mcp test` passing does not mean the current conversation can call
`mcp_amass_*` yet; it means the NEXT session can.

## 3. Smoke test (REST, before or instead of the MCP layer)

Because Amass's REST API and its MCP server share the same auth and the
same underlying data, a plain `curl` smoke test is a fast way to verify the
key and get real content-level evidence the service actually works — not
just that the MCP handshake succeeded.

```bash
python skills/hermes-amass-mcp/scripts/amass_smoke_test.py
```

Checks (content-verified, not just HTTP 200):
1. BiomedCore search returns records with a `title` and a resolvable
   `pmid`/`doi`.
2. TrialCore search returns a record with an `nctId`.
3. DrugCore search returns a record whose `name` matches the query.
4. Rate-limit headers (`X-RateLimit-Limit/Remaining/Reset`) are present.
5. `/credits/api-credits` returns a `remaining` integer.

A 200 with an empty `data` array on a query guaranteed to have results
(e.g. "endometriosis" on BiomedCore) is a FAIL, not a pass — same principle
as the Claude/OpenAI skills' "200 isn't automatically a pass" rule.

## Pitfalls (one line each)

- The public landing page oversells OAuth-only connector install (Claude
  directory / ChatGPT plugin) — the platform docs reveal a plain Bearer-key
  REST API underneath; use the key, skip OAuth, if you already have one.
- `GET https://api.amass.tech/api/v1` alone 404s — always hit a real Core
  path (`/cores/{core}/records?query=...`), the bare base URL is not a
  health-check endpoint.
- Pagination is NOT cursor/offset-based — max 300 results via `limit`;
  narrow with query/filters instead of paging for large result sets.
- Each Hermes profile has its own `.env` — wire the key into every profile
  that will use Amass, not just the one you tested in.
- `hermes mcp add` needs TWO piped `Y`s for this server (auth confirm +
  tool-enable confirm), not one.
- Key values never in repo/skill/commit — env-var names only; run the
  guard before push.
