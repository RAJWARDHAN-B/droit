"use client";

import { DraftRiskBreakdown } from "@/lib/api";

const categoryLabels: Record<string, string> = {
  missing_clause: "Missing clauses",
  asymmetric_term: "Asymmetric terms",
  auto_renewal: "Automatic renewal",
  jurisdiction: "Jurisdiction",
  pii_density: "Personal data density",
};

function band(score: number): { label: string; tone: string } {
  if (score >= 60) return { label: "High", tone: "text-rose-300 border-rose-400/60" };
  if (score >= 30) return { label: "Medium", tone: "text-amber-300 border-amber-400/60" };
  return { label: "Low", tone: "text-emerald-300 border-emerald-400/60" };
}

function FindingList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-4">
      <p className="text-xs uppercase tracking-[0.15em] text-slate-500">{title}</p>
      <ul className="mt-2 space-y-1">
        {items.map((item) => (
          <li className="text-xs leading-5 text-slate-300" key={item}>
            {item.replace(/_/g, " ")}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function DraftRiskPanel({ risk }: { risk: DraftRiskBreakdown }) {
  const score = typeof risk.score === "number" ? risk.score : null;
  if (score === null) {
    return (
      <section className="border border-slate-800 bg-slate-900/60 p-5">
        <h3 className="text-sm font-medium text-slate-100">Risk</h3>
        <p className="mt-2 text-xs text-slate-500">No risk assessment is available yet.</p>
      </section>
    );
  }

  const { label, tone } = band(score);
  const categories = Object.entries(risk.category_scores ?? {}).filter(([, value]) => value > 0);

  return (
    <section className="border border-slate-800 bg-slate-900/60 p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-100">Risk</h3>
        <span className={`border px-2 py-1 text-xs ${tone}`}>
          {label} · {score.toFixed(1)}
        </span>
      </div>

      {categories.length > 0 ? (
        <dl className="mt-4 space-y-2">
          {categories.map(([category, value]) => (
            <div className="flex items-center justify-between gap-3" key={category}>
              <dt className="text-xs text-slate-400">{categoryLabels[category] ?? category}</dt>
              <dd className="text-xs text-slate-300">{value.toFixed(1)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No weighted findings were recorded.</p>
      )}

      <FindingList items={risk.missing_clauses ?? []} title="Missing clauses" />
      <FindingList items={risk.asymmetric_terms ?? []} title="Asymmetric terms" />
      <FindingList items={risk.auto_renewal_terms ?? []} title="Automatic renewal" />
    </section>
  );
}
