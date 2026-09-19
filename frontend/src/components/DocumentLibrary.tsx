"use client";

import { useState } from "react";
import { Search, ShieldAlert, Trash2 } from "lucide-react";

import { deleteDocument, type DocumentSummary } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
  loading: boolean;
  onChanged: () => void;
  onSelect: (documentId: string) => void;
};

export function DocumentLibrary({ documents, loading, onChanged, onSelect }: Props) {
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");

  async function remove(documentId: string) {
    setPendingId(documentId);
    setError(null);
    try {
      await deleteDocument(documentId);
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Delete failed");
    } finally {
      setPendingId(null);
    }
  }

  const visibleDocuments = documents.filter((document) => {
    const matchesSearch = document.filename
      .toLowerCase()
      .includes(search.trim().toLowerCase());
    const score = document.risk_score ?? 0;
    const matchesRisk =
      riskFilter === "all" ||
      (riskFilter === "low" && score < 35) ||
      (riskFilter === "medium" && score >= 35 && score < 70) ||
      (riskFilter === "high" && score >= 70);
    return matchesSearch && matchesRisk;
  });

  return (
    <section className="gradient-border rounded-xl bg-slate-900/60 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Document library</h2>

      {!loading && documents.length > 0 ? (
        <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto]">
          <label className="relative block">
            <Search
              aria-hidden="true"
              className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500"
            />
            <span className="sr-only">Search documents</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search documents"
              className="w-full rounded-md border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-sm text-slate-100 outline-none focus:border-amber-500"
            />
          </label>
          <label>
            <span className="sr-only">Filter by risk</span>
            <select
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-amber-500 sm:w-auto"
            >
              <option value="all">All risk levels</option>
              <option value="low">Low risk</option>
              <option value="medium">Medium risk</option>
              <option value="high">High risk</option>
            </select>
          </label>
        </div>
      ) : null}

      {loading ? (
        <p className="mt-4 text-sm text-slate-400">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">
          No documents yet. Upload one to start asking questions.
        </p>
      ) : visibleDocuments.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">No documents match this view.</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {visibleDocuments.map((document) => {
            const risk = document.risk_score ?? 0;
            const riskLabel = risk >= 70 ? "High" : risk >= 35 ? "Medium" : "Low";
            const riskClass =
              risk >= 70
                ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                : risk >= 35
                  ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                  : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
            return (
            <li
              key={document.id}
              className="flex items-start justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="flex items-center gap-2 truncate text-sm font-medium text-slate-100">
                  <button
                    type="button"
                    onClick={() => onSelect(document.id)}
                    className="truncate text-left hover:text-amber-300"
                  >
                    {document.filename}
                  </button>
                  <span className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${riskClass}`}>
                    <ShieldAlert aria-hidden="true" className="size-3" />
                    {riskLabel} · {Math.round(risk)}
                  </span>
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {document.status} · {document.chunk_count} chunks
                  {document.pii_count !== null
                    ? ` · ${document.pii_count} PII aliases`
                    : ""}
                </p>
                {document.risk_breakdown ? (
                  <details className="mt-2 text-xs text-slate-500">
                    <summary className="cursor-pointer hover:text-slate-300">
                      View risk findings
                    </summary>
                    <div className="mt-2 space-y-1 pl-3">
                      {Array.isArray(document.risk_breakdown.missing_clauses) &&
                      document.risk_breakdown.missing_clauses.length > 0 ? (
                        <p>
                          Missing clauses: {document.risk_breakdown.missing_clauses.join(", ")}
                        </p>
                      ) : null}
                      {Array.isArray(document.risk_breakdown.asymmetric_terms) &&
                      document.risk_breakdown.asymmetric_terms.length > 0 ? (
                        <p>
                          Asymmetric terms: {document.risk_breakdown.asymmetric_terms.join(", ")}
                        </p>
                      ) : null}
                      {Array.isArray(document.risk_breakdown.auto_renewal_terms) &&
                      document.risk_breakdown.auto_renewal_terms.length > 0 ? (
                        <p>
                          Auto-renewal: {document.risk_breakdown.auto_renewal_terms.join(", ")}
                        </p>
                      ) : null}
                      {Array.isArray(document.risk_breakdown.llm_findings) &&
                      document.risk_breakdown.llm_findings.length > 0 ? (
                        <p>
                          Review notes: {document.risk_breakdown.llm_findings.join("; ")}
                        </p>
                      ) : null}
                    </div>
                  </details>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => void remove(document.id)}
                disabled={pendingId === document.id}
                aria-label={`Delete ${document.filename}`}
                title="Delete document"
                className="shrink-0 rounded-md border border-slate-700 p-2 text-slate-400 hover:border-rose-500 hover:text-rose-400 disabled:opacity-50"
              >
                <Trash2 aria-hidden="true" className="size-4" />
              </button>
            </li>
            );
          })}
        </ul>
      )}

      {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}
    </section>
  );
}
