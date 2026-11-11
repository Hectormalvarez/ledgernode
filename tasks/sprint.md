# Sprint 1 — Stand up the household finance instance

| | |
|---|---|
| **Epic** | Household finance visibility (v1) |
| **Story** | [US-001](../docs/stories/US-001-household-money-visibility.md) |
| **Sprint owner** | Relative (primary owner) |
| **Status** | Not started |

## Sprint goal

A running Firefly III instance reachable from both household phones on the home network, holding two
years of real Bank A history, with categorisation rules doing the repetitive work, a
month-over-month report that is readable, an export proven to open in a spreadsheet, a backup proven to
restore, and both people able to use it unaided.

Sprint is done when all twelve acceptance criteria in US-001 have recorded evidence — not when the
tasks are ticked.

## Escalations — needed before dependent tasks can start

**E-1 — RESOLVED 2026-11-09 (Product Owner decision).** Encryption on the home network is not a concern
for now. AC1 is amended: no encrypted connection is required, and this is recorded as accepted
limitation 5 in US-001. What AC1 still demands — and what T-03 must prove — is unchanged: no financial
data is reachable before signing in, and the instance is unreachable from outside the home network.

**E-2 — RESOLVED 2026-11-09 (owner checked the export).** The export contains settled transactions only;
no pending rows. Criterion 7 therefore concerns overlapping re-imports alone — the pending-then-settled
double appearance is out of scope for duplicate handling.

**E-2a — NEW, surfaced by the sample export.** The column mapping can silently produce wrong numbers in
two ways (ambiguous date format; direction taken from an unsigned amount instead of the type column).
Not blockers, but T-07 must prove both before the two-year import is trusted. Details under
"T-06 findings" below.

**E-3 — No Architect is engaged in this session.** T-01 and T-02 are decisions, not assembly. If neither
is taken, the sprint proceeds on assumptions and US-001 criteria 1, 2 and 12 become unverifiable.

## Phase 1 — Decisions

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-01 | Decide the hosting and deployment approach for the instance (vendor-supported options: container image or self-managed server install), where the data store lives, and how the instance is reached from the two phones on the LAN. Outcome recorded as a short decision record in `docs/decisions/`. | AC1 | — | Done — ADR-0001 |
| T-02 | Define the backup and restore procedure for the data store, explicitly *not* the CSV export, and state the cadence the owner will follow. Outcome recorded beside T-01. | AC12 | — | Done — ADR-0001 §5 (rehearsal at T-13) |

## Phase 2 — Stand-up

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-03 | Stand up the instance and confirm it is reachable from both phones on home Wi-Fi, that no financial data is visible before signing in, and that it is not reachable from outside the home network. Encryption is not required (E-1 resolved). Evidence: one screenshot per phone, the pre-sign-in page, and a failed external connection attempt. | AC1 | T-01 | Done — deployment record below; external-unreachability check still owed (see record) |
| T-04 | Create the household account, enable the second factor, enrol the authenticator for both people, and close open registration so no further account can be created. Store the 2FA recovery material where both people can reach it if a phone is lost (see R-1). | AC2, AC3 | T-03 | In progress — account created and signed in on desktop; 2FA enrolment and closing registration unconfirmed |
| T-05 | Create the Bank A checking account with its correct opening balance and date, so imported history lands on a sane starting point. | AC6 | T-04 | Todo |
| T-06 | Inspect the bank CSV export: confirm which columns map to date, amount and description, confirm no leading non-data line, and record whether any stable transaction identifier exists. | AC5, AC7 | — | Done — all 2,268 rows analysed |

### T-06 findings — from the real two-year export (2026-11-09)

Columns present: `Account Number, Transaction Description, Transaction Date, Transaction Type,
Transaction Amount, Balance`. The file contains **2,268 rows** for account `7718`, spanning
2024-11-09 → 2026-11-09, with the header on line 1 and no banner of any kind.

