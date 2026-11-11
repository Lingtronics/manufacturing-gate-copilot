import {
  ArrowRight,
  ShieldAlert,
  Activity,
  Clock3,
  CheckCircle2,
} from "lucide-react";
import { Badge, Card, Empty } from "../components/ui";
import type { Assessment, Project, Records, PublicationState } from "../types";
export function Dashboard({
  project,
  assessment,
  records,
  publication,
  run,
  busy,
  open,
}: {
  project: Project;
  assessment: Assessment | null;
  records: Records;
  publication: PublicationState | null;
  run: () => void;
  busy: boolean;
  open: (s: string) => void;
}) {
  const pending = records.change.filter((c) => !c.validation_complete).length;
  return (
    <>
      <div className="programme-strip">
        <div className="programme-mark">
          N<span>↗</span>
        </div>
        <div>
          <div className="eyebrow">Active programme · NS-2026-03</div>
          <h2>{project.name}</h2>
          <p>Engineering → Pilot production → Human stage-gate review</p>
        </div>
        <span className="programme-tag">GATE 03</span>
      </div>
      <div className="metric-grid">
        <Card>
          <span className="metric-label">
            Evidence coverage <Activity size={16} />
          </span>
          <div className="metric">
            {assessment
              ? Number(assessment.requirement_coverage).toFixed(0)
              : "—"}
            <small>%</small>
          </div>
          <p>
            {assessment
              ? `${Object.values(assessment.requirement_states).filter((s) => s === "VALIDATED").length} of ${Object.keys(assessment.requirement_states).length} requirements validated`
              : "Run assessment to calculate"}
          </p>
          <div className="progress">
            <span
              style={{ width: `${assessment?.requirement_coverage || 0}%` }}
            />
          </div>
        </Card>
        <Card>
          <span className="metric-label">
            Quality blockers <ShieldAlert size={16} />
          </span>
          <div className="metric red-text">
            {records.issue
              .filter(
                (i) => !i.resolved && ["HIGH", "CRITICAL"].includes(i.severity),
              )
              .length.toString()
              .padStart(2, "0")}
          </div>
          <p>Unresolved high / critical issues</p>
          <span className="tiny red-text">Requires closure verification</span>
        </Card>
        <Card>
          <span className="metric-label">
            Pending validation <Clock3 size={16} />
          </span>
          <div className="metric">{String(pending).padStart(2, "0")}</div>
          <p>Engineering changes incomplete</p>
          <span className="tiny">Approved ≠ validated</span>
        </Card>
        <Card>
          <span className="metric-label">
            Review workflow <CheckCircle2 size={16} />
          </span>
          <div className="status-metric">
            <Badge value={assessment?.review_status || "DRAFT"} />
          </div>
          <p>
            Publication:{" "}
            {publication?.workspace.status.replaceAll("_", " ") || "PREVIEW"}
          </p>
          <span className="tiny">Human decision required</span>
        </Card>
      </div>
      <div className="dashboard-columns">
        <Card className="readiness-card">
          <div className="eyebrow">Gate 3 · Readiness assessment</div>
          <div className="readiness-title">
            <h2>
              {assessment
                ? "Open issues need a human-led resolution."
                : "Turn fragmented records into a clear review."}
            </h2>
            <div className="gate-emblem">
              03<span>GATE</span>
            </div>
          </div>
          {assessment ? (
            <>
              <Badge value={assessment.overall_readiness} />
              <p className="readiness-copy">
                {assessment.blocker_count} deterministic blockers stand between
                the current evidence pack and review readiness. Missing safety
                evidence, unresolved quality issues, and change validation need
                attention.
              </p>
              <div className="readiness-stats">
                <div>
                  <strong>{assessment.findings.length}</strong>
                  <span>Total findings</span>
                </div>
                <div>
                  <strong>{assessment.warning_count}</strong>
                  <span>Review warnings</span>
                </div>
                <div>
                  <strong>v{assessment.assessment_version}</strong>
                  <span>Assessment version</span>
                </div>
              </div>
              <button
                className="primary"
                onClick={() => open("Gate Assessment")}
              >
                Review assessment
                <ArrowRight size={17} />
              </button>
            </>
          ) : (
            <>
              <p className="readiness-copy">
                Evaluate 15 gate requirements against the synthetic source pack.
                The policy defines readiness; the copilot makes the evidence
                traceable.
              </p>
              <button className="primary" disabled={busy} onClick={run}>
                Run first assessment
                <ArrowRight size={17} />
              </button>
            </>
          )}
          <div className="human-note">
            Decision support only. Production launch is never authorised by this
            application.
          </div>
        </Card>
        <Card title="Attention queue" eyebrow="Priority review">
          <div className="queue">
            {records.issue
              .filter((i) => !i.resolved)
              .map((i, n) => (
                <button key={i.id} onClick={() => open("Gate Assessment")}>
                  <span className="queue-number">
                    {String(n + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <strong>{i.title}</strong>
                    <span>{i.id} · Quality</span>
                  </div>
                  <Badge value={i.severity} />
                </button>
              ))}
          </div>
          <button
            className="text-button"
            onClick={() => open("Evidence Explorer")}
          >
            Explore the source evidence <ArrowRight size={15} />
          </button>
        </Card>
      </div>
      <Card>
        <div className="section-heading">
          <div>
            <div className="eyebrow">A transparent decision trail</div>
            <h2>From source to shared understanding</h2>
          </div>
          <span className="tiny">Four functions. One review.</span>
        </div>
        <div className="workflow">
          {[
            "01 / Collect evidence",
            "02 / Assess against policy",
            "03 / Human review",
            "04 / Approve & publish",
          ].map((s, i) => (
            <div key={s}>
              <span className={assessment && i < 2 ? "step done" : "step"}>
                {assessment && i < 2 ? "✓" : i + 1}
              </span>
              <strong>{s.split(" / ")[1]}</strong>
              <p>
                {
                  [
                    "Revisioned documents & stable IDs",
                    "Six deterministic gate rules",
                    "Separate reviewer permissions",
                    "Version-bound Miro approval",
                  ][i]
                }
              </p>
            </div>
          ))}
        </div>
      </Card>
      {!assessment && (
        <Empty>
          Run your first assessment to create findings, verified citations, a
          board scene and an executive report.
        </Empty>
      )}
    </>
  );
}
