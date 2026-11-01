"""
Запись сгенерированных данных в PostgreSQL.
Использует psycopg2 и executemany / COPY для скорости.
"""

import os
from typing import List, Any
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    psycopg2 = None

from config import config


def get_connection_params() -> dict:
    return {
        "host": os.getenv("DB_HOST", config.db_host),
        "port": int(os.getenv("DB_PORT", config.db_port)),
        "dbname": os.getenv("DB_NAME", config.db_name),
        "user": os.getenv("DB_USER", config.db_user),
        "password": os.getenv("DB_PASSWORD", config.db_password),
    }


@contextmanager
def get_conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 не установлен. Выполните: pip install psycopg2-binary")
    conn = psycopg2.connect(**get_connection_params())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def truncate_all(conn):
    """Очищает таблицы (осторожно!)."""
    tables = [
        "stock_movements", "stock_balances",
        "receipt_items", "receipts",
        "shipment_items", "shipments",
        "products", "categories",
        "suppliers", "warehouse_zones", "warehouses",
    ]
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(f"TRUNCATE TABLE {t} CASCADE;")


def insert_batch(conn, table: str, columns: List[str], rows: List[tuple]):
    if not rows:
        return
    cols = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=config.batch_size)


def save_references(conn, data: dict):
    # categories
    rows = [
        (c.category_id, c.name, c.parent_id, c.created_at, c.modified_at)
        for c in data["categories"]
    ]
    insert_batch(conn, "categories",
                 ["category_id", "name", "parent_id", "created_at", "modified_at"], rows)

    # products
    rows = [
        (p.product_id, p.category_id, p.sku, p.name, p.unit, p.is_active, p.created_at, p.modified_at)
        for p in data["products"]
    ]
    insert_batch(conn, "products",
                 ["product_id", "category_id", "sku", "name", "unit", "is_active", "created_at", "modified_at"], rows)

    # suppliers
    rows = [
        (s.supplier_id, s.name, s.inn, s.contact_phone, s.is_active, s.created_at, s.modified_at)
        for s in data["suppliers"]
    ]
    insert_batch(conn, "suppliers",
                 ["supplier_id", "name", "inn", "contact_phone", "is_active", "created_at", "modified_at"], rows)

    # warehouses
    rows = [
        (w.warehouse_id, w.name, w.address, w.is_active, w.created_at, w.modified_at)
        for w in data["warehouses"]
    ]
    insert_batch(conn, "warehouses",
                 ["warehouse_id", "name", "address", "is_active", "created_at", "modified_at"], rows)

    # warehouse_zones
    rows = [
        (z.zone_id, z.warehouse_id, z.name, z.zone_type, z.created_at, z.modified_at)
        for z in data["warehouse_zones"]
    ]
    insert_batch(conn, "warehouse_zones",
                 ["zone_id", "warehouse_id", "name", "zone_type", "created_at", "modified_at"], rows)


def save_documents(conn, receipts, receipt_items, shipments, shipment_items):
    rows = [
        (r.receipt_id, r.supplier_id, r.warehouse_id, r.doc_number, r.doc_date, r.status, r.created_at, r.modified_at)
        for r in receipts
    ]
    insert_batch(conn, "receipts",
                 ["receipt_id", "supplier_id", "warehouse_id", "doc_number", "doc_date", "status", "created_at", "modified_at"], rows)

    rows = [
        (i.receipt_item_id, i.receipt_id, i.product_id, i.quantity, i.price, i.created_at, i.modified_at)
        for i in receipt_items
    ]
    insert_batch(conn, "receipt_items",
                 ["receipt_item_id", "receipt_id", "product_id", "quantity", "price", "created_at", "modified_at"], rows)

    rows = [
        (s.shipment_id, s.warehouse_id, s.doc_number, s.doc_date, s.status, s.created_at, s.modified_at)
        for s in shipments
    ]
    insert_batch(conn, "shipments",
                 ["shipment_id", "warehouse_id", "doc_number", "doc_date", "status", "created_at", "modified_at"], rows)

    rows = [
        (i.shipment_item_id, i.shipment_id, i.product_id, i.quantity, i.created_at, i.modified_at)
        for i in shipment_items
    ]
    insert_batch(conn, "shipment_items",
                 ["shipment_item_id", "shipment_id", "product_id", "quantity", "created_at", "modified_at"], rows)