| Observation | Consequence for the plan |
|---|---|
| No transaction identifier of any kind | Duplicate detection can only compare date, amount and description. R-2 stands, and AC7 is proven by detection and resolution — never by "duplicates cannot happen" |
| Date written `11/09/26` | Month-first is assumed, but any day up to the 12th is ambiguous either way. T-07 proves the mapping against a known transaction before two years are imported |
| Amount remains unsigned, direction lives in `Transaction Type` (`Credit`, presumably `Debit`) | Reading direction from the sign would invert the whole history: expenses become income, and rules and reports are then built on wrong data. T-07 proves this on one known expense |
| A running `Balance` column is exported | Free reconciliation: the per-row balance identifies the exact row where an import diverges (AC6) |
| No category or merchant column; long uppercase descriptions carrying reference numbers | Categorisation rules must match on description substrings. T-09 should test case handling and tolerate the reference noise |
| 21 groups of identical date + description + amount rows exist *inside* the file | These are genuine repeats — same merchant, same day, same amount. All 2,268 rows must survive the import; a duplicate handler that collapses them fails AC5 |
| Exactly one `Debit` row carries an already-negative amount (`-10`, a POS reversal) | Direction must be applied as "negate for `Debit`", never as "take the absolute value" — `abs()` would turn a reversal into a second withdrawal |
| The file's first line is the column header | No banner: R-11 closed without action |
| 331 `Credit` / 1,937 `Debit` over two years | Expect roughly a 15% credit ratio; a wildly different split after import means direction is being mis-read |

Two of these — the date format and the direction column — are silent-corruption risks rather than
cosmetic ones. They are cheap to prove once and expensive to discover after rules have been built on
top of them.

### T-07 import mapping — decided from the file, not from trial and error

The importer maps columns to named roles. The roles that fit this export:

| CSV column | Importer role | Why |
|---|---|---|
| `Transaction Date` | date of the transaction, format `m/d/y` | Proven month-first: day-of-month reaches 31 |
| `Transaction Description` | description | Long uppercase strings with reference numbers; rules will match substrings |
| `Transaction Amount` | amount | Magnitude only — direction is not in this column |
| `Transaction Type` | **Bank specific credit/debit indicator** | The role built for exactly this: a column that says `Credit` or `Debit`. If direction lands inverted, use **Amount (negated column)** rather than editing data |
| `Account Number` (`7718`) | the single asset account it belongs to | Only one value appears, so the account is chosen once |

Rules for this import:

- **Row count is the first assertion:** 2,268 rows in, and the import summary must agree with that.
  A mismatch means rows were collapsed or skipped, and AC5 fails.
- **Duplicate detection is advisory.** The 21 legitimate identical triples mean the importer's
  duplicate handling must be *reviewed*, never trusted to delete silently — that review is the
  procedure T-08 records.
- **The `Balance` column is not importable.** The importer has no balance role — verified against its role
  list and English strings — so it must be mapped to "(ignore this column)". Mapping it to `Amount`
  would double-count every transaction. Its value is *external evidence*: it yields the opening balance
  (761.47), the assertion for the final balance (343.03, AC6), and a way to locate the row where an
  import diverges.
- **Verify by replaying the running balance, not by trusting a total.** After import, read the
  transactions back through the API and re-apply them to the starting balance, asserting the bank's own
  `Balance` at every row. That is the strongest available proof for AC5 and AC6, and it catches cases a
  matching total hides — a single inverted sign, or the one-in-2,268 POS reversal row.
- **Keep the JSON configuration.** The importer only produces its JSON configuration through the UI,
  and the CLI (`fireflyiii/data-importer`, `-cli` variant) reuses that file for every future month.
  Losing it means redoing the mapping by hand.
### T-07 attempt 1 (2026-11-09) — what broke, so attempt 2 does not repeat it

- **415 withdrawals imported, 0 deposits.** Every credit was rejected: `transactions.0.source_id = 0`,
  *"Could not find a valid source account"*. Cause: nothing supplied an opposing account, and the
  importer created only one `(no name)` **Expense** account — no revenue account existed, so a deposit
  had no payer. Fix for attempt 2: a `Counter Account` column (`Income` / `Expenses`) mapped to
  **Opposing account (name)**.
