"use client";

import { useEffect, useState } from "react";

import {
  getDocumentContent,
  getDocumentSummary,
  type DocumentContent,
  type DocumentSummaryText,
  type SummaryStyle,
} from "@/lib/api";

type Props = {
  documentId: string | null;
  highlightedExcerpt?: string | null;
};

export function DocumentViewer({ documentId, highlightedExcerpt = null }: Props) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [error, setError] = useState<{ documentId: string; message: string } | null>(null);
  const [summaryStyle, setSummaryStyle] = useState<SummaryStyle>("legal");
  const [summary, setSummary] = useState<DocumentSummaryText | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      return;
    }
    const selectedDocumentId = documentId;
    let active = true;
    async function loadContent() {
      try {
        const loaded = await getDocumentContent(selectedDocumentId);
        if (active) setContent(loaded);
      } catch (cause: unknown) {
        if (active) {
          setError({
            documentId: selectedDocumentId,
            message: cause instanceof Error ? cause.message : "Unable to load document",
          });
        }
      }
    }
    void loadContent();
    return () => {
      active = false;
    };
  }, [documentId]);

  async function loadSummary(style: SummaryStyle) {
    if (!documentId) return;
    setSummaryStyle(style);
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      setSummary(await getDocumentSummary(documentId, style));
    } catch (cause) {
      setSummaryError(cause instanceof Error ? cause.message : "Unable to generate summary");
    } finally {
      setSummaryLoading(false);
    }
  }

  const visibleContent = content?.id === documentId ? content : null;
  const visibleError = error?.documentId === documentId ? error.message : null;
  const loading = Boolean(documentId && !visibleContent && !visibleError);

  return (
    <section className="gradient-border rounded-xl bg-slate-900/60 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Document viewer</h2>
          <p className="mt-1 text-xs text-slate-500">Privacy view · PII remains anonymized</p>
        </div>
        {visibleContent ? <span className="text-xs text-slate-500">{visibleContent.filename}</span> : null}
      </div>
      {!documentId ? (
        <p className="mt-6 text-sm text-slate-400">Select a document to inspect its indexed text.</p>
      ) : loading ? (
        <p className="mt-6 text-sm text-slate-400">Loading document…</p>
      ) : visibleError ? (
        <p className="mt-6 text-sm text-rose-400">{visibleError}</p>
      ) : visibleContent ? (
        <>
          <div className="mt-4 flex gap-2 border-b border-slate-800 pb-3">
            {(["legal", "layman"] as const).map((style) => (
              <button
                className={`rounded px-3 py-1.5 text-xs ${summaryStyle === style ? "bg-amber-400 text-slate-950" : "text-slate-400 hover:text-slate-100"}`}
                key={style}
                onClick={() => void loadSummary(style)}
                type="button"
              >
                {style === "legal" ? "Legal summary" : "Plain-English summary"}
              </button>
            ))}
          </div>
          {summaryLoading ? <p className="mt-4 text-sm text-slate-400">Generating summary…</p> : null}
          {summaryError ? <p className="mt-4 text-sm text-rose-400">{summaryError}</p> : null}
          {summary && summary.style === summaryStyle && !summaryLoading ? (
            <p className="mt-4 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-sm leading-6 text-slate-300">
              {summary.summary}
            </p>
          ) : null}
          <pre className="mt-4 max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950/70 p-4 font-mono text-xs leading-6 text-slate-300">
          {highlightedExcerpt && visibleContent.text.includes(highlightedExcerpt) ? (
            <>
              {visibleContent.text.split(highlightedExcerpt)[0]}
              <mark className="rounded bg-amber-400/30 px-1 text-amber-100">
                {highlightedExcerpt}
              </mark>
              {visibleContent.text.split(highlightedExcerpt).slice(1).join(highlightedExcerpt)}
            </>
          ) : (
            visibleContent.text
          )}
          </pre>
        </>
      ) : null}
    </section>
  );
}