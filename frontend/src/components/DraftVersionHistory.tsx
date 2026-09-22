"use client";

import { useCallback, useEffect, useState } from "react";

import { Draft, DraftVersion, listDraftVersions, restoreDraftVersion } from "@/lib/api";

export default function DraftVersionHistory({
  draftId,
  currentVersion,
  onRestored,
}: {
  draftId: string;
  currentVersion: number;
  onRestored: (draft: Draft) => void;
}) {
  const [versions, setVersions] = useState<DraftVersion[] | null>(null);
  const [error, setError] = useState("");
  const [busyVersion, setBusyVersion] = useState<number | null>(null);

  const load = useCallback(() => {
    listDraftVersions(draftId).then(
      (items) => {
        setVersions(items);
        setError("");
      },
      (cause: unknown) =>
        setError(cause instanceof Error ? cause.message : "Unable to load version history"),
    );
  }, [draftId]);

  useEffect(() => {
    load();
  }, [load, currentVersion]);

  async function restore(version: number) {
    setBusyVersion(version);
    setError("");
    try {
      onRestored(await restoreDraftVersion(draftId, version));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to restore this version");
    } finally {
      setBusyVersion(null);
    }
  }

  return (
    <section className="border border-slate-800 bg-slate-900/60 p-5">
      <h3 className="text-sm font-medium text-slate-100">Version history</h3>
      {error ? <p className="mt-3 text-xs text-rose-300">{error}</p> : null}
      {versions === null && !error ? (
        <p className="mt-3 text-xs text-slate-500">Loading versions...</p>
      ) : null}
      {versions !== null && versions.length === 0 ? (
        <p className="mt-3 text-xs text-slate-500">No snapshots have been recorded yet.</p>
      ) : null}
      <ul className="mt-3 space-y-2">
        {[...(versions ?? [])].reverse().map((version) => (
          <li
            className="flex items-center justify-between gap-3 border border-slate-800 px-3 py-2"
            key={version.version}
          >
            <div className="min-w-0">
              <p className="truncate text-xs text-slate-200">
                v{version.version} · {version.clause_count} clauses
              </p>
              <p className="text-[11px] text-slate-500">
                {new Date(version.created_at).toLocaleString()}
              </p>
            </div>
            {version.version === currentVersion ? (
              <span className="text-[11px] text-slate-500">current</span>
            ) : (
              <button
                className="border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:border-cyan-400 disabled:opacity-50"
                disabled={busyVersion !== null}
                onClick={() => void restore(version.version)}
                type="button"
              >
                {busyVersion === version.version ? "Restoring..." : "Restore"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
