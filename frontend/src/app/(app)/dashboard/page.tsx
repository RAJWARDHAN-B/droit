"use client";

import { useEffect, useState } from "react";

import { DocumentLibrary } from "@/components/DocumentLibrary";
import { listDocuments, type DocumentSummary } from "@/lib/api";

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reach the API");
    }
  };

  useEffect(() => {
    let active = true;
    listDocuments().then(
      (loadedDocuments) => {
        if (active) {
          setDocuments(loadedDocuments);
          setError(null);
        }
      },
      (cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Unable to reach the API");
        }
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-50">Document dashboard</h1>
      {error ? <p className="mt-4 text-sm text-rose-300">{error}</p> : null}
      <div className="mt-8">
        <DocumentLibrary
          documents={documents}
          loading={false}
          onChanged={() => void refresh()}
          onSelect={() => undefined}
        />
      </div>
    </main>
  );
}