- **Everything funnelled into `(no name)`.** All 415 rows were deleted through the API (soft delete) and
  that account removed, so attempt 2 starts from an empty ledger rather than a repaired one.
- **The API cannot create an opening balance in 6.7.9.** `StoreRequest` accepts `opening-balance` while
  `AccountValidator` compares against `Opening-balance`, so every attempt returns 422. The opening
  balance has to be set in the UI.
- **`DELETE /api/v1/data/destroy` cannot remove transactions** — its allow-list is
  `budgets,bills,piggy_banks,rules,recurring,categories,tags,object_groups`.
- **Firefly soft-deletes.** `count(*)` on `transaction_journals` still reports deleted rows; count with
  `where deleted_at is null` or the cleanup looks like it did nothing.
- **Generated CSVs must be LF, not CRLF.** Python's csv writer defaults to `\r\n`, which puts a carriage
  return on the last column of every row — the bank's own export is LF-only.
### T-07 attempt 2 (2026-11-09) — outcome, and the trap it exposed

- The import landed **2,246 of 2,268** rows. The 22 absent rows were **silently dropped as duplicates** —
  they are the legitimate repeats (same date, same amount, same description), plus one reversal.
  **The importer reported no error for any of them**, and the UI looked complete; only the row count and
  the balance exposed it.
- The 22 were re-inserted through the API, one POST per group. **A multi-element `transactions` array
  means *splits of one group*, not several groups** — posting them together returns
  *"All splits must be of the same type"*.
- Final state, verified against the file as a multiset: **2,268 = 2,268, 0 missing, 0 extra**, identical
  per-day net on every day, balance **343.03**. This is the AC5/AC6 evidence.
- The bank labels the `-10` POS reversal as `Debit`; Firefly correctly stores it as a **deposit of 10**.
  Any comparison must normalise that row or it shows as one missing plus one extra.
- **Rule for every future import:** assert row count and final balance immediately. Duplicate handling
  loses legitimate repeats without complaint, and a matching balance can hide a missing row only if
  matching rows were also added.

- **Use a Personal Access Token, never the OAuth client flow.** On 2026-11-09 the client flow died with
  `SQLSTATE[22P02]: invalid input syntax for type uuid` on `GET /oauth/authorize`: Firefly 6.7.9 gave
  the importer a JWT-style client id, and Passport tried to look it up in the `uuid` column of
  `oauth_clients`. The PAT path never touches `/oauth/authorize`, so it avoids the defect entirely.
  Creating the token is "Remote access and tokens" → **Personal Access Tokens** → **Create new token**;
  the value is shown once.

## Phase 3 — Data

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-07 | Import the two-year CSV export. Before trusting it, prove two things on one known transaction and one known expense: the date lands on the day it actually happened, and the expense appears as an expense (direction taken from `Transaction Type`, not from the unsigned amount). Then record the imported/skipped counts and reconcile the final balance against the bank's own balance for the same end date — the export carries a running `Balance` column, so a mismatch can be traced to the row where it starts. | AC5, AC6 | T-05, T-06 | Done — 2,268 of 2,268 rows present; 22 silently dropped duplicates re-inserted; balance 343.03 |
| T-08 | Re-import a deliberately overlapping date range and document exactly what the tool reports and how the duplicates are resolved. Outcome: a written procedure in the operating runbook, because this will be done again every month. | AC7 | T-07 | Todo |
| T-09 | Name the five recurring merchants, build the categorisation rules, apply them to existing history, and import new transactions to confirm they land categorised while unmatched ones stay clean and uncategorised. | AC8 | T-07 | Todo |
| T-10 | Rehearse the failure path: import a deliberately malformed row (missing date, unreadable amount) into a scratch account and confirm the import completes, the bad row is identified, and nothing else changes. | AC11 | T-07 | Todo |

