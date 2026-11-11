# ADR-0006 — Categorisation conventions, and the heuristics we accept

| | |
|---|---|
| **Status** | Accepted, 2026-11-11 |
| **Story** | [US-004](../stories/US-004-budget-and-debt-visibility.md) |
| **Related** | [ADR-0004](0004-budget-and-debt-scope.md), [ADR-0005](0005-three-source-transaction-model.md) |

## Context

US-004 created budgets and liability accounts, but nothing was filed against them: of 1,552
withdrawal splits in 2026, **zero carried a budget** and 84 carried a category. The eight budgets
therefore reported 0% used. Making them measure anything needs categories, rules, and — first — a
way to name transactions whose own statement does not name them.

This ADR records the conventions chosen, **the parts that are guesses**, and how to revise them.

## Decision 1 — What can and cannot be named from the source documents

Bank B's export prints no merchant for most card activity. Account 33 held:

| Statement description | Rows | Nameable? |
|---|---|---|
| `Instant Transfer` | 205 booked as expense | **partly** — the matching prepaid app row names the recipient |
| `Purchase` | 298 | **no** |
| `POS Purchase (Domestic)` | 184 | **no** |
| `ATM Withdrawal (in-network)` | 11 | no |
| `Funds Transfer with Validation` | 312 (credits) | no — these are earned-wage advances |

Only the `Instant Transfer` rows are recoverable, because prepaid app records the recipient on its own
statement (`To Partner from Bank B x0002`). Matching on exact amount within ±3 days resolved
**102 of 205** rows ($6,720). The rest ($5,152) have no prepaid app counterpart and stay unnamed.

**The remaining 582 Bank B rows cannot be named from any document we hold.** This is a property
of the bank's export, not a tooling gap. Rules will never categorise them, and a budget that depends
on them will always be partly blind. The only real fix is to stop spending on that card.

**Explicitly rejected:** guessing a merchant from amount and date alone. A wrong name is worse than
no name, because rules will then file money into the wrong budget with confidence.

## Decision 2 — The money-order heuristic, and its known error rate

Rent moved to money orders after an NSF. Those money orders are indistinguishable from grocery
shopping in the statement: same merchant, same card, no marker.

Accepted heuristic: **any purchase at STORE C / STORE C / Store B / STORE A of $500 or more
is treated as rent.**

Evidence it is mostly right:

| Amount | Pattern | Reads as |
|---|---|---|
| `$1,000` | twice, same store | $1,000 money order + $0 fee |
| `$1,000` | exact | single money order |
| `$750` | exact | single money order |
| `$1,200` | twice, identical | structured payment, not shopping |

**Known false positives:** `$610` and `$800` at Store A could be either. Large grocery runs
for a family of four legitimately reach $500.

**How to narrow it later, in order of effort:**

1. **Per-store thresholds.** Store C money orders cap at $1,000, so `>= $1,000` there is safer than
   `>= $500` at Store A.
2. **The fee-cents signature.** A money order is `$N,000.00` plus a small fee (`$0`, `$0`).
   Matching `amount % 100 < 2` alongside a store match removes most grocery false positives.
3. **One big money order.** Once income allows a single ~$1,700 order, the amount is unique in the
   month and the heuristic becomes a rule rather than a guess. **This is the intended end state** and
   the heuristic should be retired when it arrives.

Any change to this heuristic must be recorded here before it is applied, with the false-positive
rate re-measured on the preceding twelve months.

## Decision 3 — Pass-through money is linked, not invented

Money received from the mother and paid straight out to a pawn loan (PAWN BROKER) is not household
spending. Five of six payments are matched to an equal receipt the same day.

Use Firefly's native link type **`Reimbursement`** (`is (partially) reimbursed by` /
`(partially) reimburses`) between the two transactions, with both sides categorised
`Pass-through - Mom`. The pair nets to zero and stays out of budgets.

**Do not** create an expense account for the mother, and **do not** net the amounts by editing the
bank figures. The link preserves both movements and their relationship.

## Decision 4 — Rule order is load-bearing

