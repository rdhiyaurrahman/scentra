"""Masalah 2 — pengujian endpoint profitabilitas di atas SQLite sementara."""
import io
import os
import tempfile

import pytest

DB_FILE = os.path.join(tempfile.mkdtemp(), "test_profit.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    seed()
    with TestClient(app) as c:
        yield c


def auth(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def supervisor(client):
    return auth(client, "rina@scentra.test", "rina12345")


@pytest.fixture(scope="module")
def owner(client):
    return auth(client, "husin@scentra.test", "husin12345")


@pytest.fixture(scope="module")
def cs(client):
    return auth(client, "ayu@scentra.test", "ayu12345")


# --- hak akses ---------------------------------------------------------------


def test_cs_tidak_boleh_melihat_margin(client, cs):
    assert client.get("/api/profit/report", headers=cs).status_code == 403
    assert client.get("/api/profit/transactions", headers=cs).status_code == 403


def test_supervisor_dan_pemilik_boleh(client, supervisor, owner):
    assert client.get("/api/profit/report", headers=supervisor).status_code == 200
    assert client.get("/api/profit/report", headers=owner).status_code == 200


def test_tanpa_token_ditolak(client):
    assert client.get("/api/profit/report").status_code == 401


# --- laporan -----------------------------------------------------------------


def test_laporan_memisahkan_transaksi_lengkap_dan_belum(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor).json()
    o = body["overall"]
    assert o["transactions"] == 16
    assert o["incomplete_transactions"] > 0
    assert o["complete_transactions"] + o["incomplete_transactions"] == o["transactions"]
    assert body["data_complete"] is False
    assert o["missing_reasons"]


def test_total_per_marketplace_konsisten_dengan_keseluruhan(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor).json()
    assert sum(b["profit"] for b in body["by_marketplace"]) == body["overall"]["profit"]
    assert sum(b["net_sales"] for b in body["by_marketplace"]) == body["overall"]["net_sales"]
    assert sum(b["transactions"] for b in body["by_marketplace"]) == body["overall"]["transactions"]


def test_lazada_belum_lengkap_karena_tarif_kosong(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor).json()
    lazada = next(b for b in body["by_marketplace"] if b["key"] == "lazada")
    assert lazada["complete"] is False
    assert lazada["complete_transactions"] == 0
    assert lazada["profit"] == 0            # tidak ada yang bisa dihitung
    assert lazada["margin_pct"] is None     # BUKAN 0%
    assert any("potongan marketplace" in r for r in lazada["missing_reasons"])


def test_produk_tanpa_modal_tidak_dihitung_labanya(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor).json()
    cokelat = next(b for b in body["by_product"] if b["key"] == "CKT-P100")
    assert cokelat["transactions"] > 0
    assert cokelat["complete_transactions"] == 0
    assert cokelat["margin_pct"] is None
    assert any("modal produk" in r for r in cokelat["missing_reasons"])


def test_produk_dengan_data_lengkap_punya_margin(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor).json()
    ajwa = next(b for b in body["by_product"] if b["key"] == "AJW-1000")
    assert ajwa["complete_transactions"] > 0
    assert ajwa["margin_pct"] is not None


def test_filter_marketplace_dan_periode(client, supervisor):
    body = client.get("/api/profit/report", headers=supervisor,
                      params={"marketplace": "shopee"}).json()
    assert all(b["key"] == "shopee" for b in body["by_marketplace"])

    kosong = client.get("/api/profit/report", headers=supervisor,
                        params={"start": "2099-01-01T00:00:00"}).json()
    assert kosong["overall"]["transactions"] == 0


# --- penelusuran -------------------------------------------------------------


def test_rincian_transaksi_bisa_ditelusuri(client, supervisor):
    rows = client.get("/api/profit/transactions", headers=supervisor,
                      params={"sku": "AJW-1000"}).json()
    assert rows
    for r in rows:
        if r["complete"]:
            assert (r["profit"] == r["net_sales"] - r["commission"] - r["voucher"]
                    - r["shipping"] - r["cogs"])


def test_jumlah_rincian_cocok_dengan_ringkasan_produk(client, supervisor):
    report = client.get("/api/profit/report", headers=supervisor).json()
    ajwa = next(b for b in report["by_product"] if b["key"] == "AJW-1000")
    rows = client.get("/api/profit/transactions", headers=supervisor,
                      params={"sku": "AJW-1000"}).json()
    assert sum(r["profit"] for r in rows if r["complete"]) == ajwa["profit"]
    assert len(rows) == ajwa["transactions"]


def test_saring_hanya_yang_belum_lengkap(client, supervisor):
    rows = client.get("/api/profit/transactions", headers=supervisor,
                      params={"only_incomplete": True}).json()
    assert rows and all(not r["complete"] for r in rows)
    assert all(r["missing"] for r in rows)


def test_retur_tercatat_pada_rincian(client, supervisor):
    rows = client.get("/api/profit/transactions", headers=supervisor).json()
    retur = next(r for r in rows if r["external_id"] == "SP-90003")
    assert retur["returned_quantity"] == 1
    assert retur["net_sales"] == retur["gross_sales"] - retur["returned_amount"]


def test_pengaturan_biaya_menampilkan_yang_kosong(client, supervisor):
    body = client.get("/api/profit/cost-settings", headers=supervisor).json()
    cokelat = [c for c in body["product_costs"] if c["sku"].startswith("CKT-")]
    assert cokelat and all(c["unit_cost"] is None for c in cokelat)
    lazada = next(f for f in body["marketplace_fees"] if f["marketplace_code"] == "lazada")
    assert lazada["commission_bp"] is None


# --- memasukkan data ---------------------------------------------------------


def test_tambah_transaksi_manual(client, supervisor):
    r = client.post("/api/profit/transactions", headers=supervisor, json={
        "external_id": "SP-95001", "marketplace_code": "shopee", "sku": "AJW-1000",
        "order_date": "2026-11-05T10:00:00", "quantity": 1, "gross_sales": 215_000,
        "voucher_seller": 0, "shipping_borne_by_seller": 10_000,
    })
    assert r.status_code == 201


def test_transaksi_ganda_ditolak(client, supervisor):
    """Mencegah satu pesanan terhitung dua kali saat berkas diunggah ulang."""
    r = client.post("/api/profit/transactions", headers=supervisor, json={
        "external_id": "SP-95001", "marketplace_code": "shopee", "sku": "AJW-1000",
        "order_date": "2026-11-05T10:00:00", "quantity": 1, "gross_sales": 215_000,
    })
    assert r.status_code == 409
    assert "sudah tercatat" in r.json()["detail"]


def test_sku_tidak_dikenal_ditolak(client, supervisor):
    r = client.post("/api/profit/transactions", headers=supervisor, json={
        "external_id": "SP-95002", "marketplace_code": "shopee", "sku": "TIDAK-ADA",
        "order_date": "2026-11-05T10:00:00", "quantity": 1, "gross_sales": 100_000,
    })
    assert r.status_code == 409


def test_retur_melebihi_penjualan_ditolak(client, supervisor):
    r = client.post("/api/profit/transactions", headers=supervisor, json={
        "external_id": "SP-95003", "marketplace_code": "shopee", "sku": "AJW-1000",
        "order_date": "2026-11-05T10:00:00", "quantity": 1, "gross_sales": 100_000,
        "returned_quantity": 5, "returned_amount": 0,
    })
    assert r.status_code == 409


def test_impor_csv_menyimpan_baris_sah_dan_melaporkan_yang_gagal(client, supervisor):
    csv_text = (
        "external_id,marketplace_code,sku,order_date,quantity,gross_sales,"
        "voucher_seller,shipping_borne_by_seller,returned_quantity,returned_amount\n"
        "SP-96001,shopee,AJW-1000,2026-11-06,1,215000,0,10000,0,0\n"
        "SP-96002,shopee,SKU-NGAWUR,2026-11-06,1,100000,0,0,0,0\n"
        "LZ-96003,lazada,KCA-500,2026-11-06,2,70000,,,0,0\n"
    )
    r = client.post(
        "/api/profit/transactions/import", headers=supervisor,
        files={"file": ("tx.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] == 2
    assert body["failed"] == 1
    assert "SKU-NGAWUR" in body["errors"][0]


def test_sel_kosong_pada_csv_dicatat_belum_diketahui_bukan_nol(client, supervisor):
    rows = client.get("/api/profit/transactions", headers=supervisor).json()
    imported = next(r for r in rows if r["external_id"] == "LZ-96003")
    assert imported["complete"] is False
    assert imported["voucher"] is None      # BUKAN 0
    assert imported["profit"] is None


def test_impor_tanpa_kolom_wajib_ditolak(client, supervisor):
    r = client.post(
        "/api/profit/transactions/import", headers=supervisor,
        files={"file": ("x.csv", io.BytesIO(b"external_id,sku\nA,B\n"), "text/csv")},
    )
    assert r.status_code == 422
