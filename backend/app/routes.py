"""Endpoint internal Scentra. Tidak ada satu pun panggilan ke API marketplace."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from . import nlp, schemas, services
from .auth import create_token, current_user, get_user_by_email, require_roles, verify_password
from .db import get_session
from .models import (
    Classification, Conversation, ConversationEvent, Faq, Marketplace, Message,
    Product, ProductVariant, ShippingRule, StockRecord, SuggestedReply, User,
    utcnow,
)

router = APIRouter(prefix="/api")

ESCALATION_RULES = [
    ("Stok belum tercatat atau kedaluwarsa lebih dari 48 jam",
     "Jawaban aman tanpa klaim, status menjadi Waiting for Staff"),
    ("Aturan pengiriman marketplace kosong", "Jawaban aman dan minta verifikasi staf"),
    ("Komplain terdeteksi", "Prioritas tinggi, template generik tidak dipakai"),
    ("Permintaan retur atau refund", "Eskalasi ke supervisor, aturan belum ada di KB"),
    ("Pesan tidak dikenali (unknown)", "Pesan tetap disimpan, staf diminta memeriksa"),
    ("Pertanyaan pesanan tanpa referensi order", "Minta nomor pesanan kepada pelanggan"),
]


# --- autentikasi -------------------------------------------------------------


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, session: Session = Depends(get_session)):
    user = get_user_by_email(session, body.email.strip().lower())
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah.")
    return schemas.TokenOut(
        access_token=create_token(user),
        user=schemas.UserOut(id=user.id, name=user.name, email=user.email, role=user.role),
    )


@router.get("/auth/me", response_model=schemas.UserOut)
def me(user: User = Depends(current_user)):
    return schemas.UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(session: Session = Depends(get_session), _: User = Depends(current_user)):
    rows = session.exec(select(User).where(User.is_active == True)).all()  # noqa: E712
    return [schemas.UserOut(id=u.id, name=u.name, email=u.email, role=u.role) for u in rows]


# --- bentuk keluaran ---------------------------------------------------------


def _reply_payload(session: Session, message_id: int) -> Optional[dict]:
    reply = session.exec(
        select(SuggestedReply).where(SuggestedReply.message_id == message_id)
    ).first()
    if reply is None:
        return None
    return {
        "id": reply.id,
        "reply_text": reply.reply_text,
        "knowledge_sources": reply.knowledge_sources,
        "needs_verification": reply.needs_verification,
        "verification_reason": reply.verification_reason,
        "copied_at": reply.copied_at,
    }


def _classification_payload(session: Session, message_id: int) -> Optional[dict]:
    row = session.exec(
        select(Classification).where(Classification.message_id == message_id)
    ).first()
    if row is None:
        return None
    return {
        "intent": row.intent, "priority": row.priority,
        "all_intents": row.all_intents, "rule_version": row.rule_version,
        "corrected_by": row.corrected_by,
    }


def _conversation_summary(session: Session, c: Conversation, names: dict[int, str]) -> dict:
    last = session.exec(
        select(Message)
        .where(Message.conversation_id == c.id, Message.sender_type == "customer")
        .order_by(Message.captured_at.desc(), Message.id.desc())
    ).first()
    reply = _reply_payload(session, last.id) if last else None
    return {
        "id": c.id,
        "marketplace_code": c.marketplace_code,
        "customer_name": c.customer_name,
        "external_reference": c.external_reference,
        "status": c.status,
        "priority": c.priority,
        "intent": c.intent,
        "assigned_user_id": c.assigned_user_id,
        "assigned_user_name": names.get(c.assigned_user_id),
        "updated_at": c.updated_at,
        "created_at": c.created_at,
        "last_message": last.message_text if last else "",
        "needs_verification": bool(reply and reply["needs_verification"]),
    }


def _user_names(session: Session) -> dict[int, str]:
    return {u.id: u.name for u in session.exec(select(User)).all()}


# --- percakapan --------------------------------------------------------------


@router.get("/conversations")
def list_conversations(
    marketplace: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    intent: Optional[str] = None,
    assigned_user_id: Optional[int] = None,
    needs_verification: Optional[bool] = None,
    q: Optional[str] = Query(default=None, max_length=120),
    session: Session = Depends(get_session),
    _: User = Depends(current_user),
):
    stmt = select(Conversation)
    if marketplace:
        stmt = stmt.where(Conversation.marketplace_code == marketplace)
    if status:
        stmt = stmt.where(Conversation.status == status)
    if priority:
        stmt = stmt.where(Conversation.priority == priority)
    if intent:
        stmt = stmt.where(Conversation.intent == intent)
    if assigned_user_id:
        stmt = stmt.where(Conversation.assigned_user_id == assigned_user_id)
    rows = session.exec(stmt.order_by(Conversation.updated_at.desc())).all()

    names = _user_names(session)
    items = [_conversation_summary(session, c, names) for c in rows]

    if needs_verification:
        items = [i for i in items if i["needs_verification"]]
    if q:
        needle = q.lower()
        matching_ids = {
            m.conversation_id for m in session.exec(select(Message)).all()
            if needle in m.message_text.lower()
        }
        items = [
            i for i in items
            if needle in i["customer_name"].lower()
            or needle in (i["external_reference"] or "").lower()
            or i["id"] in matching_ids
        ]
    return items


@router.get("/conversations/duplicate")
def check_duplicate(
    marketplace_code: str,
    external_reference: str,
    session: Session = Depends(get_session),
    _: User = Depends(current_user),
):
    """Dipanggil form sebelum menyimpan, supaya CS diberi tahu lebih dulu (AC-02)."""
    existing = services.find_duplicate(session, marketplace_code, external_reference)
    if existing is None:
        return {"found": False}
    return {
        "found": True,
        "conversation_id": existing.id,
        "customer_name": existing.customer_name,
        "status": existing.status,
    }


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(current_user),
):
    c = session.get(Conversation, conversation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    names = _user_names(session)
    messages = session.exec(
        select(Message).where(Message.conversation_id == c.id)
        .order_by(Message.captured_at, Message.id)
    ).all()
    events = session.exec(
        select(ConversationEvent).where(ConversationEvent.conversation_id == c.id)
        .order_by(ConversationEvent.created_at.desc(), ConversationEvent.id.desc())
    ).all()
    return {
        **_conversation_summary(session, c, names),
        "product_hint": c.product_hint,
        "messages": [
            {
                "id": m.id, "sender_type": m.sender_type, "message_text": m.message_text,
                "captured_at": m.captured_at,
                "marketplace_message_time": m.marketplace_message_time,
                "source": m.source,
                "author_name": names.get(m.author_user_id),
                "classification": _classification_payload(session, m.id)
                if m.sender_type == "customer" else None,
                "suggested_reply": _reply_payload(session, m.id)
                if m.sender_type == "customer" else None,
            }
            for m in messages
        ],
        "events": [
            {"id": e.id, "event_type": e.event_type, "detail": e.detail,
             "author_name": names.get(e.user_id), "created_at": e.created_at}
            for e in events
        ],
    }


@router.post("/conversations", status_code=201)
def create_conversation(
    body: schemas.ConversationIn,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Manual capture (FR-02). Sumber input selalu `manual`; waktu capture dicatat
    otomatis. Scentra tidak pernah mengambil pesan dari marketplace."""
    text = body.message_text.strip()
    if not text or not body.customer_name.strip():
        raise HTTPException(status_code=422, detail="Nama pelanggan dan isi pesan wajib diisi.")

    existing = services.find_duplicate(session, body.marketplace_code, body.external_reference)
    merged = False
    if existing is not None and body.merge_into_existing:
        conversation, merged = existing, True
    else:
        conversation = Conversation(
            marketplace_code=body.marketplace_code,
            customer_name=body.customer_name.strip(),
            external_reference=(body.external_reference or "").strip() or None,
            product_hint=(body.product_hint or "").strip() or None,
        )
        session.add(conversation)
        session.flush()
        services.log_event(session, conversation.id, user.id, "created",
                           f"Percakapan dibuat dari {body.marketplace_code}")

    services.record_customer_message(
        session, conversation, text, user_id=user.id,
        marketplace_message_time=body.marketplace_message_time,
    )
    if merged:
        services.log_event(session, conversation.id, user.id, "message",
                           "Pesan baru ditambahkan ke percakapan yang sudah ada")
    session.commit()
    session.refresh(conversation)
    return {"merged_into_existing": merged,
            **_conversation_summary(session, conversation, _user_names(session))}


