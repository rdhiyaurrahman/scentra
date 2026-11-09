import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Scentra — Manual Unified Inbox",
  description:
    "Workspace internal customer service untuk mencatat dan menangani percakapan " +
    "Shopee, TikTok Shop, dan Lazada dalam satu tempat.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
