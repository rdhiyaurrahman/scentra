"""Skenario pengujian PRD bab 13 (TC-01 … TC-07) atas aturan klasifikasi
dan penyusunan suggested reply. Tidak butuh database.
"""
from datetime import datetime, time, timedelta

import pytest

from app import nlp

NOW = datetime(2026, 11, 10, 10, 0)


@pytest.fixture
def kb() -> nlp.KnowledgeBase:
    return nlp.KnowledgeBase(
        products=[
            nlp.ProductInfo("Kurma Ajwa", ["kurma ajwa", "ajwa"], [
                nlp.VariantInfo("1 kg", "AJW-1000", 24, NOW - timedelta(hours=3)),
                nlp.VariantInfo("500 g", "AJW-500", 0, NOW - timedelta(hours=5)),
                nlp.VariantInfo("250 g", "AJW-250", None, None),
            ]),
            nlp.ProductInfo("Kacang Arab", ["kacang arab", "kacang"], [
                nlp.VariantInfo("500 g", "KCA-500", 61, NOW - timedelta(hours=90)),
            ]),
            nlp.ProductInfo("Cokelat Turki", ["cokelat turki", "coklat turki"], [
                nlp.VariantInfo("Pistachio 100 g", "CKT-P100", 8, NOW - timedelta(hours=6)),
                nlp.VariantInfo("Hazelnut 100 g", "CKT-H100", 0, NOW - timedelta(hours=6)),
            ]),
        ],
        faqs=[nlp.FaqInfo(1, "Apakah produk bersertifikat halal?",
                          "Semua produk kami bersertifikat halal.", ["halal"])],
        shipping={
            "shopee": nlp.ShippingInfo("shopee", "Pesanan sebelum 15.00 WIB dikirim hari ini.",
                                       time(15, 0)),
            "lazada": nlp.ShippingInfo("lazada", None, None),   # sengaja kosong
        },
    )


def run(kb, text, mp="shopee", ref="SP-1", name="Dewi"):
    cls = nlp.classify(text)
    sug = nlp.suggest(kb, text, cls, customer_name=name, marketplace_code=mp,
                      external_reference=ref, now=NOW)
    return cls, sug


# --- TC-01 … TC-07 -----------------------------------------------------------


def test_tc01_stok_tersedia_dan_valid(kb):
    cls, sug = run(kb, "Kak, kurma Ajwa 1 kg ready?")
    assert cls.intent == "stock_inquiry"
    assert sug.needs_verification is False
    assert "tersedia" in sug.text.lower()
    assert sug.sources and sug.sources[0]["type"] == "STOK"


def test_tc02_stok_tidak_ada_minta_verifikasi(kb):
    """Stok belum tercatat tidak boleh dinyatakan ada maupun kosong (AC-05)."""
    cls, sug = run(kb, "Kak, kurma Ajwa 250 g ready?")
    assert cls.intent == "stock_inquiry"
    assert sug.needs_verification is True
    low = sug.text.lower()
    # tidak boleh ada klaim ke salah satu arah
    for klaim in ("tersedia", "ready", "kosong", "habis", "tidak ada"):
        assert klaim not in low, f"balasan tidak boleh mengklaim '{klaim}'"
    assert "belum tercatat" in sug.reason


def test_tc02b_stok_kedaluwarsa_minta_verifikasi(kb):
    cls, sug = run(kb, "Kacang arab 500 g ready kak?")
    assert cls.intent == "stock_inquiry"
    assert sug.needs_verification is True
    assert "48 jam" in sug.reason


def test_tc03_varian_ditampilkan(kb):
    cls, sug = run(kb, "Cokelat Turki ada ukuran apa saja?")
    assert cls.intent == "product_inquiry"
    assert sug.needs_verification is False
    assert "Pistachio 100 g" in sug.text and "Hazelnut 100 g" in sug.text


def test_tc04_pengiriman_pakai_aturan_cutoff(kb):
    cls, sug = run(kb, "Bisa dikirim hari ini?")
    assert cls.intent == "shipping_inquiry"
    assert sug.needs_verification is False
    assert "15.00" in sug.text


def test_tc04b_aturan_pengiriman_kosong_eskalasi(kb):
    _cls, sug = run(kb, "Bisa dikirim hari ini?", mp="lazada")
    assert sug.needs_verification is True
    assert "belum tersedia" in sug.reason


def test_tc05_komplain_prioritas_tinggi(kb):
    cls, sug = run(kb, "Barang saya rusak, kecewa banget")
    assert cls.intent == "complaint"
    assert cls.priority == "high"
    assert sug.needs_verification is True


def test_tc05b_komplain_tidak_tertutup_kata_kunci_lain(kb):
    """Kalimat keluhan yang juga memuat kata 'dikirim' tetap jadi komplain."""
    cls, _ = run(kb, "Kak saya beli 1 kg kacang arab kok yang dikirim 500 g? kecewa banget")
    assert cls.intent == "complaint"
    assert "complaint" in cls.all_intents


def test_tc06_refund_eskalasi(kb):
    cls, sug = run(kb, "Saya mau refund")
    assert cls.intent == "return_refund"
    assert cls.priority == "high"
    assert sug.needs_verification is True


def test_tc07_pesan_tidak_dikenali(kb):
    cls, sug = run(kb, "Kak itu yang kemarin gimana?")
    assert cls.intent == "unknown"
    assert sug.needs_verification is True


def test_tc07b_pertanyaan_umum_dijawab_dari_faq(kb):
    _cls, sug = run(kb, "Produknya halal tidak kak?")
    assert sug.needs_verification is False
    assert sug.sources[0]["type"] == "FAQ"


# --- pencocokan varian -------------------------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("kurma ajwa 1kg masih ada?", "1 kg"),
    ("kurma ajwa 1 kg masih ada?", "1 kg"),
    ("cokelat turki pistachio 100g ready ga", "Pistachio 100 g"),
    ("cokelat turki hazelnut 100 gr ready?", "Hazelnut 100 g"),
])
def test_varian_cocok_walau_penulisan_beda(kb, text, expected):
    product = nlp.find_product(kb, text)
    variant = nlp.find_variant(product, text)
    assert variant is not None and variant.name == expected


def test_stok_nol_menawarkan_varian_lain(kb):
    _cls, sug = run(kb, "cokelat turki hazelnut 100 g ready?")
    assert sug.needs_verification is False
    assert "kosong" in sug.text.lower()
    assert "Pistachio 100 g" in sug.text


def test_pesanan_tanpa_referensi_minta_nomor(kb):
    cls, sug = run(kb, "Status pesanan saya gimana?", ref=None)
    assert cls.intent == "order_inquiry"
    assert sug.needs_verification is True
    assert "nomor pesanan" in sug.reason.lower()


def test_suggested_reply_tidak_pernah_mengklaim_terkirim(kb):
    for text in ["Kak, kurma Ajwa 1 kg ready?", "Saya mau refund", "Bisa dikirim hari ini?"]:
        _cls, sug = run(kb, text)
        assert "terkirim" not in sug.text.lower()
