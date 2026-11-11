# US-004 — A budget and debt picture that matches reality

| | |
|---|---|
| **ID** | US-004 |
| **Status** | In progress — ledger structure created 2026-11-10 |
| **Date** | 2026-11-10 |
| **Owner** | Product Owner |
| **Epic** | Household finance visibility (v1a) |
| **Depends on** | US-001 (history imported); completeness of imported accounts |

## Description

**As** the household owner
**I want** my fixed bills, discretionary spending and every debt visible against a monthly limit
**So that** I can see whether the plan is being followed, and how far each debt has actually come down

## Context & Scope

The instance was built to answer "where did last month's money go" and does. It was deliberately
not a budgeting tool (US-001 out of scope). Two years of imported history now show the limits of that
position: the household states a $540 monthly surplus, while thirteen full months net to +$404 in
total, and the largest single outflow is an opaque prepaid app pipe at $780/month net.

Debts are also entirely absent from the books. The ledger knows one asset account and no obligations,
so net worth reads $340 when the real figure is −$26,000.

The capability constraints that shape this story are recorded in
[ADR-0004](../decisions/0004-budget-and-debt-scope.md).

### In scope

- Liability accounts for every debt currently claimed on paper, with opening balances.
- Monthly budgets for the bills and living lines the household actually plans to spend.
- Piggy banks for the funds the plan depends on: an emergency buffer, a settlement fund and the
  student-loan resumption fund.
- Rules that categorise the top recurring merchants on import.
- A monthly read: spend against limit per budget, and current balance per debt.

### Out of scope

- Forecasting, projection, "will I have enough on the 1st", or any recommendation. The product does
  not advise; the plan lives outside it.
- Automatic payoff ordering, amortisation schedules, or interest calculations over time.
- Credit-score modelling, pay-for-delete tracking, or dispute workflow.
- Pay-period-length budgets. Firefly's budget periods are daily to yearly; there is no bi-weekly
  period and none can be added.
- Money movement between buckets. Budgets limit spending; they do not hold cash.

## Accepted limitations

1. **A budget cannot be funded.** Firefly reports "$912 spent of $850", never "$850 available". The
   household's three-account split does not exist at the bank, so separation has to come from real
   transfers to the real savings account plus piggy banks as earmarks.
2. **The instance sees one account.** Payroll visible in the ledger is about $2,475/month. Until the
   second income stream and prepaid app purchasing are captured, any budget is measured against
   incomplete data. This limitation is not cosmetic; it caps how much the budgets can be trusted.

## Acceptance Criteria

1. Given the debts on paper, when the instance is opened, then every one appears as a liability
   account with its balance, and net worth equals assets minus liabilities.
2. Given the monthly plan, when the budget list is opened, then each fixed bill and living line has
   a monthly limit, and the limits total no more than the household's actual average income.
3. Given a month of categorised transactions, when the budget report is opened, then spend per budget
   is shown against its limit, and the total equals the sum of that month's expense transactions.
4. Given a debt is paid down outside the instance, then the liability balance can be corrected and
   net worth changes accordingly, with no transaction on the imported asset account being edited.
5. Given the imported asset account, when any budget or piggy bank is used, then no transaction is
   created on that account and every verification run still reports a clean ledger.
6. Given the emergency buffer has a target and date, then the report shows progress toward it as a
   figure, not as a forecast.
7. *(error path)* Given a budget limit larger than the household can fund, when the month closes, then
   the overage is visible as overspend rather than being silently absorbed.

## Success measure (60 days after go-live)

- Every budget has at least one month of real spend recorded against it.
- The debt total moves down by at least $739 (the three small debts) without a new borrowing.
- No month is funded from a 401(k) withdrawal.

## Open questions

1. **Second income stream — answered 2026-11-10.** The Bank B credits are **cash advances against
   hours already worked at Employer B**, through the employer's earned-wage provider — not a fourth income
   stream. That is why payroll deposits in Bank A fall when the transfers rise: it is the same
   paycheck, taken early. Jan–Oct 2026: **214 advances, $34,000, $3,409/month, averaging $159 each —
   roughly one every 1.4 days.** The consequence for this story is that "income" is not a single
   number arriving on a schedule; it is a paycheck being consumed ahead of itself, and a budget built
   on cash-in will be wrong in both directions. Cost of the facility (fee per advance) and gross
   Employer B pay remain unknown and are needed before the income line can be stated honestly.
2. **prepaid app visibility — partially answered 2026-11-10.** Statements for Jan–Oct 2026 were
   captured and parsed by `tools/cashapp_statements.py`: 692 rows, money in $27,000, money out
   $35,000, every statement's own Money In figure matched exactly. They show what the ledger
   could not: $13,000 of card purchases (Store A $4,097, Store C $2,065, Store B $1,588),
   $10,000 of prepaid app credit repayments, and $8,080 of payments funded directly by linked banks.
   Still open: two funding sources appear that are **not** in the ledger at all — **Bank B x0002**
   ($7,250) and **Bank A x0001** ($815) — so the account map is larger than believed.
3. **The repossessed vehicle.** The auto loan balance shown ($5,251) predates the auction. After the
   sale the figure becomes a deficiency balance, which may differ and may be sold on. To be corrected
   once the lender states it.
4. **Rent arrears creditor.** Whether the $1,100 is owed to the current landlord or a previous one
   determines urgency, not just priority.
5. **New job's pay.** The plan assumes it matches the previous $2,609/month. Unconfirmed.

## Technical Guidance

Not defined here. Account types, budget behaviour and the opening-balance finding are in
[ADR-0004](../decisions/0004-budget-and-debt-scope.md).
