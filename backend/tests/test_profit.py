"""Masalah 2 — pengujian perhitungan keuntungan.

Studi kasus meminta dua hal diperiksa penguji:
  - hasil dicocokkan dengan hitungan acuan,
  - biaya yang hilang atau terhitung ganda terdeteksi.
Keduanya diuji di berkas ini, lengkap dengan hitungan manual di komentar.
"""
from datetime import datetime

import pytest

from app import profit
from app.profit import TxInput, build_report, compute_transaction

DATE = datetime(2026, 11, 1, 10, 0)


def tx(**over) -> TxInput:
    base = dict(
        id=1, external_id="SP-1", marketplace_code="shopee",
        product_name="Kurma Ajwa", variant_name="1 kg", sku="AJW-1000",
        order_date=DATE, quantity=2, gross_sales=400_000,
        voucher_seller=10_000, shipping_borne_by_seller=15_000,
        unit_cost=120_000, commission_bp=650, service_fee_bp=250,
    )
    base.update(over)
    return TxInput(**base)


# --- hitungan acuan ----------------------------------------------------------


def test_laba_cocok_dengan_hitungan_acuan():
    # penjualan bersih = 400.000 - 0            = 400.000
    # komisi           = 400.000 x 9%           =  36.000
    # voucher                                    =  10.000
    # ongkir                                     =  15.000
    # modal            = 120.000 x 2            = 240.000
    # laba             = 400.000-36.000-10.000-15.000-240.000 = 99.000
    r = compute_transaction(tx())
    assert r.complete is True
    assert r.net_sales == 400_000
    assert r.commission == 36_000
    assert r.cogs == 240_000
    assert r.profit == 99_000
    assert r.margin_pct == pytest.approx(24.75)


def test_komponen_biaya_dirinci_untuk_penelusuran():
    r = compute_transaction(tx())
    # laba harus sama dengan penjualan bersih dikurangi seluruh komponen
    assert r.profit == r.net_sales - r.commission - r.voucher - r.shipping - r.cogs


def test_tanpa_biaya_tambahan_laba_hanya_penjualan_dikurangi_modal():
    r = compute_transaction(tx(commission_bp=0, service_fee_bp=0,
                               voucher_seller=0, shipping_borne_by_seller=0))
    assert r.profit == 400_000 - 240_000


# --- retur: tidak boleh terhitung ganda --------------------------------------


def test_retur_sebagian_mengurangi_penjualan_dan_modal_sekali():
    # 1 dari 2 unit diretur senilai 200.000
    # penjualan bersih = 400.000 - 200.000      = 200.000
    # komisi           = 200.000 x 9%           =  18.000
    # modal            = 120.000 x (2-1)        = 120.000
    # laba             = 200.000-18.000-10.000-15.000-120.000 = 37.000
    r = compute_transaction(tx(returned_quantity=1, returned_amount=200_000))
    assert r.net_sales == 200_000
    assert r.commission == 18_000
    assert r.cogs == 120_000
    assert r.profit == 37_000


def test_retur_penuh_tidak_membebankan_modal_dua_kali():
    """Kalau semua barang kembali, kerugian hanya sebesar voucher dan ongkir.
    Bug hitung ganda akan memunculkan angka jauh lebih negatif."""
    r = compute_transaction(tx(returned_quantity=2, returned_amount=400_000))
    assert r.net_sales == 0
    assert r.commission == 0          # komisi ikut dikembalikan marketplace
    assert r.cogs == 0                # barang kembali ke stok
    assert r.profit == -(10_000 + 15_000)


def test_retur_melebihi_penjualan_ditolak():
    with pytest.raises(ValueError):
        compute_transaction(tx(returned_quantity=3))
    with pytest.raises(ValueError):
        compute_transaction(tx(returned_amount=500_000))


# --- data kosong bukan nol ---------------------------------------------------


def test_modal_belum_dicatat_tidak_dianggap_nol():
    r = compute_transaction(tx(unit_cost=None))
    assert r.complete is False
    assert r.profit is None
    assert r.margin_pct is None
    assert profit.REASON_NO_COST in r.missing


