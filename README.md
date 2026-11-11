# ledgernode

Self-hosted household finance that **proves** every import instead of assuming it worked.

[Firefly III](https://www.fireflyiii.org/) is excellent at showing you what happened. This repo is
about the harder question underneath it: *is the ledger actually complete?* A finance manager that
silently drops transactions is worse than a spreadsheet, because you trust it.

So every import here is followed by a verification run that compares the ledger against the bank's
own export. Row counts, dates, amounts and the closing balance all have to agree before anyone
calls the job done.

## Why this exists

The vendor's CSV importer reported a clean import. The ledger was short by **22 transactions** — no
error, no warning, no UI hint. They were legitimate repeats: three identical coffees, same day, same
amount, same description. The importer hashes the fields it is about to send, so identical rows
collide and the second one is skipped.

Two things made it invisible:

- The bank's export has **no transaction identifier**, so the rows really are indistinguishable.
- The one column that could tell them apart — a running balance that steps down twice — is mapped
  to *"(ignore this column)"* by default.

The full reasoning is in [ADR-0002](docs/decisions/0002-importer-constraints.md) and
[ADR-0005](docs/decisions/0005-three-source-transaction-model.md). The fix is to count, not to ask
"have I seen something like this before?" — a hash answers set membership, and this problem needs
multiset membership.

## What is here

| Path | What it is |
|---|---|
| `infra/firefly/` | Docker Compose stack: Firefly III, PostgreSQL, the CSV importer, a cron sidecar |
| `tools/verify_import.py` | Compares a bank CSV export against the ledger. The core idea of the repo |
| `tools/cashapp_statements.py` | PDF statement parser for a prepaid card, reconciled to printed totals |
| `tools/usbank_statements.py` | PDF statement parser for a bank card, with pre-authorisation holds excluded |
| `tools/audit_public.py` | Fails if personal detail has leaked into a tracked file |
| `docs/decisions/` | ADRs — the reasoning, including the mistakes |
| `docs/stories/`, `tasks/` | Requirements and the delivery plan |
| `docs/plans/payday-plan.example.md` | Worked example of sequencing a payday against due dates |

## The rule that makes multiple accounts work

> Each institution's statement is the truth for what happened **inside that institution**.
> Money crossing between your own accounts is a transfer, recorded once — never two expenses.

Import everything from every statement and you double-count. The naive version of that mistake here
was worth about **$22,000**. The model, and the guard that enforces it, are in
[ADR-0005](docs/decisions/0005-three-source-transaction-model.md).

Three classifications do all the work: `transfer_internal`, `income` / `expense`, and
`duplicate_of` (kept as evidence, deliberately not imported). Anything unclassifiable stops the run
rather than guessing.

## Quick start

```bash
git clone <this repo> && cd ledgernode

# 1. Secrets. Never committed.
cp infra/firefly/.env.example      infra/firefly/.env
cp infra/firefly/.db.env.example   infra/firefly/.db.env
cp infra/firefly/.importer.env.example infra/firefly/.importer.env
#    Fill in APP_KEY, DB_PASSWORD, STATIC_CRON_TOKEN and your bind address.

# 2. Household values. Also never committed.
cp .household.env.example .household.env

# 3. Bring it up, on a LAN address only.
cd infra/firefly && docker compose up -d

# 4. Import, then prove it.
python3 tools/verify_import.py --file your-bank-export.csv
```

`verify_import.py` exits `0` when the ledger matches the export, `1` on a mismatch it can describe,
and `2` on an error. It refuses to call a partial import success.

## What is reusable

| Reusable as-is | Worked example only |
|---|---|
| `verify_import.py` and the reconciliation discipline | The two PDF parsers: they target specific statement layouts. Useful as a template, not drop-in |
| The ADRs as a way to reason about imports | Categorisation rules: tied to one household's merchants |
| The Compose stack and env layout | The categories, budgets and bills themselves |
| `docs/plans/payday-plan.example.md` | — |

## A note on the figures

Numbers in `docs/` are rounded to roughly two significant figures, and names, institutions and
card labels are replaced with roles (`Bank A`, `Employer B`, `Partner`). The ratios, the ordering
and the reasoning are exact — those are the part worth reading. Household values live in the
git-ignored `.household.env`, and `tools/audit_public.py` enforces that separation.

## Status

Running against Firefly III 6.7.9 and PostgreSQL 18. The importer's own duplicate handling is still
used for bulk history; the verification step is what makes it trustworthy.

## Licence

MIT — see [LICENSE](LICENSE).
