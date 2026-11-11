from decimal import Decimal, ROUND_HALF_UP
from app.domain.models import KpiBaseline, ValueScenario
from app.persistence.store import Store


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate(baseline: KpiBaseline, scenario: ValueScenario) -> dict:
    hours = (
        (
            baseline.preparation_hours * scenario.preparation_reduction
            + baseline.evidence_collection_hours * scenario.collection_reduction
        )
        * scenario.adoption_rate
        * scenario.annual_review_volume
    )
    gross = hours * baseline.labour_cost_per_hour
    net = gross - scenario.annual_operating_cost
    first = net - scenario.implementation_cost
    return {
        "scenario_id": scenario.id,
        "name": scenario.name,
        "synthetic": True,
        "modelled": True,
        "annual_hours_saved": money(hours),
        "annual_gross_benefit": money(gross),
        "annual_net_benefit": money(net),
        "first_year_net_benefit": money(first),
        "first_year_roi_percent": money(first / scenario.implementation_cost * 100)
        if scenario.implementation_cost
        else None,
        "simple_payback_years": money(scenario.implementation_cost / net) if net > 0 else None,
        "inputs": scenario.model_dump(mode="json"),
    }


def value_case(store: Store, project_id: str) -> dict:
    raw = next(b for b in store.all("baseline") if b["project_id"] == project_id)
    baseline = KpiBaseline.model_validate(raw)
    scenarios = [ValueScenario.model_validate(s) for s in store.all("scenario")]
    return {
        "baseline": baseline.model_dump(mode="json"),
        "scenarios": [calculate(baseline, s) for s in scenarios],
        "label": "Synthetic / modelled — no achieved savings",
        "method": "Adoption multiplies realised hours saved. Gross benefit = hours × labour rate. Net = gross − operating cost. First-year ROI = (net − implementation)/implementation. Payback = implementation/positive annual net benefit. Undefined ratios return null. No defect avoidance, revenue uplift or launch acceleration assumed.",
    }
