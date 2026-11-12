"""Pengujian API end-to-end di atas SQLite sementara, mencakup acceptance
criteria PRD bab 12 yang menyangkut alur (AC-01, AC-02, AC-07, AC-09, AC-10).
"""
import os
import tempfile

import pytest

DB_FILE = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture(scope="module")
def client():
    seed()
    with TestClient(app) as c:
        yield c


def login(client, email="ayu@scentra.test", password="ayu12345"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def cs(client):
    return login(client)


@pytest.fixture(scope="module")
def owner(client):
    return login(client, "husin@scentra.test", "husin12345")


# --- autentikasi -------------------------------------------------------------


def test_login_salah_ditolak(client):
    r = client.post("/api/auth/login",
                    json={"email": "ayu@scentra.test", "password": "salah"})
    assert r.status_code == 401


def test_endpoint_butuh_token(client):
    assert client.get("/api/conversations").status_code == 401


def test_health_menyatakan_tanpa_api_marketplace(client):
    assert client.get("/api/health").json()["marketplace_api_connected"] is False


# --- AC-01 manual capture ----------------------------------------------------


def test_ac01_simpan_pesan_baru(client, cs):
    r = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "shopee", "customer_name": "Pelanggan Uji",
        "external_reference": "SP-99001", "message_text": "Kak, kurma Ajwa 1 kg ready?",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["merged_into_existing"] is False
    assert body["intent"] == "stock_inquiry"
    assert client.get("/api/conversations", headers=cs).status_code == 200


def test_ac01_field_wajib_divalidasi(client, cs):
    r = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "shopee", "customer_name": "", "message_text": "halo",
    })
    assert r.status_code == 422


# --- AC-02 percakapan yang sudah ada -----------------------------------------


def test_ac02_referensi_sama_digabung(client, cs):
    r = client.get("/api/conversations/duplicate", headers=cs, params={
        "marketplace_code": "shopee", "external_reference": "SP-99001"})
    assert r.json()["found"] is True

    r = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "shopee", "customer_name": "Pelanggan Uji",
        "external_reference": "SP-99001", "message_text": "Halo kak, sudah dicek belum?",
    })
    assert r.json()["merged_into_existing"] is True


def test_ac02_nama_sama_referensi_beda_tetap_terpisah(client, cs):
    for ref in ("SP-99100", "SP-99101"):
        client.post("/api/conversations", headers=cs, json={
            "marketplace_code": "shopee", "customer_name": "Nama Kembar",
            "external_reference": ref, "message_text": "Siwak masih ada?",
        })
    rows = [c for c in client.get("/api/conversations", headers=cs).json()
            if c["customer_name"] == "Nama Kembar"]
    assert len({c["id"] for c in rows}) == 2


def test_pesan_tanpa_referensi_tidak_pernah_digabung(client, cs):
    made = []
    for _ in range(2):
        r = client.post("/api/conversations", headers=cs, json={
            "marketplace_code": "tiktok", "customer_name": "Tanpa Referensi",
            "message_text": "Halo kak",
        })
        made.append(r.json()["id"])
    assert made[0] != made[1]


# --- AC-03 klasifikasi -------------------------------------------------------


def test_ac03_pesan_tak_dikenali_tetap_tersimpan(client, cs):
    r = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "lazada", "customer_name": "Uji Unknown",
        "external_reference": "LZ-99200", "message_text": "zzz qqq ???",
    })
    assert r.status_code == 201
    assert r.json()["intent"] == "unknown"


def test_koreksi_intent_tercatat_dan_reply_disusun_ulang(client, cs):
    created = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "shopee", "customer_name": "Uji Koreksi",
        "external_reference": "SP-99300", "message_text": "halo kak mau tanya",
    }).json()
    detail = client.get(f"/api/conversations/{created['id']}", headers=cs).json()
    message = detail["messages"][0]
    assert message["classification"]["intent"] == "unknown"

    r = client.patch(f"/api/messages/{message['id']}/classification",
                     headers=cs, json={"intent": "product_inquiry"})
    assert r.status_code == 200

    detail = client.get(f"/api/conversations/{created['id']}", headers=cs).json()
    assert detail["messages"][0]["classification"]["intent"] == "product_inquiry"
    assert detail["messages"][0]["classification"]["corrected_by"] is not None
    assert any(e["event_type"] == "classification" for e in detail["events"])


# --- AC-07 salin tidak mengubah status ---------------------------------------


def test_ac07_salin_tidak_mengubah_status(client, cs):
    created = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "shopee", "customer_name": "Uji Salin",
        "external_reference": "SP-99400", "message_text": "Kak, kurma Ajwa 1 kg ready?",
    }).json()
    before = client.get(f"/api/conversations/{created['id']}", headers=cs).json()
    reply_id = before["messages"][0]["suggested_reply"]["id"]

    assert client.post(f"/api/replies/{reply_id}/copy", headers=cs).status_code == 200

    after = client.get(f"/api/conversations/{created['id']}", headers=cs).json()
    assert after["status"] == before["status"]
    assert after["status"] not in ("Resolved", "Closed")
    assert after["messages"][0]["suggested_reply"]["copied_at"] is not None


