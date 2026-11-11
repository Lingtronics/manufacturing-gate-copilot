from app.domain.models import Model, Project, GateDefinition, GateAssessment, KpiBaseline, ValueScenario


class ProjectDetail(Project):
    gate: GateDefinition
    latest_assessment: GateAssessment | None


class ValueResult(Model):
    scenario_id: str
    name: str
    synthetic: bool
    modelled: bool
    annual_hours_saved: str
    annual_gross_benefit: str
    annual_net_benefit: str
    first_year_net_benefit: str
    first_year_roi_percent: str | None
    simple_payback_years: str | None
    inputs: ValueScenario


class ValueCaseResponse(Model):
    baseline: KpiBaseline
    scenarios: list[ValueResult]
    label: str
    method: str
