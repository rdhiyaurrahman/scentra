"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, getUser, type ConversationSummary } from "@/lib/api";
import {
  INTENTS,
  MARKETPLACES,
  Pill,
  Tile,
  type Tone,
  statusTone,
} from "@/lib/ui";

interface Data {
  totals: Record<string, number>;
  by_marketplace: Record<string, number>;
  by_intent: Record<string, number>;
  by_status: Record<string, number>;
  high_priority_queue: ConversationSummary[];
  disclaimer: string;
}

const CARDS: { key: string; label: string; tone: Tone; icon: string }[] = [
  { key: "conversations", label: "Total percakapan", tone: "lav", icon: "💬" },
  { key: "new", label: "Belum dibuka", tone: "sky", icon: "🆕" },
  { key: "waiting_staff", label: "Perlu verifikasi", tone: "amber", icon: "🔎" },
  { key: "high_priority", label: "Prioritas tinggi", tone: "rose", icon: "⚠️" },
  { key: "resolved", label: "Selesai internal", tone: "mint", icon: "✓" },
];

export default function DashboardPage() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const user = typeof window !== "undefined" ? getUser() : null;

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) {
    return <p className="card p-5 text-sm text-rose-fg">{error}</p>;
  }
  if (!data) {
    return <p className="text-sm text-muted">Memuat ringkasan…</p>;
  }

  const mpMax = Math.max(1, ...Object.values(data.by_marketplace));
  const intents = Object.entries(data.by_intent).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[25px] font-bold tracking-tight">
            Selamat datang{user ? `, ${user.name.split(" ")[0]}` : ""}
          </h1>
          <p className="mt-0.5 text-sm text-muted">
            {new Date().toLocaleDateString("id-ID", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </p>
        </div>
        <Link
          href="/inbox"
          className="focus-ring rounded-full bg-navy px-4 py-2 text-[13px] font-semibold text-white transition hover:bg-[#262b45]"
        >
          Buka inbox
        </Link>
      </header>

      {/* Ringkasan antrean, mengikuti pola kartu "AI Summary" pada referensi. */}
      <section className="card p-5">
        <div className="flex flex-wrap items-center gap-3">
          <Tile tone="lav">◧</Tile>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[15px] font-bold tracking-tight">Ringkasan antrean</h2>
              <Pill tone={data.totals.high_priority ? "rose" : "mint"}>
                {data.totals.high_priority
                  ? `${data.totals.high_priority} perlu perhatian`
                  : "Antrean aman"}
              </Pill>
            </div>
            <p className="mt-0.5 text-xs text-muted">{data.disclaimer}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-2.5 border-t border-line pt-4 sm:grid-cols-2">
          <SummaryLine
            ok={data.totals.waiting_staff === 0}
            text={
              data.totals.waiting_staff === 0
                ? "Tidak ada percakapan yang menunggu verifikasi staf."
                : `${data.totals.waiting_staff} percakapan menunggu verifikasi informasi.`
            }
          />
          <SummaryLine
            ok={data.totals.high_priority === 0}
            text={
              data.totals.high_priority === 0
                ? "Tidak ada komplain terbuka."
                : `${data.totals.high_priority} komplain atau permintaan refund ditandai prioritas tinggi.`
            }
          />
          <SummaryLine
            ok
            text={`${data.totals.conversations} percakapan tercatat dari tiga marketplace.`}
          />
          <SummaryLine
            ok={data.totals.new === 0}
            text={
              data.totals.new === 0
                ? "Semua percakapan sudah dibuka CS."
                : `${data.totals.new} percakapan belum dibuka.`
            }
          />
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {CARDS.map((c) => (
          <div key={c.key} className="card p-4">
            <div className="flex items-start justify-between gap-2">
              <Tile tone={c.tone}>{c.icon}</Tile>
            </div>
            <p className="mt-3 text-xs font-medium text-muted">{c.label}</p>
            <p className="mt-0.5 text-[30px] leading-none font-bold tracking-tight">
              {data.totals[c.key] ?? 0}
            </p>
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="card p-5">
          <div className="mb-1 flex items-center justify-between gap-3">
            <h2 className="text-[15px] font-bold tracking-tight">Antrean prioritas tinggi</h2>
            <Link href="/inbox?priority=high" className="text-xs font-semibold text-lav-fg">
              Lihat semua →
            </Link>
          </div>
          <p className="mb-3 text-xs text-muted">
            Komplain dan permintaan refund tidak tertimbun pertanyaan umum.
          </p>

          {data.high_priority_queue.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">
              Tidak ada antrean prioritas tinggi.
            </p>
          ) : (
            <ul className="divide-y divide-line">
              {data.high_priority_queue.map((c) => (
                <li key={c.id} className="flex items-center gap-3 py-2.5">
                  <Pill tone={MARKETPLACES[c.marketplace_code].tone}>
                    {MARKETPLACES[c.marketplace_code].name}
                  </Pill>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-semibold">{c.customer_name}</p>
                    <p className="truncate text-xs text-muted">{c.last_message}</p>
                  </div>
                  <Pill tone={statusTone(c.status)}>{c.status}</Pill>
                  <Link
                    href={`/inbox?open=${c.id}`}
                    className="focus-ring rounded-full bg-[#eceeff] px-3 py-1.5 text-xs font-semibold text-[#4a4fc4]"
                  >
                    Buka
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="mb-3 text-[15px] font-bold tracking-tight">
              Percakapan per marketplace
            </h2>
            {Object.entries(MARKETPLACES).map(([code, mp]) => {
              const n = data.by_marketplace[code] ?? 0;
              return (
                <div key={code} className="mb-3 last:mb-0">
                  <div className="flex items-center justify-between text-[13px]">
                    <span className="font-medium">{mp.name}</span>
                    <span className="text-muted">{n}</span>
                  </div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#eef0f7]">
                    <div
                      className="h-full rounded-full bg-[#5b63d8]"
                      style={{ width: `${(n / mpMax) * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card p-5">
            <h2 className="mb-3 text-[15px] font-bold tracking-tight">Distribusi intent</h2>
            <ul className="divide-y divide-line">
              {intents.map(([intent, n]) => (
                <li key={intent} className="flex items-center justify-between py-2">
                  <Pill tone={intent === "complaint" ? "rose" : "lav"}>
                    {INTENTS[intent] ?? intent}
                  </Pill>
                  <span className="text-[13px] font-semibold">{n}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card p-5">
            <h2 className="mb-3 text-[15px] font-bold tracking-tight">Status percakapan</h2>
            <ul className="space-y-1.5">
              {Object.entries(data.by_status).map(([status, n]) => (
                <li key={status} className="flex items-center justify-between text-[13px]">
                  <span className="flex items-center gap-2">
                    <Pill tone={statusTone(status)}>{status}</Pill>
                  </span>
                  <span className="font-semibold">{n}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

function SummaryLine({ ok, text }: { ok: boolean; text: string }) {
  return (
    <p className="flex items-start gap-2 text-[12.5px] text-muted">
      <span
        className={`mt-0.5 grid h-4 w-4 flex-none place-items-center rounded-full text-[9px] font-bold text-white ${
          ok ? "bg-[#2ca568]" : "bg-[#e0973a]"
        }`}
        aria-hidden
      >
        {ok ? "✓" : "!"}
      </span>
      <span>{text}</span>
    </p>
  );
}
