# Explicit monthly model

## Scope

One fictional community clinic and one payer. Constant enrolled population; complete collection of payments. Both payment arrangements cover exactly the same clinic visits. Other services, referral costs, copays, denials, reserves, risk adjustment, contractual exclusions, and quality incentives are omitted. This is not an actuarial model.

All monetary inputs and outputs are USD. Fixed costs are monthly. Additional per-visit costs must exclude costs already in fixed operating costs. Expected visits may be fractional because these are expected monthly totals, not individual patient records.

## Accounting

Let N be enrolled patients, u monthly visits per patient, F fixed monthly costs, c additional visit cost, r the per-visit payment, and p the per-patient monthly payment.

- Visits V = N × u.
- Total care delivery costs C = F + c × V.
- Per-visit revenue R = r × V.
- Per-patient revenue R = p × N.
- Payer spending equals clinic revenue in this simplified two-party model.
- Operating surplus = R − C; operating margin = (R − C) / R.
- Zero revenue gives an undefined percentage margin. The solver uses R × (1 − target margin) ≥ C, which permits the zero-cost, zero-revenue case without division by zero.

Changing a contract never changes assumed visit need or predicts better health outcomes. Above-capacity demand remains in cost calculations; it makes the scenario infeasible rather than silently rationing care. The model does not price capacity expansion.

## Optimization

The objective is to minimize payer spending for a given payment model while meeting constraints in both baseline and the selected higher-utilization stress case. It does not maximize a universal notion of social welfare.

For each case, divide C / (1 − target margin) by payment units (visits or patients) to get the lower rate bound. Divide payer budget by payment units to get the upper rate bound. Intersect both cases: largest lower bound, smallest upper bound. Round lower bound up to cents and upper bound down to cents. Any rate in the resulting interval is financially feasible for both cases. If the interval is empty or either case exceeds appointment capacity, no contract is recommended.

Cost-only break-even excludes the target margin and is reported separately. The plotted sweep is exploratory; the solver guarantees constraints only for baseline and the selected stress case. With the linear formulas and nonnegative visit costs used here, those endpoints also bound intermediate utilization, but not different populations or clinical needs.

Rates and totals are displayed rounded; full calculation values are in the JSON download. Floating point tolerances handle insignificant binary representation errors. This is a prototype, not a financial ledger.

## Intended use and validation gap

A clinic manager could use this interface to ask preliminary questions about offers and assumptions. No clinic has validated these assumptions in this project. Real use needs domain review, contract-specific scope, calibrated costs, staffing mix, quality/access safeguards, and uncertainty beyond a single utilization stress test. No patient records are required or collected.
