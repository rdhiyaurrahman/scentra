"use client";

import { useEffect, useState } from "react";

import {
  api,
  type ConversationDetail,
  type ConversationMessage,
  type User,
} from "@/lib/api";
import {
  Button,
  INTENTS,
  MARKETPLACES,
  Pill,
  STATUSES,
  formatTime,
  inputClass,
  priorityLabel,
  priorityTone,
  statusTone,
} from "@/lib/ui";

export function ConversationPane({
  detail,
  users,
  me,
  onChanged,
  onFlash,
}: {
  detail: ConversationDetail;
  users: User[];
  me: User | null;
  onChanged: (message?: string) => Promise<void>;
  onFlash: (message: string) => void;
}) {
  const lastCustomer = [...detail.messages]
    .reverse()
    .find((m) => m.sender_type === "customer");
  const reply = lastCustomer?.suggested_reply ?? null;

  const [draft, setDraft] = useState(reply?.reply_text ?? "");
  const [note, setNote] = useState("");
  const [extraMessage, setExtraMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => setDraft(reply?.reply_text ?? ""), [reply?.id, reply?.reply_text]);

  // Matriks hak akses PRD bab 4.3: pemilik boleh membaca inbox, tidak menulis.
  const canWrite = me?.role === "cs";
  const mp = MARKETPLACES[detail.marketplace_code];

  async function guard(fn: () => Promise<void>) {
    if (busy) return; // cegah klik ganda (NFR 9.4)
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      onFlash(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setBusy(false);
    }
  }

  async function copyReply() {
    if (!reply) return;
    await guard(async () => {
      if (draft !== reply.reply_text) await api.editReply(reply.id, draft);
      try {
        await navigator.clipboard.writeText(draft);
      } catch {
        /* clipboard bisa diblokir browser; pencatatan tetap jalan */
      }
      await api.markCopied(reply.id);
      await onChanged();
      onFlash(
        "Teks tersalin. Kirim lewat Seller Center — status percakapan tidak berubah.",
      );
    });
  }

  return (
    <section className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_282px]">
      <div className="space-y-4">
        <div className="card p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-[19px] font-bold tracking-tight">{detail.customer_name}</h2>
              <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                <Pill tone={mp.tone}>{mp.name}</Pill>
                <span className="font-mono text-[11px]">CV-{String(detail.id).padStart(3, "0")}</span>
                {detail.external_reference ? (
                  <span className="font-mono text-[11px]">· Ref {detail.external_reference}</span>
                ) : (
                  <span className="text-faint">· tanpa referensi percakapan</span>
                )}
              </div>
            </div>
            <Pill tone={priorityTone(detail.priority)}>
              Prioritas {priorityLabel(detail.priority)}
            </Pill>
          </div>

          <div className="mt-4 space-y-2.5 border-t border-line pt-4">
            {detail.messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>

          <div className="mt-4 flex gap-2 border-t border-line pt-4">
            <input
              className={inputClass}
              disabled={!canWrite}
              placeholder="Catat pesan pelanggan berikutnya…"
              value={extraMessage}
              onChange={(e) => setExtraMessage(e.target.value)}
            />
            <Button
              disabled={busy || !canWrite || !extraMessage.trim()}
              onClick={() =>
                guard(async () => {
                  await api.addMessage(detail.id, extraMessage.trim());
                  setExtraMessage("");
                  await onChanged("Pesan ditambahkan dan diklasifikasikan.");
                })
              }
            >
              Simpan
            </Button>
          </div>
        </div>

        {lastCustomer?.classification ? (
          <div className="card p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-[15px] font-bold tracking-tight">Klasifikasi</h3>
              <span className="font-mono text-[11px] text-faint">
                {lastCustomer.classification.rule_version}
                {lastCustomer.classification.corrected_by ? " · dikoreksi CS" : ""}
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-muted">
                  Intent (dapat dikoreksi CS)
                </span>
                <select
                  className={inputClass}
                  disabled={!canWrite}
                  value={lastCustomer.classification.intent}
                  onChange={(e) =>
                    guard(async () => {
                      await api.correctIntent(lastCustomer.id, e.target.value);
                      await onChanged("Klasifikasi dikoreksi dan rekomendasi disusun ulang.");
                    })
                  }
                >
                  {Object.entries(INTENTS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-muted">Prioritas</span>
                <select
                  className={inputClass}
                  disabled={!canWrite}
                  value={detail.priority}
                  onChange={(e) =>
                    guard(async () => {
                      await api.patchConversation(detail.id, { priority: e.target.value });
                      await onChanged("Prioritas diperbarui.");
                    })
                  }
                >
                  {["high", "normal", "low"].map((p) => (
                    <option key={p} value={p}>
                      {priorityLabel(p)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {lastCustomer.classification.all_intents.length > 1 ? (
              <p className="mt-3 text-xs text-muted">
                Terdeteksi lebih dari satu indikasi:{" "}
                {lastCustomer.classification.all_intents
                  .map((i) => INTENTS[i] ?? i)
                  .join(", ")}
                .
              </p>
            ) : null}
          </div>
        ) : null}

        {reply ? (
          <div className="card overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-4">
              <div>
                <h3 className="text-[15px] font-bold tracking-tight">Suggested reply</h3>
                <p className="mt-0.5 text-xs text-muted">
                  Rekomendasi internal. Scentra tidak mengirim pesan ke marketplace.
                </p>
              </div>
              <Pill tone={reply.copied_at ? "sky" : "slate"}>
                {reply.copied_at ? "pernah disalin · belum dikirim" : "belum dikirim"}
              </Pill>
            </div>

            {reply.needs_verification ? (
              <p className="border-b border-[#f3dcbd] bg-amber-bg px-5 py-3 text-[12.5px] font-medium text-amber-fg">
                ⚠ Perlu verifikasi — {reply.verification_reason}
              </p>
            ) : null}

            <textarea
              className="focus-ring min-h-[128px] w-full resize-y border-0 px-5 py-4 text-sm leading-relaxed outline-none"
              value={draft}
              disabled={!canWrite}
              onChange={(e) => setDraft(e.target.value)}
              aria-label="Teks rekomendasi balasan"
            />

            <div className="flex flex-wrap gap-1.5 px-5 pb-3">
              {reply.knowledge_sources.length ? (
                reply.knowledge_sources.map((s, i) => (
                  <Pill key={i} tone="mint">
                    {s.type} · {s.label}
                  </Pill>
                ))
              ) : (
                <Pill>tanpa sumber knowledge base</Pill>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3.5">
              <Button variant="primary" onClick={copyReply} disabled={busy || !canWrite || !draft.trim()}>
                Salin teks
              </Button>
              <Button
                disabled={busy || !canWrite}
                onClick={() =>
                  guard(async () => {
                    await api.addAction(
                      detail.id,
                      `Balasan dikirim melalui Seller Center ${mp.name}.`,
                    );
                    await onChanged(
                      "Tindakan dicatat. Scentra tidak memverifikasi pengiriman di marketplace.",
                    );
                  })
                }
              >
                Catat: sudah dikirim via Seller Center
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <aside className="space-y-4">
        <div className="card space-y-3 p-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-muted">Status</span>
            <select
              className={inputClass}
              disabled={!canWrite}
              value={detail.status}
              onChange={(e) =>
                guard(async () => {
                  await api.patchConversation(detail.id, { status: e.target.value });
                  await onChanged("Status diperbarui dan tercatat di riwayat.");
                })
              }
            >
              {STATUSES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold text-muted">
              Penanggung jawab
            </span>
            <select
              className={inputClass}
              disabled={!canWrite}
              value={detail.assigned_user_id ?? ""}
              onChange={(e) =>
                guard(async () => {
                  await api.patchConversation(detail.id, {
                    assigned_user_id: e.target.value ? Number(e.target.value) : null,
                  });
                  await onChanged("Penugasan diperbarui.");
                })
              }
            >
              <option value="">— belum ditugaskan —</option>
              {users
                .filter((u) => u.role !== "owner")
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
            </select>
            {!canWrite ? (
              <span className="mt-1 block text-[11px] text-faint">
                Penugasan diatur CS. Pemilik membaca inbox tanpa mengubahnya.
              </span>
            ) : null}
          </label>

          <p className="rounded-xl bg-[#f7f8fc] px-3 py-2.5 text-[11px] leading-relaxed text-muted">
            Status di Scentra adalah pencatatan internal, bukan bukti bahwa pesan sudah
            terkirim atau masalah selesai di marketplace.
          </p>
        </div>

        <div className="card p-4">
          <h3 className="mb-2 text-sm font-bold tracking-tight">Catatan internal</h3>
          <textarea
            className={`${inputClass} min-h-[72px] resize-y`}
            placeholder="Tidak terlihat pelanggan…"
            disabled={!canWrite}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <Button
            className="mt-2 w-full"
            disabled={busy || !canWrite || !note.trim()}
            onClick={() =>
              guard(async () => {
                await api.addNote(detail.id, note.trim());
                setNote("");
                await onChanged("Catatan internal tersimpan.");
              })
            }
          >
            Simpan catatan
          </Button>
        </div>

        <div className="card p-4">
          <h3 className="mb-2 text-sm font-bold tracking-tight">Riwayat aktivitas</h3>
          {detail.events.length === 0 ? (
            <p className="text-xs text-muted">Belum ada aktivitas.</p>
          ) : (
            <ul className="divide-y divide-line">
              {detail.events.map((e) => (
                <li key={e.id} className="py-2">
                  <p className="text-[12.5px] leading-snug">{e.detail}</p>
                  <p className="mt-0.5 text-[10.5px] text-faint">
                    {e.author_name ?? "sistem"} · {formatTime(e.created_at)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </section>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  if (message.sender_type === "internal_note") {
    return (
      <div className="ml-auto max-w-[86%] rounded-2xl border border-dashed border-[#efd9a7] bg-[#fffbeb] px-4 py-3">
        <p className="mb-1 text-[10px] font-bold tracking-wide text-[#8a6d1f] uppercase">
          Catatan internal
        </p>
        <p className="text-[13px] whitespace-pre-wrap">{message.message_text}</p>
        <p className="mt-1.5 text-[10.5px] text-faint">
          {message.author_name} · {formatTime(message.captured_at)}
        </p>
      </div>
    );
  }
  if (message.sender_type === "cs_action") {
    return (
      <div className="ml-auto max-w-[86%] rounded-2xl bg-mint-bg px-4 py-3">
        <p className="mb-1 text-[10px] font-bold tracking-wide text-mint-fg uppercase">
          Tindakan CS
        </p>
        <p className="text-[13px] whitespace-pre-wrap">{message.message_text}</p>
        <p className="mt-1.5 text-[10.5px] text-faint">
          {message.author_name} · {formatTime(message.captured_at)}
        </p>
      </div>
    );
  }
  return (
    <div className="max-w-[86%] rounded-2xl border border-line bg-[#f9fafd] px-4 py-3">
      <p className="text-[13px] whitespace-pre-wrap">{message.message_text}</p>
      <p className="mt-1.5 text-[10.5px] text-faint">
        Pelanggan · dicatat {formatTime(message.captured_at)} · sumber: {message.source}
      </p>
    </div>
  );
}
