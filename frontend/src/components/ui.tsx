import type { ReactNode } from "react";
import { CheckCircle2, FileCheck2, ArrowUpRight } from "lucide-react";
import type { EvidenceReference } from "../types";
export function Badge({ value }: { value: string }) {
  const v = value.toLowerCase();
  const tone = [
    "not_ready",
    "blocker",
    "missing",
    "critical",
    "high",
    "conflicting",
    "failed",
    "changes_requested",
  ].includes(v)
    ? "red"
    : [
          "validated",
          "complete",
          "ready_for_review",
          "published",
          "acknowledged",
          "reviewed",
        ].includes(v)
      ? "green"
      : [
            "warning",
            "partial",
            "conditional_review",
            "in_progress",
            "approved",
            "approval_pending",
          ].includes(v)
        ? "amber"
        : "slate";
  return (
    <span className={`badge ${tone}`}>
      <i />
      {value.replaceAll("_", " ")}
    </span>
  );
}
export function Card({
  title,
  eyebrow,
  children,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
export function Citation({ reference }: { reference: EvidenceReference }) {
  return (
    <details className="citation">
      <summary>
        <FileCheck2 size={14} />
        {reference.document_id} · rev {reference.revision}
        <span className="verified">
          <CheckCircle2 size={12} /> Quote verified
        </span>
      </summary>
      <blockquote>{reference.quote}</blockquote>
      <p className="mono">
        {reference.location}
        <br />
        SHA-256 {reference.content_hash}
      </p>
    </details>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <FileCheck2 size={32} />
      <h3>Start with the evidence</h3>
      <p>{children}</p>
    </div>
  );
}
export function ActionLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-button" onClick={onClick}>
      {children}
      <ArrowUpRight size={15} />
    </button>
  );
}
export const gbp = (v: string | number) =>
  new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(Number(v));
