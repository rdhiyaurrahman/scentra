"""Endpoint Masalah 2: profitabilitas produk.

Hanya untuk supervisor dan pemilik. CS tidak perlu melihat margin
(matriks hak akses PRD bab 4.4).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from . import profit
from .auth import require_roles
from .db import get_session
from .models import (
    MarketplaceFee, Product, ProductCost, ProductVariant, Transaction, User, utcnow,
)

router = APIRouter(prefix="/api/profit")

analyst = require_roles("supervisor", "owner")

MAX_IMPORT_ROWS = 5_000           # batasi agar satu unggahan tidak menghabiskan memori
MAX_IMPORT_BYTES = 2 * 1024 * 1024

CSV_COLUMNS = [
    "external_id", "marketplace_code", "sku", "order_date", "quantity",
    "gross_sales", "voucher_seller", "shipping_borne_by_seller",
    "returned_quantity", "returned_amount",
]


class TransactionIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=64)
    marketplace_code: str
    sku: str
    order_date: datetime
    quantity: int = Field(gt=0)
    gross_sales: int = Field(ge=0)
    voucher_seller: Optional[int] = Field(default=None, ge=0)
    shipping_borne_by_seller: Optional[int] = Field(default=None, ge=0)
    returned_quantity: int = Field(default=0, ge=0)
    returned_amount: int = Field(default=0, ge=0)


# --- memuat data -------------------------------------------------------------


def _load_rows(
    session: Session,
    start: Optional[datetime],
    end: Optional[datetime],
    marketplace: Optional[str],
) -> list[profit.TxInput]:
    stmt = select(Transaction)
    if start:
        stmt = stmt.where(Transaction.order_date >= start)
    if end:
        stmt = stmt.where(Transaction.order_date <= end)
    if marketplace:
        stmt = stmt.where(Transaction.marketplace_code == marketplace)
    transactions = session.exec(stmt.order_by(Transaction.order_date)).all()

    variants = {v.id: v for v in session.exec(select(ProductVariant)).all()}
    products = {p.id: p for p in session.exec(select(Product)).all()}
    costs = {c.variant_id: c for c in session.exec(select(ProductCost)).all()}
    fees = {f.marketplace_code: f for f in session.exec(select(MarketplaceFee)).all()}

    rows: list[profit.TxInput] = []
    for t in transactions:
        variant = variants.get(t.variant_id)
        if variant is None:
            continue
        product = products.get(variant.product_id)
        cost = costs.get(t.variant_id)
        fee = fees.get(t.marketplace_code)
        rows.append(profit.TxInput(
            id=t.id, external_id=t.external_id, marketplace_code=t.marketplace_code,
            product_name=product.name if product else "(produk terhapus)",
            variant_name=variant.variant_name, sku=variant.sku,
            order_date=t.order_date, quantity=t.quantity, gross_sales=t.gross_sales,
            returned_quantity=t.returned_quantity, returned_amount=t.returned_amount,
            voucher_seller=t.voucher_seller,
            shipping_borne_by_seller=t.shipping_borne_by_seller,
            unit_cost=cost.unit_cost if cost else None,
            commission_bp=fee.commission_bp if fee else None,
            service_fee_bp=fee.service_fee_bp if fee else None,
        ))
    return rows


def _bucket_payload(b: profit.Bucket) -> dict:
    return {
        "key": b.key, "label": b.label,
        "transactions": b.transactions,
        "complete_transactions": b.complete_transactions,
        "incomplete_transactions": b.incomplete_transactions,
        "complete": b.complete,
        "units_sold": b.units_sold, "units_returned": b.units_returned,
        "gross_sales": b.gross_sales, "returned_amount": b.returned_amount,
        "net_sales": b.net_sales, "net_sales_complete": b.net_sales_complete,
        "commission": b.commission, "voucher": b.voucher, "shipping": b.shipping,
        "cogs": b.cogs, "profit": b.profit, "margin_pct": b.margin_pct,
        "missing_reasons": sorted(b.missing_reasons),
    }


# --- laporan -----------------------------------------------------------------


@router.get("/report")
def report(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    marketplace: Optional[str] = None,
    session: Session = Depends(get_session),
    _: User = Depends(analyst),
):
    rows = _load_rows(session, start, end, marketplace)
    try:
        rep = profit.build_report(rows, period_start=start, period_end=end)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return {
        "period": {"start": start, "end": end, "marketplace": marketplace},
        "overall": _bucket_payload(rep.overall),
        "by_product": [_bucket_payload(b) for b in rep.by_product],
        "by_marketplace": [_bucket_payload(b) for b in rep.by_marketplace],
        "data_complete": rep.data_complete,
        "note": (
            "Transaksi yang modal produk atau tarif potongannya belum dicatat tidak "
            "dihitung labanya dan tidak dianggap nol. Angka laba hanya berasal dari "
            "transaksi dengan data lengkap."
        ),
    }


@router.get("/transactions")
def list_transactions(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    marketplace: Optional[str] = None,
    sku: Optional[str] = None,
    only_incomplete: bool = False,
    limit: int = Query(default=200, le=1000),
    session: Session = Depends(get_session),
    _: User = Depends(analyst),
):
    """Rincian per transaksi — dasar penelusuran angka pada laporan."""
    rows = _load_rows(session, start, end, marketplace)
    if sku:
        rows = [r for r in rows if r.sku == sku]

    out = []
    for r in rows:
        try:
            res = profit.compute_transaction(r)
        except ValueError as exc:
            out.append({
                "id": r.id, "external_id": r.external_id,
                "marketplace_code": r.marketplace_code, "sku": r.sku,
                "error": str(exc), "complete": False, "missing": ["data tidak konsisten"],
            })
            continue
        if only_incomplete and res.complete:
            continue
        out.append({
            "id": r.id, "external_id": r.external_id,
            "marketplace_code": r.marketplace_code,
            "product_label": f"{r.product_name} {r.variant_name}", "sku": r.sku,
            "order_date": r.order_date, "quantity": r.quantity,
            "returned_quantity": r.returned_quantity,
            "gross_sales": r.gross_sales, "returned_amount": r.returned_amount,
            "net_sales": res.net_sales, "commission": res.commission,
            "voucher": res.voucher, "shipping": res.shipping, "cogs": res.cogs,
            "profit": res.profit, "margin_pct": res.margin_pct,
            "complete": res.complete, "missing": res.missing,
        })
    return out[:limit]


@router.get("/cost-settings")
def cost_settings(
    session: Session = Depends(get_session), _: User = Depends(analyst),
):
    """Modal per varian dan tarif potongan per marketplace, termasuk yang kosong."""
    costs = {c.variant_id: c for c in session.exec(select(ProductCost)).all()}
    products = {p.id: p for p in session.exec(select(Product)).all()}
    variants = session.exec(select(ProductVariant)).all()
    fees = {f.marketplace_code: f for f in session.exec(select(MarketplaceFee)).all()}

    return {
        "product_costs": [
            {
                "variant_id": v.id, "sku": v.sku,
                "product_name": products[v.product_id].name if v.product_id in products else "",
                "variant_name": v.variant_name,
                "unit_cost": costs[v.id].unit_cost if v.id in costs else None,
                "updated_at": costs[v.id].updated_at if v.id in costs else None,
            }
            for v in variants
        ],
        "marketplace_fees": [
            {
                "marketplace_code": code,
                "commission_bp": fees[code].commission_bp if code in fees else None,
                "service_fee_bp": fees[code].service_fee_bp if code in fees else None,
                "updated_at": fees[code].updated_at if code in fees else None,
            }
            for code in ("shopee", "tiktok", "lazada")
        ],
    }


# --- memasukkan data ---------------------------------------------------------


def _save_transaction(session: Session, body: TransactionIn, user_id: int,
                      source: str) -> Transaction:
    variant = session.exec(
        select(ProductVariant).where(ProductVariant.sku == body.sku)
    ).first()
    if variant is None:
        raise ValueError(f"SKU {body.sku} tidak ada di katalog.")
    if body.returned_quantity > body.quantity:
        raise ValueError(f"{body.external_id}: jumlah retur melebihi jumlah terjual.")
    if body.returned_amount > body.gross_sales:
        raise ValueError(f"{body.external_id}: nilai retur melebihi penjualan.")

    existing = session.exec(
        select(Transaction).where(
            Transaction.marketplace_code == body.marketplace_code,
            Transaction.external_id == body.external_id,
        )
    ).first()
    if existing is not None:
        # Mencegah satu pesanan terhitung dua kali saat berkas diunggah ulang.
        raise ValueError(
            f"Transaksi {body.external_id} pada {body.marketplace_code} sudah tercatat."
        )

    row = Transaction(
        external_id=body.external_id, marketplace_code=body.marketplace_code,
        variant_id=variant.id, order_date=body.order_date, quantity=body.quantity,
        gross_sales=body.gross_sales, voucher_seller=body.voucher_seller,
        shipping_borne_by_seller=body.shipping_borne_by_seller,
        returned_quantity=body.returned_quantity, returned_amount=body.returned_amount,
        source=source, created_by=user_id, created_at=utcnow(),
    )
    session.add(row)
    return row


@router.post("/transactions", status_code=201)
def create_transaction(
    body: TransactionIn,
    session: Session = Depends(get_session),
    user: User = Depends(analyst),
):
    try:
        row = _save_transaction(session, body, user.id, "manual")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    session.commit()
    return {"id": row.id, "external_id": row.external_id}


@router.post("/transactions/import")
async def import_transactions(
    file: UploadFile,
    session: Session = Depends(get_session),
    user: User = Depends(analyst),
):
    """Impor transaksi dari berkas CSV yang diekspor manual dari Seller Center.

    Baris yang bermasalah dilaporkan satu per satu dan tidak menggagalkan
    seluruh berkas; baris yang sah tetap tersimpan.
    """
    raw = await file.read()
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="Berkas lebih besar dari 2 MB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Berkas harus berupa CSV UTF-8.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="Berkas CSV kosong.")
    missing_cols = [c for c in CSV_COLUMNS[:6] if c not in reader.fieldnames]
    if missing_cols:
        raise HTTPException(
            status_code=422,
            detail=f"Kolom wajib tidak ada: {', '.join(missing_cols)}.",
        )

    def num(value: Optional[str], *, allow_blank: bool) -> Optional[int]:
        """Sel kosong berarti belum diketahui, bukan nol."""
        v = (value or "").strip().replace(".", "").replace(",", "")
        if v == "":
            if allow_blank:
                return None
            raise ValueError("nilai wajib kosong")
        return int(v)

    saved, errors = 0, []
    for line, row in enumerate(reader, start=2):
        if line - 1 > MAX_IMPORT_ROWS:
            errors.append(f"baris {line}: melebihi batas {MAX_IMPORT_ROWS} baris")
            break
        try:
            body = TransactionIn(
                external_id=(row.get("external_id") or "").strip(),
                marketplace_code=(row.get("marketplace_code") or "").strip().lower(),
                sku=(row.get("sku") or "").strip(),
                order_date=datetime.fromisoformat((row.get("order_date") or "").strip()),
                quantity=num(row.get("quantity"), allow_blank=False),
                gross_sales=num(row.get("gross_sales"), allow_blank=False),
                voucher_seller=num(row.get("voucher_seller"), allow_blank=True),
                shipping_borne_by_seller=num(
                    row.get("shipping_borne_by_seller"), allow_blank=True),
                returned_quantity=num(row.get("returned_quantity"), allow_blank=True) or 0,
                returned_amount=num(row.get("returned_amount"), allow_blank=True) or 0,
            )
            _save_transaction(session, body, user.id, "import")
            session.flush()
            saved += 1
        except Exception as exc:  # noqa: BLE001 - satu baris gagal, sisanya lanjut
            session.rollback()
            errors.append(f"baris {line}: {exc}")

    session.commit()
    return {"saved": saved, "failed": len(errors), "errors": errors[:50]}


@router.get("/import-template")
def import_template(_: User = Depends(analyst)):
    """Contoh isi CSV. Sel kosong pada kolom biaya berarti belum diketahui."""
    return {
        "columns": CSV_COLUMNS,
        "example": (
            "external_id,marketplace_code,sku,order_date,quantity,gross_sales,"
            "voucher_seller,shipping_borne_by_seller,returned_quantity,returned_amount\n"
            "SP-90001,shopee,AJW-1000,2026-11-01,2,400000,10000,15000,0,0\n"
            "LZ-90002,lazada,KCA-500,2026-11-02,1,95000,,,0,0\n"
        ),
        "note": (
            "Kolom voucher_seller dan shipping_borne_by_seller boleh dikosongkan bila "
            "belum diketahui. Sel kosong dicatat sebagai belum lengkap, bukan nol."
        ),
    }
