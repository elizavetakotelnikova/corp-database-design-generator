"""
Точка входа генератора суррогатных данных склада.

Примеры запуска:
    python -m generator.main --mode primary
    python -m generator.main --mode primary --years 2 --movements 700000
    python -m generator.main --mode incremental --days 7
    python -m generator.main --mode primary --dry-run
"""

import argparse
import random
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
from faker import Faker

# Чтобы можно было запускать и как модуль, и как скрипт
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config, GeneratorConfig
from generators.references import generate_all_references
from generators.documents import (
    generate_receipts_for_period,
    generate_shipments_for_period,
)
from generators.movements import (
    build_movements_from_documents,
    balances_to_objects,
)
from consistency import run_all_checks
import db


def set_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)


def run_primary(args):
    print("=" * 60)
    print("ПЕРВИЧНАЯ ГЕНЕРАЦИЯ")
    print("=" * 60)

    set_seeds(config.seed)
    fake = Faker(config.locale)

    # 1. Справочники
    print("Генерация справочников...")
    refs = generate_all_references(fake)
    print(f"  categories: {len(refs['categories'])}")
    print(f"  products:   {len(refs['products'])}")
    print(f"  suppliers:  {len(refs['suppliers'])}")
    print(f"  warehouses: {len(refs['warehouses'])}")
    print(f"  zones:      {len(refs['warehouse_zones'])}")

    # 2. Период
    start = config.start_date
    end = start + timedelta(days=365 * config.years - 1)
    print(f"Период: {start} → {end}")

    # 3. Документы
    print("Генерация поступлений...")
    receipts, receipt_items = generate_receipts_for_period(
        fake,
        refs["products"],
        refs["suppliers"],
        refs["warehouses"],
        start, end,
    )
    print(f"  receipts: {len(receipts)}, items: {len(receipt_items)}")

    print("Генерация отгрузок...")
    shipments, shipment_items = generate_shipments_for_period(
        fake,
        refs["products"],
        refs["warehouses"],
        start, end,
    )
    print(f"  shipments: {len(shipments)}, items: {len(shipment_items)}")

    # 4. Движения и остатки
    print("Построение движений и остатков...")
    movements, balances_dict = build_movements_from_documents(
        receipts, receipt_items,
        shipments, shipment_items,
        refs["warehouse_zones"],
    )
    balances = balances_to_objects(balances_dict)
    print(f"  stock_movements: {len(movements)}")
    print(f"  stock_balances:  {len(balances)}")

    # 5. Проверки
    print("\nПроверка согласованности...")
    ok = run_all_checks(movements, balances, receipt_items, shipment_items)

    if args.dry_run:
        print("\n[DRY-RUN] Данные не записываются в БД.")
        return

    # 6. Запись в PostgreSQL
    print("\nЗапись в PostgreSQL...")
    with db.get_conn() as conn:
        if args.truncate:
            print("  Очистка таблиц...")
            db.truncate_all(conn)
        db.save_references(conn, refs)
        db.save_documents(conn, receipts, receipt_items, shipments, shipment_items)
        db.save_movements_and_balances(conn, movements, balances)

    print("Готово.")
    if not ok:
        print("Внимание: были замечания по согласованности (см. выше).")


