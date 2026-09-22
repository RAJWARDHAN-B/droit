"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, logout as endSession } from "@/lib/api";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentUser().then(
      () => {
        if (active) setAuthorized(true);
      },
      () => {
        router.replace("/login");
      },
    );
    function handleExpired() {
      router.replace("/login");
    }
    window.addEventListener("droit:auth-expired", handleExpired);
    return () => {
      active = false;
      window.removeEventListener("droit:auth-expired", handleExpired);
    };
  }, [router]);

  async function logout() {
    try {
      await endSession();
    } finally {
      router.replace("/login");
    }
  }

  if (!authorized) return <main className="min-h-screen bg-slate-950" />;

  return (
    <div className="min-h-screen bg-slate-950">
      <nav className="mx-auto flex max-w-6xl justify-end px-6 py-4">
        <button className="text-sm text-slate-400 hover:text-slate-100" onClick={logout} type="button">
          Sign out
        </button>
      </nav>
      {children}
    </div>
  );
}