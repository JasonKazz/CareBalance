"""Analytical interval optimization, not learned or clinical prediction."""
import json
import math
from pathlib import Path
from backend.models.contracts import evaluate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "shared/request.schema.json").read_text())

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Provide one scenario object.")
    expected = set(SCHEMA["properties"])
    if set(data) != expected:
        raise ValueError("Scenario fields are missing or unrecognized.")
    for name, rule in SCHEMA["properties"].items():
        value = data[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(rule["title"] + " must be a finite number.")
        if rule["type"] == "integer" and int(value) != value:
            raise ValueError(rule["title"] + " must be a whole number.")
        if not rule["minimum"] <= value <= rule["maximum"]:
            raise ValueError(f'{rule["title"]} must be between {rule["minimum"]} and {rule["maximum"]}.')
    return dict(data)

def interval(inputs, scenarios, model):
    units = [s["visits"] if model == "ffs" else inputs["patients"] for s in scenarios]
    costs = [s["contracts"][model]["cost"] for s in scenarios]
    break_even = max(cost / unit for cost, unit in zip(costs, units))
    minimum = max(cost / (1 - inputs["min_margin"] / 100) / unit for cost, unit in zip(costs, units))
    maximum = min(inputs["payer_budget"] / unit for unit in units)
    # Inward rounding: any displayed whole-cent rate satisfies the interval.
    lower = math.ceil(minimum * 100 - 1e-7) / 100
    upper = math.floor(maximum * 100 + 1e-7) / 100
    reasons = []
    if any(not s["contracts"][model]["capacity_ok"] for s in scenarios):
        reasons.append("Appointment demand exceeds capacity. Changing payment alone cannot create appointments.")
    if lower > upper:
        reasons.append("The payment needed to cover costs and the target margin exceeds the insurer budget at whole-cent rates.")
    return {"break_even_rate": math.ceil(break_even * 100 - 1e-7) / 100,
            "minimum_rate": lower, "maximum_rate": upper,
            "recommended_rate": lower if not reasons else None,
            "feasible": not reasons, "reasons": reasons}

def analyze(data):
    inputs = validate(data)
    baseline_visits = inputs["patients"] * inputs["visits_per_patient"]
    baseline = evaluate(inputs, baseline_visits)
    stress = evaluate(inputs, baseline_visits * (1 + inputs["stress_pct"] / 100))
    terms = {model: interval(inputs, [baseline, stress], model) for model in ("ffs", "pmpm")}
    sweep_max = max(100, inputs["stress_pct"])
    sweep = [{"additional_visits_pct": i * sweep_max / 20,
              **evaluate(inputs, baseline_visits * (1 + i * sweep_max / 2000))} for i in range(21)]
    return {"version": 1, "inputs": inputs, "baseline": baseline, "stress": stress,
            "terms": terms, "sweep": sweep,
            "assumptions": [
                "Synthetic planning scenario, not validated clinical or contract advice.",
                "Monthly totals; full collection of payments, constant enrollment, no copays or denials.",
                "Both contracts cover exactly the same modeled clinic visits; other care is excluded.",
                "Fixed costs include existing staffing; per-visit costs are additional and must not double-count staffing.",
                "All demanded visits are costed. Demand above capacity makes a scenario infeasible; patients are not silently removed.",
                "Visit needs are user assumptions. Contract changes do not predict improvements in care.",
                "Minimum margin is surplus divided by revenue. Feasible terms must satisfy both baseline and stress cases.",
                "Lowest feasible payment minimizes payer spend within this simplified model; it is not a fair-price or clinical recommendation."
            ]}
