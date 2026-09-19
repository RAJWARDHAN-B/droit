"use client";

import { useEffect, useState } from "react";

import { DocumentViewer } from "@/components/DocumentViewer";
import { QueryPanel } from "@/components/QueryPanel";
import { listDocuments, type Citation, type DocumentSummary } from "@/lib/api";

export default function DocumentPage({
  params,
}: {
  params: { id: string };
}) {
  const [selectedDocumentId, setSelectedDocumentId] = useState(params.id);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [highlightedExcerpt, setHighlightedExcerpt] = useState<string | null>(null);

  useEffect(() => {
    listDocuments().then((loadedDocuments) => setDocuments(loadedDocuments));
  }, []);

  function selectCitation(citation: Citation) {
    setSelectedDocumentId(citation.document_id);
    setHighlightedExcerpt(citation.excerpt);
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-50">Document workspace</h1>
      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <DocumentViewer
          documentId={selectedDocumentId}
          highlightedExcerpt={highlightedExcerpt}
        />
        <QueryPanel
          documents={documents}
          selectedDocumentId={selectedDocumentId}
          onSelectDocument={setSelectedDocumentId}
          onSelectCitation={selectCitation}
        />
      </div>
    </main>
  );
}
