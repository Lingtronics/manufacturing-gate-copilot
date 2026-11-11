import { useMemo, useState } from "react";
import { Search, FileText, Link2 } from "lucide-react";
import { Badge, Card, Citation } from "../components/ui";
import type { Assessment, Evidence, Requirement } from "../types";
export function EvidenceExplorer({
  requirements,
  evidence,
  assessment,
}: {
  requirements: Requirement[];
  evidence: Evidence[];
  assessment: Assessment | null;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const docs = useMemo(
    () =>
      evidence.filter(
        (d) =>
          (!selected || d.requirement_ids.includes(selected)) &&
          `${d.id} ${d.title} ${d.source_text}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [query, selected, evidence],
  );
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">Source evidence / traceability</div>
          <h2>Every conclusion starts here.</h2>
          <p>
            Ten logical documents, eleven revisions. Conflicts stay visible
            until a human reconciles them.
          </p>
        </div>
        <span className="pill">
          <Link2 size={14} /> SHA-256 anchored sources
        </span>
      </div>
      <div className="evidence-layout">
        <Card title="Gate requirements">
          <button
            className={`requirement-row ${selected === null ? "selected" : ""}`}
            onClick={() => setSelected(null)}
          >
            All supporting documents <span>11</span>
          </button>
          {requirements.map((r) => (
            <button
              key={r.id}
              className={`requirement-row ${selected === r.id ? "selected" : ""}`}
              onClick={() => setSelected(r.id)}
            >
              <span>
                <small className="mono">
                  {r.id} · {r.criticality}
                </small>
                <strong>{r.title}</strong>
                <Badge
                  value={assessment?.requirement_states[r.id] || "NOT ASSESSED"}
                />
              </span>
            </button>
          ))}
        </Card>
        <div>
          <label className="search-box">
            <Search size={18} />
            <input
              aria-label="Search evidence"
              placeholder="Search by document ID or source text…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <span>{docs.length} sources</span>
          </label>
          {selected && (
            <div className="notice">
              {requirements.find((r) => r.id === selected)?.criteria}
            </div>
          )}
          {docs.map((d) => (
            <Card key={d.id + d.revision} className="source-card">
              <div className="section-heading">
                <span className="document-id">
                  <FileText size={18} />
                  {d.id}
                  <span>REV {d.revision}</span>
                </span>
                <Badge value={d.evidence_status} />
              </div>
              <h2>{d.title}</h2>
              <pre className="source-text">{d.source_text}</pre>
              <div className="source-footer">
                <span>{d.requirement_ids.join(" · ")}</span>
                <span className="mono">{d.content_hash.slice(0, 16)}…</span>
              </div>
              {assessment?.evidence_references
                .filter(
                  (r) => r.document_id === d.id && r.revision === d.revision,
                )
                .map((r) => <Citation key={r.id} reference={r} />)}
              {d.evidence_status === "MISSING" && (
                <p className="tiny red-text">
                  Placeholder metadata only — no validated source supplied.
                </p>
              )}
            </Card>
          ))}
          {docs.length === 0 && (
            <Card>
              No matching evidence. Clear the search or select another
              requirement.
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
