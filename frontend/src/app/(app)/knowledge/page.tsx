"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { MARKETPLACES, Pill, Tile, relativeTime } from "@/lib/ui";

type Knowledge = Awaited<ReturnType<typeof api.knowledge>>;

const TABS = [
  { key: "faq", label: "FAQ" },
  { key: "produk", label: "Produk, varian & stok" },
  { key: "kirim", label: "Aturan pengiriman" },
  { key: "eskalasi", label: "Aturan eskalasi" },
] as const;

export default function KnowledgePage() {
  const [data, setData] = useState<Knowledge | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("faq");
  const [error, setError] = useState("");

  useEffect(() => {
    api.knowledge().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="card p-5 text-sm text-rose-fg">{error}</p>;
  if (!data) return <p className="text-sm text-muted">Memuat knowledge base…</p>;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-[25px] font-bold tracking-tight">Knowledge Base</h1>
        <p className="mt-0.5 text-sm text-muted">
          Satu-satunya sumber fakta untuk suggested reply. Dikelola Supervisor/Admin.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            aria-pressed={tab === t.key}
            className={`focus-ring rounded-full px-4 py-2 text-[13px] font-medium transition ${
              tab === t.key
                ? "bg-white text-ink shadow-[0_1px_2px_rgba(20,24,41,0.05),0_8px_20px_rgba(20,24,41,0.06)]"
                : "text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "faq" ? (
        <div className="card overflow-hidden">
          <Table head={["Pertanyaan", "Jawaban disetujui", "Kata kunci"]}>
            {data.faqs.map((f) => (
              <tr key={f.id} className="border-t border-line align-top">
                <td className="px-5 py-3.5">
                  <p className="text-[13px] font-semibold">{f.question}</p>
                  <p className="mt-0.5 font-mono text-[10.5px] text-faint">FAQ-{f.id}</p>
                </td>
                <td className="px-5 py-3.5 text-[13px] text-muted">{f.answer}</td>
                <td className="px-5 py-3.5">
                  <div className="flex flex-wrap gap-1">
                    {f.keywords.map((k) => (
                      <Pill key={k}>{k}</Pill>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </Table>
        </div>
      ) : null}

      {tab === "produk" ? (
        <>
          <div className="card overflow-hidden">
            <Table head={["Produk", "Varian", "SKU", "Stok", "Diperbarui"]}>
              {data.products.flatMap((p) =>
                p.variants.map((v, i) => (
                  <tr key={v.id} className="border-t border-line align-middle">
                    <td className="px-5 py-3 text-[13px] font-semibold">
                      {i === 0 ? p.name : ""}
                    </td>
                    <td className="px-5 py-3 text-[13px]">{v.variant_name}</td>
                    <td className="px-5 py-3 font-mono text-[11.5px] text-muted">{v.sku}</td>
                    <td className="px-5 py-3">
                      {v.quantity === null ? (
                        <Pill tone="amber">belum tercatat</Pill>
                      ) : v.quantity === 0 ? (
                        <Pill tone="rose">0 · kosong</Pill>
                      ) : (
                        <span className="text-[13px] font-semibold">{v.quantity}</span>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      {v.stock_updated_at ? (
                        v.is_stale ? (
                          <Pill tone="amber">
                            {relativeTime(v.stock_updated_at)} · kedaluwarsa
                          </Pill>
                        ) : (
                          <span className="text-xs text-muted">
                            {relativeTime(v.stock_updated_at)}
                          </span>
                        )
                      ) : (
                        <span className="text-xs text-faint">—</span>
                      )}
                    </td>
                  </tr>
                )),
              )}
            </Table>
          </div>
          <Notice>
            Stok yang <b>belum tercatat</b> tidak dianggap tersedia maupun kosong. Stok yang
            lebih tua dari 48 jam ditandai kedaluwarsa, dan suggested reply akan meminta
            verifikasi staf alih-alih membuat klaim.
          </Notice>
        </>
      ) : null}

      {tab === "kirim" ? (
        <>
          <div className="card overflow-hidden">
            <Table head={["Marketplace", "Cutoff", "Aturan", "Diperbarui"]}>
              {data.shipping_rules.map((r) => {
                const mp = MARKETPLACES[r.marketplace_code as keyof typeof MARKETPLACES];
                return (
                  <tr key={r.marketplace_code} className="border-t border-line align-top">
                    <td className="px-5 py-3.5">
                      <Pill tone={mp?.tone ?? "slate"}>{mp?.name ?? r.marketplace_code}</Pill>
                    </td>
                    <td className="px-5 py-3.5">
                      {r.cutoff_time ? (
                        <span className="text-[13px] font-semibold">{r.cutoff_time}</span>
                      ) : (
                        <Pill tone="amber">belum diisi</Pill>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-[13px] text-muted">
                      {r.rule_text ?? <span className="text-faint">—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-muted">
                      {relativeTime(r.updated_at)}
                    </td>
                  </tr>
                );
              })}
            </Table>
          </div>
          <Notice>
            Aturan Lazada sengaja dikosongkan pada data demo untuk menunjukkan perilaku
            eskalasi saat informasi tidak tersedia.
          </Notice>
        </>
      ) : null}

      {tab === "eskalasi" ? (
        <div className="card overflow-hidden">
          <Table head={["Kondisi", "Tindakan sistem"]}>
            {data.escalation_rules.map((r) => (
              <tr key={r.condition} className="border-t border-line align-top">
                <td className="px-5 py-3.5 text-[13px] font-semibold">{r.condition}</td>
                <td className="px-5 py-3.5 text-[13px] text-muted">{r.action}</td>
              </tr>
            ))}
          </Table>
        </div>
      ) : null}
    </div>
  );
}

function Table({ head, children }: { head: string[]; children: React.ReactNode }) {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          {head.map((h) => (
            <th
              key={h}
              className="px-5 pt-4 pb-2.5 text-left text-[10px] font-semibold tracking-[0.07em] text-faint uppercase"
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3 rounded-2xl bg-sky-bg px-4 py-3.5 text-[12.5px] leading-relaxed text-sky-fg">
      <Tile tone="sky">ℹ</Tile>
      <p className="self-center">{children}</p>
    </div>
  );
}
