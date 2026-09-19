"use client";

import { UploadPanel } from "@/components/UploadPanel";

export default function UploadPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold text-slate-50">Upload document</h1>
      <div className="mt-8">
        <UploadPanel onIngested={() => undefined} />
      </div>
    </main>
  );
}
