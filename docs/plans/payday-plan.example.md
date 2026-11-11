# Payday plan — worked example

> **This is a worked example, not a real household.** Every figure is invented and rounded. It
> exists to show the *method*: how to turn a set of due dates and two pay cycles into a plan you
> can actually follow, and how to sequence the first month when income changes.
>
> Copy it, replace the numbers with your own, and keep the copy out of version control
> (`docs/plans/*.md` is git-ignored; only `*.example.md` is published).

| | |
|---|---|
| **Effective from** | the first full check of the new income |
| **Basis** | 12 months of actual transactions, not estimates |
| **Review** | when income changes, or every three months |

## 1. Why a separate document

Firefly III makes the truth visible; it does not advise. It cannot sequence a payday, choose between
rent and a collection, or decide which debt gets the surplus. It also has no forecasting.

So the plan lives here, in prose and tables, and the ledger is used to check whether the plan was
followed. Any plan that needs the tool to generate it is a plan that cannot be argued with.

## 2. Income

| Source | Per check | Cadence | Per month |
|---|---|---|---|
| Earner A | $2,400 | bi-weekly Friday | $5,200 |
| Earner B | $1,000 | bi-weekly Tuesday | $2,167 |
| **Total** | | | **$7,367** |

Bi-weekly is **not** twice monthly. `check × 26 ÷ 12` is the monthly figure; using `× 2` overstates
income by about 8%, which is exactly the size of the hole people fall into.

## 3. Living costs

| Fixed | Amount | | Variable | Amount |
|---|---|---|---|---|
| Rent (incl. water/sewer) | 1,500 | | Groceries | 700 |
| Utilities | 280 | | Fuel | 180 |
| Phone | 150 | | Medical | 100 |
| Internet | 80 | | Subscriptions | 60 |
| Insurance | 140 | | | |
| **Fixed total** | **2,150** | | **Variable total** | **1,040** |

**Living total $3,190. Available for debt and savings: $4,177.**

Take these from measured history, not from what you believe you spend. When the first draft of this
was written, the stated monthly surplus was $540 and the measured figure was $31.

## 4. The first month is the hard one

New income rarely starts cleanly. A first check is often prorated, and the bills do not wait.

| | Amount |
|---|---|
| Money in: check 1 + prorated check 2 + check 3 | 3,700 |
| Rent on the 1st | −1,500 |
| Other fixed bills in the window | −650 |
| Groceries, fuel, fees for ~3.5 weeks | −1,040 |
| **Position** | **+510** |

If that number is negative, you have exactly three honest options, in order of preference:

1. **Do not stop the temporary income source this month.** Stop it after the first full check.
   Keeping it one extra cycle is cheaper than a late fee plus a missed payment.
2. **Trim the variable lines for one window** — groceries to $150/week instead of $175.
3. **Defer a payment that is already scheduled for the same day the next check lands.**

Do not borrow to bridge it. The bridge is what creates the next problem.

## 5. Allocation

| Destination | Per month | Done when |
|---|---|---|
| Emergency buffer | 750 | reaches one month of living (~$3,200) |
| Rent arrears | 500 | balance is zero |
| Small debts | 600 | after written settlement terms, never before |
| Sinking fund (annual costs) | 400 | funded |
| Debt snowball | 1,927 | ongoing |
| **Total** | **4,177** | |

### The rule that keeps it honest

> The day a check lands, the debt and savings share leaves the account first. What remains is
> spendable.

Not a budget and not a virtual earmark — a real transfer to a real savings account. That way it
appears in the bank export, the ledger sees it, and the import stays reconcilable.

Doing it the other way round ("save whatever is left") fails for a structural reason: the spending
expands to the available balance, so nothing is ever left.

## 6. Sequence

| Phase | Window | Actions |
|---|---|---|
| 1 | Weeks 1–4 | Rent on time. No new borrowing. Keep any temporary income this cycle |
| 2 | Weeks 4–8 | Buffer started. Oldest small obligation cleared |
| 3 | Weeks 8–12 | Arrears cleared. Written terms on any collections, then pay |
| 4 | Month 3+ | Buffer complete. Snowball onto the largest remaining balance |

## 7. Cautions

**Collections are not a payment problem, they are a paperwork problem.** Paying a collection without
written terms can restart the clock and leave the mark in place. Get the letter first. This is the
one place where paying early is worse than paying late.

**A liability on hold is still a liability.** A debt deferred to a future date needs a sinking fund
now, or it becomes a crisis on the date it wakes up.

**Do not pay off a low-interest debt before funding a buffer.** One unplanned repair will go back on
a card at a worse rate, and the payoff is undone.

## 8. How to revise

This plan is expected to be wrong within 60 days. Revise it when:

1. **Income changes** — restate §2 and §5 together, never just one.
2. **A balance reaches zero** — move that line to the buffer until the buffer is complete.
3. **A deferred debt approaches** — move its sinking fund line up the sequence.
4. **Three consecutive months pass without new borrowing** — that is the signal you can raise the
   snowball, not the spending.
5. **Any new borrowing appears in a monthly report** — treat it as a plan failure, not a variance.

The ledger checks the plan. It never writes it.
