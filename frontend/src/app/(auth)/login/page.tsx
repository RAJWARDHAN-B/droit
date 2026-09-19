"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { login } from "@/lib/api";

export default function LoginPage() {
  const [message, setMessage] = useState("");
  const router = useRouter();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      router.push("/dashboard");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to sign in");
    }
  }

  return (
    <main className="mx-auto w-full max-w-md px-6 py-16">
      <h1 className="text-3xl font-semibold text-slate-50">Sign in</h1>
      <form className="mt-8 space-y-4" onSubmit={submit}>
        <input className="w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" name="email" type="email" placeholder="Email" required />
        <input className="w-full rounded border border-slate-700 bg-slate-900 p-3 text-slate-100" name="password" type="password" placeholder="Password" required />
        <button className="rounded bg-amber-400 px-4 py-2 font-medium text-slate-950" type="submit">Sign in</button>
      </form>
      {message ? <p className="mt-4 text-sm text-slate-400">{message}</p> : null}
    </main>
  );
}
