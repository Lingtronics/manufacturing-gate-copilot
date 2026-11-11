import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard,
  Files,
  ClipboardCheck,
  PanelsTopLeft,
  ChartNoAxesCombined,
  ArrowUpRight,
  Play,
  ChevronDown,
  Factory,
  Check,
  LoaderCircle,
  History,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { api, downloadReport } from "./api/client";
import { Dashboard } from "./pages/Dashboard";
import { EvidenceExplorer } from "./pages/EvidenceExplorer";
import { GateAssessmentPage } from "./pages/GateAssessment";
import { MiroWorkspace } from "./pages/MiroWorkspace";
import { ExecutiveValue } from "./pages/ExecutiveValue";
import { Badge, Card } from "./components/ui";
import type {
  Role,
  Assessment,
  Project,
  Requirement,
  Evidence,
  ValueCase,
  PublicationState,
  Capabilities,
  Records,
  Audit,
  Explanation,
} from "./types";
import "./styles.css";

const PID = "PRJ-NORTHSTAR";
const navigation = [
  { name: "Dashboard", icon: LayoutDashboard, sub: "Programme overview" },
  { name: "Evidence Explorer", icon: Files, sub: "Sources & traceability" },
  {
    name: "Gate Assessment",
    icon: ClipboardCheck,
    sub: "Findings & human review",
  },
  { name: "Miro Workspace", icon: PanelsTopLeft, sub: "Preview & publication" },
  {
    name: "Executive Value Case",
    icon: ChartNoAxesCombined,
    sub: "Assumptions & outcomes",
  },
];
function App() {
  const [page, setPage] = useState("Dashboard");
  const [role, setRole] = useState<Role>("Analyst");
  const [project, setProject] = useState<Project | null>(null);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [value, setValue] = useState<ValueCase | null>(null);
  const [records, setRecords] = useState<Records | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [publication, setPublication] = useState<PublicationState | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [audit, setAudit] = useState<Audit[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showAudit, setShowAudit] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const load = useCallback(async () => {
    const [p, r, e, v, rec, cap, events] = await Promise.all([
      api<Project>(`/projects/${PID}`),
      api<Requirement[]>(`/projects/${PID}/requirements`),
      api<Evidence[]>(`/projects/${PID}/evidence`),
      api<ValueCase>(`/projects/${PID}/value-case`),
      api<Records>(`/projects/${PID}/records`),
      api<Capabilities>("/capabilities"),
      api<Audit[]>("/audit"),
    ]);
    setProject(p);
    setRequirements(r);
    setEvidence(e);
    setValue(v);
    setRecords(rec);
    setCapabilities(cap);
    setAudit(events);
    setAssessment(p.latest_assessment);
    if (p.latest_assessment) {
      const a = p.latest_assessment;
      const [pub, exp] = await Promise.all([
        api<PublicationState>(`/assessments/${a.id}/publication`),
        api<Explanation>(`/assessments/${a.id}/explanation`),
      ]);
      setPublication(pub);
      setExplanation(exp);
    } else {
      setPublication(null);
      setExplanation(null);
    }
  }, []);
  useEffect(() => {
    (async () => {
      try {
        try {
          const s = await api<{ role: Role }>("/session");
          setRole(s.role);
        } catch {
          await api("/demo-sessions", "POST", { role: "Analyst" });
        }
        await load();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    })();
  }, [load]);
  async function act(task: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
      await load();
      setMessage(success);
    } catch (e) {
      setError((e as Error).message);
      await load().catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  const run = () =>
    void act(
      () => api(`/projects/${PID}/assessments`, "POST"),
      "Assessment generated from the source snapshot. Previous approvals are superseded.",
    );
  const switchRole = (next: Role) =>
    void act(async () => {
      await api("/demo-sessions", "POST", { role: next });
      setRole(next);
    }, `Signed in as demo ${next}. This identity system is non-production.`);
  const review = (decision: string, note: string) =>
    assessment &&
    void act(
      () =>
        api(`/assessments/${assessment.id}/review`, "POST", { decision, note }),
      "Human review recorded. Production launch remains unauthorised.",
    );
  const approve = (action: string) =>
    assessment &&
    capabilities &&
    void act(
      () =>
        api(`/assessments/${assessment.id}/publication-approvals`, "POST", {
          action,
          destination_board: capabilities.destination_board,
        }),
      action === "request"
        ? "Publication approval requested."
        : "This assessment version and scene are approved for publication.",
    );
  const publish = (approval_id: string) =>
    assessment &&
    void act(
      () =>
        api(`/assessments/${assessment.id}/publish`, "POST", { approval_id }),
      `${capabilities?.miro_mode === "mock" ? "Local mock" : "Miro"} publication reconciled. Inspect saved item mappings below.`,
    );
  return (
    <div className={`app ${collapsed ? "collapsed" : ""}`}>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("Dashboard");
          }}
        >
          <div className="brand-icon">
            <Factory size={23} />
          </div>
          <div>
            NORTHSTAR<span>Manufacturing intelligence</span>
          </div>
        </a>
        <div className="workspace-label">PROGRAMME WORKSPACE</div>
        <nav>
          {navigation.map((n) => (
            <button
              key={n.name}
              onClick={() => setPage(n.name)}
              className={page === n.name ? "nav-item active" : "nav-item"}
              title={n.name}
            >
              <n.icon size={20} />
              <span>
                {n.name}
                <small>{n.sub}</small>
              </span>
              {page === n.name && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="environment">
            <i className="dot" />
            <span>
              LOCAL DEMO<small>Entirely synthetic data</small>
            </span>
          </div>
          <div className="sidebar-note">
            <strong>Human-led decisions.</strong>
            <p>
              Evidence you can trace.
              <br />
              Assumptions you can inspect.
            </p>
            <a href="/docs" target="_blank" rel="noreferrer">
              API documentation
              <ArrowUpRight size={13} />
            </a>
          </div>
          <button
            className="collapse-button"
            onClick={() => setCollapsed(!collapsed)}
            aria-label="Toggle sidebar"
          >
            {collapsed ? (
              <PanelLeftOpen size={18} />
            ) : (
              <PanelLeftClose size={18} />
            )}
            <span>Collapse workspace</span>
          </button>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span>
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <span className="synthetic-label">SYNTHETIC PROGRAMME</span>
            <button
              className="icon-button"
              onClick={() => setShowAudit(!showAudit)}
              aria-label="Show audit trail"
            >
              <History size={19} />
            </button>
            <label className="identity">
              <span className="avatar">{role[0]}</span>
              <select
                aria-label="Demo identity"
                value={role}
                disabled={busy}
                onChange={(e) => switchRole(e.target.value as Role)}
              >
                {(["Analyst", "Reviewer", "Publisher"] as Role[]).map((r) => (
                  <option key={r} value={r}>
                    Demo {r}
                  </option>
                ))}
              </select>
              <ChevronDown size={13} />
            </label>
          </div>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">NORTHSTAR / GATE 3 READINESS</div>
              <h1>{page}</h1>
              <p>
                {page === "Dashboard"
                  ? "A clear view of the evidence. A confident next conversation."
                  : "Manufacturing Quality & Stage-Gate Review Copilot"}
              </p>
            </div>
            <button
              className="primary"
              disabled={busy || role !== "Analyst"}
              onClick={run}
            >
              {busy ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <Play size={15} />
              )}
              Run assessment
            </button>
          </div>
          {error && (
            <div role="alert" className="alert error">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                ×
              </button>
            </div>
          )}
          {message && (
            <div role="status" className="alert success">
              <Check size={17} />
              {message}
              <button
                onClick={() => setMessage("")}
                aria-label="Dismiss notification"
              >
                ×
              </button>
            </div>
          )}
          {!project || !records || !value || !capabilities ? (
            <Card>
              <div className="empty">
                <LoaderCircle className="spin" />
                <p>
                  {error
                    ? "Check that the backend is running, then reload this page."
                    : "Loading the synthetic programme…"}
                </p>
              </div>
            </Card>
          ) : (
            <>
              {page === "Dashboard" && (
                <Dashboard
                  project={project}
                  assessment={assessment}
                  records={records}
                  publication={publication}
                  run={run}
                  busy={busy}
                  open={setPage}
                />
              )}
              {page === "Evidence Explorer" && (
                <EvidenceExplorer
                  requirements={requirements}
                  evidence={evidence}
                  assessment={assessment}
                />
              )}
              {page === "Gate Assessment" && (
                <GateAssessmentPage
                  assessment={assessment}
                  role={role}
                  busy={busy}
                  review={review}
                  explanation={explanation}
                />
              )}
              {page === "Miro Workspace" && (
                <MiroWorkspace
                  assessment={assessment}
                  publication={publication}
                  capabilities={capabilities}
                  role={role}
                  busy={busy}
                  approve={approve}
                  publish={publish}
                />
              )}
              {page === "Executive Value Case" && (
                <ExecutiveValue
                  value={value}
                  busy={busy || !assessment}
                  download={() =>
                    void act(
                      () => downloadReport(PID),
                      "Executive report downloaded.",
                    )
                  }
                />
              )}
            </>
          )}
          {showAudit && (
            <Card title="Audit trail" eyebrow="Persisted actors & transitions">
              <button
                className="text-button"
                onClick={() => setShowAudit(false)}
              >
                Close audit trail
              </button>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Actor</th>
                      <th>Event</th>
                      <th>Entity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit
                      .slice()
                      .reverse()
                      .map((a) => (
                        <tr key={a.id}>
                          <td>
                            {new Date(a.timestamp).toLocaleString("en-GB")}
                          </td>
                          <td>{a.actor}</td>
                          <td>{a.event}</td>
                          <td className="mono">{a.entity_id}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
          <footer>
            <span>
              <i className="dot" />
              Offline-ready · {capabilities?.miro_mode || "mock"} Miro adapter
            </span>
            <span>
              Policy v1.0 · Decision support only · <Badge value="SYNTHETIC" />
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
