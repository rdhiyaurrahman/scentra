"""Klasifikasi pesan (FR-06) dan penyusunan suggested reply (FR-08/FR-09).

Murni fungsi atas snapshot knowledge base, tanpa sentuhan database, supaya bisa
diuji langsung di pytest tanpa menyalakan Postgres.

Tidak memakai model bahasa apa pun: aturan kata kunci yang hasilnya bisa
dijelaskan ke juri dan ditelusuri baris per baris.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional

RULE_VERSION = "rules-v1.0"
STALE_AFTER = timedelta(hours=48)

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


MARKETPLACE_NAMES = {"shopee": "Shopee", "tiktok": "TikTok Shop", "lazada": "Lazada"}

# Urutan penting. Komplain dan refund diperiksa lebih dulu supaya kalimat seperti
# "kok yang dikirim 500 g, kecewa" tidak tertangkap sebagai pertanyaan pengiriman.
RULES: list[tuple[str, tuple[str, ...]]] = [
    ("complaint", (
        "rusak", "pecah", "bocor", "kecewa", "komplain", "protes", "salah kirim",
        "salah barang", "tidak sesuai", "ga sesuai", "gak sesuai", "nggak sesuai",
        "beda sama", "basi", "jamur", "berulat", "kok yang dikirim", "kok dikirim",
        "parah", "penipu", "lama banget", "belum sampai juga", "kurang berat",
        "kurang isi", "mengecewakan",
    )),
    ("return_refund", (
        "refund", "retur", "pengembalian", "uang kembali", "balikin uang",
        "tukar barang", "ganti barang", "batalkan pesanan", "cancel pesanan",
    )),
    ("stock_inquiry", (
        "ready", "redy", "redi", "stok", "stock", "tersedia", "masih ada",
        "ada gak", "ada ga", "adakah", "kosong", "restock", "ready stock",
    )),
    ("shipping_inquiry", (
        "dikirim hari ini", "kirim hari ini", "bisa dikirim", "ongkir",
        "ongkos kirim", "cutoff", "cut off", "berapa hari sampai", "estimasi",
        "kapan sampai", "same day", "instant", "ekspedisi", "kurir",
    )),
    ("product_inquiry", (
        "ukuran apa", "ukuran berapa", "varian", "size", "berapa gram",
        "isi berapa", "kemasan", "rasa apa", "pilihan", "ada ukuran", "beratnya",
    )),
    ("order_inquiry", (
        "pesanan saya", "nomor pesanan", "no pesanan", "resi", "nomor resi",
        "status pesanan", "orderan saya", "sudah dikirim belum",
    )),
]


# --- bentuk data knowledge base ---------------------------------------------


@dataclass
class VariantInfo:
    name: str
    sku: str
    quantity: Optional[int] = None          # None = belum tercatat, BUKAN nol
    stock_updated_at: Optional[datetime] = None


@dataclass
class ProductInfo:
    name: str
    aliases: list[str]
    variants: list[VariantInfo] = field(default_factory=list)


@dataclass
class FaqInfo:
    id: int
    question: str
    answer: str
    keywords: list[str]


@dataclass
class ShippingInfo:
    marketplace_code: str
    rule_text: Optional[str] = None
    cutoff_time: Optional[time] = None


@dataclass
class KnowledgeBase:
    products: list[ProductInfo] = field(default_factory=list)
    faqs: list[FaqInfo] = field(default_factory=list)
    shipping: dict[str, ShippingInfo] = field(default_factory=dict)
    refund_rule: Optional[str] = None       # belum ada di MVP -> selalu eskalasi


@dataclass
class Classified:
    intent: str
    priority: str
    all_intents: list[str]
    rule_version: str = RULE_VERSION


@dataclass
class Suggestion:
    text: str
    sources: list[dict]
    needs_verification: bool
    reason: str = ""


# --- util --------------------------------------------------------------------

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Rapikan jadi ' kata kata ' supaya pencocokan kata kunci punya batas jelas."""
    return " " + _SPACE.sub(" ", _PUNCT.sub(" ", text.lower())).strip() + " "


def squash(text: str) -> str:
    """Buang spasi & tanda baca agar '100 g', '100g', dan '100gr' sama.

    shortcut: pencocokan substring, jadi '1 kg' ikut cocok pada '11 kg'.
    Ganti ke pencocokan token/SKU kalau katalog sudah lebih dari puluhan varian.
    """
    s = re.sub(r"[^a-z0-9]", "", text.lower())
    return re.sub(r"gr(?![a-z])", "g", s)


# --- klasifikasi -------------------------------------------------------------


