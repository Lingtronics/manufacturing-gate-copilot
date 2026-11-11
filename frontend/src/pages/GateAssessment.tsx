import { useState } from "react";
import { ShieldCheck, Filter, MessageSquareText } from "lucide-react";
import { Badge, Card, Citation, Empty } from "../components/ui";
import type { Assessment, Role, Explanation } from "../types";
export function GateAssessmentPage({
  assessment,
  role,
  busy,
  review,
  explanation,
}: {
  assessment: Assessment | null;
  role: Role;
  busy: boolean;
  review: (decision: string, note: string) => void;
  explanation: Explanation | null;
}) {
  const [filter, setFilter] = useState("all");
  const [note, setNote] = useState("");
  if (!assessment)
    return <Empty>Run an assessment from the dashboard first.</Empty>;
  const a = assessment;
  return (
    <>
      <div className="assessment-banner">
        <ShieldCheck size={25} />
        <div>
          <div className="eyebrow">
            Deterministic assessment · Policy {a.policy_version}
          </div>
          <h2>{a.overall_readiness.replaceAll("_", " ")}</h2>
          <p>
            {a.blocker_count} blockers · {a.warning_count} warnings ·{" "}
            {a.requirement_coverage}% validated coverage
          </p>
        </div>
        <Badge value={a.review_status} />
      </div>
      <div className="assessment-layout">
        <div>
          <div className="filter-row">
            <Filter size={16} />
            {["all", "blocker", "insufficient", "warning"].map((f) => (
              <button
                key={f}
                className={filter === f ? "active" : ""}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All findings" : f}
              </button>
            ))}
          </div>
          {a.findings
            .filter((f) => filter === "all" || f.category === filter)
            .map((f) => (
              <Card key={f.id} className={`finding ${f.category}`}>
                <div className="section-heading">
                  <span className="mono">
                    {f.rule_id} · {f.record_id}
                  </span>
                  <Badge value={f.category} />
                </div>
                <h3>{f.message}</h3>
                <p className="tiny">
                  Rule-based finding ·{" "}
                  {f.requirement_ids.join(", ") || "Corrective action record"}
                </p>
                {f.evidence_references.length ? (
                  f.evidence_references.map((r) => (
                    <Citation key={r.id} reference={r} />
                  ))
                ) : (
                  <p className="citation-missing">
                    {f.rule_id === "GATE-001"
                      ? "Missing evidence — no source quotation available."
                      : "Derived from structured source record " +
                        f.record_id +
                        "."}
                  </p>
                )}
              </Card>
            ))}
        </div>
        <aside>
          <Card title="Human review" eyebrow="Separate from launch approval">
            <Badge value={a.review_status} />
            <p>
              Acknowledge the evidence and findings, or request changes.
              Acknowledging this review does not clear blockers.
            </p>
            <label className="field-label" htmlFor="review-note">
              Reviewer note
            </label>
            <textarea
              id="review-note"
              placeholder="Record your review rationale…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={role !== "Reviewer"}
              maxLength={2000}
            />
            <button
              className="primary full"
              disabled={busy || role !== "Reviewer" || !note.trim()}
              onClick={() => {
                review("ACKNOWLEDGED", note);
                setNote("");
              }}
            >
              Acknowledge review
            </button>
            <button
              className="secondary full"
              disabled={busy || role !== "Reviewer" || !note.trim()}
              onClick={() => {
                review("CHANGES_REQUESTED", note);
                setNote("");
              }}
            >
              Request changes
            </button>
            {role !== "Reviewer" && (
              <p className="tiny">
                Switch to the Reviewer demo identity to record a decision.
              </p>
            )}
          </Card>
          <Card
            title="AI interpretation"
            eyebrow={
              explanation?.provider === "llm"
                ? "Optional local model"
                : "Deterministic template"
            }
          >
            <MessageSquareText size={22} />
            <p>{explanation?.summary || "Explanation unavailable."}</p>
            {explanation?.runtime_status === "model_used" && (
              <p className="tiny">
                Local model: {explanation.model} · {explanation.latency_ms} ms ·
                validated model output
              </p>
            )}
            {explanation?.runtime_status === "fallback" && (
              <div className="notice">
                Local model unavailable or output rejected (
                {explanation.fallback_reason?.replaceAll("_", " ")}). Showing
                the deterministic explanation.
              </div>
            )}
            <h4>Suggested review questions</h4>
            <ul className="plain-list">
              {explanation?.review_questions.map((q) => <li key={q}>{q}</li>)}
            </ul>
            {explanation?.provider === "llm" && (
              <details>
                <summary>Model-selected review sequence</summary>
                <ol className="plain-list">
                  {explanation.lines.map((line) => (
                    <li key={line.finding_id}>{line.statement}</li>
                  ))}
                </ol>
              </details>
            )}
            <p className="tiny">{explanation?.limitation}</p>
          </Card>
          <Card title="Assessment provenance">
            <div className="provenance">
              <span>Version</span>
              <strong>{a.assessment_version}</strong>
              <span>Generated</span>
              <strong>
                {new Date(a.generated_at).toLocaleString("en-GB")}
              </strong>
            </div>
            <p className="mono hash">{a.source_snapshot_hash}</p>
          </Card>
        </aside>
      </div>
      <Card title="Human decision log">
        {a.decisions.length ? (
          a.decisions.map((d) => (
            <div className="decision" key={d.id}>
              <Badge value={d.decision} />
              <strong>{d.actor}</strong>
              <p>{d.note}</p>
              <small>{new Date(d.timestamp).toLocaleString("en-GB")}</small>
            </div>
          ))
        ) : (
          <p>No human decisions recorded.</p>
        )}
      </Card>
    </>
  );
}