Firefly applies rules in `order` within a group, and `stop_processing` halts the chain. Because
several rules match the same merchant, order is not cosmetic:

| # | Trigger | Category | Stop? |
|---|---|---|---|
| 1 | description contains `partner` | Family - Partner | no |
| 2 | description contains `pawn broker` or `relative` | Pass-through - Relative | no |
| 3 | store matches **and** amount >= $500 | Rent | **yes** |
| 4 | STORE A / HE B / WAL MART / STORE E / STORE D | Groceries | yes |
| 5 | CHEVRON / STORE D FUEL / gas | Fuel & Transport | yes |
| 6 | CITY UTILITIES / MOBILE CARRIER / ISP | Utilities | yes |
| 7 | ORTHODONTIST / pharmacy | Medical & Dental | yes |
| 8 | SCHOOL MEALS / QUINCEANERA | Kids & School | yes |
| 9 | HOUR FITNESS / GOOGLE / APPLE | Subscriptions | yes |
| 10 | OVERDRAFT / FEE | Fees & Interest | yes |
| 11 | BANK A AUTO / CRCARDPMT / BNPL A / BNPL B / KOALAFI | Debt Payments | yes |

The rent rule **must** precede the groceries rule, or every money order files as groceries. This is
the single most fragile part of the setup and the first thing to check when a number looks wrong.

## Decision 5 — Rules do not apply retroactively

A rule with trigger `store-journal` fires only on new journals. Existing rows must be backfilled
separately. Any future rule must therefore be shipped in three parts: the rule, the backfill, and the
documentation that says which one was run.

## Decision 6 — `amount_more` triggers do not fire on withdrawals in this build

Rent was first modelled as five rules (`description_contains` a store **and** `amount_more` 500).
They matched **zero** transactions. The cause is in the data, not the configuration: on the asset
side of a withdrawal the amount is stored **negative** (`-1883.97`), so a `> 500` comparison can never
be true. The expense side carries the positive figure, but the rule engine evaluates against the
asset split.

This is not a bug to work around with a different number — `amount_more` cannot express "spending over
$500" on the account being spent from.

**Therefore:** the five rent rules are created but **disabled**, and the fifteen money order
transactions are categorised by explicit assignment (matched on store name plus amount >= $500 across
accounts 1, 32 and 33). The list is deterministic and re-runnable.

**Consequence for the future:** a new money order will **not** be categorised automatically. It must
be picked up by re-running the assignment pass, which is idempotent. Once income allows a single
monthly money order, the better fix is to give that transaction a distinctive description at entry
(for example `MONEY ORDER - RENT`), and then a plain `description_contains` rule handles it forever
with no amount condition at all.

## Decision 7 — Debt payments become transfers, forward only

Paying a liability is a **transfer from the asset account to the liability account**, not an expense.
Booked as an expense it lowers net worth by the payment *and* leaves the debt unchanged, so a debt
being paid down looks like spending and the balance never moves.

Historical payments (197 rows, $12,579) are **not** re-pointed. The liability opening balances were
set to the *current* debt figures, so re-pointing old payments on top of them would either fabricate
history or inflate every balance by the amount already repaid. There is no version where both the
current balance and the historical detail are true, because the debt at the start of the imported
history is unknown.

Forward payment is handled by five rules using the `convert_transfer` action, which takes the
liability account as its value:

| Merchant fragment | Liability account |
|---|---|
| `CRCARDPMT` | Bank A Credit Card |
| `BANK A AUTO` | Bank A Auto Loan (repossessed) |
| `COLLECTOR A` | Collector A Associates |
| `COLLECTOR B` | Collector B Collection |
| `STUDENT LOAN` | Student Loan |

The two category rules for those same merchants (`Debt - Bank A card`, `Debt - Bank A auto`) are
**disabled**, because they carry `stop_processing` and would prevent the conversion from running.

**Unresolved:** rent arrears are paid by money order, which the bank records as a store purchase. Until
those transactions are given a distinctive description, payments against `Past Due Rent` cannot be
separated from grocery spending, so that liability has no forward rule.