def classify(text: str) -> Classified:
    t = normalize(text)
    hits = [intent for intent, words in RULES
            if any(f" {w}" in t or f"{w} " in t for w in words)]
    intent = hits[0] if hits else "unknown"
    high = "complaint" in hits or "return_refund" in hits
    return Classified(intent=intent, priority="high" if high else "normal",
                      all_intents=hits)


# --- pencarian di knowledge base ---------------------------------------------


def find_product(kb: KnowledgeBase, text: str) -> Optional[ProductInfo]:
    t = normalize(text)
    for p in kb.products:
        if any(alias.lower() in t for alias in p.aliases):
            return p
    return None


def find_variant(product: Optional[ProductInfo], text: str) -> Optional[VariantInfo]:
    if not product:
        return None
    t = squash(text)
    # varian paling spesifik lebih dulu, mis. "Pistachio 100 g" sebelum "100 g"
    for v in sorted(product.variants, key=lambda v: -len(squash(v.name))):
        if squash(v.name) in t:
            return v
    return None


def find_faq(kb: KnowledgeBase, text: str) -> Optional[FaqInfo]:
    t = normalize(text)
    for f in kb.faqs:
        if any(k.lower() in t for k in f.keywords):
            return f
    return None


def is_stale(variant: VariantInfo, now: Optional[datetime] = None) -> bool:
    if variant.stock_updated_at is None:
        return True
    return (now or utcnow()) - variant.stock_updated_at > STALE_AFTER


