"use client";

import { useEffect, useState } from "react";

import { getDocumentContent, type DocumentContent } from "@/lib/api";

type Props = {
  documentId: string | null;
  highlightedExcerpt?: string | null;
};

export function DocumentViewer({ documentId, highlightedExcerpt = null }: Props) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [error, setError] = useState<{ documentId: string; message: string } | null>(null);

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
      ) : null}
    </section>
  );
}