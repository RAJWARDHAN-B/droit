"use client";

import { useState } from "react";

import { askQuestion, type DocumentSummary, type QueryAnswer } from "@/lib/api";

type Props = {
  documents: DocumentSummary[];
};

export function QueryPanel({ documents }: Props) {
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<string>("all");
  const [answer, setAnswer] = useState<QueryAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setAnswer(await askQuestion(question, scope === "all" ? null : scope));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Query failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="gradient-border rounded-xl bg-slate-900/60 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Ask your documents</h2>

      <form className="mt-4 space-y-3" onSubmit={submit}>
        <select
          value={scope}
          onChange={(event) => setScope(event.target.value)}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
        >
          <option value="all">All documents</option>
          {documents.map((document) => (
            <option key={document.id} value={document.id}>
              {document.filename}
            </option>
          ))}
        </select>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What are the termination rights?"
          required
          minLength={3}
          rows={3}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
        >
          {busy ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}

      {answer ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
            <p className="whitespace-pre-wrap text-sm text-slate-100">
              {answer.answer}
            </p>
            <p className="mt-3 text-xs text-slate-500">
              {answer.provider} · {answer.model}
            </p>
          </div>

          {answer.citations.length > 0 ? (
            <div>
              <h3 className="text-sm font-medium text-slate-300">Citations</h3>
              <ol className="mt-2 space-y-2">
                {answer.citations.map((citation, index) => (
                  <li
                    key={citation.chunk_id}
                    className="rounded-md border border-slate-800 bg-slate-950/40 px-3 py-2"
                  >
                    <p className="text-xs font-medium text-amber-400">
                      [{index + 1}] {citation.filename}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {citation.excerpt}
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