## Phase 4 — Prove the value

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-11 | Open the monthly report for the last month with the previous month beside it, and hand-check the categories total against the month's expense transactions added up manually. Record both figures. | AC9 | T-09 | Todo |
| T-12 | Export transactions, open the file in a spreadsheet, confirm the columns are usable with no manual preparation, and confirm the date-scoped fallback works if the in-app export times out on the full history. | AC10 | T-07 | Todo |
| T-13 | Restore rehearsal: take a backup, destroy or replace the instance in a scratch context, restore, and confirm balances and last month's report match what they were. Do this *before* the household depends on the data. | AC12 | T-02, T-07 | **Deferred 2026-11-10 (Product Owner decision)** — deprioritised in favour of making the ledger usable. Consequence stated plainly: the recovery path is unproven while the ledger holds the only copy of two years of history and now also the debt picture. Mitigation: everything added under US-004 is additive configuration (accounts, budgets, piggy banks) that can be deleted through the UI, and no transaction row is created or edited. AC12 stays open; see R-14 |
| T-14 | Partner onboarding: she signs in on her own phone, adds a real transaction she just made, and it appears on the owner's device with correct date, amount and merchant and is reflected in balances. Keep the transaction — it is the start of the usage-habit measure. | AC3, AC4 | T-04, T-07 | Todo |

## Phase 5 — Operate

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-15 | Write `docs/runbook.md`: how to start/stop, how to upgrade and roll back, the monthly import procedure (including the overlap step from T-08), the backup step and cadence from T-02, and what to do if the second factor is lost. Written for the owner six months from now, and for the partner if the owner is unavailable. | AC12 | T-08, T-13 | Todo |
| T-16 | Schedule the 30-day success review: statements imported for two consecutive months, report opened at least twice, partner entered at least five transactions unprompted. Record the outcome against US-001 before calling it Done. | Success measure | T-14 | Todo |

## Phase 6 — US-004: budget and debt picture

Scope change agreed 2026-11-10; see [ADR-0004](../docs/decisions/0004-budget-and-debt-scope.md).

| ID | Task | Satisfies | Depends on | Status |
|---|---|---|---|---|
| T-21 | Create a liability account for every debt the household claims, with its balance, and confirm net worth becomes assets minus liabilities rather than the flattering $340. | AC1 | T-07 | Done 2026-11-10 — 7 liabilities, $26,000; net worth −$26,000. Opening balances set through the API (corrects ADR-0002 §3) |
| T-22 | Create the monthly budgets for the fixed bills and living lines, sized against actual average income rather than the stated figure, using `rollover` only where money genuinely carries. | AC2 | T-21 | Done 2026-11-10 — 8 budgets; `Household Buffer` set to `rollover`, the rest `reset` |
| T-23 | Create piggy banks for the funds the plan depends on: emergency buffer, debt settlement, and the student-loan resumption fund with its May 2027 date. | AC6 | T-21 | Done 2026-11-10 — targets $1,000 / $600 / $1,200 |
| T-24 | Make the ledger complete: establish where the second income stream lands now the job has changed, and capture the spending that currently disappears into prepaid app (move daily spending to the debit card, or capture the prepaid statements). Until this is done every budget is measured against roughly half the household's money. | AC2, AC3 | T-21 | **Blocked — open question 1 and 2** |
| T-25 | Build categorisation rules for the top recurring merchants and have them `set_budget` on import, so a month closes already measured. | AC3 | T-09, T-22 | Todo |
| T-26 | Take the monthly read: budget report with spend against limit, and every liability balance, for two consecutive months. Confirm no transaction was created on the imported asset account. | AC3, AC4, AC5 | T-22, T-24 | Todo |
| T-27 | Agree one row schema and one classification for all three institutions, so a Bank A CSV, a prepaid app PDF and a Bank B statement all produce the same shape. | AC3 | — | Done 2026-11-10 — [ADR-0005](../docs/decisions/0005-three-source-transaction-model.md) |
| T-28 | Parse Bank B statements into that schema, reconciled against each statement's own opening and closing balance. | AC3 | T-27 | Blocked — awaiting the exports |
| T-29 | Match transfers across sources on exact amount with a date window, and report the observed day offsets rather than assuming them. | AC5 | T-27 | Methodology proved — 24 of 24 Bank A→prepaid app transfers matched at exactly −1 day |
| T-30 | Import with the duplicate-count guard: for every matched pair exactly one side is written, or the run aborts before writing anything. Reclassify Bank A's own-account `PREPAID APP` debits in the same operation. | AC5 | T-28, T-29 | Todo |


