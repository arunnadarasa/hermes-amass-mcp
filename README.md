# hermes-amass-mcp

Hermes Agent skill for wiring the [Amass](https://amass.tech) life-sciences
data platform into Hermes as a remote MCP server: 14 tools across six
"Cores" — biomedical literature, clinical trials, FDA/EMA regulatory
authorizations, drugs/molecules, genes, and patents (preview).

Documentation sources used:

- [Amass MCP overview](https://amass.tech/mcp)
- [Amass platform API overview](https://platform.amass.tech/documentation/getting-started/overview)
- [OpenAPI spec](https://api.amass.tech/api/doc/openapi.json)

## Cores

| Core | Records | Status |
|---|---|---|
| BiomedCore | 43M+ PubMed/PMC citations + conference abstracts | Available |
| TrialCore | 1.2M+ trials (ClinicalTrials.gov + WHO ICTRP) | Available |
| DrugCore | 22K+ harmonized drugs/molecules (ChEMBL) | Available |
| RegulatoryCore | FDA + EMA authorizations, unified schema | Available |
| GeneCore | 43K+ genes (HGNC + NCBI Gene) | Available |
| PatentCore | Patent publications, full text, CPC/IPC | Preview |

## Layout

```
skills/hermes-amass-mcp/SKILL.md
skills/hermes-amass-mcp/scripts/amass_smoke_test.py
```

## Wiring

```bash
# 1. put your key in .env as AMASS_API_KEY, then also copy it to the name
#    hermes mcp add's header-auth flow expects:
echo "MCP_AMASS_API_KEY=$(grep '^AMASS_API_KEY=' ~/.hermes/.env | cut -d= -f2-)" >> ~/.hermes/.env

# 2. wire the server (two piped Y's: auth confirm + tool-enable confirm)
printf 'Y\nY\n' | hermes mcp add amass --url https://mcp.amass.tech/mcp --auth header --connect-timeout 90

# 3. verify
hermes mcp test amass
```

Full detail, including the profile-scoped `.env` trap and why header auth
beats the marketed OAuth connector flow for headless wiring, is in
`skills/hermes-amass-mcp/SKILL.md`.

## Verification

A live, content-checked smoke test (HTTP 200 with empty data is a FAIL, not
a pass — same rule as the sibling OpenAI/Claude Jev skills):

```bash
python skills/hermes-amass-mcp/scripts/amass_smoke_test.py
```

Checks BiomedCore/TrialCore/DrugCore return real matching records,
rate-limit headers are present, and the credits endpoint returns a numeric
balance. Live run (2026-10-02): **5/5 checks passed.**

## Security

No key values belong in this repository. The script sources
`AMASS_API_KEY` from the environment without printing it. Run
`scripts/guard_secrets.py` before every push. Never paste a credential into
a command line, issue, commit or chat.