def save_movements_and_balances(conn, movements, balances):
    rows = [
        (m.movement_id, m.product_id, m.zone_id, m.quantity, m.movement_type,
         m.movement_dt, m.document_type, m.document_id, m.created_at, m.modified_at)
        for m in movements
    ]
    insert_batch(conn, "stock_movements",
                 ["movement_id", "product_id", "zone_id", "quantity", "movement_type",
                  "movement_dt", "document_type", "document_id", "created_at", "modified_at"], rows)

    # Для остатков используем UPSERT (обновляем если уже есть)
    if balances:
        with conn.cursor() as cur:
            for b in balances:
                cur.execute("""
                    INSERT INTO stock_balances (product_id, zone_id, quantity, modified_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id, zone_id)
                    DO UPDATE SET quantity = EXCLUDED.quantity,
                                  modified_at = EXCLUDED.modified_at
                """, (b.product_id, b.zone_id, b.quantity, b.modified_at))


# ---------------------------------------------------------------------------
# Чтение состояния БД (нужно для инкрементальной генерации)
# ---------------------------------------------------------------------------

def fetch_max_ids(conn) -> dict:
    """Возвращает максимальные id по всем ключевым таблицам."""
    tables = {
        "category_id": "categories",
        "product_id": "products",
        "supplier_id": "suppliers",
        "warehouse_id": "warehouses",
        "zone_id": "warehouse_zones",
        "receipt_id": "receipts",
        "receipt_item_id": "receipt_items",
        "shipment_id": "shipments",
        "shipment_item_id": "shipment_items",
        "movement_id": "stock_movements",
    }
    result = {}
    with conn.cursor() as cur:
        for col, table in tables.items():
            cur.execute(f"SELECT COALESCE(MAX({col}), 0) FROM {table}")
            result[col] = cur.fetchone()[0]
    return result


def fetch_last_dates(conn) -> dict:
    """Последние даты документов и движений."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(doc_date) FROM receipts")
        last_receipt = cur.fetchone()[0]
        cur.execute("SELECT MAX(doc_date) FROM shipments")
        last_shipment = cur.fetchone()[0]
        cur.execute("SELECT MAX(movement_dt::date) FROM stock_movements")
        last_movement = cur.fetchone()[0]
    return {
        "last_receipt_date": last_receipt,
        "last_shipment_date": last_shipment,
        "last_movement_date": last_movement,
    }


def fetch_existing_references(conn) -> dict:
    """Читает существующие справочники (нужны для генерации новых документов)."""
    from generator.models import Category, Product, Supplier, Warehouse, WarehouseZone

    with conn.cursor() as cur:
        cur.execute("SELECT category_id, name, parent_id, created_at, modified_at FROM categories")
        categories = [Category(*row) for row in cur.fetchall()]

        cur.execute("""
            SELECT product_id, category_id, sku, name, unit, is_active, created_at, modified_at
            FROM products
        """)
        products = [Product(*row) for row in cur.fetchall()]

        cur.execute("""
            SELECT supplier_id, name, inn, contact_phone, is_active, created_at, modified_at
            FROM suppliers
        """)
        suppliers = [Supplier(*row) for row in cur.fetchall()]

        cur.execute("""
            SELECT warehouse_id, name, address, is_active, created_at, modified_at
            FROM warehouses
        """)
        warehouses = [Warehouse(*row) for row in cur.fetchall()]

        cur.execute("""
            SELECT zone_id, warehouse_id, name, zone_type, created_at, modified_at
            FROM warehouse_zones
        """)
        zones = [WarehouseZone(*row) for row in cur.fetchall()]

    return {
        "categories": categories,
        "products": products,
        "suppliers": suppliers,
        "warehouses": warehouses,
        "warehouse_zones": zones,
    }


def fetch_current_balances(conn) -> dict:
    """Текущие остатки в виде {(product_id, zone_id): quantity}."""
    from decimal import Decimal
    with conn.cursor() as cur:
        cur.execute("SELECT product_id, zone_id, quantity FROM stock_balances")
        return {(r[0], r[1]): Decimal(str(r[2])) for r in cur.fetchall()}


def touch_modified_at(conn, table: str, id_column: str, ids: list, new_ts):
    """Обновляет modified_at у части существующих записей."""
    if not ids:
        return
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {table} SET modified_at = %s WHERE {id_column} = ANY(%s)",
            (new_ts, ids),
        )
