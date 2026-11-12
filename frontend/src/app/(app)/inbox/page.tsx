"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  api,
  getUser,
  type ConversationDetail,
  type ConversationSummary,
  type User,
} from "@/lib/api";
import {
  Button,
  INTENTS,
  MARKETPLACES,
  Pill,
  STATUSES,
  inputClass,
  priorityLabel,
  priorityTone,
  relativeTime,
  statusTone,
} from "@/lib/ui";

import { AddConversationDialog } from "./AddConversationDialog";
import { ConversationPane } from "./ConversationPane";

export default function InboxPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted">Memuat inbox…</p>}>
      <Inbox />
    </Suspense>
  );
}

function Inbox() {
  const params = useSearchParams();
  const [me, setMe] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [list, setList] = useState<ConversationSummary[]>([]);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [toast, setToast] = useState("");
  const [loading, setLoading] = useState(true);

  const [marketplace, setMarketplace] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [priority, setPriority] = useState<string>(params.get("priority") ?? "");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [mine, setMine] = useState(false);
  const [q, setQ] = useState(params.get("q") ?? "");

  useEffect(() => {
    setMe(getUser());
    api.users().then(setUsers).catch(() => setUsers([]));
  }, []);

  const refreshList = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await api.conversations({
        marketplace,
        status,
        priority,
        needs_verification: needsVerification,
        assigned_user_id: mine && me ? me.id : undefined,
        q,
      });
      setList(rows);
      setSelected((current) => {
        if (current && rows.some((r) => r.id === current)) return current;
        const fromUrl = Number(params.get("open"));
        if (fromUrl && rows.some((r) => r.id === fromUrl)) return fromUrl;
        return rows[0]?.id ?? null;
      });
    } finally {
      setLoading(false);
    }
  }, [marketplace, status, priority, needsVerification, mine, me, q, params]);

  useEffect(() => {
    const timer = setTimeout(refreshList, q ? 250 : 0); // debounce pencarian
    return () => clearTimeout(timer);
  }, [refreshList, q]);

  const refreshDetail = useCallback(async () => {
    if (!selected) {
      setDetail(null);
      return;
    }
    setDetail(await api.conversation(selected));
  }, [selected]);

  useEffect(() => {
    refreshDetail();
  }, [refreshDetail]);

  function flash(message: string) {
    setToast(message);
    setTimeout(() => setToast(""), 4200);
  }

  async function afterChange(message?: string) {
    await Promise.all([refreshList(), refreshDetail()]);
    if (message) flash(message);
  }

  const counts = {
    all: list.length,
  };

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[25px] font-bold tracking-tight">Unified Inbox</h1>
          <p className="mt-0.5 text-sm text-muted">
            Percakapan Shopee, TikTok Shop, dan Lazada yang dicatat manual oleh CS.
          </p>
        </div>
        <Button variant="primary" onClick={() => setAdding(true)}>
          + Tambah percakapan
        </Button>
      </header>

      <div className="grid gap-4 xl:grid-cols-[198px_minmax(300px,340px)_minmax(0,1fr)]">
        <aside className="card h-fit p-3.5 xl:sticky xl:top-[86px]">
          <FilterGroup title="Marketplace">
            <FilterButton active={!marketplace} onClick={() => setMarketplace("")}>
              Semua
            </FilterButton>
            {Object.entries(MARKETPLACES).map(([code, mp]) => (
              <FilterButton
                key={code}
                active={marketplace === code}
                onClick={() => setMarketplace(marketplace === code ? "" : code)}
              >
                {mp.name}
              </FilterButton>
            ))}
          </FilterGroup>

          <FilterGroup title="Filter cepat">
            <FilterButton
              active={needsVerification}
              onClick={() => setNeedsVerification((v) => !v)}
            >
              Perlu verifikasi
            </FilterButton>
            <FilterButton
              active={priority === "high"}
              onClick={() => setPriority(priority === "high" ? "" : "high")}
            >
              Prioritas tinggi
            </FilterButton>
            <FilterButton active={mine} onClick={() => setMine((v) => !v)}>
              Ditugaskan ke saya
            </FilterButton>
          </FilterGroup>

          <FilterGroup title="Status">
            <FilterButton active={!status} onClick={() => setStatus("")}>
              Semua status
            </FilterButton>
            {STATUSES.map((s) => (
              <FilterButton
                key={s}
                active={status === s}
                onClick={() => setStatus(status === s ? "" : s)}
              >
                {s}
              </FilterButton>
            ))}
          </FilterGroup>
        </aside>

        <section className="card overflow-hidden">
          <div className="border-b border-line p-3">
            <input
              className={inputClass}
              placeholder="Cari nama, referensi, atau isi pesan…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Cari percakapan"
            />
            <p className="mt-2 px-1 text-[11px] text-faint">
              {loading ? "Memuat…" : `${counts.all} percakapan`}
            </p>
          </div>

          <ul className="max-h-[calc(100vh-240px)] divide-y divide-line overflow-auto">
            {list.map((c) => {
              const active = c.id === selected;
              return (
                <li key={c.id}>
                  <button
                    onClick={() => setSelected(c.id)}
                    aria-current={active ? "true" : undefined}
                    className={`w-full px-4 py-3 text-left transition ${
                      active ? "bg-[#f0f1ff]" : "hover:bg-[#f9fafd]"
                    }`}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <Pill tone={MARKETPLACES[c.marketplace_code].tone}>
                        {MARKETPLACES[c.marketplace_code].name}
                      </Pill>
                      <span className="min-w-0 flex-1 truncate text-[13px] font-semibold">
                        {c.customer_name}
                      </span>
                      <span className="text-[10.5px] text-faint">
                        {relativeTime(c.updated_at)}
                      </span>
                    </div>
                    <p className="line-clamp-2 text-xs text-muted">{c.last_message}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <Pill tone="lav">{INTENTS[c.intent] ?? c.intent}</Pill>
                      {c.priority === "high" ? <Pill tone="rose">⬆ Tinggi</Pill> : null}
                      <Pill tone={statusTone(c.status)}>{c.status}</Pill>
                      {c.assigned_user_name ? (
                        <Pill tone="sky">@{c.assigned_user_name.split(" ")[0]}</Pill>
                      ) : (
                        <Pill>belum ditugaskan</Pill>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
            {!loading && list.length === 0 ? (
              <li className="p-6 text-center text-sm text-muted">
                Tidak ada percakapan yang cocok dengan filter.
              </li>
            ) : null}
          </ul>
        </section>

        {detail ? (
          <ConversationPane
            key={detail.id}
            detail={detail}
            users={users}
            me={me}
            onChanged={afterChange}
            onFlash={flash}
          />
        ) : (
          <section className="card grid place-items-center p-10 text-sm text-muted">
            Pilih percakapan di daftar sebelah kiri.
          </section>
        )}
      </div>

      {adding ? (
        <AddConversationDialog
          onClose={() => setAdding(false)}
          onSaved={async (id, merged) => {
            setAdding(false);
            setSelected(id);
            await afterChange(
              merged
                ? "Pesan ditambahkan ke percakapan yang sudah ada."
                : "Percakapan baru tersimpan.",
            );
          }}
        />
      ) : null}

      {toast ? (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-navy px-5 py-3 text-[13px] font-medium text-white shadow-[0_12px_30px_rgba(20,24,41,0.3)]"
        >
          {toast}
        </div>
      ) : null}
    </div>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 last:mb-0">
      <p className="mb-1.5 px-1 text-[10px] font-semibold tracking-[0.09em] text-faint uppercase">
        {title}
      </p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`focus-ring w-full rounded-lg px-2.5 py-1.5 text-left text-[12.5px] font-medium transition ${
        active ? "bg-navy text-white" : "text-muted hover:bg-[#f5f6fb] hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
