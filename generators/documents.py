"""
Генерация документов:
receipts + receipt_items
shipments + shipment_items
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
import random
from typing import List, Dict, Tuple

from faker import Faker

from config import config
from models import (
    Receipt, ReceiptItem, Shipment, ShipmentItem,
    Product, Supplier, Warehouse
)


def _random_quantity() -> Decimal:
    """Случайное количество товара."""
    if random.random() < 0.7:
        return Decimal(random.randint(1, 30))
    return Decimal(random.randint(30, 200))


def generate_receipts_for_period(
    fake: Faker,
    products: List[Product],
    suppliers: List[Supplier],
    warehouses: List[Warehouse],
    start_date: date,
    end_date: date,
    start_receipt_id: int = 1,
    start_item_id: int = 1,
) -> Tuple[List[Receipt], List[ReceiptItem]]:
    """Генерирует поступления за период."""
    receipts = []
    items = []
    receipt_id = start_receipt_id
    item_id = start_item_id

    active_suppliers = [s for s in suppliers if s.is_active] or suppliers
    active_products = [p for p in products if p.is_active] or products

    current = start_date
    while current <= end_date:
        # Сколько поступлений в этот день
        n_docs = max(0, int(random.gauss(config.receipts_per_day_mean, 4)))
        for _ in range(n_docs):
            supplier = random.choice(active_suppliers)
            warehouse = random.choice(warehouses)
            doc_dt = datetime.combine(current, datetime.min.time()) + timedelta(
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59),
            )

            receipt = Receipt(
                receipt_id=receipt_id,
                supplier_id=supplier.supplier_id,
                warehouse_id=warehouse.warehouse_id,
                doc_number=f"ПН-{current.strftime('%Y%m%d')}-{receipt_id:05d}",
                doc_date=current,
                status="posted",
                created_at=doc_dt,
                modified_at=doc_dt,
            )
            receipts.append(receipt)

            # Позиции
            n_items = max(1, int(random.gauss(config.avg_items_per_receipt, 2)))
            chosen_products = random.sample(
                active_products, k=min(n_items, len(active_products))
            )
            for prod in chosen_products:
                item = ReceiptItem(
                    receipt_item_id=item_id,
                    receipt_id=receipt_id,
                    product_id=prod.product_id,
                    quantity=_random_quantity(),
                    price=Decimal(str(round(random.uniform(50, 5000), 2))),
                    created_at=doc_dt,
                    modified_at=doc_dt,
                )
                items.append(item)
                item_id += 1

            receipt_id += 1

        current += timedelta(days=1)

    return receipts, items


def generate_shipments_for_period(
    fake: Faker,
    products: List[Product],
    warehouses: List[Warehouse],
    start_date: date,
    end_date: date,
    start_shipment_id: int = 1,
    start_item_id: int = 1,
) -> Tuple[List[Shipment], List[ShipmentItem]]:
    """Генерирует отгрузки за период."""
    shipments = []
    items = []
    shipment_id = start_shipment_id
    item_id = start_item_id

    active_products = [p for p in products if p.is_active] or products

    current = start_date
    while current <= end_date:
        n_docs = max(0, int(random.gauss(config.shipments_per_day_mean, 5)))
        for _ in range(n_docs):
            warehouse = random.choice(warehouses)
            doc_dt = datetime.combine(current, datetime.min.time()) + timedelta(
                hours=random.randint(9, 19),
                minutes=random.randint(0, 59),
            )

            shipment = Shipment(
                shipment_id=shipment_id,
                warehouse_id=warehouse.warehouse_id,
                doc_number=f"РН-{current.strftime('%Y%m%d')}-{shipment_id:05d}",
                doc_date=current,
                status="posted",
                created_at=doc_dt,
                modified_at=doc_dt,
            )
            shipments.append(shipment)

            n_items = max(1, int(random.gauss(config.avg_items_per_shipment, 1.5)))
            chosen_products = random.sample(
                active_products, k=min(n_items, len(active_products))
            )
            for prod in chosen_products:
                item = ShipmentItem(
                    shipment_item_id=item_id,
                    shipment_id=shipment_id,
                    product_id=prod.product_id,
                    quantity=_random_quantity(),
                    created_at=doc_dt,
                    modified_at=doc_dt,
                )
                items.append(item)
                item_id += 1

            shipment_id += 1

        current += timedelta(days=1)

    return shipments, items
