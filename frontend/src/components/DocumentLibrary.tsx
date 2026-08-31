"use client";

import { useState } from "react";

import { deleteDocument, type DocumentSummary } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
  loading: boolean;
  onChanged: () => void;
};

export function DocumentLibrary({ documents, loading, onChanged }: Props) {
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <section className="gradient-border rounded-xl bg-slate-900/60 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Document library</h2>

      {loading ? (
        <p className="mt-4 text-sm text-slate-400">Loading documents…</p>
      ) : documents.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">
          No documents yet. Upload one to start asking questions.
        </p>
      ) : (
        <ul className="mt-4 space-y-3">
          {documents.map((document) => (
            <li
              key={document.id}
              className="flex items-start justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-100">
                  {document.filename}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {document.status} · {document.chunk_count} chunks
                  {document.pii_count !== null
                    ? ` · ${document.pii_count} PII aliases`
                    : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void remove(document.id)}
                disabled={pendingId === document.id}
                className="shrink-0 rounded-md border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-rose-500 hover:text-rose-400 disabled:opacity-50"
              >
                {pendingId === document.id ? "Deleting…" : "Delete"}
              </button>
            </li>
          ))}
        </ul>
      )}

      {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}
    </section>
  );
}
