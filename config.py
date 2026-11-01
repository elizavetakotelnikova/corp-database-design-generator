"""
Конфигурация генератора суррогатных данных склада.
"""

from dataclasses import dataclass
from datetime import date
import os


@dataclass
class GeneratorConfig:
    # Воспроизводимость
    seed: int = 42

    # Период истории (первичная генерация)
    start_date: date = date(2023, 1, 1)
    years: int = 2

    # Объёмы справочников
    num_categories: int = 25
    num_products: int = 2500
    num_suppliers: int = 80
    num_warehouses: int = 4
    zones_per_warehouse: int = 8

    # Целевой объём фактов
    target_movements: int = 600_000

    # Параметры документов
    avg_items_per_receipt: int = 6
    avg_items_per_shipment: int = 4
    receipts_per_day_mean: float = 18.0
    shipments_per_day_mean: float = 22.0

    # Инкрементальная генерация
    incremental_days: int = 7
    new_products_ratio: float = 0.015
    modify_existing_ratio: float = 0.03

    # Технические
    batch_size: int = 5000
    locale: str = "ru_RU"

    # Подключение к PostgreSQL
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", 5433))
    db_name: str = os.getenv("DB_NAME", "warehouse")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")

config = GeneratorConfig()
