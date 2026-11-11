export type Role = "Analyst" | "Reviewer" | "Publisher";
export interface EvidenceReference {
  id: string;
  document_id: string;
  revision: string;
  location: string;
  quote: string;
  content_hash: string;
}
export interface Requirement {
  id: string;
  title: string;
  criteria: string;
  criticality: string;
  mandatory: boolean;
  evidence_ids: string[];
  expected_classification: string;
}
export interface Evidence {
  id: string;
  revision: string;
  title: string;
  source_text: string;
  location: string;
  content_hash: string;
  evidence_status: string;
  requirement_ids: string[];
}
export interface Finding {
  id: string;
  rule_id: string;
  category: string;
  requirement_ids: string[];
  record_id: string;
  message: string;
  evidence_references: EvidenceReference[];
  provenance: string;
}
export interface Decision {
  id: string;
  actor: string;
  decision: string;
  note: string;
  timestamp: string;
}
export interface Assessment {
  id: string;
  project_id: string;
  assessment_version: number;
  overall_readiness: string;
  requirement_coverage: string;
  blocker_count: number;
  warning_count: number;
  review_status: string;
  findings: Finding[];
  evidence_references: EvidenceReference[];
  requirement_states: Record<string, string>;
  source_snapshot_hash: string;
  policy_version: string;
  generated_at: string;
  decisions: Decision[];
}
export interface Project {
  id: string;
  name: string;
  participants: string[];
  synthetic: boolean;
  gate: { name: string; policy_version: string };
  latest_assessment: Assessment | null;
}
export interface Scenario {
  scenario_id: string;
  name: string;
  annual_hours_saved: string;
  annual_gross_benefit: string;
  annual_net_benefit: string;
  first_year_net_benefit: string;
  first_year_roi_percent: string | null;
  simple_payback_years: string | null;
  inputs: Record<string, string | number>;
}
export interface ValueCase {
  baseline: Record<string, string | number | null | boolean>;
  scenarios: Scenario[];
  method: string;
  label: string;
}
export interface Approval {
  id: string;
  status: string;
  scene_content_hash: string;
  actor: string;
  destination_board: string;
  timestamp: string;
}
export interface Publication {
  approval_id: string;
  id: string;
  status: string;
  mode: string;
  board_url: string | null;
  result: Record<string, string | number | boolean>;
}
export interface PublicationState {
  workspace: { status: string; approval_id?: string };
  approvals: Approval[];
  publications: Publication[];
  mappings: { key: string; remote_id: string; type: string }[];
  mode: string;
}
export interface Capabilities {
  identity_mode: string;
  miro_mode: string;
  destination_board: string;
  llm_enabled: boolean;
}
export interface Records {
  issue: { id: string; title: string; severity: string; resolved: boolean }[];
  change: {
    id: string;
    title: string;
    validation_complete: boolean;
    status: string;
  }[];
  action: {
    id: string;
    title: string;
    owner: string;
    status: string;
    due_date: string;
  }[];
  policy: { source_text: string }[];
}
export interface Audit {
  id: string;
  event: string;
  actor: string;
  timestamp: string;
  entity_id: string;
  correlation_id: string;
}
export interface Explanation {
  runtime_status: "not_requested" | "model_used" | "fallback";
  fallback_reason: string | null;
  model: string | null;
  latency_ms: number | null;
  review_questions: string[];
  provider: string;
  summary: string;
  limitation: string;
  lines: { finding_id: string; statement: string; question: string }[];
}
