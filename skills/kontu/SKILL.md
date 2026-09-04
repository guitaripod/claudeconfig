---
name: kontu
description: Search for and evaluate houses to buy in Finland with the agent-native `kontu` CLI (Cloudflare Worker backend) - ingest live listings for a municipality, filter by price, shore, type and year, run the deterministic multi-year cost and risk models, and compare candidates. Use for any Finnish house-hunting question, e.g. "lakeside house in Outokumpu under 120k" or "what would this house cost me over 20 years".
---

# kontu

- Binary on PATH or `~/Dev/kontu/tui/target/debug/kontu` (repo `~/Dev/kontu`). Run `kontu guide` for the full playbook and `kontu <cmd> --help` per command. Always pass `--json`.
- Vague request: ask 2–4 clarifying questions first (budget, area(s), type, must-haves such as shore/year/heating, deal-breakers, cost-model horizon), then encode the answers as filters.
- Typical flow: `kontu pull <Municipality>` (ingests real listings; must run from a local machine, the Worker's IP is portal-blocked) → `kontu list --municipality <M> --price-max 120000 --shore oma_ranta --json` → `kontu cost <id> --horizon 20 --json`, `kontu risk <id> --json`, `kontu compare <ids> --json` → `kontu open <id>`. The cost and risk models run locally and are deterministic.
