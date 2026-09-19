"use client";

import { FormEvent, useEffect, useState } from "react";

import { getLLMSettings, testLLMSettings, updateLLMSettings } from "@/lib/api";

const providers = ["groq", "openai", "anthropic", "ollama"];

export default function SettingsPage() {
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [keyConfigured, setKeyConfigured] = useState(false);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getLLMSettings().then(
      (settings) => {
        setProvider(settings.provider);
        setModel(settings.model);
        setBaseUrl(settings.base_url ?? "");
        setKeyConfigured(settings.api_key_configured);
      },
      (cause: unknown) => setMessage(cause instanceof Error ? cause.message : "Unable to load settings"),
    );
  }, []);

  function payload() {
    return { provider, model, base_url: baseUrl || null, api_key: apiKey || null };
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const result = await updateLLMSettings(payload());
      setKeyConfigured(result.api_key_configured);
      setApiKey("");
      setMessage("Settings saved securely.");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to save settings");
    } finally {
      setBusy(false);
    }
  }

  async function testConnection() {
    setBusy(true);
    setMessage("");
    try {
      const result = await testLLMSettings(payload());
      setMessage(result.message);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Connection test failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-50">LLM settings</h1>
      <p className="mt-3 text-sm text-slate-400">Only administrators can change provider settings. API keys are encrypted and never displayed.</p>
      <form className="mt-8 space-y-5" onSubmit={save}>
        <label className="block text-sm text-slate-300">Provider
          <select className="mt-2 w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" value={provider} onChange={(event) => setProvider(event.target.value)}>
            {providers.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="block text-sm text-slate-300">Model
          <input className="mt-2 w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" value={model} onChange={(event) => setModel(event.target.value)} required />
        </label>
        <label className="block text-sm text-slate-300">Base URL
          <input className="mt-2 w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" placeholder="Optional, required for Ollama" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
        </label>
        <label className="block text-sm text-slate-300">API key {keyConfigured ? "(configured; leave blank to keep it)" : ""}
          <input className="mt-2 w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
        </label>
        <div className="flex gap-3">
          <button className="rounded bg-amber-400 px-4 py-2 font-medium text-slate-950 disabled:opacity-50" disabled={busy} type="submit">Save settings</button>
          <button className="rounded border border-slate-700 px-4 py-2 text-slate-200 disabled:opacity-50" disabled={busy} onClick={() => void testConnection()} type="button">Test connection</button>
        </div>
      </form>
      {message ? <p className="mt-5 text-sm text-slate-300" role="status">{message}</p> : null}
    </main>
  );
}
