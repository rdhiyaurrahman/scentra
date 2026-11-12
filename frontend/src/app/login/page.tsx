"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import { Button, Field, inputClass } from "@/lib/ui";

const DEMO = [
  { label: "Ayu — CS", email: "ayu@scentra.test", password: "ayu12345" },
  { label: "Bima — CS", email: "bima@scentra.test", password: "bima12345" },
  { label: "Husin — Pemilik", email: "husin@scentra.test", password: "husin12345" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("ayu@scentra.test");
  const [password, setPassword] = useState("ayu12345");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return; // cegah pengiriman ganda (NFR 9.4)
    setBusy(true);
    setError("");
    try {
      await api.login(email.trim().toLowerCase(), password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal masuk.");
      setBusy(false);
    }
  }

  return (
    <main className="app-bg flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-[920px] overflow-hidden rounded-[28px] border border-line bg-white shadow-[0_24px_70px_rgba(20,24,41,0.12)] md:grid md:grid-cols-[1.05fr_1fr]">
        <section className="hidden flex-col justify-between bg-[linear-gradient(160deg,#eef0ff_0%,#e4edff_55%,#dfe9ff_100%)] p-10 md:flex">
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-[12px] bg-accent text-sm font-bold text-white">
              S
            </span>
            <span className="text-[15px] font-bold tracking-tight">Scentra</span>
          </div>
          <div>
            <h1 className="text-[30px] leading-[1.15] font-bold tracking-tight">
              Satu workspace.
              <br />
              Percakapan lebih jelas.
            </h1>
            <p className="mt-3 max-w-[320px] text-sm text-muted">
              Catat pesan pelanggan dari Shopee, TikTok Shop, dan Lazada dalam satu
              antrean. Scentra menyusun rekomendasi jawaban dari knowledge base toko.
            </p>
          </div>
          <p className="text-[11px] leading-relaxed text-muted">
            Scentra tidak terhubung ke API marketplace. Pesan dicatat manual oleh CS dan
            balasan tetap dikirim melalui Seller Center.
          </p>
        </section>

        <section className="p-8 sm:p-10">
          <h2 className="text-[21px] font-bold tracking-tight">Masuk ke Scentra</h2>
          <p className="mt-1 text-sm text-muted">Gunakan akun yang diberikan pemilik usaha.</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <Field label="Email">
              <input
                className={inputClass}
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Password">
              <input
                className={inputClass}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>

            {error ? (
              <p role="alert" className="rounded-xl bg-rose-bg px-3 py-2.5 text-xs font-medium text-rose-fg">
                {error}
              </p>
            ) : null}

            <Button type="submit" variant="primary" className="w-full !py-2.5" disabled={busy}>
              {busy ? "Memeriksa…" : "Masuk"}
            </Button>
          </form>

          <div className="mt-7 rounded-2xl bg-[#f7f8fc] p-4">
            <p className="text-[11px] font-semibold tracking-wide text-faint uppercase">
              Akun demo (data sintetis)
            </p>
            <div className="mt-2.5 space-y-1.5">
              {DEMO.map((d) => (
                <button
                  key={d.email}
                  type="button"
                  onClick={() => {
                    setEmail(d.email);
                    setPassword(d.password);
                  }}
                  className="focus-ring flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs transition hover:bg-white"
                >
                  <span className="font-medium">{d.label}</span>
                  <span className="font-mono text-[11px] text-faint">{d.email}</span>
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