## Decision 8 — Rent composition, and why `apply-rules` clobbers it

The monthly rent obligation is:

| Component | Amount |
|---|---|
| Base rent | $1,600 |
| Water and sewer (variable) | $100–150 |
| **Expected payment** | **~$1,681** |
| Late fee when paid late | $160 |

The **Rent budget is $1,681** — base rent plus water. The late fee is deliberately excluded, so a late
month shows as an overage rather than being absorbed. On time reports 100%; late reports about 109%.
That variance *is* the signal.

Measured outflow: **32 rent transactions totalling $35,000** from 2025-05 to 2026-11, about
**$1,853 per month**. That exceeds the $1,681 obligation by roughly $172 — very close to the $160
late fee. The household is paying the full rent; the late fee is a surcharge on top, worth about
**$1,867 per year**.

### The ordering hazard, stated plainly

Rent money orders look exactly like grocery spending: same stores, same cards, no marker. They are
categorised by an explicit assignment pass (store plus amount >= $500), **not** by a rule, because
`amount_more` cannot work on withdrawals (Decision 6).

**Running `firefly-iii:apply-rules` re-categorises those rows as Groceries**, because the Groceries
rules match the same store names and carry `stop_processing`. This was observed: one rule run dropped
Rent from 19 rows / $24,449 to 4 rows / $6,975.

**The assignment pass must therefore be re-run after any rule application.** It is idempotent, so
re-running is always safe. Correct order:

```text
1. edit or add rules
2. php artisan firefly-iii:apply-rules ...
3. re-run the rent assignment pass
```

The permanent fix is to give each money order a distinctive description as it is entered
(`MONEY ORDER - RENT`), which a plain `description_contains` rule can catch above Groceries. That
cannot be done retroactively for account 1, whose descriptions must keep matching the bank's CSV or
`verify_import` breaks.

Earlier landlords are covered by ordinary rules because their descriptions name them:
`YSI LE MONTREAUX` and `PREMIER ASSET`.

## Decision 9 — Bank B retirement, and what it fixes

The Bank B card is tied to the Employer B job and is being closed the week of 2026-11-11. The account is
still active as of the last imported statement (1,193 journals, last transaction 2026-10-31, with
$6,200 of inflow in October alone), so the final statement is a real one.

### What closes with it

Decision 1 recorded that 582 Bank B rows cannot be named from any document we hold, roughly a third
of that card's outflow. **That gap closes permanently when the card stops being used.** No further work
is possible or needed on those historical rows: they stay as unnamed history, correctly dated and
valued, and no rule will ever categorise them.

The earned-wage advance stream also ends here. It reached Bank B as `Funds Transfer with
Validation` — 220 advances in ten months, one every 1.4 days, median $100. This was never extra income;
it was the paycheck consumed early. Its disappearance removes both the fee drain and the reason the
income line never matched the payroll deposits.

### Sequence when the final statement arrives

```text
1. import the final statement as usual
2. confirm the closing balance from the statement matches the account
3. set the account inactive  (active = false)
```

**Deactivate, never delete.** Firefly keeps the history and every report stays correct; deleting would
remove four years of transactions. An inactive account is hidden from pickers and new-entry screens but
remains fully queryable.

### What remains afterwards

Two institutions, not four: **Bank A** (the verified mirror) and **prepaid app**. Every remaining
account can be checked against a statement that names its merchants, so categorisation stops depending
on heuristics. The one exception stays rent, whose money orders are still store purchases.


## Consequences

- Budgets begin to measure spend instead of reading 0%.
- Roughly 582 Bank B rows remain uncategorised by construction. That gap closes for good once the
  card is retired (Decision 9); the historical rows stay unnamed by design.
- The rent heuristic will misfile occasional large grocery runs. Accepted, bounded, documented.
- `Instant Transfer - To <name>` descriptions (102 rows) now carry the recipient, so future rules
  match on a name rather than on amount coincidence.
- STORE D is in-store shopping, not fuel, per the household owner. It belongs with groceries.
