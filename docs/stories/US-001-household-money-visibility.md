# US-001 — Household money visibility with data we can take with us

| | |
|---|---|
| **ID** | US-001 |
| **Status** | Ready for development |
| **Date** | 2026-11-09 |
| **Owner** | Product Owner |
| **Epic** | Household finance visibility (v1) |
| **Depends on** | Nothing |

## Description

**As** one half of a two-person household
**I want** our real spending in one place, usable from both our phones, and exportable
**So that** we can see what happened last month next to the month before, and still own the data

## Context & Scope

The household currently has no single answer to "where did last month's money go?". Bank data lives
in the bank's own interface, and anything gathered by hand lives in a spreadsheet that nobody
maintains. Firefly III is adopted as the whole product; nothing is built on top of it.

Two years of history are already available as a CSV export from Bank A, so month-over-month
comparison is possible from the first day of use rather than after months of accumulation.

### In scope

- One instance on the home network, reachable from both people's phones over home Wi-Fi, never
  exposed to the internet.
- One Bank A account with two years of real history imported from the bank's CSV export.
- Rules that categorise the top recurring merchants automatically.
- Monthly report for the last month with the previous month alongside it, for comparison.
- CSV export of transactions that opens in a spreadsheet.
- Data survives restarts, and a documented backup/restore step exists.
- Sign-in protected by a password plus a second factor.

### Out of scope

| Excluded | Reason |
|---|---|
| Separate logins, view-only rights, per-person attribution | Not possible in Firefly III — see Accepted Limitations |
| Internet exposure (tunnels, public DNS, remote access) | A home tool for two people; not exposing it removes a class of risk. Remote access, if ever wanted, is a separate story with its own risk acceptance |
| Automatic bank sync | Paid, region-limited aggregators; the free CSV export is sufficient |
| Budgets, piggy banks, savings goals | Not needed to answer "where did it go"; revisit after two months of real use |
| Multi-currency | One household, one currency |
| Third-party mobile apps, custom code, integrations | The product already exists |
| Monitoring, high availability, upgrade automation | Disproportionate for a two-person home tool |
| CSV export used as backup | Vendor explicitly warns against it; recovery is a data-store backup |
| Mobile-app-style experience or custom screens | The product's own interface is the interface |

Existing acceptance criteria must not be weakened to fit these exclusions. Any later request for an
excluded item is a new story with its own scope decision.

## Accepted limitations

Agreed with the user on 2026-11-09, recorded here so they are decisions rather than silent gaps:

1. **Both people share one login.** Firefly III keeps every user's administration strictly separate
   and provides no sharing-with-roles; the documented workaround is sharing a password. Therefore the
   partner cannot have her own identity, cannot be given view-only limits, and transactions cannot be
   attributed to a person. The stated functional need — she can view, add and edit — is fully met.
2. **The second factor is shared.** Because the login is shared, both people hold the same
   authenticator secret. This protects the household books from anyone else; it does not distinguish
   the two people.
3. **Export is not recovery.** CSV export serves "use my data in other tools". Recovery relies on a
   separate backup step, as the vendor instructs.
4. **No forecasting or advice.** The product reports what happened; interpretation stays human.
5. **Traffic inside the home network is not encrypted** (decided 2026-11-09, closing escalation E-1).
   Anything on the home Wi-Fi can reach the instance without TLS; protection comes from the sign-in and
   the second factor, plus the instance never being exposed to the internet. This must be revisited the
   moment remote access (backlog B-04) is considered, because unprotected traffic over the internet is a
   different proposition entirely.

## Acceptance Criteria

1. Given the instance is running on the home network, when the partner opens it on her phone over home
   Wi-Fi, then she reaches a sign-in page and sees no financial data before signing in. (Traffic inside
   the home network is not encrypted — an accepted limitation, decided 2026-11-09 under escalation E-1.)
2. Given sign-in is attempted, when the password is supplied but no valid second factor is, then
   access is refused and no financial data is shown.
3. Given either person signs in with the household credentials and the second factor, when
   authentication succeeds, then both see the same accounts and the same transactions, and neither
   person can be distinguished from the other in the records.
4. Given the partner adds a transaction on her phone for a purchase she just made, when the owner
   opens that account on his computer, then the transaction is present with the correct date, amount
   and merchant, and account balances reflect it.
5. Given a Bank A CSV export covering a date range, when it is imported, then every row appears
   exactly once with the correct date, amount and description, and the number of imported rows and
   skipped rows is reported.
6. Given two years of history are imported, when the account is viewed, then its balance equals the
   bank's own balance for the same end date.
7. Given a file is imported whose dates overlap an earlier import, when the import runs, then
   duplicate-looking entries are reported and can be resolved without corrupting balances. (The bank's
   CSV may carry no stable transaction identifier, so "detected and resolvable" is promised rather
   than "never duplicates".)
8. Given rules exist for the top five recurring merchants, when new transactions from those merchants
   are imported, then they are categorised without manual editing; transactions matching no rule
   remain uncategorised rather than being mis-categorised.
9. Given a month of categorised data, when the monthly report is opened, then total spend and spend
   per category are shown for that month with the previous month alongside, and the total equals what
   is obtained by adding up that month's expense transactions manually.
10. Given months of imported history, when the export feature is used, then a CSV of transactions
    (date, amount, description, category, account) is obtained that opens cleanly in a spreadsheet
    with no preparation beforehand; and if the volume causes the in-app export to time out, a
    date-scoped export is still obtainable.
11. *(error path)* Given a statement row with a missing date or an unreadable amount, when the import
    runs, then the import completes, that row is identified to the user, and no other transaction or
    balance is altered.
12. *(recovery path)* Given the documented backup step is followed, when the instance is lost and
    rebuilt, then everything restores and balances and last month's report match what they were
    before.

## Success measure (30 days after go-live)

The story succeeded only if all three hold:

- Statements imported for two consecutive months.
- The monthly report opened at least twice.
- The partner enters at least five transactions on her own, without being asked.

If she never touches it, the two-person requirement failed in practice even though criterion 3 passed.

## Open questions

1. **Settled rows only — confirmed.** The owner checked the export on 2026-11-09: no pending
   transactions are included. Criterion 7 therefore concerns overlapping re-imports only; the
   pending-then-settled double-appearance case does not arise.
2. **Ambiguous date format.** The export writes dates as `11/09/26`, which is month-first but could be
   read either way for any day up to the 12th. If the mapping is wrong, dates and therefore monthly
   totals are silently wrong. Must be confirmed against a known transaction before the two-year import.
3. **Direction is a separate column.** Amounts are unsigned with a `Transaction Type` of `Credit` (and
   presumably `Debit`). If direction is taken from the sign of the amount instead of the type column,
   every expense becomes income. Must be proven on the first import, not assumed.
4. **Possible leading non-data line.** The sample begins with `EXAMPLE DATA` ahead of the column
   headers; confirm whether the real export has any such line, or the header will not be recognised.
5. **Categorisation baseline.** The five merchants for criterion 8 are not yet named; the owner will
   name them at first import.
6. **Backup cadence.** Criterion 12 requires a documented backup step; how often it is performed is
   the owner's operating decision, not a requirement to be invented here.

## Technical Guidance

Not defined here. Hosting, deployment, data-store backup mechanics and CSV column mapping are owned
by the Solution Delivery Manager. No custom code is expected: every criterion above is a capability
of the product as shipped.
