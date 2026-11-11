import {
  ExternalLink,
  LockKeyhole,
  LayoutTemplate,
  RefreshCw,
} from "lucide-react";
import { Badge, Card, Empty } from "../components/ui";
import type {
  Assessment,
  PublicationState,
  Capabilities,
  Role,
} from "../types";
export function MiroWorkspace({
  assessment,
  publication,
  capabilities,
  role,
  busy,
  approve,
  publish,
}: {
  assessment: Assessment | null;
  publication: PublicationState | null;
  capabilities: Capabilities;
  role: Role;
  busy: boolean;
  approve: (action: string) => void;
  publish: (id: string) => void;
}) {
  if (!assessment || !publication)
    return <Empty>Run an assessment to generate the local board scene.</Empty>;
  const approval = publication.approvals.find((a) => a.status === "APPROVED");
  const pending = publication.approvals.find(
    (a) => a.status === "APPROVAL_PENDING",
  );
  const reviewed = assessment.decisions.at(-1)?.decision === "ACKNOWLEDGED";
  const published = publication.publications
    .filter(
      (p) =>
        p.status === "PUBLISHED" &&
        publication.workspace.status === "PUBLISHED" &&
        p.approval_id === publication.workspace.approval_id,
    )
    .at(-1);
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">Collaborative review workspace</div>
          <h2>A shared view of readiness.</h2>
          <p>
            Seven sections generated from the assessment. The local preview
            never calls Miro.
          </p>
        </div>
        <span className="pill">
          <LayoutTemplate size={15} />
          {capabilities.miro_mode === "mock"
            ? "MOCK ADAPTER"
            : "LIVE REST ADAPTER"}
        </span>
      </div>
      <div className="workspace-layout">
        <div className="board-shell">
          <div className="board-toolbar">
            <span>
              <i className="dot" />
              Local board preview
            </span>
            <a
              href={`/api/v1/assessments/${assessment.id}/board-preview`}
              target="_blank"
              rel="noreferrer"
            >
              Open full preview
              <ExternalLink size={14} />
            </a>
          </div>
          <iframe
            key={`${assessment.id}-${assessment.decisions.length}`}
            title="Local Miro board preview"
            sandbox=""
            src={`/api/v1/assessments/${assessment.id}/board-preview`}
          />
        </div>
        <aside>
          <Card
            title="Publication controls"
            eyebrow="Explicit approval boundary"
          >
            <Badge value={publication.workspace.status} />
            <div className="notice">
              <LockKeyhole size={18} />
              <span>
                {capabilities.miro_mode === "mock"
                  ? "Mock publication writes to local SQLite only. No real Miro board is created."
                  : "Live writes require prior human authorisation and a valid OAuth token."}
              </span>
            </div>
            <dl className="meta-list">
              <dt>Destination board</dt>
              <dd className="mono">{capabilities.destination_board}</dd>
              <dt>Assessment version</dt>
              <dd>{assessment.assessment_version}</dd>
              <dt>Managed items</dt>
              <dd>{publication.mappings.length}</dd>
            </dl>
            <button
              className="secondary full"
              disabled={
                busy || !reviewed || !["Analyst", "Publisher"].includes(role)
              }
              onClick={() => approve("request")}
            >
              1. Request approval
            </button>
            <button
              className="secondary full"
              disabled={busy || role !== "Publisher" || !pending}
              onClick={() => approve("approve")}
            >
              2. Approve this version
            </button>
            <button
              className="primary full"
              disabled={busy || role !== "Publisher" || !approval}
              onClick={() => approval && publish(approval.id)}
            >
              {published ? <RefreshCw size={15} /> : null}3.{" "}
              {published
                ? "Republish unchanged board"
                : `Publish to ${capabilities.miro_mode === "mock" ? "mock" : "Miro"}`}
            </button>
            {!reviewed && (
              <p className="tiny">
                A Reviewer must acknowledge the assessment first.
              </p>
            )}
            {approval && (
              <p className="mono hash">
                Approved scene: {approval.scene_content_hash}
              </p>
            )}
            {published && (
              <div className="success-note">
                {published.mode === "mock" ? (
                  "Published to local mock storage. Live Miro publication has not occurred."
                ) : (
                  <a
                    href={published.board_url || undefined}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open published Miro board ↗
                  </a>
                )}
                <p>Last reconciliation: {JSON.stringify(published.result)}</p>
              </div>
            )}
          </Card>
          <Card title="Approval history">
            {publication.approvals.length ? (
              publication.approvals.map((a) => (
                <div className="approval" key={a.id}>
                  <Badge value={a.status} />
                  <p>{a.actor}</p>
                  <small>{new Date(a.timestamp).toLocaleString("en-GB")}</small>
                </div>
              ))
            ) : (
              <p className="tiny">No approval requested yet.</p>
            )}
          </Card>
        </aside>
      </div>
      <Card title="Managed-item mapping" eyebrow="Persistent reconciliation">
        <p>
          Only known item IDs are managed. Unrelated board content is preserved.
        </p>
        <details>
          <summary>
            Inspect {publication.mappings.length} saved remote mappings
          </summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Stable key</th>
                  <th>Type</th>
                  <th>Remote ID</th>
                </tr>
              </thead>
              <tbody>
                {publication.mappings.map((m) => (
                  <tr key={m.key}>
                    <td className="mono">{m.key}</td>
                    <td>{m.type}</td>
                    <td className="mono">{m.remote_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Card>
    </>
  );
}
