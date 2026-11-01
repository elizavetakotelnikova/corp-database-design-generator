"""
Описание сущностей (dataclasses).
Используются внутри генератора до записи в БД.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal


@dataclass
class Category:
    category_id: int
    name: str
    parent_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Product:
    product_id: int
    category_id: int
    sku: str
    name: str
    unit: str = "шт"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Supplier:
    supplier_id: int
    name: str
    inn: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Warehouse:
    warehouse_id: int
    name: str
    address: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WarehouseZone:
    zone_id: int
    warehouse_id: int
    name: str
    zone_type: str = "storage"          # storage / picking / receiving / shipping
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Receipt:
    receipt_id: int
    supplier_id: int
    warehouse_id: int
    doc_number: str
    doc_date: date
    status: str = "posted"              # draft / posted / cancelled
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ReceiptItem:
    receipt_item_id: int
    receipt_id: int
    product_id: int
    quantity: Decimal
    price: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Shipment:
    shipment_id: int
    warehouse_id: int
    doc_number: str
    doc_date: date
    status: str = "posted"
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ShipmentItem:
    shipment_item_id: int
    shipment_id: int
    product_id: int
    quantity: Decimal
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StockMovement:
    movement_id: int
    product_id: int
    zone_id: int
    quantity: Decimal                   # + приход, - расход
    movement_type: str                  # receipt / shipment / transfer / adjustment
    movement_dt: datetime
    document_type: Optional[str] = None # receipt / shipment
    document_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    modified_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StockBalance:
    product_id: int
    zone_id: int
    quantity: Decimal
    modified_at: datetime = field(default_factory=datetime.utcnow)