def _ago(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if dt is None:
        return "belum pernah"
    mins = int(((now or utcnow()) - dt).total_seconds() // 60)
    if mins < 60:
        return f"{mins} menit lalu"
    if mins < 1440:
        return f"{mins // 60} jam lalu"
    return f"{mins // 1440} hari lalu"


# --- suggested reply ---------------------------------------------------------


def suggest(
    kb: KnowledgeBase,
    text: str,
    cls: Classified,
    *,
    customer_name: str,
    marketplace_code: str,
    external_reference: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Suggestion:
    """Susun rekomendasi balasan HANYA dari fakta yang ada di knowledge base.

    Kalau data tidak ada / kedaluwarsa, jawaban tidak boleh menyatakan apa pun
    dan percakapan ditandai perlu verifikasi (FR-08, FR-09, AC-05).
    """
    now = now or utcnow()
    hi = f"Halo Kak {customer_name},"
    product = find_product(kb, text)
    variant = find_variant(product, text)
    ship = kb.shipping.get(marketplace_code)
    intent = cls.intent

    if intent == "complaint":
        return Suggestion(
            text=(f"{hi} mohon maaf atas ketidaknyamanannya.\n"
                  "Kami akan segera memeriksa pesanan Kakak. Boleh dibantu kirimkan "
                  "foto/video produk yang diterima beserta nomor pesanannya? Tim kami "
                  "akan menindaklanjuti dan mengabari hasilnya."),
            sources=[], needs_verification=True,
            reason="Keluhan pelanggan — tidak dijawab template generik sebelum diperiksa staf.")

    if intent == "return_refund":
        return Suggestion(
            text=(f"{hi} terima kasih sudah menghubungi kami.\n"
                  "Permintaan Kakak sedang kami teruskan ke tim terkait untuk diperiksa. "
                  "Mohon ditunggu, kami kabari secepatnya melalui chat ini."),
            sources=[], needs_verification=True,
            reason=("Aturan retur/refund belum tersedia di knowledge base — "
                    "wajib diperiksa pemilik usaha."))

    if intent == "stock_inquiry":
        if product is None:
            return Suggestion(
                text=f"{hi} boleh dibantu sebutkan nama produk dan ukurannya? "
                     "Akan kami cek ketersediaannya ya.",
                sources=[], needs_verification=True,
                reason="Produk tidak dapat dikenali dari isi pesan.")
        if variant is None:
            pilihan = ", ".join(v.name for v in product.variants)
            return Suggestion(
                text=f"{hi} untuk {product.name} tersedia dalam pilihan: {pilihan}.\n"
                     "Ukuran mana yang Kakak butuhkan? Akan kami cek ketersediaannya.",
                sources=[_src("PRODUK", product.name)], needs_verification=False)
        if variant.quantity is None:
            return Suggestion(
                text=f"{hi} mohon waktu sebentar, kami periksa dulu stok "
                     f"{product.name} {variant.name} di gudang ya. Kami kabari secepatnya.",
                sources=[_src("PRODUK", f"{product.name} {variant.name}")],
                needs_verification=True,
                reason=(f"Stok {product.name} {variant.name} belum tercatat di knowledge "
                        "base. Tidak boleh dinyatakan tersedia maupun kosong."))
        if is_stale(variant, now):
            return Suggestion(
                text=f"{hi} mohon waktu sebentar, kami konfirmasi dulu stok terbaru "
                     f"{product.name} {variant.name} ya. Kami kabari segera.",
                sources=[_src("STOK", f"{variant.name} · {_ago(variant.stock_updated_at, now)}")],
                needs_verification=True,
                reason=(f"Data stok terakhir diperbarui {_ago(variant.stock_updated_at, now)} "
                        "(lebih dari 48 jam) sehingga belum bisa dijanjikan."))
        if variant.quantity == 0:
            lain = ", ".join(v.name for v in product.variants
                             if v.sku != variant.sku and (v.quantity or 0) > 0) or "—"
            return Suggestion(
                text=f"{hi} mohon maaf, {product.name} {variant.name} sedang kosong.\n"
                     f"Tersedia ukuran lain: {lain}. Apakah Kakak berkenan?",
                sources=[_src("STOK", f"{variant.name} · stok 0 · {_ago(variant.stock_updated_at, now)}")],
                needs_verification=False)
        return Suggestion(
            text=f"{hi} {product.name} {variant.name} tersedia ya.\n"
                 "Silakan langsung checkout, pesanan akan kami proses sesuai jadwal pengiriman.",
            sources=[_src("STOK", f"{variant.name} · {variant.quantity} pcs · "
                                  f"{_ago(variant.stock_updated_at, now)}")],
            needs_verification=False)

    if intent == "product_inquiry":
        if product is None:
            return Suggestion(
                text=f"{hi} boleh dibantu sebutkan produk yang dimaksud? "
                     "Akan kami kirimkan pilihan ukurannya ya.",
                sources=[], needs_verification=True,
                reason="Produk tidak dapat dikenali dari isi pesan.")
        daftar = "\n".join(f"• {v.name}" for v in product.variants)
        return Suggestion(
            text=f"{hi} {product.name} tersedia dalam pilihan berikut:\n{daftar}\n"
                 "Ukuran mana yang Kakak minati?",
            sources=[_src("PRODUK", product.name)], needs_verification=False)

    if intent == "shipping_inquiry":
        if ship is None or not ship.rule_text or ship.cutoff_time is None:
            nama = MARKETPLACE_NAMES.get(marketplace_code, marketplace_code)
            return Suggestion(
                text=f"{hi} mohon waktu sebentar, kami cek dulu jadwal pengiriman "
                     "untuk pesanan Kakak ya.",
                sources=[], needs_verification=True,
                reason=f"Aturan pengiriman {nama} belum tersedia di knowledge base.")
        kini = (f"Saat ini masih sebelum pukul {ship.cutoff_time:%H.%M}, jadi pesanan "
                "Kakak masih bisa kami kirim hari ini."
                if now.time() < ship.cutoff_time else
                f"Saat ini sudah lewat pukul {ship.cutoff_time:%H.%M}, sehingga pesanan "
                "dikirim pada hari kerja berikutnya.")
        nama = MARKETPLACE_NAMES.get(marketplace_code, marketplace_code)
        return Suggestion(
            text=f"{hi} {ship.rule_text}\n{kini}",
            sources=[_src("ATURAN", f"Cutoff {nama} {ship.cutoff_time:%H.%M}")],
            needs_verification=False)

    if intent == "order_inquiry":
        if not external_reference:
            return Suggestion(
                text=f"{hi} boleh dibantu kirimkan nomor pesanannya? "
                     "Akan langsung kami cek statusnya ya.",
                sources=[], needs_verification=True,
                reason="Nomor pesanan belum tercatat pada percakapan ini.")
        return Suggestion(
            text=f"{hi} kami cek dulu status pesanan {external_reference} ya. "
                 "Mohon ditunggu, kami kabari di chat ini.",
            sources=[_src("REF", external_reference)], needs_verification=True,
            reason="Status pesanan tidak ada di ResponIn — harus dicek manual di Seller Center.")

    faq = find_faq(kb, text)
    if faq is not None:
        return Suggestion(text=f"{hi} {faq.answer}",
                          sources=[_src("FAQ", faq.question)], needs_verification=False)

    return Suggestion(
        text=f"{hi} terima kasih sudah menghubungi kami. Mohon waktu sebentar, "
             "pesan Kakak sedang kami periksa dan akan kami balas secepatnya.",
        sources=[], needs_verification=True,
        reason="Pesan tidak dikenali aturan klasifikasi — perlu dibaca dan dijawab staf.")


def _src(kind: str, label: str) -> dict:
    return {"type": kind, "label": label}
