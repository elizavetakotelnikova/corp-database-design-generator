"""
Проверки согласованности данных.
"""

from decimal import Decimal
from typing import List, Dict, Tuple
from collections import defaultdict

from models import (
    StockMovement, StockBalance, ReceiptItem, ShipmentItem
)


def check_movements_vs_balances(
    movements: List[StockMovement],
    balances: List[StockBalance],
    tolerance: Decimal = Decimal("0.001"),
) -> List[str]:
    """
    Проверяет, что сумма движений совпадает с остатками.
    Возвращает список ошибок (пустой = всё ок).
    """
    calc: Dict[Tuple[int, int], Decimal] = defaultdict(lambda: Decimal(0))
    for mv in movements:
        calc[(mv.product_id, mv.zone_id)] += mv.quantity

    balance_map = {(b.product_id, b.zone_id): b.quantity for b in balances}

    errors = []
    all_keys = set(calc.keys()) | set(balance_map.keys())
    for key in all_keys:
        calc_qty = calc.get(key, Decimal(0))
        bal_qty = balance_map.get(key, Decimal(0))
        if abs(calc_qty - bal_qty) > tolerance:
            errors.append(
                f"Расхождение остатка {key}: движения={calc_qty}, stock_balances={bal_qty}"
            )
    return errors


def check_document_quantities(
    receipt_items: List[ReceiptItem],
    shipment_items: List[ShipmentItem],
    movements: List[StockMovement],
) -> List[str]:
    """Проверяет, что количества в движениях соответствуют документам."""
    errors = []

    # Поступления
    receipt_qty = defaultdict(lambda: Decimal(0))
    for it in receipt_items:
        receipt_qty[it.receipt_id] += it.quantity

    move_receipt_qty = defaultdict(lambda: Decimal(0))
    for mv in movements:
        if mv.document_type == "receipt" and mv.document_id is not None:
            move_receipt_qty[mv.document_id] += mv.quantity

    for doc_id, qty in receipt_qty.items():
        if abs(qty - move_receipt_qty.get(doc_id, Decimal(0))) > Decimal("0.001"):
            errors.append(f"Receipt {doc_id}: items={qty}, movements={move_receipt_qty.get(doc_id)}")

    # Отгрузки
    shipment_qty = defaultdict(lambda: Decimal(0))
    for it in shipment_items:
        shipment_qty[it.shipment_id] += it.quantity

    move_ship_qty = defaultdict(lambda: Decimal(0))
    for mv in movements:
        if mv.document_type == "shipment" and mv.document_id is not None:
            move_ship_qty[mv.document_id] += abs(mv.quantity)

    for doc_id, qty in shipment_qty.items():
        if abs(qty - move_ship_qty.get(doc_id, Decimal(0))) > Decimal("0.001"):
            errors.append(f"Shipment {doc_id}: items={qty}, movements={move_ship_qty.get(doc_id)}")

    return errors


def run_all_checks(
    movements: List[StockMovement],
    balances: List[StockBalance],
    receipt_items: List[ReceiptItem],
    shipment_items: List[ShipmentItem],
) -> bool:
    """Запускает все проверки. Возвращает True, если ошибок нет."""
    errors = []
    errors.extend(check_movements_vs_balances(movements, balances))
    errors.extend(check_document_quantities(receipt_items, shipment_items, movements))

    if errors:
        print("Найдены проблемы согласованности:")
        for e in errors[:20]:
            print("  -", e)
        if len(errors) > 20:
            print(f"  ... и ещё {len(errors) - 20}")
        return False

    print("Проверки согласованности пройдены успешно.")
    return True
