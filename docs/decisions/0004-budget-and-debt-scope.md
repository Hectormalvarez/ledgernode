# ADR-0004 — Budgets and debt tracking enter scope, and what they can and cannot do

| | |
|---|---|
| **Status** | Accepted, 2026-11-10 |
| **Tasks** | T-21 to T-25 (see sprint) |
| **Story** | [US-004](../stories/US-004-budget-and-debt-visibility.md) |
| **Amends** | US-001 out-of-scope rows "Budgets, piggy banks, savings goals"; backlog B-02, B-07 |
| **Validated against** | Firefly III 6.7.9, PHP 8.5.12, PostgreSQL 18 |

## Context

US-001 excluded budgets, piggy banks and savings goals, on the grounds that bare reporting was enough
to answer "where did it go". The Product Owner now wants the instance to carry a household budget and
a debt payoff plan. That is a scope change, not a configuration change, so it is recorded here rather
than slipped in.

Two things forced the timing rather than the preference. Two years of imported data show the stated
monthly surplus of $540 does not exist — 13 full months net to +$404 in total, about $31/month. And
the largest single outflow relationship is prepaid app, at $780/month net, which the ledger sees as one
anonymous line.

## Decisions

### 1. Budgets and piggy banks are in scope; the rest of the v1 exclusions stand

Budgets, piggy banks and liability accounts are adopted. Every other US-001 exclusion is unchanged:
no per-user identity, no internet exposure, no automatic bank sync, no custom software on top of the
product (X-04 still stands).

### 2. The product measures execution; it does not produce the plan

`PROJECT.md` is explicit: *"It makes the truth visible; it does not advise."* There is no forecasting,
no payoff ordering, no amortisation schedule, no credit-score modelling in Firefly III, and none can
be configured into it. The payoff plan therefore lives outside the instance and the instance is used
to check whether it is being followed. Any future request to make the instance "recommend" something
is a new product decision, not a feature request.

### 3. Budgets are spending limits, not funded envelopes

`auto_budget_type` accepts `reset`, `rollover`, `adjusted` and `none`, with periods from daily to
yearly. A budget with `rollover` carries unspent balance forward, which is close to an envelope, but
no budget holds cash. Firefly cannot move money between buckets. Reporting reads "you spent $912 of
$850", never "you have $850 available".

Consequence: the three-account split (bills / everyday / debt) cannot be modelled as accounts, because
those accounts do not exist at the bank. There is one checking account and one empty savings account.
Separation is therefore created with real transfers to the real savings account, plus piggy banks as
virtual earmarks — never with transactions invented on the imported asset account.

### 4. Account 1 stays a pure mirror of the bank export

Every row in `Bank A` (id 1) must correspond to a row in the bank's CSV. A manual or
automatically-created transaction on that account appears as an `extra` in every verification run and
breaks the balance assertion that makes imports trustworthy. Scheduled transfers and payday entries
must therefore be expressed as budgets and piggy banks, or booked against a separate account, never
posted to account 1.

### 5. Liability accounts are created through the API, and opening balances work in 6.7.9

ADR-0002 §3 recorded that the API cannot set an opening balance in 6.7.9, because `StoreRequest`
validates `opening-balance` while `AccountValidator` compares against `Opening-balance`. That is true
for creating an initial-balance account directly, but **not** for the `opening_balance` field on an
ordinary account: supplying `opening_balance` **and** `opening_balance_date` together satisfies both
`required_with` rules and the request returns 200. Verified 2026-11-10 by creating seven liability
accounts and reading back their balances.

### 6. Liabilities are recorded as `type: liability` with `liability_direction: debit`

`subTitlesByIdentifier` accepts only `asset, expense, revenue, cash, liabilities, liability`, so
`liability_type` (`loan`/`debt`/`mortgage`) and `liability_direction` are required. A debt owed
carries `debit`, which presents as a negative balance — correct for net worth, and the reason the
household's net worth now reads about −$26,000 rather than a flattering $340.

## Consequences

- Net worth becomes honest: assets $340 against liabilities $26,000.
- Seven bills and the debt payoff are now measurable rather than remembered.
- The student loan resuming in May 2027 is visible as a dated obligation, not a vague future problem.
- **The ledger still cannot see roughly half the household's money.** Payroll visible in the account
  is about $2,475/month; one earner's pay was diverted to prepaid app and never arrived here. Budgets
  built on the visible half will read as authoritative and be wrong. Completing the ledger is a
  precondition for trusting any budget, not an optional refinement.
- prepaid app purchasing is opaque. Until daily spending moves to the Bank A debit card — or Cash
  App statements are captured — the grocery and transport budgets cannot be measured.
