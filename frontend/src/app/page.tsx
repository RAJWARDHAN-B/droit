"use client";

import { useCallback, useEffect, useState } from "react";

import { DocumentLibrary } from "@/components/DocumentLibrary";
import { QueryPanel } from "@/components/QueryPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { listDocuments, type DocumentSummary } from "@/lib/api";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">
          Droit
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          Privacy-first legal intelligence. Documents are anonymized before
          indexing, and answers cite the passages they came from.
        </p>
      </header>

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
          />
        </div>
        <QueryPanel documents={documents} />
      </div>
    </main>
  );
}