@router.post("/conversations/{conversation_id}/messages", status_code=201)
def add_message(
    conversation_id: int,
    body: schemas.MessageIn,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    c = session.get(Conversation, conversation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    services.record_customer_message(
        session, c, body.message_text.strip(), user_id=user.id,
        marketplace_message_time=body.marketplace_message_time,
    )
    services.log_event(session, c.id, user.id, "message", "Pesan pelanggan ditambahkan")
    session.commit()
    return {"ok": True}


@router.patch("/conversations/{conversation_id}")
def patch_conversation(
    conversation_id: int,
    body: schemas.ConversationPatch,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    try:
        body = body.validated()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    c = session.get(Conversation, conversation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")

    if body.assigned_user_id is not None and user.role not in ("supervisor",):
        raise HTTPException(status_code=403,
                            detail="Hanya supervisor yang dapat menugaskan percakapan.")

    if body.status is not None and body.status != c.status:
        services.log_event(session, c.id, user.id, "status",
                           f"Status {c.status} → {body.status}", c.status, body.status)
        c.status = body.status
    if body.priority is not None and body.priority != c.priority:
        services.log_event(session, c.id, user.id, "priority",
                           f"Prioritas {c.priority} → {body.priority}", c.priority, body.priority)
        c.priority = body.priority
    if body.assigned_user_id is not None and body.assigned_user_id != c.assigned_user_id:
        target = session.get(User, body.assigned_user_id) if body.assigned_user_id else None
        services.log_event(session, c.id, user.id, "assign",
                           f"Ditugaskan ke {target.name}" if target else "Penugasan dilepas")
        c.assigned_user_id = body.assigned_user_id or None
        if c.assigned_user_id and c.status == "New":
            c.status = "Assigned"

    c.updated_at = utcnow()
    session.add(c)
    session.commit()
    return {"ok": True}


@router.patch("/messages/{message_id}/classification")
def correct_classification(
    message_id: int,
    body: schemas.ClassificationPatch,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Koreksi CS disimpan untuk evaluasi akurasi (FR-06)."""
    try:
        body = body.validated()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    row = session.exec(
        select(Classification).where(Classification.message_id == message_id)
    ).first()
    message = session.get(Message, message_id)
    if row is None or message is None:
        raise HTTPException(status_code=404, detail="Klasifikasi tidak ditemukan.")

    conversation = session.get(Conversation, message.conversation_id)
    services.log_event(session, conversation.id, user.id, "classification",
                       f"Intent dikoreksi {row.intent} → {body.intent}", row.intent, body.intent)
    row.intent = body.intent
    row.corrected_by = user.id
    conversation.intent = body.intent

    # Susun ulang rekomendasi memakai intent hasil koreksi.
    kb = services.load_knowledge_base(session)
    cls = nlp.Classified(intent=body.intent, priority=row.priority,
                         all_intents=row.all_intents, rule_version=row.rule_version)
    suggestion = nlp.suggest(
        kb, message.message_text, cls,
        customer_name=conversation.customer_name,
        marketplace_code=conversation.marketplace_code,
        external_reference=conversation.external_reference,
    )
    reply = session.exec(
        select(SuggestedReply).where(SuggestedReply.message_id == message_id)
    ).first()
    if reply is not None:
        reply.reply_text = suggestion.text
        reply.knowledge_sources = suggestion.sources
        reply.needs_verification = suggestion.needs_verification
        reply.verification_reason = suggestion.reason or None
        reply.copied_at = None
        session.add(reply)

    session.add_all([row, conversation])
    session.commit()
    return {"ok": True}


@router.patch("/replies/{reply_id}")
def edit_reply(
    reply_id: int,
    body: schemas.ReplyEditIn,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """CS boleh menyunting rekomendasi sebelum menyalin (FR-08)."""
    reply = session.get(SuggestedReply, reply_id)
    if reply is None:
        raise HTTPException(status_code=404, detail="Rekomendasi tidak ditemukan.")
    reply.reply_text = body.reply_text
    session.add(reply)
    session.commit()
    return {"ok": True}


@router.post("/replies/{reply_id}/copy")
def mark_copied(
    reply_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Mencatat bahwa teks disalin. Status percakapan sengaja TIDAK diubah:
    disalin bukan berarti terkirim (aturan bisnis no. 8 dan 9, AC-07)."""
    reply = session.get(SuggestedReply, reply_id)
    if reply is None:
        raise HTTPException(status_code=404, detail="Rekomendasi tidak ditemukan.")
    message = session.get(Message, reply.message_id)
    reply.copied_at = utcnow()
    session.add(reply)
    services.log_event(session, message.conversation_id, user.id, "copy",
                       "Suggested reply disalin CS (belum tentu terkirim)")
    session.commit()
    return {"copied_at": reply.copied_at}


@router.post("/conversations/{conversation_id}/notes", status_code=201)
def add_note(
    conversation_id: int,
    body: schemas.NoteIn,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Catatan internal disimpan sebagai pesan bertipe terpisah supaya tidak
    pernah tercampur dengan pesan pelanggan (FR-11)."""
    c = session.get(Conversation, conversation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    session.add(Message(conversation_id=c.id, sender_type="internal_note",
                        message_text=body.note_text.strip(), source="manual",
                        author_user_id=user.id))
    services.log_event(session, c.id, user.id, "note", "Catatan internal ditambahkan")
    session.commit()
    return {"ok": True}


@router.post("/conversations/{conversation_id}/actions", status_code=201)
def add_action(
    conversation_id: int,
    body: schemas.ActionIn,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    """Catatan tindakan CS, misalnya 'balasan dikirim lewat Seller Center'.
    Scentra tidak punya konfirmasi dari marketplace, jadi ini murni catatan
    internal (AC-08)."""
    c = session.get(Conversation, conversation_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan.")
    session.add(Message(conversation_id=c.id, sender_type="cs_action",
                        message_text=body.action_text.strip(), source="manual",
                        author_user_id=user.id))
    services.log_event(session, c.id, user.id, "action", body.action_text.strip())
    if c.status in ("New", "Waiting for Staff"):
        c.status = "Waiting for Customer"
        session.add(c)
    session.commit()
    return {"ok": True}


# --- knowledge base ----------------------------------------------------------


@router.get("/knowledge")
def knowledge(session: Session = Depends(get_session), _: User = Depends(current_user)):
    stock = {s.variant_id: s for s in session.exec(select(StockRecord)).all()}
    variants: dict[int, list[dict]] = {}
    for v in session.exec(select(ProductVariant)).all():
        s = stock.get(v.id)
        variants.setdefault(v.product_id, []).append({
            "id": v.id, "variant_name": v.variant_name, "sku": v.sku,
            "quantity": s.quantity if s else None,
            "stock_updated_at": s.updated_at if s else None,
            "is_stale": nlp.is_stale(
                nlp.VariantInfo(v.variant_name, v.sku,
                                s.quantity if s else None, s.updated_at if s else None)),
        })
    return {
        "faqs": [
            {"id": f.id, "question": f.question, "answer": f.answer,
             "keywords": f.keywords, "updated_at": f.updated_at}
            for f in session.exec(select(Faq).where(Faq.is_active == True)).all()  # noqa: E712
        ],
        "products": [
            {"id": p.id, "name": p.name, "aliases": p.aliases,
             "variants": variants.get(p.id, [])}
            for p in session.exec(select(Product).where(Product.is_active == True)).all()  # noqa: E712
        ],
        "shipping_rules": [
            {"marketplace_code": r.marketplace_code, "rule_text": r.rule_text,
             "cutoff_time": r.cutoff_time.strftime("%H:%M") if r.cutoff_time else None,
             "updated_at": r.updated_at}
            for r in session.exec(select(ShippingRule)).all()
        ],
        "escalation_rules": [{"condition": c, "action": a} for c, a in ESCALATION_RULES],
        "marketplaces": [
            {"code": m.code, "name": m.name} for m in session.exec(select(Marketplace)).all()
        ],
    }


# --- dashboard ---------------------------------------------------------------


@router.get("/dashboard")
def dashboard(session: Session = Depends(get_session), _: User = Depends(current_user)):
    names = _user_names(session)
    rows = session.exec(select(Conversation)).all()
    items = [_conversation_summary(session, c, names) for c in rows]
    done = ("Resolved", "Closed")
    hot = [i for i in items if i["priority"] == "high" and i["status"] not in done]
    return {
        "totals": {
            "conversations": len(items),
            "new": sum(1 for i in items if i["status"] == "New"),
            "waiting_staff": sum(1 for i in items if i["status"] == "Waiting for Staff"),
            "high_priority": sum(1 for i in items if i["priority"] == "high"),
            "resolved": sum(1 for i in items if i["status"] in done),
        },
        "by_marketplace": Counter(i["marketplace_code"] for i in items),
        "by_intent": Counter(i["intent"] for i in items),
        "by_status": Counter(i["status"] for i in items),
        "high_priority_queue": sorted(hot, key=lambda i: i["updated_at"], reverse=True)[:8],
        "disclaimer": ("Metrik dihitung dari pesan yang dicatat ke Scentra oleh CS, "
                       "bukan dari seluruh percakapan di Shopee, TikTok Shop, dan Lazada."),
    }
