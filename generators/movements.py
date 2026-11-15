"""
Генерация движений и поддержание остатков.
Самая важная часть с точки зрения согласованности.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Tuple
from collections import defaultdict

from models import (
    Receipt, ReceiptItem, Shipment, ShipmentItem,
    StockMovement, StockBalance, WarehouseZone
)


def build_movements_from_documents(
    receipts: List[Receipt],
    receipt_items: List[ReceiptItem],
    shipments: List[Shipment],
    shipment_items: List[ShipmentItem],
    zones: List[WarehouseZone],
    start_movement_id: int = 1,
) -> Tuple[List[StockMovement], Dict[Tuple[int, int], Decimal]]:
    """
    Создаёт stock_movements на основании документов.
    Возвращает список движений и итоговые остатки {(product_id, zone_id): qty}.
    """
    movements: List[StockMovement] = []
    balances: Dict[Tuple[int, int], Decimal] = defaultdict(lambda: Decimal(0))
    movement_id = start_movement_id

    # Индексы для быстрого доступа
    zones_by_wh = defaultdict(list)
    for z in zones:
        zones_by_wh[z.warehouse_id].append(z)

    # --- Приходы ---
    items_by_receipt = defaultdict(list)
    for it in receipt_items:
        items_by_receipt[it.receipt_id].append(it)

    for rec in receipts:
        if rec.status != "posted":
            continue
        # Берём зону приёмки или любую зону склада
        wh_zones = zones_by_wh.get(rec.warehouse_id, zones)
        zone = next((z for z in wh_zones if z.zone_type == "receiving"), wh_zones[0])

        for it in items_by_receipt[rec.receipt_id]:
            mv = StockMovement(
                movement_id=movement_id,
                product_id=it.product_id,
                zone_id=zone.zone_id,
                quantity=it.quantity,                    # + приход
                movement_type="receipt",
                movement_dt=rec.created_at,
                document_type="receipt",
                document_id=rec.receipt_id,
                created_at=rec.created_at,
                modified_at=rec.created_at,
            )
            movements.append(mv)
            balances[(it.product_id, zone.zone_id)] += it.quantity
            movement_id += 1

    # --- Расходы ---
    items_by_shipment = defaultdict(list)
    for it in shipment_items:
        items_by_shipment[it.shipment_id].append(it)

    for ship in shipments:
        if ship.status != "posted":
            continue
        wh_zones = zones_by_wh.get(ship.warehouse_id, zones)
        zone = next((z for z in wh_zones if z.zone_type == "shipping"), wh_zones[0])

        for it in items_by_shipment[ship.shipment_id]:
            # Для упрощения разрешаем уходить в небольшой минус
            # (в реальной системе здесь была бы проверка остатка)
            qty = -it.quantity
            mv = StockMovement(
                movement_id=movement_id,
                product_id=it.product_id,
                zone_id=zone.zone_id,
                quantity=qty,
                movement_type="shipment",
                movement_dt=ship.created_at,
                document_type="shipment",
                document_id=ship.shipment_id,
                created_at=ship.created_at,
                modified_at=ship.created_at,
            )
            movements.append(mv)
            balances[(it.product_id, zone.zone_id)] += qty
            movement_id += 1

    return movements, dict(balances)


def balances_to_objects(
    balances: Dict[Tuple[int, int], Decimal],
) -> List[StockBalance]:
    """Преобразует словарь остатков в список объектов StockBalance."""
    now = datetime.utcnow()
    result = []
    for (product_id, zone_id), qty in balances.items():
        if qty == 0:
            continue
        result.append(
            StockBalance(
                product_id=product_id,
                zone_id=zone_id,
                quantity=qty,
                modified_at=now,
            )
        )
    return result
