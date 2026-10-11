# Repricing model and interpretation

The calculation holds historical annual service volumes constant. For each exact code selected by the user:

- Current reimbursement = annual volume × current rate.
- Proposed reimbursement = annual volume × confirmed proposed rate.
- Difference = proposed minus current.
- Overall difference sums only matched services on both sides.
- Volume coverage = matched annual volume / total annual volume.
- Reimbursement coverage = current matched reimbursement / all current reimbursement; undefined if the denominator is zero.
- Uniform break-even uplift = max(0, current matched / proposed matched − 1), before cent rounding; undefined for zero proposed reimbursement.

Counteroffers increase confirmed rates uniformly, round each rate to cents using Decimal ROUND_HALF_UP, then recompute totals. All core monetary calculations use Decimal. JSON numbers and visual totals are presentation values. Dollar amounts are limited to $1 million per input service rate and annual service counts to 1 million per code.

Unmatched services have unknown proposed reimbursement, not zero reimbursement. Duplicate activity codes must be aggregated before upload. Multiple proposed alternatives require explicit selection of one per code. A source-presence check verifies only that quoted text, code, and rate appear; it does not verify whether that rate applies legally or clinically.

Inputs cannot describe modifiers not included in the exact code, patient/payer responsibility splits, collection losses, payment timing, utilization changes, quality incentives, or all conditions. Review effective dates, service scope, missing addenda, eligibility, and all applicable contract rules independently. This is a narrow decision-support prototype, not general contract interpretation or calibrated forecasting.
