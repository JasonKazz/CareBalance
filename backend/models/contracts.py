"""Pure monthly accounting. Costs cover all modeled visits, even above capacity."""
def evaluate(inputs, visits):
    cost = inputs["fixed_cost"] + inputs["visit_cost"] * visits
    revenues = {"ffs": inputs["ffs_rate"] * visits,
                "pmpm": inputs["pmpm_rate"] * inputs["patients"]}
    results = {}
    for name, revenue in revenues.items():
        surplus = revenue - cost
        margin = surplus / revenue * 100 if revenue else None
        capacity_ok = visits <= inputs["capacity"] + 1e-8
        budget_ok = revenue <= inputs["payer_budget"] + 1e-8
        margin_ok = revenue * (1 - inputs["min_margin"] / 100) + 1e-8 >= cost
        results[name] = {
            "revenue": revenue, "payer_spend": revenue, "cost": cost,
            "surplus": surplus, "margin_pct": margin,
            "capacity_ok": capacity_ok, "budget_ok": budget_ok,
            "margin_ok": margin_ok,
            "feasible": capacity_ok and budget_ok and margin_ok,
        }
    return {"visits": visits, "capacity_gap": max(0, visits - inputs["capacity"]),
            "capacity_use_pct": visits / inputs["capacity"] * 100, "contracts": results}