def test_tarif_marketplace_belum_dicatat_tidak_dianggap_nol():
    r = compute_transaction(tx(commission_bp=None))
    assert r.complete is False
    assert r.profit is None
    assert profit.REASON_NO_FEE in r.missing


def test_voucher_dan_ongkir_kosong_ditandai_terpisah():
    r = compute_transaction(tx(voucher_seller=None, shipping_borne_by_seller=None))
    assert r.complete is False
    assert {profit.REASON_NO_VOUCHER, profit.REASON_NO_SHIPPING} <= set(r.missing)


def test_nol_eksplisit_berbeda_dari_belum_dicatat():
    nol = compute_transaction(tx(voucher_seller=0))
    kosong = compute_transaction(tx(voucher_seller=None))
    assert nol.complete is True and nol.voucher == 0
    assert kosong.complete is False and kosong.voucher is None


# --- agregasi ----------------------------------------------------------------


def test_transaksi_belum_lengkap_dikeluarkan_dari_total_laba():
    rows = [
        tx(id=1, external_id="A", sku="AJW-1000"),
        tx(id=2, external_id="B", sku="AJW-1000", unit_cost=None),
    ]
    rep = build_report(rows)
    bucket = rep.by_product[0]
    assert bucket.transactions == 2
    assert bucket.complete_transactions == 1
    assert bucket.incomplete_transactions == 1
    assert bucket.profit == 99_000          # hanya dari transaksi A
    assert bucket.complete is False
    assert profit.REASON_NO_COST in bucket.missing_reasons


def test_margin_memakai_penjualan_dari_transaksi_lengkap_saja():
    """Kalau margin dibagi dengan penjualan seluruh transaksi (termasuk yang
    datanya bolong), persentasenya akan terlihat lebih kecil dari kenyataan."""
    rows = [tx(id=1, external_id="A"), tx(id=2, external_id="B", unit_cost=None)]
    rep = build_report(rows)
    assert rep.by_product[0].margin_pct == pytest.approx(24.75)


def test_pengelompokan_per_produk_dan_marketplace():
    rows = [
        tx(id=1, external_id="A", marketplace_code="shopee", sku="AJW-1000"),
        tx(id=2, external_id="B", marketplace_code="lazada", sku="KCA-500",
           product_name="Kacang Arab", variant_name="500 g"),
        tx(id=3, external_id="C", marketplace_code="lazada", sku="AJW-1000"),
    ]
    rep = build_report(rows)
    assert {b.key for b in rep.by_product} == {"AJW-1000", "KCA-500"}
    assert {b.key for b in rep.by_marketplace} == {"shopee", "lazada"}
    assert next(b for b in rep.by_product if b.key == "AJW-1000").transactions == 2
    assert rep.overall.transactions == 3


def test_total_keseluruhan_sama_dengan_jumlah_per_marketplace():
    rows = [
        tx(id=1, external_id="A", marketplace_code="shopee"),
        tx(id=2, external_id="B", marketplace_code="tiktok"),
        tx(id=3, external_id="C", marketplace_code="lazada"),
    ]
    rep = build_report(rows)
    assert sum(b.profit for b in rep.by_marketplace) == rep.overall.profit
    assert sum(b.net_sales for b in rep.by_marketplace) == rep.overall.net_sales
    assert sum(b.cogs for b in rep.by_marketplace) == rep.overall.cogs


def test_produk_belum_lengkap_tidak_menempati_urutan_teratas():
    rows = [
        tx(id=1, external_id="A", sku="LENGKAP"),
        tx(id=2, external_id="B", sku="BOLONG", unit_cost=None),
    ]
    rep = build_report(rows)
    assert rep.by_product[0].key == "LENGKAP"
    assert rep.by_product[-1].key == "BOLONG"


def test_laporan_menandai_data_belum_lengkap():
    assert build_report([tx()]).data_complete is True
    assert build_report([tx(unit_cost=None)]).data_complete is False


def test_produk_rugi_terdeteksi():
    """Omzet besar belum tentu untung — inti Masalah 2 pada studi kasus."""
    r = compute_transaction(tx(gross_sales=250_000, unit_cost=120_000))
    # 250.000 - 22.500 - 10.000 - 15.000 - 240.000 = -37.500
    assert r.profit == -37_500
    assert r.margin_pct < 0
