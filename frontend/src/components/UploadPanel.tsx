"use client";

import { useState } from "react";
import { FileUp, UploadCloud, X } from "lucide-react";

import { getProcessingJob, pasteDocument, uploadDocument, type ProcessingJob } from "@/lib/api";

type Props = {
  onIngested: () => void;
};

type Mode = "file" | "paste";
type UploadState = "queued" | "uploading" | "done" | "error";
type UploadItem = {
  id: string;
  file: File;
  state: UploadState;
  stage?: string;
  error?: string;
};

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".txt", ".csv", ".xlsx"];

export function UploadPanel({ onIngested }: Props) {
  const [mode, setMode] = useState<Mode>("file");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  function addFiles(files: File[]) {
    const accepted = files.filter((file) =>
      ACCEPTED_EXTENSIONS.some((extension) => file.name.toLowerCase().endsWith(extension)),
    );
    setQueue((current) => [
      ...current,
      ...accepted.map((file) => ({
        id: `${file.name}-${file.lastModified}-${crypto.randomUUID()}`,
        file,
        state: "queued" as const,
      })),
    ]);
  }

  async function uploadQueue() {
    if (queue.length === 0) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    let completed = 0;
    for (const item of queue) {
      if (item.state === "done") {
        completed += 1;
        continue;
      }
      setQueue((current) =>
        current.map((entry) =>
          entry.id === item.id ? { ...entry, state: "uploading" } : entry,
        ),
      );
      try {
        const job = await uploadDocument(item.file);
        await waitForJob(job, item.id);
        completed += 1;
        setQueue((current) =>
          current.map((entry) =>
            entry.id === item.id
              ? { ...entry, state: "done", stage: "done" }
              : entry,
          ),
        );
      } catch (cause) {
        const message = cause instanceof Error ? cause.message : "Upload failed";
        setQueue((current) =>
          current.map((entry) =>
            entry.id === item.id
              ? { ...entry, state: "error", error: message }
              : entry,
          ),
        );
      }
    }
    setStatus(`${completed} of ${queue.length} document${queue.length === 1 ? "" : "s"} indexed`);
    setBusy(false);
    onIngested();
  }

  async function waitForJob(initialJob: ProcessingJob, itemId: string) {
    let job = initialJob;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      setQueue((current) =>
        current.map((entry) =>
          entry.id === itemId ? { ...entry, stage: job.stage } : entry,
        ),
      );
      if (job.document_status === "ready") return;
      if (job.document_status === "failed") {
        throw new Error(job.error_message ?? "Document processing failed");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      job = await getProcessingJob(job.job_id);
    }
    throw new Error("Document processing timed out");
  }

  async function runPaste() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const job = await pasteDocument(title, text);
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
        <>
          <div
            onDragEnter={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              addFiles(Array.from(event.dataTransfer.files));
            }}
            className={`mt-4 rounded-lg border border-dashed px-4 py-8 text-center transition ${
              dragging
                ? "border-amber-400 bg-amber-400/10"
                : "border-slate-700 hover:border-amber-500/60"
            }`}
          >
          <UploadCloud className="mx-auto size-7 text-amber-400" aria-hidden="true" />
          <p className="mt-2 text-sm text-slate-300">
            Drop one or more supported files here
          </p>
          <p className="mt-1 text-xs text-slate-500">PDF, DOCX, TXT, CSV, or XLSX</p>
          <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-amber-500/60">
            <FileUp className="size-4" aria-hidden="true" />
            Choose files
            <input
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="hidden"
              multiple
              disabled={busy}
              onChange={(event) => {
                addFiles(Array.from(event.target.files ?? []));
                event.target.value = "";
              }}
            />
          </label>
          </div>
          {queue.length > 0 ? (
          <div className="mt-4 space-y-2">
            {queue.map((item) => (
              <div key={item.id} className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm">
                <span className="min-w-0 flex-1 truncate text-slate-300">{item.file.name}</span>
                <span className={item.state === "error" ? "text-rose-400" : item.state === "done" ? "text-emerald-400" : "text-slate-500"}>
                  {item.state === "uploading"
                    ? item.stage
                      ? `${item.stage.replaceAll("_", " ")}…`
                      : "Uploading…"
                    : item.state === "done"
                      ? "Indexed"
                      : item.state === "error"
                        ? item.error
                        : "Queued"}
                </span>
                {item.state !== "uploading" ? (
                  <button
                    type="button"
                    aria-label={`Remove ${item.file.name}`}
                    title="Remove file"
                    onClick={() => setQueue((current) => current.filter((entry) => entry.id !== item.id))}
                    className="text-slate-500 hover:text-slate-200"
                  >
                    <X className="size-4" aria-hidden="true" />
                  </button>
                ) : null}
              </div>
            ))}
            <button
              type="button"
              onClick={() => void uploadQueue()}
              disabled={busy || queue.every((item) => item.state === "done")}
              className="mt-2 inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            >
              <UploadCloud className="size-4" aria-hidden="true" />
              {busy ? "Processing…" : "Index queued files"}
            </button>
          </div>
          ) : null}
        </>
      ) : (
        <form
          className="mt-4 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void runPaste();
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

      {status ? <p className="mt-3 text-sm text-emerald-400">{status}</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}
    </section>
  );
}
