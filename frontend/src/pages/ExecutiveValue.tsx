import { Download, TrendingUp, Calculator } from "lucide-react";
import { Card, gbp } from "../components/ui";
import type { ValueCase } from "../types";
export function ExecutiveValue({
  value,
  download,
  busy,
}: {
  value: ValueCase;
  download: () => void;
  busy: boolean;
}) {
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">
            Executive value case / synthetic assumptions
          </div>
          <h2>Make the investment case transparent.</h2>
          <p>
            Scenario estimates are modelled in GBP. No savings have been
            achieved or customer-validated.
          </p>
        </div>
        <button className="primary" onClick={download} disabled={busy}>
          <Download size={16} />
          Export executive report
        </button>
      </div>
      <div className="baseline-grid">
        {[
          ["Evidence collection", "evidence_collection_hours", "h / gate"],
          ["Review preparation", "preparation_hours", "h / gate"],
          ["Labour cost", "labour_cost_per_hour", "GBP / h"],
          ["Annual reviews", "annual_reviews", "reviews"],
          ["Gate cycle time", "gate_cycle_days", "days"],
          ["Baseline coverage", "evidence_coverage", "fraction"],
        ].map(([title, key, unit]) => (
          <Card key={key}>
            <div className="eyebrow">{title}</div>
            <div className="baseline-number">
              {String(value.baseline[key])}
              <span>{unit}</span>
            </div>
          </Card>
        ))}
      </div>
      <div className="scenario-grid">
        {value.scenarios.map((s, i) => (
          <Card
            key={s.scenario_id}
            className={i === 1 ? "scenario featured" : "scenario"}
          >
            <div className="section-heading">
              <span className="eyebrow">{s.name}</span>
              {i === 1 ? (
                <span className="pill">BASE CASE</span>
              ) : (
                <TrendingUp size={19} />
              )}
            </div>
            <h2>
              {gbp(s.annual_net_benefit)}
              <small>Annual net benefit</small>
            </h2>
            <div className="scenario-bar">
              <span
                style={{ width: `${Number(s.inputs.adoption_rate) * 100}%` }}
              />
            </div>
            <dl className="meta-list">
              <dt>Hours saved / year</dt>
              <dd>{s.annual_hours_saved}</dd>
              <dt>Gross benefit / year</dt>
              <dd>{gbp(s.annual_gross_benefit)}</dd>
              <dt>First-year net benefit</dt>
              <dd>{gbp(s.first_year_net_benefit)}</dd>
              <dt>First-year ROI</dt>
              <dd>
                {s.first_year_roi_percent === null
                  ? "Undefined"
                  : `${s.first_year_roi_percent}%`}
              </dd>
              <dt>Simple payback</dt>
              <dd>
                {s.simple_payback_years === null
                  ? "Not calculable"
                  : `${s.simple_payback_years} years`}
              </dd>
            </dl>
            <details>
              <summary>Inspect versioned assumptions</summary>
              <dl className="meta-list assumptions">
                {Object.entries(s.inputs).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k.replaceAll("_", " ")}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </details>
          </Card>
        ))}
      </div>
      <div className="dashboard-columns">
        <Card
          title="Calculation methodology"
          eyebrow="Deterministic / Decimal arithmetic"
        >
          <Calculator size={25} />
          <p>{value.method}</p>
          <div className="formula">
            Realised hours = (preparation × reduction + collection × reduction)
            × adoption × annual reviews
          </div>
          <p className="tiny">
            Payback uses recurring annual net benefit. Zero implementation cost
            gives an undefined ROI. Non-positive annual net benefit gives no
            calculable payback.
          </p>
        </Card>
        <Card
          title="Recommended next steps"
          eyebrow="Hypothetical consulting proposal"
        >
          <ol className="recommendations">
            <li>
              <strong>Validate the operating baseline.</strong>
              <p>
                Measure collection and review effort with Engineering and
                Quality owners.
              </p>
            </li>
            <li>
              <strong>Resolve evidence and validation risks.</strong>
              <p>Agree owners, acceptance criteria and closure verification.</p>
            </li>
            <li>
              <strong>Test adoption before scaling.</strong>
              <p>
                Run the fictional two-week Validation Sprint described in the
                project charter.
              </p>
            </li>
          </ol>
        </Card>
      </div>
    </>
  );
}
