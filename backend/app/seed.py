"""Isi database dengan data sintetis untuk demo dan pengujian.

Semua nama, nomor pesanan, dan angka stok dibuat sendiri. Tidak ada data
pelanggan nyata maupun kredensial toko (lihat Guidebook bab Perlindungan Data).

Jalankan:  python -m app.seed
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlmodel import Session, delete, select

from .auth import hash_password
from .db import engine, init_db
from .models import (
    Classification, Conversation, ConversationEvent, Faq, Marketplace, Message,
    Product, ProductVariant, ShippingRule, StockRecord, SuggestedReply, User,
    utcnow,
)
from .services import log_event, record_customer_message

NOW = utcnow()


def ago(hours: float) -> datetime:
    return NOW - timedelta(hours=hours)


def reset(session: Session) -> None:
    for model in (ConversationEvent, SuggestedReply, Classification, Message,
                  Conversation, StockRecord, ProductVariant, Product, Faq,
                  ShippingRule, Marketplace, User):
        session.exec(delete(model))
    session.commit()


def seed() -> None:
    init_db()
    with Session(engine) as session:
        reset(session)

        # --- pengguna (password demo, bukan kredensial nyata) ----------------
        users = [
            User(name="Ayu Lestari", email="ayu@scentra.test",
                 password_hash=hash_password("ayu12345"), role="cs"),
            User(name="Bima Saputra", email="bima@scentra.test",
                 password_hash=hash_password("bima12345"), role="cs"),
            User(name="Rina Wijaya", email="rina@scentra.test",
                 password_hash=hash_password("rina12345"), role="supervisor"),
            User(name="Husin", email="husin@scentra.test",
                 password_hash=hash_password("husin12345"), role="owner"),
        ]
        session.add_all(users)
        session.add_all([
            Marketplace(code="shopee", name="Shopee"),
            Marketplace(code="tiktok", name="TikTok Shop"),
            Marketplace(code="lazada", name="Lazada"),
        ])
        session.commit()
        ayu, bima, rina, _husin = users

        # --- katalog ---------------------------------------------------------
        catalog = [
            ("Kurma Ajwa", ["kurma ajwa", "ajwa"], [
                ("1 kg", "AJW-1000", 24, ago(3)),
                ("500 g", "AJW-500", 0, ago(5)),
                ("250 g", "AJW-250", None, None),      # stok belum tercatat → TC-02
            ]),
            ("Kacang Arab", ["kacang arab", "kacang"], [
                ("500 g", "KCA-500", 61, ago(90)),     # kedaluwarsa > 48 jam
                ("1 kg", "KCA-1000", 12, ago(8)),
            ]),
            ("Siwak Al-Falah", ["siwak"], [
                ("Batang 15 cm", "SWK-15", 140, ago(2)),
                ("Pasta 75 g", "SWK-P75", 33, ago(2)),
            ]),
            ("Cokelat Turki", ["cokelat turki", "coklat turki", "cokelat"], [
                ("Pistachio 100 g", "CKT-P100", 8, ago(6)),
                ("Hazelnut 100 g", "CKT-H100", 0, ago(6)),
            ]),
        ]
        for name, aliases, variants in catalog:
            product = Product(name=name, aliases=aliases)
            session.add(product)
            session.flush()
            for variant_name, sku, qty, updated in variants:
                variant = ProductVariant(product_id=product.id,
                                         variant_name=variant_name, sku=sku)
                session.add(variant)
                session.flush()
                if qty is not None:
                    session.add(StockRecord(variant_id=variant.id, quantity=qty,
                                            updated_at=updated, updated_by=rina.id))

        # --- FAQ -------------------------------------------------------------
        session.add_all([
            Faq(question="Apakah produk bersertifikat halal?",
                answer=("Semua produk kami bersertifikat halal dan dilengkapi label "
                        "resmi pada kemasan."),
                category="produk", keywords=["halal", "sertifikat", "sertifikasi"],
                updated_by=rina.id),
            Faq(question="Berapa lama masa simpan kurma?",
                answer=("Kurma aman disimpan 12 bulan pada suhu ruang dan terhindar "
                        "dari sinar matahari langsung. Tanggal kedaluwarsa tercetak "
                        "pada kemasan."),
                category="produk",
                keywords=["expired", "kadaluarsa", "kedaluwarsa", "masa simpan",
                          "tahan berapa lama"],
                updated_by=rina.id),
            Faq(question="Apakah bisa minta packing tambahan?",
                answer=("Bisa. Tambahkan catatan \"packing bubble\" saat checkout, "
                        "tanpa biaya tambahan."),
                category="pengiriman", keywords=["packing", "bubble", "kayu", "pengemasan"],
                updated_by=rina.id),
            Faq(question="Apakah bisa beli grosir?",
                answer=("Pembelian mulai 10 kg mendapat harga grosir. Silakan "
                        "tinggalkan nomor WhatsApp agar tim kami menghubungi."),
                category="pemesanan", keywords=["grosir", "reseller", "partai", "borongan"],
                updated_by=rina.id),
        ])

        # --- aturan pengiriman ----------------------------------------------
        # Lazada sengaja dikosongkan untuk mendemonstrasikan perilaku eskalasi.
        session.add_all([
            ShippingRule(marketplace_code="shopee", cutoff_time=time(15, 0),
                         rule_text=("Pesanan masuk sebelum 15.00 WIB dikirim hari yang "
                                    "sama. Setelah itu dikirim hari kerja berikutnya."),
                         effective_from=ago(240)),
            ShippingRule(marketplace_code="tiktok", cutoff_time=time(14, 0),
                         rule_text=("Pesanan masuk sebelum 14.00 WIB dikirim hari yang "
                                    "sama. Sabtu dikirim maksimal pukul 12.00 WIB."),
                         effective_from=ago(240)),
            ShippingRule(marketplace_code="lazada", cutoff_time=None, rule_text=None),
        ])
        session.commit()

        # --- percakapan ------------------------------------------------------
        script = [
            ("shopee", "Dewi Rahma", "SP-88211", "Kak, kurma Ajwa 1 kg ready?", 1.2),
            ("tiktok", "Fajar Nugroho", "TT-40192", "min kurma ajwa 250 g redy ga?", 2),
            ("lazada", "Siti Aminah", "LZ-77301", "Cokelat Turki ada ukuran apa saja ya kak?", 3),
            ("shopee", "Bagus Pratama", "SP-88240", "Kalau order sekarang bisa dikirim hari ini?", 4),
            ("tiktok", "Rina Marlina", "TT-40255",
             "Kak saya beli 1 kg kacang arab kok yang dikirim 500 g? kecewa banget", 5),
            ("lazada", "Hendra Gunawan", "LZ-77355", "Saya mau refund pesanan saya", 6),
            ("shopee", "Nabila Putri", "SP-88299", "Kak itu yang kemarin gimana ya jadinya?", 7),
            ("shopee", "Dewi Rahma", "SP-88412", "Siwak pasta 75 g masih ada stok?", 8),
            ("lazada", "Teguh Santoso", "LZ-77390", "Produknya halal tidak kak?", 9),
            ("tiktok", "Yuni Astuti", "TT-40301", "Kacang arab 500 g ready kak?", 10),
            ("shopee", "Agus Salim", "SP-88450", "Bisa minta packing bubble wrap?", 11),
            ("lazada", "Maya Sari", "LZ-77401",
             "Pesanan saya kok belum sampai juga sudah seminggu", 12),
        ]
        created: dict[str, Conversation] = {}
        for mp, customer, ref, text, hours in script:
            conversation = Conversation(
                marketplace_code=mp, customer_name=customer, external_reference=ref,
                created_at=ago(hours), updated_at=ago(hours),
            )
            session.add(conversation)
            session.flush()
            log_event(session, conversation.id, ayu.id, "created",
                      f"Percakapan dibuat dari {mp}")
            message, _, _ = record_customer_message(
                session, conversation, text, user_id=ayu.id)
            # record_customer_message memakai waktu sekarang; kembalikan ke waktu
            # skenario supaya antrean demo tidak tampak masuk serentak.
            message.captured_at = ago(hours)
            conversation.updated_at = ago(hours)
            created[ref] = conversation
        session.commit()

        # Kondisi lanjutan supaya dashboard dan filter terlihat hidup.
        c = created["SP-88211"]
        c.assigned_user_id, c.status = ayu.id, "Resolved"
        session.add(Message(conversation_id=c.id, sender_type="cs_action",
                            message_text="Balasan dikirim melalui Seller Center Shopee.",
                            captured_at=ago(1), author_user_id=ayu.id))

        c = created["TT-40255"]
        c.assigned_user_id = rina.id
        session.add(Message(
            conversation_id=c.id, sender_type="internal_note",
            message_text=("Sudah cek foto packing, memang salah ambil SKU. "
                          "Ajukan kirim ulang ke tim gudang."),
            captured_at=ago(4.5), author_user_id=rina.id))

        created["LZ-77390"].status = "Open"
        created["SP-88450"].assigned_user_id = bima.id
        session.commit()

        total = len(session.exec(select(Conversation)).all())
        print(f"Seed selesai: {len(users)} pengguna, {total} percakapan, "
              f"{len(catalog)} produk.")
        print("Login demo: ayu@scentra.test / ayu12345 (CS), "
              "rina@scentra.test / rina12345 (Supervisor)")


if __name__ == "__main__":
    seed()
