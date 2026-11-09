"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearSession, getUser, type User } from "@/lib/api";

const NAV = [
  {
    section: "Operasional",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: "◧" },
      { href: "/inbox", label: "Unified Inbox", icon: "✉" },
    ],
  },
  {
    section: "Pengaturan",
    items: [{ href: "/knowledge", label: "Knowledge Base", icon: "◆" }],
  },
];

const ROLE_LABEL: Record<string, string> = {
  cs: "Customer Service",
  supervisor: "Supervisor",
  owner: "Pemilik usaha",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const u = getUser();
    if (!u) router.replace("/login");
    else setUser(u);
  }, [router]);

  if (!user) {
    return (
      <div className="app-bg grid min-h-screen place-items-center text-sm text-muted">
        Memuat…
      </div>
    );
  }

  return (
    <div className="app-bg min-h-screen">
      <div className="mx-auto flex max-w-[1600px]">
        <aside className="sticky top-0 hidden h-screen w-[232px] flex-none flex-col border-r border-line bg-white px-3.5 py-5 lg:flex">
          <div className="mb-7 flex items-center gap-2.5 px-2">
            <span className="grid h-9 w-9 place-items-center rounded-[12px] bg-navy text-sm font-bold text-white">
              S
            </span>
            <span className="leading-tight">
              <span className="block text-[14px] font-bold tracking-tight">Scentra</span>
              <span className="block text-[10.5px] text-faint">Manual Unified Inbox</span>
            </span>
          </div>

          <nav className="flex-1 space-y-6">
            {NAV.map((group) => (
              <div key={group.section}>
                <p className="mb-2 px-2 text-[10px] font-semibold tracking-[0.09em] text-faint uppercase">
                  {group.section}
                </p>
                <ul className="space-y-1">
                  {group.items.map((item) => {
                    const active = pathname.startsWith(item.href);
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          aria-current={active ? "page" : undefined}
                          className={`focus-ring flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[13px] font-medium transition ${
                            active
                              ? "bg-navy text-white"
                              : "text-muted hover:bg-[#f5f6fb] hover:text-ink"
                          }`}
                        >
                          <span className="w-4 text-center text-[13px] opacity-80">
                            {item.icon}
                          </span>
                          {item.label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>

          <div className="rounded-2xl bg-[#f6f7fc] p-3.5 text-[11px] leading-relaxed text-muted">
            <p className="mb-1 font-semibold text-ink">Tanpa API marketplace</p>
            Pesan dicatat manual. Balasan dikirim lewat Seller Center, bukan dari Scentra.
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-line bg-white/85 px-5 py-3 backdrop-blur-md sm:px-7">
            <div className="lg:hidden">
              <span className="grid h-8 w-8 place-items-center rounded-[10px] bg-navy text-xs font-bold text-white">
                S
              </span>
            </div>
            <div className="hidden sm:block">
              <p className="text-[13px] font-semibold tracking-tight">Scentra Parfume</p>
              <p className="text-[11px] text-faint">Oleh-oleh haji &amp; herbal</p>
            </div>

            <nav className="flex gap-1 lg:hidden">
              {NAV.flatMap((g) => g.items).map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                    pathname.startsWith(item.href) ? "bg-navy text-white" : "text-muted"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="flex-1" />

            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <p className="text-[12.5px] font-semibold leading-tight">{user.name}</p>
                <p className="text-[11px] text-faint">{ROLE_LABEL[user.role] ?? user.role}</p>
              </div>
              <span className="grid h-9 w-9 place-items-center rounded-full bg-lav-bg text-[12px] font-bold text-lav-fg">
                {user.name.slice(0, 1).toUpperCase()}
              </span>
              <button
                onClick={() => {
                  clearSession();
                  router.replace("/login");
                }}
                className="focus-ring rounded-full border border-line px-3 py-1.5 text-xs font-medium text-muted transition hover:bg-[#f7f8fc]"
              >
                Keluar
              </button>
            </div>
          </header>

          <main className="px-5 py-6 sm:px-7">{children}</main>
        </div>
      </div>
    </div>
  );
}
