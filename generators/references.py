"""
Генерация справочников:
categories, products, suppliers, warehouses, warehouse_zones
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Tuple

from faker import Faker

from config import config
from models import (
    Category, Product, Supplier, Warehouse, WarehouseZone
)


def generate_categories(fake: Faker, start_id: int = 1) -> List[Category]:
    """Генерирует плоский список категорий (+ немного иерархии)."""
    categories = []
    base_names = [
        "Электроника", "Бытовая техника", "Одежда", "Обувь", "Продукты",
        "Напитки", "Косметика", "Спорттовары", "Книги", "Канцтовары",
        "Автотовары", "Стройматериалы", "Мебель", "Игрушки", "Зоотовары",
        "Аптека", "Сад и огород", "Хозтовары", "Посуда", "Текстиль",
        "Инструменты", "Свет", "Климат", "Безопасность", "Разное"
    ]

    now = datetime.utcnow()
    for i, name in enumerate(base_names[:config.num_categories]):
        cat = Category(
            category_id=start_id + i,
            name=name,
            parent_id=None,
            created_at=now - timedelta(days=random.randint(400, 800)),
            modified_at=now - timedelta(days=random.randint(0, 100)),
        )
        categories.append(cat)

    # Добавим немного дочерних категорий
    for i in range(min(8, len(categories) // 3)):
        parent = random.choice(categories[:15])
        child = Category(
            category_id=start_id + len(categories),
            name=f"{parent.name} / подкатегория {i+1}",
            parent_id=parent.category_id,
            created_at=now - timedelta(days=random.randint(200, 500)),
            modified_at=now - timedelta(days=random.randint(0, 50)),
        )
        categories.append(child)

    return categories


def generate_products(
    fake: Faker,
    categories: List[Category],
    start_id: int = 1,
    count: int | None = None,
) -> List[Product]:
    count = count or config.num_products
    products = []
    units = ["шт", "уп", "кг", "л", "м"]
    now = datetime.utcnow()

    for i in range(count):
        cat = random.choice(categories)
        created = now - timedelta(days=random.randint(30, 700))
        product = Product(
            product_id=start_id + i,
            category_id=cat.category_id,
            sku=f"SKU-{start_id + i:06d}",
            name=fake.catch_phrase()[:80],
            unit=random.choice(units),
            is_active=random.random() > 0.05,
            created_at=created,
            modified_at=created + timedelta(days=random.randint(0, 60)),
        )
        products.append(product)

    return products


def generate_suppliers(fake: Faker, start_id: int = 1) -> List[Supplier]:
    suppliers = []
    now = datetime.utcnow()

    for i in range(config.num_suppliers):
        created = now - timedelta(days=random.randint(100, 900))
        supplier = Supplier(
            supplier_id=start_id + i,
            name=fake.company(),
            inn=fake.businesses_inn() if hasattr(fake, "businesses_inn") else f"{random.randint(10**9, 10**10-1)}",
            contact_phone=fake.phone_number(),
            is_active=random.random() > 0.08,
            created_at=created,
            modified_at=created + timedelta(days=random.randint(0, 120)),
        )
        suppliers.append(supplier)

    return suppliers


def generate_warehouses_and_zones(
    fake: Faker,
    start_wh_id: int = 1,
    start_zone_id: int = 1,
) -> Tuple[List[Warehouse], List[WarehouseZone]]:
    warehouses = []
    zones = []
    now = datetime.utcnow()
    zone_types = ["storage", "picking", "receiving", "shipping"]

    zone_id = start_zone_id
    for i in range(config.num_warehouses):
        created = now - timedelta(days=random.randint(300, 1000))
        wh = Warehouse(
            warehouse_id=start_wh_id + i,
            name=f"Склад {fake.city()} #{i+1}",
            address=fake.address().replace("\n", ", "),
            is_active=True,
            created_at=created,
            modified_at=created,
        )
        warehouses.append(wh)

        for z in range(config.zones_per_warehouse):
            zone = WarehouseZone(
                zone_id=zone_id,
                warehouse_id=wh.warehouse_id,
                name=f"Зона {z+1}",
                zone_type=zone_types[z % len(zone_types)],
                created_at=created,
                modified_at=created,
            )
            zones.append(zone)
            zone_id += 1

    return warehouses, zones


def generate_all_references(fake: Faker) -> Dict[str, list]:
    """Удобная обёртка — генерирует все справочники сразу."""
    categories = generate_categories(fake)
    products = generate_products(fake, categories)
    suppliers = generate_suppliers(fake)
    warehouses, zones = generate_warehouses_and_zones(fake)

    return {
        "categories": categories,
        "products": products,
        "suppliers": suppliers,
        "warehouses": warehouses,
        "warehouse_zones": zones,
    }
