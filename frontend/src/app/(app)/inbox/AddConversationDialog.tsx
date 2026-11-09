"use client";

import { FormEvent, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Button, MARKETPLACES, inputClass } from "@/lib/ui";

export function AddConversationDialog({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (conversationId: number, merged: boolean) => void | Promise<void>;
}) {
  const [marketplace, setMarketplace] = useState<"shopee" | "tiktok" | "lazada">("shopee");
  const [customer, setCustomer] = useState("");
  const [reference, setReference] = useState("");
  const [product, setProduct] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [duplicate, setDuplicate] = useState<{
    conversation_id: number;
    customer_name: string;
    status: string;
  } | null>(null);

  // Peringatan duplikasi muncul sebelum CS menyimpan (AC-02, FR-03).
  useEffect(() => {
    const ref = reference.trim();
    if (!ref) {
      setDuplicate(null);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await api.checkDuplicate(marketplace, ref);
        setDuplicate(
          res.found
            ? {
                conversation_id: res.conversation_id!,
                customer_name: res.customer_name!,
                status: res.status!,
              }
            : null,
        );
      } catch {
        setDuplicate(null);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [marketplace, reference]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!customer.trim() || !text.trim()) {
      setError("Marketplace, nama pelanggan, dan isi pesan wajib diisi.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api.createConversation({
        marketplace_code: marketplace,
        customer_name: customer.trim(),
        external_reference: reference.trim() || null,
        product_hint: product.trim() || null,
        message_text: text.trim(),
        merge_into_existing: true,
      });
      await onSaved(res.id, res.merged_into_existing);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menyimpan pesan.");
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center overflow-auto bg-[rgba(20,24,41,0.45)] p-5 backdrop-blur-[3px]"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <form
        onSubmit={submit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-title"
        className="w-full max-w-[560px] overflow-hidden rounded-[22px] bg-white shadow-[0_24px_70px_rgba(20,24,41,0.28)]"
      >
        <div className="border-b border-line px-6 py-4">
          <h3 id="add-title" className="text-[17px] font-bold tracking-tight">
            Tambah percakapan
          </h3>
          <p className="mt-0.5 text-xs text-muted">
            Salin pesan pelanggan dari Seller Center. Waktu capture dicatat otomatis.
          </p>
        </div>

        <div className="space-y-3.5 px-6 py-5">
          {duplicate ? (
            <p className="rounded-xl bg-lav-bg px-3.5 py-3 text-[12.5px] leading-relaxed text-lav-fg">
              Referensi <b>{reference.trim()}</b> sudah ada pada percakapan CV-
              {String(duplicate.conversation_id).padStart(3, "0")} ({duplicate.customer_name},{" "}
              {duplicate.status}). Pesan akan <b>ditambahkan ke percakapan tersebut</b>,
              bukan membuat percakapan baru.
            </p>
          ) : null}

          <div className="grid gap-3.5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-muted">
                Marketplace <span className="text-rose-fg">*</span>
              </span>
              <select
                className={inputClass}
                value={marketplace}
                onChange={(e) => setMarketplace(e.target.value as typeof marketplace)}
              >
                {Object.entries(MARKETPLACES).map(([code, mp]) => (
                  <option key={code} value={code}>
                    {mp.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-muted">
                Nama / label pelanggan <span className="text-rose-fg">*</span>
              </span>
              <input
                className={inputClass}
                placeholder="mis. Dewi Rahma"
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
                autoFocus
              />
            </label>
          </div>

          <div className="grid gap-3.5 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-muted">
                Referensi percakapan / order
              </span>
              <input
                className={inputClass}
                placeholder="mis. SP-88211"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
              <span className="mt-1 block text-[11px] text-faint">
                Pengenal utama untuk mencocokkan percakapan.
              </span>
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-muted">
                Produk terkait (opsional)
              </span>
              <input
                className={inputClass}
                placeholder="mis. Kurma Ajwa 1 kg"
                value={product}
                onChange={(e) => setProduct(e.target.value)}
              />
            </label>
          </div>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-muted">
              Isi pesan pelanggan <span className="text-rose-fg">*</span>
            </span>
            <textarea
              className={`${inputClass} min-h-[96px] resize-y`}
              placeholder="Salin persis dari Seller Center…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </label>

          {error ? (
            <p role="alert" className="rounded-xl bg-rose-bg px-3 py-2.5 text-xs font-medium text-rose-fg">
              {error}
            </p>
          ) : null}

          <p className="text-[11px] text-faint">
            Sumber input tercatat sebagai <span className="font-mono">manual</span>. Scentra
            tidak pernah mengambil pesan langsung dari marketplace.
          </p>
        </div>

        <div className="flex justify-end gap-2 border-t border-line px-6 py-4">
          <Button type="button" onClick={onClose} disabled={busy}>
            Batal
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Menyimpan…" : "Simpan pesan"}
          </Button>
        </div>
      </form>
    </div>
  );
}