def test_catat_tindakan_tidak_mengklaim_terkirim_di_marketplace(client, cs):
    created = client.post("/api/conversations", headers=cs, json={
        "marketplace_code": "tiktok", "customer_name": "Uji Tindakan",
        "external_reference": "TT-99500", "message_text": "Kak, kurma Ajwa 1 kg ready?",
    }).json()
    client.post(f"/api/conversations/{created['id']}/actions", headers=cs,
                json={"action_text": "Balasan dikirim melalui Seller Center TikTok Shop."})
    detail = client.get(f"/api/conversations/{created['id']}", headers=cs).json()
    actions = [m for m in detail["messages"] if m["sender_type"] == "cs_action"]
    assert len(actions) == 1
    assert detail["status"] != "Resolved"


# --- AC-09 assignment dan status ---------------------------------------------


def test_ac09_pemilik_tidak_boleh_mengubah_percakapan(client, owner, cs):
    """Matriks PRD bab 4.3: pemilik membaca inbox, tidak menulis ke dalamnya."""
    cid = client.get("/api/conversations", headers=cs).json()[0]["id"]
    assert client.get(f"/api/conversations/{cid}", headers=owner).status_code == 200

    assert client.patch(f"/api/conversations/{cid}", headers=owner,
                        json={"status": "Open"}).status_code == 403
    assert client.post(f"/api/conversations/{cid}/notes", headers=owner,
                       json={"note_text": "coba"}).status_code == 403
    assert client.post("/api/conversations", headers=owner, json={
        "marketplace_code": "shopee", "customer_name": "Uji",
        "message_text": "Halo",
    }).status_code == 403


def test_ac09_cs_assign_tercatat_di_riwayat(client, cs):
    cid = client.get("/api/conversations", headers=cs).json()[0]["id"]
    users = client.get("/api/users", headers=cs).json()
    target = next(u for u in users if u["role"] == "cs")

    r = client.patch(f"/api/conversations/{cid}", headers=cs,
                     json={"assigned_user_id": target["id"], "status": "Assigned"})
    assert r.status_code == 200

    detail = client.get(f"/api/conversations/{cid}", headers=cs).json()
    assert detail["assigned_user_id"] == target["id"]
    assert {"assign", "status"} <= {e["event_type"] for e in detail["events"]}


def test_status_tidak_dikenal_ditolak(client, cs):
    cid = client.get("/api/conversations", headers=cs).json()[0]["id"]
    r = client.patch(f"/api/conversations/{cid}", headers=cs, json={"status": "Selesai"})
    assert r.status_code == 422


# --- AC-10 filter ------------------------------------------------------------


def test_ac10_filter_marketplace_dan_status(client, cs):
    rows = client.get("/api/conversations", headers=cs,
                      params={"marketplace": "lazada"}).json()
    assert rows and all(c["marketplace_code"] == "lazada" for c in rows)

    rows = client.get("/api/conversations", headers=cs,
                      params={"status": "Waiting for Staff"}).json()
    assert all(c["status"] == "Waiting for Staff" for c in rows)


def test_pencarian_isi_pesan(client, cs):
    rows = client.get("/api/conversations", headers=cs, params={"q": "siwak"}).json()
    assert rows


def test_filter_perlu_verifikasi(client, cs):
    rows = client.get("/api/conversations", headers=cs,
                      params={"needs_verification": True}).json()
    assert rows and all(c["needs_verification"] for c in rows)


# --- catatan internal, knowledge base, dashboard -----------------------------


def test_catatan_internal_terpisah_dari_pesan_pelanggan(client, cs):
    cid = client.get("/api/conversations", headers=cs).json()[0]["id"]
    client.post(f"/api/conversations/{cid}/notes", headers=cs,
                json={"note_text": "Sudah hubungi tim gudang."})
    detail = client.get(f"/api/conversations/{cid}", headers=cs).json()
    notes = [m for m in detail["messages"] if m["sender_type"] == "internal_note"]
    assert notes and notes[-1]["classification"] is None


def test_knowledge_base_menandai_stok_belum_tercatat(client, cs):
    kb = client.get("/api/knowledge", headers=cs).json()
    ajwa = next(p for p in kb["products"] if p["name"] == "Kurma Ajwa")
    v250 = next(v for v in ajwa["variants"] if v["variant_name"] == "250 g")
    assert v250["quantity"] is None and v250["is_stale"] is True

    lazada = next(r for r in kb["shipping_rules"] if r["marketplace_code"] == "lazada")
    assert lazada["rule_text"] is None


def test_dashboard_menyertakan_disclaimer(client, cs):
    body = client.get("/api/dashboard", headers=cs).json()
    assert body["totals"]["conversations"] > 0
    assert "dicatat ke ResponIn" in body["disclaimer"]


def test_url_database_penyedia_cloud_dapat_nama_driver():
    """Neon/Vercel memberi "postgres://"; SQLAlchemy menolaknya tanpa driver."""
    from app.db import normalize_db_url

    assert normalize_db_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalize_db_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalize_db_url("sqlite:///./x.db") == "sqlite:///./x.db"