## Dependency map

```
T-01 ──► T-03 ──► T-04 ──► T-05 ──┐
                                  │
T-06 ─────────────────────────────┴──► T-07 ──┬──► T-08 ──┐
                                              ├──► T-09 ──┴──► T-11
                                              ├──► T-10
                                              ├──► T-12
                                              └──► T-14 ──► T-16

T-02 ─────────────────────┐
T-07 ─────────────────────┴──► T-13 ──┐
T-08 ─────────────────────────────────┴──► T-15
```

Critical path: **T-01 → T-03 → T-04 → T-05 → T-07 → T-09 → T-11**. E-1 and E-2 are closed, so the
only thing between this plan and T-03 is the T-01 decision — and nobody currently owns it.

## Risks

| ID | Risk | Impact | Mitigation | Owner |
|---|---|---|---|---|
| R-1 | **Second factor lock-out.** A single shared account with 2FA means a lost phone locks *both* people out of the household books. | High — this is the most likely way the whole thing becomes unusable | Store the authenticator secret and any recovery material where both people can reach it; rehearse one recovery before T-14; put the procedure in the runbook (T-15) | Owner |
| R-2 | **Duplicates on re-import.** The bank CSV may carry no stable transaction identifier, so overlapping imports can double-count and quietly corrupt balances. | High — corrupts the one number anyone trusts | T-06 establishes the facts, T-08 documents detection and resolution, T-11 reconciles totals against a manual sum | Owner |
| R-3 | **Pending rows.** If pending transactions are exported, a row can legitimately appear twice (pending, then settled) and look like a duplicate. | Medium — false positives in duplicate handling | **Closed 2026-11-09:** the owner confirmed the export contains settled rows only. Kept here so the question is not reopened | PO then Owner |
| R-4 | **Backup untested until it is needed.** A backup that has never been restored is a hope, not a backup. | High — AC12 is the difference between a bad week and losing two years of history | T-13 happens before the household depends on the data, not after go-live | Owner |
| R-5 | **Encryption ambiguity on the LAN (E-1).** Building before the decision means either rework or a silently weakened AC1. | Medium | Do not start T-03 until the PO answers E-1 | PO |
| R-6 | **The vendor's upgrade path can break a running instance.** Self-hosted applications need attention the household does not want to give. | Medium | Pin the version at T-01; upgrade deliberately, never automatically; rollback step in T-15 | Owner |
| R-7 | **Adoption risk — the real failure mode.** A perfect install the partner never touches fails the two-person requirement while every technical criterion passes. | High | T-14 is a real first transaction, not a walkthrough; T-16 measures it honestly | Owner |
| R-8 | **Categorisation noise.** Rules applied to two years of history can mis-label silently, and criteria 8 and 9 then prove nothing. | Medium | Spot-check a sample of categorised history at T-09, not just newly imported rows | Owner |
| R-9 | **Silent date inversion.** `11/09/26` read day-first instead of month-first shifts every transaction dated up to the 12th, and monthly totals are wrong in a way nobody notices. | High — corrupts the month-over-month comparison that is the entire point | Prove the mapping on a known dated transaction at T-07; spot-check the first and last imported rows against the bank's own view | Owner |
| R-10 | **Direction inverted.** Amounts are unsigned with direction in `Transaction Type`; taking it from the sign turns every expense into income. | High — reports become fiction and rules are built on fiction | Prove on one known expense at T-07: an amount that must appear as a withdrawal | Owner |
| R-11 | **Header not recognised.** A leading line before the column headers (the sample shows an `EXAMPLE DATA` banner) breaks the column mapping. | Low — fails loudly, caught on the first attempt | Check the real file's first line at T-06 before any import | Owner |
| R-12 | **The instance lives on a laptop.** Suspend, lid-close, reboot or a flat battery takes the instance *and* the cron sidecar down; imports and backups silently stop and the household notices weeks later. | Medium — availability, not correctness | **Mitigated 2026-11-09:** the owner confirms the host is already configured not to suspend or sleep on lid-close. Residual risk is a reboot or power loss, which the `restart: unless-stopped` policy covers once the machine is back | Owner |
| R-13 | **Shared host blast radius.** The books sit beside media and public web stacks reached through cloudflared tunnels; a compromise of any of them reaches the financial data. | High — one host, many attack surfaces | **Accepted for now**, owner decision 2026-11-09. Structural mitigation stands regardless: no tunnel and no inbound rule for port 8090 (ADR-0001). Revisit if another public service lands on this host or if the data's value grows | Owner |
| R-14 | **Unproven recovery on a ledger that now cannot be recreated.** T-13 is deferred while the instance holds the only copy of two years of history *and* the debt picture. | High — the bank can re-issue statements; the categorisation, rules and debt state cannot be recovered from anywhere else | Take a backup **before** any further structural change; keep everything added under US-004 additive and UI-deletable; reinstate T-13 before the instance is treated as irreplaceable | Owner |
| R-15 | **Budgets measured against half the household's money.** One income stream was diverted to a prepaid card and never reached the imported account; prepaid app purchasing is invisible to the ledger. A budget built on the visible half reads as authoritative and is wrong. | High — a wrong budget is worse than none, because it is acted upon | T-24 before any budget is trusted; state the known income gap in every monthly read until it is closed | Owner |

