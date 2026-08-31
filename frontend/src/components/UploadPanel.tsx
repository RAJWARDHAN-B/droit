"use client";

import { useState } from "react";

import { pasteDocument, uploadDocument } from "@/lib/api";

type Props = {
  onIngested: () => void;
};

type Mode = "file" | "paste";

export function UploadPanel({ onIngested }: Props) {
  const [mode, setMode] = useState<Mode>("file");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function run(action: () => Promise<{ filename: string }>) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const job = await action();
      setStatus(`Indexed ${job.filename}`);
      setTitle("");
      setText("");
      onIngested();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="gradient-border rounded-xl bg-slate-900/60 p-5">
      <h2 className="text-lg font-semibold text-slate-100">Add a document</h2>
      <p className="mt-1 text-sm text-slate-400">
        PII is replaced with aliases before text is chunked and indexed.
      </p>

      <div className="mt-4 flex gap-2">
        {(["file", "paste"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setMode(option)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              mode === option
                ? "bg-amber-500 text-slate-950 font-medium"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            {option === "file" ? "Upload file" : "Paste text"}
          </button>
        ))}
      </div>

      {mode === "file" ? (
        <label className="mt-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-700 px-4 py-8 text-center hover:border-amber-500/60">
          <span className="text-sm text-slate-300">
            Choose a PDF, DOCX, TXT, CSV, or XLSX file
          </span>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.csv,.xlsx"
            className="hidden"
            disabled={busy}
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) {
                void run(() => uploadDocument(file));
              }
            }}
          />
        </label>
      ) : (
        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void run(() => pasteDocument(title, text));
          }}
        >
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Document title"
            required
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
          />
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste contract text"
            required
            rows={6}
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-amber-500"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
          >
            {busy ? "Processing…" : "Ingest text"}
          </button>
        </form>
      )}

      {busy && mode === "file" ? (
        <p className="mt-3 text-sm text-slate-400">Processing…</p>
      ) : null}
      {status ? <p className="mt-3 text-sm text-emerald-400">{status}</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}
    </section>
  );
}
