"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getUser } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getUser() ? "/dashboard" : "/login");
  }, [router]);
  return <div className="app-bg grid min-h-screen place-items-center text-sm text-muted">Memuat…</div>;
}
