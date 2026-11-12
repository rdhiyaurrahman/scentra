"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  getUser,
  profitApi,
  type CostSettings,
  type ProfitBucket,
  type ProfitReport,
  type ProfitTransaction,
} from "@/lib/api";
import {
  Button,
  MARKETPLACES,
  Pill,
  Tile,
  type Tone,
  formatTime,
  persen,
  relativeTime,
  rupiah,
} from "@/lib/ui";

const PERIODS = [
  { key: "30", label: "30 hari terakhir", days: 30 },
  { key: "90", label: "90 hari terakhir", days: 90 },
  { key: "all", label: "Semua periode", days: null as number | null },
];

type Tab = "produk" | "marketplace" | "transaksi" | "biaya";

export default function ProfitabilityPage() {
  const [period, setPeriod] = useState("30");
  const [marketplace, setMarketplace] = useState("");
  const [tab, setTab] = useState<Tab>("produk");
  const [report, setReport] = useState<ProfitReport | null>(null);
  const [transactions, setTransactions] = useState<ProfitTransaction[]>([]);
  const [costs, setCosts] = useState<CostSettings | null>(null);
  const [skuFilter, setSkuFilter] = useState("");
  const [onlyIncomplete, setOnlyIncomplete] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const role = typeof window !== "undefined" ? getUser()?.role : undefined;
  const allowed = role === "owner";

  const startIso = (() => {
    const days = PERIODS.find((p) => p.key === period)?.days;
    if (!days) return undefined;
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 19);
  })();

  const load = useCallback(async () => {
    if (!allowed) return;
    setError("");
    try {
      const [rep, txs] = await Promise.all([
        profitApi.report({ start: startIso, marketplace }),
        profitApi.transactions({
          start: startIso,
          marketplace,
          sku: skuFilter || undefined,
          only_incomplete: onlyIncomplete,
        }),
      ]);
      setReport(rep);
      setTransactions(txs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat laporan.");
    }
  }, [allowed, startIso, marketplace, skuFilter, onlyIncomplete]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (allowed && tab === "biaya" && !costs) {
      profitApi.costSettings().then(setCosts).catch(() => setCosts(null));
    }
  }, [allowed, tab, costs]);

  function flash(message: string) {
    setToast(message);
    setTimeout(() => setToast(""), 5000);
  }

  async function onImport(file: File) {
    try {
      const res = await profitApi.importCsv(file);
      await load();
      flash(
        `${res.saved} transaksi tersimpan` +
          (res.failed ? `, ${res.failed} baris gagal: ${res.errors[0]}` : "."),
      );
    } catch (e) {
      flash(e instanceof Error ? e.message : "Impor gagal.");
    }
  }

  if (!allowed) {
    return (
      <div className="card p-8 text-center">
        <h1 className="text-[17px] font-bold tracking-tight">Akses terbatas</h1>
        <p className="mt-1.5 text-sm text-muted">
          Laporan profitabilitas hanya dapat dibuka pemilik usaha.
        </p>
      </div>
    );
  }

  if (error) return <p className="card p-5 text-sm text-rose-fg">{error}</p>;
  if (!report) return <p className="text-sm text-muted">Memuat laporan…</p>;

  const o = report.overall;
  const totalCost = o.commission + o.voucher + o.shipping + o.cogs;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[25px] font-bold tracking-tight">Profitabilitas Produk</h1>
          <p className="mt-0.5 text-sm text-muted">
            Omzet besar belum tentu untung. Laba dihitung setelah komisi, voucher,
            ongkir yang ditanggung penjual, dan retur.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onImport(f);
              e.target.value = "";
            }}
          />
          <Button variant="primary" onClick={() => fileRef.current?.click()}>Impor CSV</Button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPeriod(p.key)}
            aria-pressed={period === p.key}
            className={`focus-ring rounded-full px-3.5 py-1.5 text-[12.5px] font-medium transition ${
              period === p.key ? "bg-navy text-white" : "bg-white border border-line text-muted"
            }`}
          >
            {p.label}
          </button>
        ))}
        <span className="mx-1 h-5 w-px bg-line" />
        <button
          onClick={() => setMarketplace("")}
          aria-pressed={!marketplace}
          className={`focus-ring rounded-full px-3.5 py-1.5 text-[12.5px] font-medium transition ${
            !marketplace ? "bg-navy text-white" : "bg-white border border-line text-muted"
          }`}
        >
          Semua marketplace
        </button>
        {Object.entries(MARKETPLACES).map(([code, mp]) => (
          <button
            key={code}
            onClick={() => setMarketplace(marketplace === code ? "" : code)}
            aria-pressed={marketplace === code}
            className={`focus-ring rounded-full px-3.5 py-1.5 text-[12.5px] font-medium transition ${
              marketplace === code
                ? "bg-navy text-white"
                : "bg-white border border-line text-muted"
            }`}
          >
            {mp.name}
          </button>
        ))}
      </div>

      {!report.data_complete ? (
        <div className="card flex flex-wrap items-center gap-3 border-[#f3dcbd] bg-amber-bg p-4">
          <Tile tone="amber">⚠</Tile>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-bold text-amber-fg">
              {o.incomplete_transactions} dari {o.transactions} transaksi belum lengkap
              datanya
            </p>
            <p className="mt-0.5 text-[12px] leading-relaxed text-amber-fg">
              Transaksi ini <b>tidak dihitung labanya dan tidak dianggap nol</b>.
              Penyebab: {o.missing_reasons.join("; ")}.
            </p>
          </div>
          <Button
            onClick={() => {
              setOnlyIncomplete(true);
              setSkuFilter("");
              setTab("transaksi");
            }}
          >
            Lihat transaksinya
          </Button>
        </div>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi label="Penjualan bersih" value={rupiah(o.net_sales)} tone="sky" icon="💰"
             hint={`${o.units_sold} unit terjual`} />
        <Kpi label="Total biaya" value={rupiah(totalCost)} tone="amber" icon="📉"
             hint="komisi + voucher + ongkir + modal" />
        <Kpi label="Laba" value={rupiah(o.profit)} tone={o.profit >= 0 ? "mint" : "rose"}
             icon={o.profit >= 0 ? "📈" : "🔻"}
             hint={`dari ${o.complete_transactions} transaksi lengkap`} />
        <Kpi label="Margin" value={persen(o.margin_pct)} tone="lav" icon="％"
             hint={o.margin_pct === null ? "data belum cukup" : "atas penjualan bersih"} />
        <Kpi label="Belum lengkap" value={String(o.incomplete_transactions)} tone="rose"
             icon="⚠️" hint="dikeluarkan dari laba" />
      </section>

      <div className="flex flex-wrap gap-1.5">
        {([
          ["produk", "Per produk"],
          ["marketplace", "Per marketplace"],
          ["transaksi", "Rincian transaksi"],
          ["biaya", "Modal & tarif"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            aria-pressed={tab === key}
            className={`focus-ring rounded-full px-4 py-2 text-[13px] font-medium transition ${
              tab === key
                ? "bg-white text-ink shadow-[0_1px_2px_rgba(20,24,41,0.05),0_8px_20px_rgba(20,24,41,0.06)]"
                : "text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "produk" ? (
        <BucketTable
          buckets={report.by_product}
          firstHead="Produk"
          onDrill={(key) => {
            setSkuFilter(key);
            setOnlyIncomplete(false);
            setTab("transaksi");
          }}
        />
      ) : null}

      {tab === "marketplace" ? (
        <BucketTable
          buckets={report.by_marketplace.map((b) => ({
            ...b,
            label:
              MARKETPLACES[b.key as keyof typeof MARKETPLACES]?.name ?? b.label,
          }))}
          firstHead="Marketplace"
        />
      ) : null}

      {tab === "transaksi" ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            {skuFilter ? (
              <Pill tone="lav">
                SKU {skuFilter}
                <button
                  onClick={() => setSkuFilter("")}
                  className="ml-1 font-bold"
                  aria-label="Hapus filter SKU"
                >
                  ×
                </button>
              </Pill>
            ) : null}
            <button
              onClick={() => setOnlyIncomplete((v) => !v)}
              aria-pressed={onlyIncomplete}
              className={`focus-ring rounded-full px-3.5 py-1.5 text-[12.5px] font-medium transition ${
                onlyIncomplete
                  ? "bg-navy text-white"
                  : "bg-white border border-line text-muted"
              }`}
            >
              Hanya yang belum lengkap
            </button>
            <span className="text-[12px] text-muted">{transactions.length} transaksi</span>
          </div>
          <TransactionTable rows={transactions} />
        </div>
      ) : null}

      {tab === "biaya" ? <CostTables costs={costs} /> : null}

      <p className="px-1 text-[11.5px] leading-relaxed text-muted">{report.note}</p>

      {toast ? (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 z-50 max-w-[90vw] -translate-x-1/2 rounded-full bg-navy px-5 py-3 text-center text-[13px] font-medium text-white shadow-[0_12px_30px_rgba(20,24,41,0.3)]"
        >
          {toast}
        </div>
      ) : null}
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
  icon,
  hint,
}: {
  label: string;
  value: string;
  tone: Tone;
  icon: string;
  hint: string;
}) {
  return (
    <div className="card p-4">
      <Tile tone={tone}>{icon}</Tile>
      <p className="mt-3 text-xs font-medium text-muted">{label}</p>
      <p className="mt-0.5 text-[23px] leading-tight font-bold tracking-tight">{value}</p>
      <p className="mt-0.5 text-[11px] text-faint">{hint}</p>
    </div>
  );
}

function BucketTable({
  buckets,
  firstHead,
  onDrill,
}: {
  buckets: ProfitBucket[];
  firstHead: string;
  onDrill?: (key: string) => void;
}) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[920px] border-collapse">
        <thead>
          <tr>
            {[firstHead, "Terjual", "Penjualan bersih", "Komisi", "Voucher", "Ongkir",
              "Modal", "Laba", "Margin"].map((h, i) => (
              <th
                key={h}
                className={`px-4 pt-4 pb-2.5 text-[10px] font-semibold tracking-[0.07em] text-faint uppercase ${
                  i === 0 ? "text-left" : "text-right"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.key} className="border-t border-line">
              <td className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  {onDrill ? (
                    <button
                      onClick={() => onDrill(b.key)}
                      className="focus-ring rounded text-left text-[13px] font-semibold hover:text-accent"
                      title="Lihat transaksinya"
                    >
                      {b.label}
                    </button>
                  ) : (
                    <span className="text-[13px] font-semibold">{b.label}</span>
                  )}
                  {!b.complete ? (
                    <Pill tone="amber">{b.incomplete_transactions} belum lengkap</Pill>
                  ) : null}
                </div>
                <p className="mt-0.5 text-[10.5px] text-faint">
                  {b.transactions} transaksi
                  {b.units_returned ? ` · ${b.units_returned} unit diretur` : ""}
                </p>
              </td>
              <td className="px-4 py-3 text-right text-[13px]">{b.units_sold}</td>
              <td className="px-4 py-3 text-right text-[13px]">{rupiah(b.net_sales)}</td>
              <Money v={b.commission} muted />
              <Money v={b.voucher} muted />
              <Money v={b.shipping} muted />
              <Money v={b.cogs} muted />
              <td className="px-4 py-3 text-right">
                {b.complete_transactions === 0 ? (
                  <span className="text-[13px] text-faint">belum bisa dihitung</span>
                ) : (
                  <span
                    className={`text-[13px] font-bold ${
                      b.profit >= 0 ? "text-mint-fg" : "text-rose-fg"
                    }`}
                  >
                    {rupiah(b.profit)}
                  </span>
                )}
              </td>
              <td className="px-4 py-3 text-right text-[13px]">
                {b.margin_pct === null ? (
                  <span className="text-faint">—</span>
                ) : (
                  <span className={b.margin_pct >= 0 ? "" : "text-rose-fg"}>
                    {persen(b.margin_pct)}
                  </span>
                )}
              </td>
            </tr>
          ))}
          {buckets.length === 0 ? (
            <tr>
              <td colSpan={9} className="px-4 py-8 text-center text-sm text-muted">
                Belum ada transaksi pada periode ini.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function Money({ v, muted }: { v: number | null; muted?: boolean }) {
  return (
    <td className={`px-4 py-3 text-right text-[13px] ${muted ? "text-muted" : ""}`}>
      {rupiah(v)}
    </td>
  );
}

function TransactionTable({ rows }: { rows: ProfitTransaction[] }) {
  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[1040px] border-collapse">
        <thead>
          <tr>
            {["Pesanan", "Produk", "Qty", "Penjualan bersih", "Komisi", "Voucher",
              "Ongkir", "Modal", "Laba"].map((h, i) => (
              <th
                key={h}
                className={`px-4 pt-4 pb-2.5 text-[10px] font-semibold tracking-[0.07em] text-faint uppercase ${
                  i < 2 ? "text-left" : "text-right"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.id} className="border-t border-line align-top">
              <td className="px-4 py-3">
                <p className="font-mono text-[11.5px] font-semibold">{t.external_id}</p>
                <div className="mt-1 flex items-center gap-1.5">
                  <Pill
                    tone={
                      MARKETPLACES[t.marketplace_code as keyof typeof MARKETPLACES]
                        ?.tone ?? "slate"
                    }
                  >
                    {MARKETPLACES[t.marketplace_code as keyof typeof MARKETPLACES]?.name ??
                      t.marketplace_code}
                  </Pill>
                </div>
                <p className="mt-1 text-[10.5px] text-faint">{formatTime(t.order_date)}</p>
              </td>
              <td className="px-4 py-3">
                <p className="text-[13px]">{t.product_label}</p>
                <p className="font-mono text-[10.5px] text-faint">{t.sku}</p>
                {!t.complete ? (
                  <p className="mt-1 text-[10.5px] leading-snug text-amber-fg">
                    Belum lengkap: {t.missing.join(", ")}
                  </p>
                ) : null}
              </td>
              <td className="px-4 py-3 text-right text-[13px]">
                {t.quantity}
                {t.returned_quantity ? (
                  <span className="block text-[10.5px] text-rose-fg">
                    −{t.returned_quantity} retur
                  </span>
                ) : null}
              </td>
              <td className="px-4 py-3 text-right text-[13px]">{rupiah(t.net_sales)}</td>
              <Money v={t.commission} muted />
              <Money v={t.voucher} muted />
              <Money v={t.shipping} muted />
              <Money v={t.cogs} muted />
              <td className="px-4 py-3 text-right">
                {t.profit === null ? (
                  <span className="text-[12.5px] text-faint">belum bisa dihitung</span>
                ) : (
                  <span
                    className={`text-[13px] font-bold ${
                      t.profit >= 0 ? "text-mint-fg" : "text-rose-fg"
                    }`}
                  >
                    {rupiah(t.profit)}
                  </span>
                )}
              </td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={9} className="px-4 py-8 text-center text-sm text-muted">
                Tidak ada transaksi yang cocok.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function CostTables({ costs }: { costs: CostSettings | null }) {
  if (!costs) return <p className="text-sm text-muted">Memuat data biaya…</p>;
  return (
    <div className="space-y-4">
      <div className="card overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["Produk", "Varian", "SKU", "Modal per unit", "Diperbarui"].map((h, i) => (
                <th
                  key={h}
                  className={`px-5 pt-4 pb-2.5 text-[10px] font-semibold tracking-[0.07em] text-faint uppercase ${
                    i === 3 ? "text-right" : "text-left"
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {costs.product_costs.map((c) => (
              <tr key={c.variant_id} className="border-t border-line">
                <td className="px-5 py-3 text-[13px] font-semibold">{c.product_name}</td>
                <td className="px-5 py-3 text-[13px]">{c.variant_name}</td>
                <td className="px-5 py-3 font-mono text-[11.5px] text-muted">{c.sku}</td>
                <td className="px-5 py-3 text-right">
                  {c.unit_cost === null ? (
                    <Pill tone="amber">belum dicatat</Pill>
                  ) : (
                    <span className="text-[13px] font-semibold">{rupiah(c.unit_cost)}</span>
                  )}
                </td>
                <td className="px-5 py-3 text-xs text-muted">
                  {c.updated_at ? relativeTime(c.updated_at) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["Marketplace", "Komisi", "Biaya layanan", "Total potongan", "Diperbarui"].map(
                (h, i) => (
                  <th
                    key={h}
                    className={`px-5 pt-4 pb-2.5 text-[10px] font-semibold tracking-[0.07em] text-faint uppercase ${
                      i === 0 || i === 4 ? "text-left" : "text-right"
                    }`}
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {costs.marketplace_fees.map((f) => {
              const mp = MARKETPLACES[f.marketplace_code as keyof typeof MARKETPLACES];
              const known = f.commission_bp !== null;
              return (
                <tr key={f.marketplace_code} className="border-t border-line">
                  <td className="px-5 py-3">
                    <Pill tone={mp?.tone ?? "slate"}>{mp?.name ?? f.marketplace_code}</Pill>
                  </td>
                  <td className="px-5 py-3 text-right text-[13px]">
                    {known ? `${(f.commission_bp! / 100).toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-5 py-3 text-right text-[13px]">
                    {f.service_fee_bp !== null ? `${(f.service_fee_bp / 100).toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {known ? (
                      <span className="text-[13px] font-semibold">
                        {((f.commission_bp! + (f.service_fee_bp ?? 0)) / 100).toFixed(2)}%
                      </span>
                    ) : (
                      <Pill tone="amber">belum dicatat</Pill>
                    )}
                  </td>
                  <td className="px-5 py-3 text-xs text-muted">
                    {f.updated_at ? relativeTime(f.updated_at) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex gap-3 rounded-2xl bg-sky-bg px-4 py-3.5 text-[12.5px] leading-relaxed text-sky-fg">
        <Tile tone="sky">ℹ</Tile>
        <p className="self-center">
          Modal Cokelat Turki dan tarif potongan Lazada sengaja dikosongkan pada data demo.
          Transaksi yang memakai keduanya tidak dihitung labanya dan ditandai belum
          lengkap, bukan dianggap nol.
        </p>
      </div>
    </div>
  );
}
