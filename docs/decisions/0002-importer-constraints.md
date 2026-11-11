# ADR-0002 — Importer constraints, and how the ledger is verified

| | |
|---|---|
| **Status** | Accepted, 2026-11-09 |
| **Tasks** | T-17 (constraints), T-18/T-19 (verification tool), T-20 (repair, gated) |
| **Story** | [US-002](../stories/US-002-verify-every-import.md) |
| **Validated against** | Firefly III 6.7.9, data-importer 2.3.5, PostgreSQL 18 |

## Context

Two imports of the same 2,268-row Bank A export were needed to get a correct ledger. Everything
below was learned by observation, then confirmed against the source at the running tag. These are facts
about the tools, not preferences — recording them is cheaper than rediscovering them at the next
upgrade or the next monthly import.

## Constraints learned

### 1. A deposit needs an opposing account, or it fails

Every credit was rejected with `transactions.0.source_id = "0"`, *"Could not find a valid source
account"*. Nothing supplied a payer account, and the importer creates only a single `(no name)` expense
account, never a revenue one. Fix: an explicit column mapped to **Opposing account (name)**.

### 2. Duplicates are dropped silently

2,246 of 2,268 rows arrived. The 22 absent were legitimate repeats — same date, amount and description
appearing two or three times. No error, no warning, no UI indication. Only the row count and balance
exposed it.

### 3. The API cannot create an opening balance in 6.7.9

`StoreRequest` validates `in:…,opening-balance,…` while `AccountValidator` compares against
`Opening-balance`, so every attempt returns 422. Opening balances must be set through the UI.

### 4. The bulk destroy endpoint cannot delete transactions

`DELETE /api/v1/data/destroy` accepts `objects` from a fixed list: `budgets,bills,piggy_banks,rules,
recurring,categories,tags,object_groups`. Transactions are not in it. Bulk removal goes through
per-group `DELETE /api/v1/transactions/{group}`.

### 5. Firefly soft-deletes

Deleted transactions remain as rows with `deleted_at` set. `count(*)` still reports them, so a cleanup
appears not to have worked unless you filter `where deleted_at is null`.

### 6. A multi-element `transactions` array means splits, not groups

Posting many groups in one request returns *"All splits must be of the same type"*. Each transaction
group is one POST carrying a single-element array.

### 7. Generated CSVs must be LF, not CRLF

Python's `csv` writer defaults to `\r\n`, which puts a carriage return on the last column of every row.
The bank's export is LF-only. A `\r` in a numeric column is exactly the class of defect that produces
silent parse errors.

### 8. Amounts are stored at higher precision than they are stated

The `transactions.amount` column is `numeric(32,12)`; reads return `603.950000000000`. Any comparison
must normalise to two decimals.

### 9. A journal holds two split rows, and a reversal can invert the direction

Firefly stores double-entry splits, so per-journal counts must group by journal. Separately, the bank
records the `-10` POS reversal as `Debit` with a negative amount — meaning money **in**. Firefly stores
it correctly as a **deposit of 10**. Comparisons must normalise: *file amount < 0 ⇒ expected type is
the opposite of the bank's type column, amount = `abs()`*.

### 10. The importer UI does not use the vocabulary the documentation does

The date role appears as **"Date (primary transaction date)"**, not "Date". Personal access tokens live
under **"Remote access and tokens"** → Personal Access Tokens, not "Options → Profile → OAuth". The
OAuth client flow fails outright (`SQLSTATE[22P02]`, a JWT client id cast to `uuid`), so the token is
supplied through `FIREFLY_III_ACCESS_TOKEN`.

## Verification tool decisions

The tool that checks an import (`tools/verify_import.py`) is constrained as follows.

| Decision | Reason |
|---|---|
| **Runs on `host-a`**, reads files from `/srv/ledgernode/import` | The token is already there at mode 600; running it on a laptop would copy a full-authority credential to a second machine |
| **API only, never PostgreSQL** | The API recalculates cached balances; raw SQL leaves the UI wrong. Observed during cleanup |
| **Read-only by default; writes only behind `--repair`** | The failure being guarded against is an unrequested write |
| **Repair inserts only — never deletes or edits** | Extra rows are reported. Deleting on a heuristic is how a ledger loses real money |
| **Repair is gated on T-13 (restore rehearsal)** | No write path ships before a backup has been restored once |
| **Pagination totals asserted; short reads abort with exit 2** | A dropped page would look like "missing rows" and then be written into the ledger |
| **Account ids configurable, defaults `1` / `8` / `9`** | Those ids are this household's, not universal; a recreated account changes them |
| **Standard library only** | No dependency approval, and it runs on any machine with Python 3 |
| **Exit codes `0` clean, `1` mismatch, `2` error** | Lets the check run unattended later without parsing prose |

## Consequences

Positive: a repeatable, row-level proof for AC5 and AC6 instead of a total that can hide a defect; and
a written record of tool behaviour that will otherwise be rediscovered after the next version bump.

Negative, accepted: the tool encodes behaviour of a specific Firefly version, so it must be re-run
after any upgrade (T-22 is written to be re-runnable); and the repair path writes to the only copy of
the ledger, which is why it waits for the restore rehearsal.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Query PostgreSQL directly | Balances would not be recalculated; the UI would report values the tool disagrees with |
| Trust the importer's own summary | It reported success while dropping 22 rows |
| Verify by comparing totals only | A missing row offset by a duplicated one produces an identical total |
| Hand-run the comparison each month | Repeated by hand, it will drift, then be skipped |
