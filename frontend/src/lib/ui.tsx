"use client";

import { ReactNode } from "react";

export const MARKETPLACES = {
  shopee: { name: "Shopee", tone: "amber" as Tone, emoji: "🛍️" },
  tiktok: { name: "TikTok Shop", tone: "slate" as Tone, emoji: "🎵" },
  lazada: { name: "Lazada", tone: "sky" as Tone, emoji: "📦" },
};

export const INTENTS: Record<string, string> = {
  stock_inquiry: "Stok",
  product_inquiry: "Produk / Varian",
  shipping_inquiry: "Pengiriman",
  order_inquiry: "Pesanan",
  complaint: "Komplain",
  return_refund: "Retur / Refund",
  other: "Lainnya",
  unknown: "Tidak dikenali",
};

export const STATUSES = [
  "New",
  "Open",
  "Assigned",
  "Waiting for Staff",
  "Waiting for Customer",
  "Resolved",
  "Closed",
];

export type Tone = "lav" | "mint" | "amber" | "rose" | "sky" | "slate";

const TONES: Record<Tone, string> = {
  lav: "bg-lav-bg text-lav-fg",
  mint: "bg-mint-bg text-mint-fg",
  amber: "bg-amber-bg text-amber-fg",
  rose: "bg-rose-bg text-rose-fg",
  sky: "bg-sky-bg text-sky-fg",
  slate: "bg-[#eef0f6] text-[#4d5370]",
};

export function Pill({
  children,
  tone = "slate",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <span className={`pill ${TONES[tone]} ${className}`}>{children}</span>;
}

export function Tile({ children, tone = "lav" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`tile ${TONES[tone]}`}>{children}</span>;
}

export function statusTone(status: string): Tone {
  if (status === "Waiting for Staff") return "amber";
  if (status === "Resolved" || status === "Closed") return "mint";
  if (status === "New") return "sky";
  return "slate";
}

export function priorityTone(priority: string): Tone {
  return priority === "high" ? "rose" : "slate";
}

/** Status dibedakan huruf, bukan warna saja (NFR 9.5 aksesibilitas). */
export function priorityLabel(priority: string): string {
  return priority === "high" ? "Tinggi" : priority === "low" ? "Rendah" : "Normal";
}

export function relativeTime(iso: string): string {
  const then = new Date(iso.endsWith("Z") ? iso : `${iso}Z`).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "baru saja";
  if (mins < 60) return `${mins} mnt lalu`;
  if (mins < 1440) return `${Math.round(mins / 60)} jam lalu`;
  return `${Math.round(mins / 1440)} hari lalu`;
}

export function formatTime(iso: string): string {
  return new Date(iso.endsWith("Z") ? iso : `${iso}Z`).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Button({
  children,
  variant = "ghost",
  className = "",
  ...rest
}: {
  children: ReactNode;
  variant?: "primary" | "ghost" | "soft";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  // Referensi tidak memakai tombol berisi warna sama sekali; tindakan utama
  // digambarkan sebagai tombol bergaris biru di atas putih.
  const styles = {
    primary: "bg-white border border-accent-line text-accent hover:bg-accent-soft",
    ghost: "bg-white border border-line text-ink hover:bg-[#f7f8fc]",
    soft: "bg-accent-soft text-accent hover:bg-[#e3ecff]",
  }[variant];
  return (
    <button
      {...rest}
      className={`focus-ring rounded-full px-4 py-2 text-[13px] font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold text-muted">{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-[11px] text-faint">{hint}</span> : null}
    </label>
  );
}

export const inputClass =
  "focus-ring w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm outline-none transition placeholder:text-faint";

/** Rupiah bulat. Nilai null berarti belum diketahui, dan TIDAK ditulis sebagai 0. */
export function rupiah(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value < 0 ? "-" : "";
  return `${sign}Rp${Math.abs(value).toLocaleString("id-ID")}`;
}

export function persen(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}%`;
}