def run_incremental(args):
    print("=" * 60)
    print("ИНКРЕМЕНТАЛЬНАЯ ГЕНЕРАЦИЯ")
    print("=" * 60)

    set_seeds(config.seed + 17_000 + config.incremental_days)
    fake = Faker(config.locale)

    from datetime import date, datetime, timedelta
    from generator.generators.references import generate_products
    from generator.models import StockBalance
    from decimal import Decimal
    from collections import defaultdict

    with db.get_conn() as conn:
        # 1. Читаем текущее состояние
        print("Чтение текущего состояния БД...")
        max_ids = db.fetch_max_ids(conn)
        last_dates = db.fetch_last_dates(conn)
        refs = db.fetch_existing_references(conn)
        current_balances = db.fetch_current_balances(conn)

        print(f"  products: {len(refs['products'])}")
        print(f"  max movement_id: {max_ids['movement_id']}")
        print(f"  last movement date: {last_dates['last_movement_date']}")

        if not refs["products"]:
            print("БД пустая. Сначала запустите --mode primary")
            return

        # 2. Определяем период инкремента
        last_date = (
            last_dates["last_movement_date"]
            or last_dates["last_receipt_date"]
            or last_dates["last_shipment_date"]
            or config.start_date
        )
        if isinstance(last_date, datetime):
            last_date = last_date.date()

        start = last_date + timedelta(days=1)
        end = start + timedelta(days=config.incremental_days - 1)
        print(f"Период инкремента: {start} → {end}")

        # 3. Иногда добавляем новые товары
        new_products = []
        n_new = int(len(refs["products"]) * config.new_products_ratio)
        if n_new > 0:
            print(f"Генерация {n_new} новых товаров...")
            new_products = generate_products(
                fake,
                refs["categories"],
                start_id=max_ids["product_id"] + 1,
                count=n_new,
            )
            refs["products"].extend(new_products)

        # 4. Новые документы
        print("Генерация новых поступлений и отгрузок...")
        receipts, receipt_items = generate_receipts_for_period(
            fake,
            refs["products"],
            refs["suppliers"],
            refs["warehouses"],
            start, end,
            start_receipt_id=max_ids["receipt_id"] + 1,
            start_item_id=max_ids["receipt_item_id"] + 1,
        )
        shipments, shipment_items = generate_shipments_for_period(
            fake,
            refs["products"],
            refs["warehouses"],
            start, end,
            start_shipment_id=max_ids["shipment_id"] + 1,
            start_item_id=max_ids["shipment_item_id"] + 1,
        )
        print(f"  + receipts: {len(receipts)}, items: {len(receipt_items)}")
        print(f"  + shipments: {len(shipments)}, items: {len(shipment_items)}")

        # 5. Движения
        movements, delta_balances = build_movements_from_documents(
            receipts, receipt_items,
            shipments, shipment_items,
            refs["warehouse_zones"],
            start_movement_id=max_ids["movement_id"] + 1,
        )
        print(f"  + stock_movements: {len(movements)}")

        # 6. Обновляем остатки (старые + дельта)
        for key, delta in delta_balances.items():
            current_balances[key] = current_balances.get(key, Decimal(0)) + delta

        balances = [
            StockBalance(product_id=k[0], zone_id=k[1], quantity=qty, modified_at=datetime.utcnow())
            for k, qty in current_balances.items()
            if qty != 0
        ]

        # 7. Иногда «трогаем» старые записи (modified_at)
        now = datetime.utcnow()
        if refs["products"] and config.modify_existing_ratio > 0:
            n_touch = max(1, int(len(refs["products"]) * config.modify_existing_ratio))
            touch_ids = [p.product_id for p in random.sample(refs["products"], k=min(n_touch, len(refs["products"])))]
            print(f"Обновление modified_at у {len(touch_ids)} товаров...")
            db.touch_modified_at(conn, "products", "product_id", touch_ids, now)

        if args.dry_run:
            print("\n[DRY-RUN] Данные не записываются в БД.")
            print(f"Было бы добавлено: {len(new_products)} products, "
                  f"{len(receipts)} receipts, {len(shipments)} shipments, "
                  f"{len(movements)} movements")
            return

        # 8. Запись
        print("Запись инкремента в PostgreSQL...")
        if new_products:
            db.insert_batch(conn, "products",
                ["product_id", "category_id", "sku", "name", "unit", "is_active", "created_at", "modified_at"],
                [(p.product_id, p.category_id, p.sku, p.name, p.unit, p.is_active, p.created_at, p.modified_at)
                 for p in new_products])

        db.save_documents(conn, receipts, receipt_items, shipments, shipment_items)
        db.save_movements_and_balances(conn, movements, balances)

    print("Инкрементальная генерация завершена.")


def parse_args():
    parser = argparse.ArgumentParser(description="Генератор данных склада")
    parser.add_argument("--mode", choices=["primary", "incremental"], default="primary")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--movements", type=int, default=None, help="Целевое кол-во движений (пока ориентир)")
    parser.add_argument("--days", type=int, default=None, help="Дней для incremental")
    parser.add_argument("--dry-run", action="store_true", help="Не писать в БД")
    parser.add_argument("--truncate", action="store_true", help="Очистить таблицы перед загрузкой")
    return parser.parse_args()


def main():
    args = parse_args()

    # Переопределение конфига из аргументов
    if args.seed is not None:
        config.seed = args.seed
    if args.years is not None:
        config.years = args.years
    if args.movements is not None:
        config.target_movements = args.movements
    if args.days is not None:
        config.incremental_days = args.days

    if args.mode == "primary":
        run_primary(args)
    else:
        run_incremental(args)


if __name__ == "__main__":
    main()
