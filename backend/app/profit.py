"""Masalah 2 — perhitungan keuntungan per produk, marketplace, dan periode.

Fungsi murni tanpa database supaya setiap angka bisa diuji dan ditelusuri.

Dua aturan dari studi kasus yang menentukan seluruh rancangan modul ini:

1. **Data kosong bukan nol.** Kalau modal produk atau tarif komisi belum
   dicatat, laba transaksi itu TIDAK dihitung. Transaksinya tetap muncul,
   ditandai belum lengkap, dan dikeluarkan dari total laba. Menganggapnya nol
   akan membuat produk terlihat jauh lebih untung daripada kenyataannya.

2. **Perhitungan harus dapat ditelusuri.** Setiap transaksi mengembalikan
   rincian per komponen biaya, bukan satu angka jadi, sehingga penguji bisa
   mencocokkan dengan hitungan acuan dan memeriksa biaya yang hilang atau
   terhitung ganda.

Rumus per transaksi:

    penjualan bersih = gross_sales - returned_amount
    komisi           = penjualan bersih x (commission_bp + service_fee_bp) / 10000
    modal            = unit_cost x (quantity - returned_quantity)
    laba             = penjualan bersih - komisi - voucher - ongkir - modal

Catatan antihitung-ganda: nilai retur dikurangkan SEKALI dari penjualan.
Barang yang diretur kembali ke stok, jadi modalnya ikut berkurang dan tidak
dibebankan lagi. Komisi dihitung dari penjualan bersih, bukan kotor, karena
marketplace mengembalikan komisi atas pesanan yang diretur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# Alasan sebuah transaksi tidak bisa dihitung labanya.
REASON_NO_COST = "modal produk belum dicatat"
REASON_NO_FEE = "tarif potongan marketplace belum dicatat"
REASON_NO_VOUCHER = "nilai voucher penjual belum dicatat"
REASON_NO_SHIPPING = "ongkir yang ditanggung penjual belum dicatat"


@dataclass
class TxInput:
    """Satu transaksi beserta data pendukung yang berhasil ditemukan."""
    id: int
    external_id: str
    marketplace_code: str
    product_name: str
    variant_name: str
    sku: str
    order_date: datetime
    quantity: int
    gross_sales: int
    returned_quantity: int = 0
    returned_amount: int = 0
    voucher_seller: Optional[int] = None
    shipping_borne_by_seller: Optional[int] = None
    unit_cost: Optional[int] = None            # None = modal belum dicatat
    commission_bp: Optional[int] = None        # None = tarif belum dicatat
    service_fee_bp: Optional[int] = None


@dataclass
class TxResult:
    tx: TxInput
    net_sales: int
    commission: Optional[int]
    voucher: Optional[int]
    shipping: Optional[int]
    cogs: Optional[int]
    profit: Optional[int]                      # None kalau ada komponen tak diketahui
    complete: bool
    missing: list[str] = field(default_factory=list)

    @property
    def margin_pct(self) -> Optional[float]:
        if self.profit is None or self.net_sales == 0:
            return None
        return round(self.profit / self.net_sales * 100, 2)


def compute_transaction(tx: TxInput) -> TxResult:
    missing: list[str] = []

    if tx.returned_quantity > tx.quantity:
        raise ValueError(
            f"Transaksi {tx.external_id}: jumlah retur ({tx.returned_quantity}) "
            f"melebihi jumlah terjual ({tx.quantity})."
        )
    if tx.returned_amount > tx.gross_sales:
        raise ValueError(
            f"Transaksi {tx.external_id}: nilai retur melebihi penjualan kotor."
        )

    net_sales = tx.gross_sales - tx.returned_amount

    if tx.commission_bp is None:
        commission = None
        missing.append(REASON_NO_FEE)
    else:
        rate_bp = tx.commission_bp + (tx.service_fee_bp or 0)
        commission = net_sales * rate_bp // 10_000

    if tx.voucher_seller is None:
        voucher = None
        missing.append(REASON_NO_VOUCHER)
    else:
        voucher = tx.voucher_seller

    if tx.shipping_borne_by_seller is None:
        shipping = None
        missing.append(REASON_NO_SHIPPING)
    else:
        shipping = tx.shipping_borne_by_seller

    if tx.unit_cost is None:
        cogs = None
        missing.append(REASON_NO_COST)
    else:
        # Barang yang diretur kembali ke stok, modalnya tidak ikut hilang.
        cogs = tx.unit_cost * (tx.quantity - tx.returned_quantity)

    complete = not missing
    profit = (net_sales - commission - voucher - shipping - cogs) if complete else None

    return TxResult(
        tx=tx, net_sales=net_sales, commission=commission, voucher=voucher,
        shipping=shipping, cogs=cogs, profit=profit, complete=complete, missing=missing,
    )


@dataclass
class Bucket:
    """Ringkasan untuk satu produk atau satu marketplace."""
    key: str
    label: str
    transactions: int = 0
    complete_transactions: int = 0
    units_sold: int = 0
    units_returned: int = 0
    gross_sales: int = 0
    returned_amount: int = 0
    net_sales: int = 0
    # Total biaya hanya dijumlahkan dari transaksi yang datanya lengkap,
    # supaya laba dan komponennya selalu berasal dari himpunan yang sama.
    commission: int = 0
    voucher: int = 0
    shipping: int = 0
    cogs: int = 0
    profit: int = 0
    net_sales_complete: int = 0
    missing_reasons: set[str] = field(default_factory=set)

    @property
    def incomplete_transactions(self) -> int:
        return self.transactions - self.complete_transactions

    @property
    def complete(self) -> bool:
        return self.incomplete_transactions == 0

    @property
    def margin_pct(self) -> Optional[float]:
        if not self.complete_transactions or self.net_sales_complete == 0:
            return None
        return round(self.profit / self.net_sales_complete * 100, 2)

    def add(self, r: TxResult) -> None:
        self.transactions += 1
        self.units_sold += r.tx.quantity
        self.units_returned += r.tx.returned_quantity
        self.gross_sales += r.tx.gross_sales
        self.returned_amount += r.tx.returned_amount
        self.net_sales += r.net_sales
        if r.complete:
            self.complete_transactions += 1
            self.net_sales_complete += r.net_sales
            self.commission += r.commission or 0
            self.voucher += r.voucher or 0
            self.shipping += r.shipping or 0
            self.cogs += r.cogs or 0
            self.profit += r.profit or 0
        else:
            self.missing_reasons.update(r.missing)


@dataclass
class Report:
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    results: list[TxResult]
    by_product: list[Bucket]
    by_marketplace: list[Bucket]
    overall: Bucket

    @property
    def data_complete(self) -> bool:
        return self.overall.complete


def build_report(
    rows: list[TxInput],
    *,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Report:
    results = [compute_transaction(tx) for tx in rows]

    products: dict[str, Bucket] = {}
    marketplaces: dict[str, Bucket] = {}
    overall = Bucket(key="all", label="Seluruh produk")

    for r in results:
        pkey = r.tx.sku
        plabel = f"{r.tx.product_name} {r.tx.variant_name}"
        products.setdefault(pkey, Bucket(key=pkey, label=plabel)).add(r)
        mkey = r.tx.marketplace_code
        marketplaces.setdefault(mkey, Bucket(key=mkey, label=mkey)).add(r)
        overall.add(r)

    # Produk paling menguntungkan lebih dulu; yang belum lengkap ditaruh terakhir
    # supaya tidak terbaca seolah labanya nol.
    by_product = sorted(
        products.values(),
        key=lambda b: (b.complete_transactions == 0, -b.profit),
    )
    by_marketplace = sorted(marketplaces.values(), key=lambda b: b.key)

    return Report(
        period_start=period_start, period_end=period_end, results=results,
        by_product=by_product, by_marketplace=by_marketplace, overall=overall,
    )
