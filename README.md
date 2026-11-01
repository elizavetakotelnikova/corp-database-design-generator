# Генератор суррогатных данных склада

Программный генератор для операционной БД «Склад» (OLTP).

## Возможности

- Первичная генерация справочников + истории за 1–3 года
- Логически согласованные поступления, отгрузки, движения и остатки
- Воспроизводимость через `seed`
- Запись в PostgreSQL батчами
- Проверки согласованности

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
# Первичная генерация (без записи в БД)
python -m main --mode primary --dry-run

# Первичная генерация (с записью в БД)
python -m main --mode primary

# Полная генерация с очисткой таблиц
python -m main --mode primary --truncate

# Свои параметры
python -m main --mode primary --years 2 --seed 42 --truncate
```

## Структура

```
cord-database-design-generator/
├── config.py              # параметры
├── models.py              # модели сущностей
├── generators/
│   ├── references.py      # categories, products, suppliers, warehouses...
│   ├── documents.py       # receipts, shipment, items
│   └── movements.py       # stock_movements, balances
├── consistency.py         # проверки
├── db.py                  # запись в PostgreSQL
└── main.py                # точка входа
```

## Важно

Перед записью в БД таблицы должны существовать.

### Режимы

- `--mode primary` — полная генерация с нуля
- `--mode incremental --days 7` — дописать ещё N дней работы (читает текущее состояние из БД)

```bash
# Инкремент после primary
python -m generator.main --mode incremental --days 7
```
