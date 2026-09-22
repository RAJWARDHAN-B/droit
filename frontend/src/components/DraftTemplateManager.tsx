"use client";

import { FormEvent, useState } from "react";

import {
  createDraftTemplate,
  deleteDraftTemplate,
  DraftTemplate,
  DraftTemplateInput,
  updateDraftTemplate,
} from "@/lib/api";

type InputRow = { label: string; required: boolean };
type ClauseRow = { heading: string; purpose: string };

const emptyForm = {
  name: "",
  documentType: "",
  inputs: [{ label: "", required: true }] as InputRow[],
  clauses: [{ heading: "", purpose: "" }] as ClauseRow[],
};

function inputKey(label: string): string {
  return label
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function toForm(template: DraftTemplate) {
  return {
    name: template.name,
    documentType: template.document_type,
    inputs: Object.values(template.input_schema).map((definition) => ({
      label: definition.label,
      required: Boolean(definition.required),
    })),
    clauses: template.clause_outline.map((clause) => ({
      heading: clause.heading,
      purpose: clause.purpose ?? "",
    })),
  };
}

export default function DraftTemplateManager({
  templates,
  onChanged,
}: {
  templates: DraftTemplate[];
  onChanged: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const authored = templates.filter((template) => !template.is_builtin);

  function startNew() {
    setEditingId(null);
    setForm(emptyForm);
    setMessage("");
    setOpen(true);
  }

  function startEdit(template: DraftTemplate) {
    setEditingId(template.id);
    setForm(toForm(template));
    setMessage("");
    setOpen(true);
  }

  function buildPayload(): DraftTemplateInput {
    const input_schema: DraftTemplateInput["input_schema"] = {};
    for (const row of form.inputs) {
      const key = inputKey(row.label);
      if (key) input_schema[key] = { label: row.label.trim(), required: row.required };
    }
    return {
      name: form.name.trim(),
      document_type: form.documentType.trim(),
      input_schema,
      clause_outline: form.clauses
        .filter((clause) => clause.heading.trim())
        .map((clause) => ({
          heading: clause.heading.trim(),
          ...(clause.purpose.trim() ? { purpose: clause.purpose.trim() } : {}),
        })),
    };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = buildPayload();
    if (payload.clause_outline.length === 0) {
      setMessage("Add at least one clause heading.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (editingId) {
        await updateDraftTemplate(editingId, payload);
      } else {
        await createDraftTemplate(payload);
      }
      setOpen(false);
      setForm(emptyForm);
      setEditingId(null);
      onChanged();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to save the template");
    } finally {
      setBusy(false);
    }
  }

  async function remove(templateId: string) {
    setBusy(true);
    setMessage("");
    try {
      await deleteDraftTemplate(templateId);
      if (editingId === templateId) {
        setOpen(false);
        setEditingId(null);
      }
      onChanged();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to delete the template");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8 border-t border-slate-800 pt-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
          Organization templates
        </h2>
        <button
          className="text-xs text-cyan-300 hover:text-cyan-200"
          onClick={open ? () => setOpen(false) : startNew}
          type="button"
        >
          {open ? "Close" : "New template"}
        </button>
      </div>

      {authored.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">
          Your organization has not authored any templates yet.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {authored.map((template) => (
            <li className="flex items-center justify-between gap-2" key={template.id}>
              <span className="min-w-0 truncate text-xs text-slate-300">{template.name}</span>
              <span className="flex shrink-0 gap-2">
                <button
                  className="text-[11px] text-slate-400 hover:text-cyan-300"
                  onClick={() => startEdit(template)}
                  type="button"
                >
                  Edit
                </button>
                <button
                  className="text-[11px] text-slate-400 hover:text-rose-300 disabled:opacity-50"
                  disabled={busy}
                  onClick={() => void remove(template.id)}
                  type="button"
                >
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <form className="mt-5 space-y-4" onSubmit={submit}>
          <label className="block text-xs text-slate-300">
            Template name
            <input
              className="mt-1 w-full border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              required
              value={form.name}
            />
          </label>
          <label className="block text-xs text-slate-300">
            Document type
            <input
              className="mt-1 w-full border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
              onChange={(event) =>
                setForm((current) => ({ ...current, documentType: event.target.value }))
              }
              required
              value={form.documentType}
            />
          </label>

          <div>
            <p className="text-xs uppercase tracking-[0.15em] text-slate-500">Inputs</p>
            {form.inputs.map((row, index) => (
              <div className="mt-2 flex items-center gap-2" key={index}>
                <input
                  className="min-w-0 flex-1 border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      inputs: current.inputs.map((item, position) =>
                        position === index ? { ...item, label: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Label"
                  value={row.label}
                />
                <label className="flex shrink-0 items-center gap-1 text-[11px] text-slate-400">
                  <input
                    checked={row.required}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        inputs: current.inputs.map((item, position) =>
                          position === index ? { ...item, required: event.target.checked } : item,
                        ),
                      }))
                    }
                    type="checkbox"
                  />
                  required
                </label>
              </div>
            ))}
            <button
              className="mt-2 text-[11px] text-cyan-300 hover:text-cyan-200"
              onClick={() =>
                setForm((current) => ({
                  ...current,
                  inputs: [...current.inputs, { label: "", required: false }],
                }))
              }
              type="button"
            >
              Add input
            </button>
          </div>

          <div>
            <p className="text-xs uppercase tracking-[0.15em] text-slate-500">Clause outline</p>
            {form.clauses.map((row, index) => (
              <div className="mt-2 space-y-1" key={index}>
                <input
                  className="w-full border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      clauses: current.clauses.map((item, position) =>
                        position === index ? { ...item, heading: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Clause heading"
                  value={row.heading}
                />
                <input
                  className="w-full border border-slate-800 bg-slate-900 px-2 py-1.5 text-[11px] text-slate-400 outline-none focus:border-cyan-400"
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      clauses: current.clauses.map((item, position) =>
                        position === index ? { ...item, purpose: event.target.value } : item,
                      ),
                    }))
                  }
                  placeholder="Drafting purpose (optional)"
                  value={row.purpose}
                />
              </div>
            ))}
            <button
              className="mt-2 text-[11px] text-cyan-300 hover:text-cyan-200"
              onClick={() =>
                setForm((current) => ({
                  ...current,
                  clauses: [...current.clauses, { heading: "", purpose: "" }],
                }))
              }
              type="button"
            >
              Add clause
            </button>
          </div>

          <button
            className="w-full bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 disabled:opacity-50"
            disabled={busy}
            type="submit"
          >
            {busy ? "Saving..." : editingId ? "Save template" : "Create template"}
          </button>
        </form>
      ) : null}

      {message ? <p className="mt-3 text-xs text-rose-300">{message}</p> : null}
    </section>
  );
}
