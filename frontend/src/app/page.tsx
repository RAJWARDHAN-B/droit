"use client";

import { useCallback, useEffect, useState } from "react";

import { DocumentLibrary } from "@/components/DocumentLibrary";
import { DocumentViewer } from "@/components/DocumentViewer";
import { QueryPanel } from "@/components/QueryPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { listDocuments, type DocumentSummary } from "@/lib/api";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to reach the API",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    listDocuments().then(
      (loadedDocuments) => {
        if (active) {
          setDocuments(loadedDocuments);
          setError(null);
          setLoading(false);
        }
      },
      (cause: unknown) => {
        if (active) {
          setError(
            cause instanceof Error ? cause.message : "Unable to reach the API",
          );
          setLoading(false);
        }
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-12">
      <header>
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-amber-400">
              Legal intelligence workspace
            </p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">
              Droit
            </h1>
          </div>
          <p className="hidden max-w-xs text-right text-xs leading-5 text-slate-500 sm:block">
            Private by design. Your contracts are anonymized before they reach
            the retrieval layer.
          </p>
        </div>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400 sm:hidden">
          Privacy-first legal intelligence. Documents are anonymized before
          indexing, and answers cite the passages they came from.
        </p>
      </header>

      <div className="mt-8 grid grid-cols-3 divide-x divide-slate-800 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-4">
        <div className="px-3 first:pl-0">
          <p className="text-2xl font-semibold text-slate-100">{documents.length}</p>
          <p className="mt-1 text-xs text-slate-500">Documents</p>
        </div>
        <div className="px-3">
          <p className="text-2xl font-semibold text-slate-100">
            {documents.reduce((total, document) => total + document.chunk_count, 0)}
          </p>
          <p className="mt-1 text-xs text-slate-500">Indexed chunks</p>
        </div>
        <div className="px-3 last:pr-0">
          <p className="text-2xl font-semibold text-amber-400">
            {documents.filter((document) => (document.risk_score ?? 0) >= 70).length}
          </p>
          <p className="mt-1 text-xs text-slate-500">High risk</p>
        </div>
      </div>

      {error ? (
        <p className="mt-6 rounded-md border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-300">
          {error}
        </p>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <UploadPanel onIngested={() => void refresh()} />
          <DocumentLibrary
            documents={documents}
            loading={loading}
            onChanged={() => void refresh()}
            onSelect={setSelectedDocumentId}
          />
        </div>
        <div className="space-y-6">
          <DocumentViewer documentId={selectedDocumentId} />
          <QueryPanel
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelectDocument={setSelectedDocumentId}
          />
        </div>
      </div>
    </main>
  );
}
