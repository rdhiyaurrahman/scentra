"""Tabel basis data ResponIn — mengikuti PRD bab 11 (Model Data Konseptual)."""
from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

# --- nilai tetap -------------------------------------------------------------

ROLES = ("cs", "owner")
MARKETPLACES = ("shopee", "tiktok", "lazada")
STATUSES = (
    "New", "Open", "Assigned", "Waiting for Staff",
    "Waiting for Customer", "Resolved", "Closed",
)
PRIORITIES = ("high", "normal", "low")
INTENTS = (
    "stock_inquiry", "product_inquiry", "shipping_inquiry", "order_inquiry",
    "complaint", "return_refund", "other", "unknown",
)


def utcnow() -> datetime:
    """UTC naive — kolom datetime di database juga naive, jangan dicampur aware."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- tabel -------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="cs")
    is_active: bool = Field(default=True)


class Marketplace(SQLModel, table=True):
    __tablename__ = "marketplaces"
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: Optional[int] = Field(default=None, primary_key=True)
    marketplace_code: str = Field(index=True)
    customer_name: str
    # Boleh kosong. Nama pelanggan BUKAN kunci unik (aturan bisnis PRD no. 2).
    external_reference: Optional[str] = Field(default=None, index=True)
    product_hint: Optional[str] = None
    assigned_user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    status: str = Field(default="New", index=True)
    priority: str = Field(default="normal", index=True)
    intent: str = Field(default="unknown", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    sender_type: str = Field(default="customer")  # customer | internal_note | cs_action
    message_text: str
    marketplace_message_time: Optional[datetime] = None
    captured_at: datetime = Field(default_factory=utcnow)
    source: str = Field(default="manual")
    author_user_id: Optional[int] = Field(default=None, foreign_key="users.id")


class Classification(SQLModel, table=True):
    __tablename__ = "classifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="messages.id", index=True)
    intent: str
    priority: str
    all_intents: list = Field(default_factory=list, sa_column=Column(JSON))
    rule_version: str
    corrected_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow)


class SuggestedReply(SQLModel, table=True):
    __tablename__ = "suggested_replies"
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="messages.id", index=True)
    reply_text: str
    knowledge_sources: list = Field(default_factory=list, sa_column=Column(JSON))
    needs_verification: bool = Field(default=False)
    verification_reason: Optional[str] = None
    copied_at: Optional[datetime] = None  # disalin != terkirim (aturan bisnis no. 8)


class Faq(SQLModel, table=True):
    __tablename__ = "faqs"
    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    answer: str
    category: Optional[str] = None
    keywords: list = Field(default_factory=list, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    description: Optional[str] = None
    is_active: bool = Field(default=True)


class ProductVariant(SQLModel, table=True):
    __tablename__ = "product_variants"
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    variant_name: str
    sku: str = Field(unique=True)


class StockRecord(SQLModel, table=True):
    """Satu baris per varian. Varian TANPA baris = stok belum tercatat,
    yang menurut aturan bisnis PRD no. 6 tidak boleh dianggap nol."""
    __tablename__ = "stock_records"
    __table_args__ = (UniqueConstraint("variant_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    quantity: int
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")


class ShippingRule(SQLModel, table=True):
    __tablename__ = "shipping_rules"
    id: Optional[int] = Field(default=None, primary_key=True)
    marketplace_code: str = Field(index=True, unique=True)
    rule_text: Optional[str] = None
    cutoff_time: Optional[time] = None
    effective_from: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utcnow)


class ConversationEvent(SQLModel, table=True):
    __tablename__ = "conversation_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


# --- Masalah 2: profitabilitas produk ---------------------------------------
# Seluruh nilai uang disimpan sebagai bilangan bulat rupiah supaya tidak ada
# galat pembulatan float. Kolom yang boleh None berarti "belum diketahui",
# BUKAN nol (aturan studi kasus: data kosong tidak boleh dianggap nol).


class ProductCost(SQLModel, table=True):
    """Modal (HPP) per varian. Varian tanpa baris di sini = modal belum dicatat,
    sehingga marginnya tidak dihitung dan ditandai belum lengkap."""
    __tablename__ = "product_costs"
    __table_args__ = (UniqueConstraint("variant_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    unit_cost: int
    effective_from: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")


class MarketplaceFee(SQLModel, table=True):
    """Potongan marketplace dalam basis poin (1% = 100 bp) agar tetap bilangan bulat."""
    __tablename__ = "marketplace_fees"
    __table_args__ = (UniqueConstraint("marketplace_code"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    marketplace_code: str = Field(index=True)
    commission_bp: Optional[int] = None       # None = tarif belum dicatat
    service_fee_bp: Optional[int] = None
    effective_from: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: Optional[int] = Field(default=None, foreign_key="users.id")


class Transaction(SQLModel, table=True):
    """Satu baris penjualan yang dimasukkan manual atau lewat impor CSV."""
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("marketplace_code", "external_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: str = Field(index=True)       # nomor pesanan di marketplace
    marketplace_code: str = Field(index=True)
    variant_id: int = Field(foreign_key="product_variants.id", index=True)
    order_date: datetime = Field(index=True)
    quantity: int
    gross_sales: int                            # penjualan kotor, rupiah
    voucher_seller: Optional[int] = None        # diskon yang ditanggung penjual
    shipping_borne_by_seller: Optional[int] = None
    returned_quantity: int = Field(default=0)
    returned_amount: int = Field(default=0)
    source: str = Field(default="manual")       # manual | import
    created_at: datetime = Field(default_factory=utcnow)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