**Risk closures, 2026-11-09** — retired by parsing the real 2,268-row export rather than by review:
R-9 (dates are provably month-first), R-10 (direction proven against 2,267 balance deltas), R-11 (first
line is the header). R-3 was closed earlier by the settled-rows confirmation. Two new risks were opened
above: R-12 and R-13.

## Evidence log

Every criterion closes with evidence, recorded here — a screenshot path, a figure, or a written
observation. A task marked Todo without evidence is not done.

| AC | Evidence | Verified by | Date |
|---|---|---|---|
| 1 | Partial: `GET /` → 302 at the LAN address with no data served pre-sign-in, `/register` → 200, reachable from 192.168.1.12 in 0.26 s, published on 192.168.1.10:8090 only. Outstanding: both phones in hand, and a failed external connection attempt. | delivery | 2026-11-09 |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | 2,268 imported rows compared with the file as a multiset: 0 missing, 0 extra, after normalising the bank's `-10` "Debit" reversal which Firefly correctly stores as a +10 deposit. Per-day net identical on every one of the 21 affected days. | delivery | 2026-11-09 |
| 6 | Balance 343.03 equals the bank's last balance, reached as opening 761.47 + net −418.44 across 2,268 rows. | delivery | 2026-11-09 |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |
| 11 | | | |
| 12 | | | |

## Definition of Done — sprint

1. All twelve ACs have evidence above, and none was weakened to fit reality — if reality differs, the
   story goes back to the PO for an explicit decision.
2. Escalations E-1 and E-2 have written answers.
3. `docs/runbook.md` exists and someone other than its author can follow it.
4. A restore has been performed successfully at least once (T-13).
5. The partner has entered at least one real transaction unaided (T-14).
6. US-001 status is updated; anything deliberately left out goes to `tasks/backlog.md`, not silently
   dropped.

## Not in this sprint

See [backlog.md](backlog.md). New requirements discovered during the sprint are added there and
escalated to the Product Owner — they do not enter this sprint without explicit human approval.

## Deployment record — 2026-11-09

