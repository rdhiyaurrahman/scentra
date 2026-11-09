"""Jembatan antara tabel database dan fungsi murni di nlp.py."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from . import nlp
from .models import (
    Classification, Conversation, ConversationEvent, Faq, Message, Product,
    ProductVariant, ShippingRule, StockRecord, SuggestedReply,
    utcnow,
)


def load_knowledge_base(session: Session) -> nlp.KnowledgeBase:
    stock_by_variant = {s.variant_id: s for s in session.exec(select(StockRecord)).all()}
    variants_by_product: dict[int, list[nlp.VariantInfo]] = {}
    for v in session.exec(select(ProductVariant)).all():
        stock = stock_by_variant.get(v.id)
        variants_by_product.setdefault(v.product_id, []).append(
            nlp.VariantInfo(
                name=v.variant_name,
                sku=v.sku,
                quantity=stock.quantity if stock else None,
                stock_updated_at=stock.updated_at if stock else None,
            )
        )
    products = [
        nlp.ProductInfo(name=p.name, aliases=list(p.aliases),
                        variants=variants_by_product.get(p.id, []))
        for p in session.exec(select(Product).where(Product.is_active == True)).all()  # noqa: E712
    ]
    faqs = [
        nlp.FaqInfo(id=f.id, question=f.question, answer=f.answer, keywords=list(f.keywords))
        for f in session.exec(select(Faq).where(Faq.is_active == True)).all()  # noqa: E712
    ]
    shipping = {
        r.marketplace_code: nlp.ShippingInfo(
            marketplace_code=r.marketplace_code,
            rule_text=r.rule_text,
            cutoff_time=r.cutoff_time,
        )
        for r in session.exec(select(ShippingRule)).all()
    }
    return nlp.KnowledgeBase(products=products, faqs=faqs, shipping=shipping)


def log_event(session: Session, conversation_id: int, user_id: Optional[int],
              event_type: str, detail: str, old: str | None = None,
              new: str | None = None) -> None:
    """Audit log (FR-13). Dipanggil untuk setiap perubahan penting."""
    session.add(ConversationEvent(
        conversation_id=conversation_id, user_id=user_id, event_type=event_type,
        detail=detail, old_value=old, new_value=new,
    ))


def record_customer_message(
    session: Session,
    conversation: Conversation,
    text: str,
    *,
    user_id: Optional[int],
    marketplace_message_time: Optional[datetime] = None,
) -> tuple[Message, Classification, SuggestedReply]:
    """Simpan pesan, klasifikasikan, lalu susun suggested reply.

    Kegagalan klasifikasi tidak boleh membatalkan penyimpanan pesan (FR-02,
    NFR 9.4), jadi pesan di-flush lebih dulu dan tahap berikutnya dibungkus
    penanganan error yang jatuh ke label `unknown`.
    """
    message = Message(
        conversation_id=conversation.id, sender_type="customer", message_text=text,
        marketplace_message_time=marketplace_message_time, source="manual",
        author_user_id=user_id,
    )
    session.add(message)
    session.flush()

    try:
        cls = nlp.classify(text)
    except Exception:  # noqa: BLE001 - pesan tetap tersimpan apa pun yang terjadi
        cls = nlp.Classified(intent="unknown", priority="normal", all_intents=[])

    classification = Classification(
        message_id=message.id, intent=cls.intent, priority=cls.priority,
        all_intents=cls.all_intents, rule_version=cls.rule_version,
    )
    session.add(classification)

    try:
        kb = load_knowledge_base(session)
        suggestion = nlp.suggest(
            kb, text, cls,
            customer_name=conversation.customer_name,
            marketplace_code=conversation.marketplace_code,
            external_reference=conversation.external_reference,
        )
    except Exception:  # noqa: BLE001 - kegagalan penyusunan balasan harus terlihat jelas
        suggestion = nlp.Suggestion(
            text="", sources=[], needs_verification=True,
            reason="Suggested reply gagal dibuat. Jawab manual dan laporkan ke admin.")

    reply = SuggestedReply(
        message_id=message.id, reply_text=suggestion.text,
        knowledge_sources=suggestion.sources,
        needs_verification=suggestion.needs_verification,
        verification_reason=suggestion.reason or None,
    )
    session.add(reply)

    conversation.intent = cls.intent
    conversation.updated_at = utcnow()
    if cls.priority == "high":
        conversation.priority = "high"
    if conversation.status in ("Resolved", "Closed"):
        log_event(session, conversation.id, user_id, "status",
                  f"Status {conversation.status} → Open karena pesan baru masuk",
                  conversation.status, "Open")
        conversation.status = "Open"
    if suggestion.needs_verification and conversation.status in ("New", "Open", "Assigned"):
        conversation.status = "Waiting for Staff"
    session.add(conversation)
    return message, classification, reply


def find_duplicate(session: Session, marketplace_code: str,
                   reference: Optional[str]) -> Optional[Conversation]:
    """Referensi percakapan adalah pengenal utama (aturan bisnis PRD no. 3).
    Nama pelanggan sengaja TIDAK dipakai supaya dua orang bernama sama tidak
    pernah digabung (aturan bisnis no. 2, AC-02)."""
    if not reference or not reference.strip():
        return None
    return session.exec(
        select(Conversation).where(
            Conversation.marketplace_code == marketplace_code,
            Conversation.external_reference == reference.strip(),
        )
    ).first()
