#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для экспорта данных из локальной БД в SQL файл.
Использование: python export_local_db.py [output_file.sql]
"""
import os
import sys
from datetime import datetime
from database import Database

# Список таблиц в порядке зависимостей (сначала родительские, потом дочерние)
TABLES_ORDER = [
    'categories',
    'stores',
    'warehouses',
    'products',
    'employees',
    'shifts',
    'operations',
    'operation_items',
    'store_product_stock',
    'warehouse_product_stock',
    'notifications'
]


def export_table_data(db, table_name, output_file):
    """Экспортирует данные из таблицы в SQL формат."""
    try:
        # Получаем все данные из таблицы
        rows = db.execute(f"SELECT * FROM {table_name} ORDER BY 1")
        
        if not rows:
            output_file.write(f"-- Таблица {table_name} пуста\n\n")
            return
        
        # Получаем имена колонок
        columns = db.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position")
        column_names = [col[0] for col in columns]
        
        output_file.write(f"-- Данные таблицы {table_name}\n")
        output_file.write(f"TRUNCATE TABLE {table_name} CASCADE;\n\n")
        
        # Формируем INSERT запросы
        for row in rows:
            values = []
            for i, val in enumerate(row):
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    # Экранируем кавычки и спецсимволы
                    escaped = val.replace("'", "''").replace("\\", "\\\\")
                    values.append(f"'{escaped}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                elif isinstance(val, bool):
                    values.append('TRUE' if val else 'FALSE')
                elif hasattr(val, 'isoformat'):  # datetime, date, time
                    values.append(f"'{val.isoformat()}'")
                else:
                    # Для других типов (например, Decimal) преобразуем в строку
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")
            
            columns_str = ', '.join(column_names)
            values_str = ', '.join(values)
            output_file.write(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});\n")
        
        output_file.write("\n")
        print(f"✓ Экспортировано {len(rows)} записей из таблицы {table_name}")
        
    except Exception as e:
        print(f"✗ Ошибка при экспорте таблицы {table_name}: {e}")
        output_file.write(f"-- ОШИБКА при экспорте таблицы {table_name}: {e}\n\n")


def main():
    output_filename = sys.argv[1] if len(sys.argv) > 1 else f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    print(f"Подключение к локальной БД...")
    try:
        db = Database()
        print(f"✓ Подключено к БД: {db.db_params['dbname']} на {db.db_params['host']}")
    except Exception as e:
        print(f"✗ Ошибка подключения к БД: {e}")
        print("\nПроверьте параметры подключения:")
        print("  - Переменные окружения: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT")
        print("  - Или значения по умолчанию в database.py")
        sys.exit(1)
    
    print(f"\nЭкспорт данных в файл: {output_filename}")
    print("=" * 60)
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(f"-- Экспорт данных из БД {db.db_params['dbname']}\n")
        f.write(f"-- Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- Хост: {db.db_params['host']}:{db.db_params['port']}\n\n")
        f.write("SET client_encoding = 'UTF8';\n\n")
        
        for table in TABLES_ORDER:
            export_table_data(db, table, f)
    
    db.close()
    print("=" * 60)
    print(f"✓ Экспорт завершен. Файл сохранен: {output_filename}")


if __name__ == "__main__":
    main()
