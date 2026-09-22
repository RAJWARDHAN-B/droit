"use client";

import { useEffect, useState } from "react";

import {
  createDraft,
  Draft,
  DraftTemplate,
  exportDraft,
  listDraftTemplates,
  regenerateDraftClause,
  updateDraftClause,
} from "@/lib/api";

export default function DraftingPage() {
  const [templates, setTemplates] = useState<DraftTemplate[]>([]);
  const [selected, setSelected] = useState<DraftTemplate | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [title, setTitle] = useState("New legal draft");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    listDraftTemplates().then((items) => {
      setTemplates(items);
      setSelected(items[0] ?? null);
    }).catch((error: Error) => setMessage(error.message));
  }, []);

  function chooseTemplate(template: DraftTemplate) {
    setSelected(template);
    setInputs({});
    setMessage("");
  }

  async function generate() {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    try {
      setDraft(await createDraft(selected.id, title, inputs));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to generate draft");
    } finally {
      setBusy(false);
    }
  }

  async function saveClause(clauseId: string, heading: string, body: string) {
    if (!draft) return;
    try {
      setDraft(await updateDraftClause(draft.id, clauseId, heading, body));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save clause");
    }
  }

  async function regenerate(clauseId: string) {
    if (!draft) return;
    setBusy(true);
    try {
      setDraft(await regenerateDraftClause(draft.id, clauseId));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to regenerate clause");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto grid w-full max-w-6xl gap-8 px-6 py-10 lg:grid-cols-[20rem_1fr]">
      <aside className="border-r border-slate-800 pr-6">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-cyan-400">Droit studio</p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-50">Drafting</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">Build a clause-structured first draft from a governed template.</p>
        <div className="mt-8 space-y-2">
          {templates.map((template) => (
            <button
              className={`w-full border px-4 py-3 text-left text-sm transition ${selected?.id === template.id ? "border-cyan-400 bg-cyan-400/10 text-cyan-100" : "border-slate-800 text-slate-300 hover:border-slate-600"}`}
              key={template.id}
              onClick={() => chooseTemplate(template)}
              type="button"
            >
              <span className="block font-medium">{template.name}</span>
              <span className="mt-1 block text-xs text-slate-500">{template.clause_outline.length} clauses</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="min-w-0">
        {!draft ? (
          <div className="max-w-2xl">
            <h2 className="text-xl font-medium text-slate-100">Start a draft</h2>
            <label className="mt-6 block text-sm text-slate-300">
              Draft title
              <input className="mt-2 w-full border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400" value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {selected && Object.entries(selected.input_schema).map(([key, definition]) => (
                <label className="text-sm text-slate-300" key={key}>
                  {definition.label}{definition.required ? " *" : ""}
                  <input className="mt-2 w-full border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-cyan-400" value={inputs[key] ?? ""} onChange={(event) => setInputs((current) => ({ ...current, [key]: event.target.value }))} />
                </label>
              ))}
            </div>
            <button className="mt-8 bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50" disabled={busy || !selected} onClick={generate} type="button">
              {busy ? "Generating..." : "Generate draft"}
            </button>
            {message && <p className="mt-4 text-sm text-rose-300">{message}</p>}
          </div>
        ) : (
          <div>
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-6">
              <div><p className="text-xs uppercase tracking-[0.2em] text-cyan-400">Working draft</p><h2 className="mt-2 text-2xl font-semibold text-slate-50">{draft.title}</h2></div>
              <button className="border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400" onClick={() => exportDraft(draft.id)} type="button">Export DOCX</button>
            </div>
            <div className="mt-6 space-y-5">
              {draft.clauses.map((clause) => <ClauseEditor busy={busy} clause={clause} key={clause.id} onRegenerate={() => regenerate(clause.id)} onSave={(heading, body) => saveClause(clause.id, heading, body)} />)}
            </div>
            {message && <p className="mt-4 text-sm text-rose-300">{message}</p>}
          </div>
        )}
      </section>
    </main>
  );
}

function ClauseEditor({ clause, busy, onSave, onRegenerate }: { clause: Draft["clauses"][number]; busy: boolean; onSave: (heading: string, body: string) => void; onRegenerate: () => void }) {
  const [heading, setHeading] = useState(clause.heading);
  const [body, setBody] = useState(clause.body);
  return <article className="border border-slate-800 bg-slate-900/60 p-5">
    <div className="flex items-center justify-between gap-3"><span className="text-xs uppercase tracking-[0.15em] text-slate-500">Clause {clause.ordinal + 1}</span><span className="text-xs text-slate-500">{clause.source}</span></div>
    <input className="mt-3 w-full border-b border-slate-700 bg-transparent pb-2 text-lg font-medium text-slate-100 outline-none focus:border-cyan-400" value={heading} onChange={(event) => setHeading(event.target.value)} />
    <textarea className="mt-4 min-h-36 w-full resize-y border border-slate-800 bg-slate-950 p-3 text-sm leading-6 text-slate-300 outline-none focus:border-cyan-400" value={body} onChange={(event) => setBody(event.target.value)} />
    <div className="mt-4 flex flex-wrap gap-3"><button className="border border-cyan-400/60 px-3 py-2 text-xs text-cyan-200" onClick={() => onSave(heading, body)} type="button">Save clause</button><button className="border border-slate-700 px-3 py-2 text-xs text-slate-300 disabled:opacity-50" disabled={busy} onClick={onRegenerate} type="button">Regenerate</button></div>
    {clause.rationale && <p className="mt-4 border-l-2 border-cyan-400/50 pl-3 text-xs leading-5 text-slate-500">{clause.rationale}</p>}
  </article>;
}