| | |
|---|---|
| Host | `host-a`, directory `/srv/ledgernode`, its own compose project and bridge network |
| Images (pinned) | `fireflyiii/core:version-6.7.9`, `postgres:18-alpine`, `alpine:3.20`, `fireflyiii/data-importer:version-2.3.5` |
| LAN address | Firefly III `http://192.168.1.10:8090`, Data Importer `http://192.168.1.10:8091` — both published on that address only |
| Data | `/srv/ledgernode/data/upload` and `/srv/ledgernode/data/db` (Postgres 18 cluster in `data/db/18`) |
| Secrets | `/srv/ledgernode/.env`, `.db.env` and `.importer.env`, mode 600, git-ignored, generated on the host |
| Importer token | Personal access token named `ledger-importer`, created 2026-11-09, expires **2027-11-09**, revoked flag clear. Supplied as `FIREFLY_III_ACCESS_TOKEN` because the importer UI only offers a Client ID field. Must be rotated before expiry, which the runbook (T-15) has to cover |
| Database change | MariaDB (vendor default) replaced by PostgreSQL 18 at the owner's instruction *before* first start, so nothing was migrated and no data existed |
| Verified | db container healthy; `GET /` → 302; `GET /register` → 200; 51 MB cluster written into the bind mount rather than the container layer; LAN request from `192.168.1.12` answered in 0.26 s |
| Owed | both phones in hand, a failed external connection attempt, first-user registration, 2FA enrolment (T-04), then the importer and the CSV import (T-07) |

Recreating the stack from a bare host: copy `infra/firefly/` to `/srv/ledgernode`, create `.env` and
`.db.env` from the examples with fresh 32-character `APP_KEY` and `STATIC_CRON_TOKEN`, create
`data/upload` and `data/db`, then `docker compose up -d`.

## US-002 — verify every import (read-only half delivered, 2026-11-09)

Story: [US-002](../docs/stories/US-002-verify-every-import.md) · Tool: `tools/verify_import.py` ·
Tests: `tests/test_verify_import.py` (17 cases)

| ID | Task | Status |
|---|---|---|
| T-17 | ADR-0002: constraints and tool decisions | Done — `docs/decisions/0002-importer-constraints.md` |
| T-18 | Define the check's contract | Done — arguments, report fields and exit codes are in the module docstring and `--help` |
| T-19 | Read-only verification | Done — API only, pagination asserted, per-day net, balance compared |
| T-20 | Repair behind an explicit flag | **Not started — blocked on T-13** |
| T-21 | Monthly procedure in the runbook | Not started — lands with T-15 |
| T-22 | Prove it on the real ledger | Partial — clean run and both failure modes proven; the repair pass belongs to T-20 |
| T-23 | Architecture overview | Done — `docs/ARCHITECTURE.md` |

### Evidence

| AC | Evidence | Date |
|---|---|---|
| 1 | Clean run: `file 2268` / `ledger 2268`, `607 dates compared, 0 differ`, exit 0 | 2026-11-09 |
| 2 | Interior row deleted from the file → `EXTRA 2026-05-08 withdrawal 190.00 …` plus the differing day; newest row deleted → reported as a row outside the date range | 2026-11-09 |
| 3 | **Not delivered** — gated on the restore rehearsal (T-13) | — |
| 4 | Balance column edited → `file 999.99 | ledger 343.03`, exit 1 | 2026-11-09 |
| 5 | Unreachable host, invalid token, missing file, non-numeric amount and empty balance → exit 2, naming the line, with no traceback | 2026-11-09 |
| 6 | No write verbs exist in the tool; the ledger stayed at 2,269 journals and 343.03 across every test run | 2026-11-09 |

### Gates passed

QA (gate 6) passed AC1, 2, 4, 5 and 6, recording AC3 as not testable rather than as a pass. Code review
(gate 7) requested changes for one blocker — a crash exiting 1, which is the mismatch code — fixed in
`18cb6c5` and locked down by a 17-case suite in `e97aaea`, then approved.

### Deferred, with reasons

- **DEF-1** (QA): when only the balance differs, the message claims a missing edge row; an edited balance
  column is equally likely. To be corrected with T-20 rather than patched separately.
- Nitpicks, not blocking: shebang without an executable bit; `net` recomputed in `main()`; the row
  description is read from the first split.

### Still open from US-001

T-04 (2FA enrolment unconfirmed, phones not checked), T-08, T-09, T-11, T-12, T-13, T-14, T-15, T-16.


