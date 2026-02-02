#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания структуры БД с уникальным префиксом на удаленной БД.
Использование: python create_prefixed_schema.py <prefix> [remote_db_config]
Пример: python create_prefixed_schema.py student4
"""
import os
import sys
import re
from database import Database

# Настройка кодировки для Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Читаем init_db.sql и модифицируем его для работы с префиксом
def read_init_sql():
    """Читает init_db.sql и возвращает его содержимое."""
    try:
        with open('init_db.sql', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("✗ Файл init_db.sql не найден!")
        sys.exit(1)


def add_prefix_to_sql(sql_content, prefix):
    """Добавляет префикс ко всем именам таблиц в SQL скрипте."""
    # Список таблиц для замены
    tables = [
        'categories', 'stores', 'warehouses', 'products', 'employees',
        'shifts', 'operations', 'operation_items', 'store_product_stock',
        'warehouse_product_stock', 'notifications'
    ]
    
    # Заменяем имена таблиц на версии с префиксом
    modified_sql = sql_content
    
    for table in tables:
        prefixed_table = f"{prefix}_{table}"
        
        # Используем регулярные выражения для более точной замены
        # CREATE TABLE IF NOT EXISTS table
        modified_sql = re.sub(
            rf'\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{table}\b',
            f'CREATE TABLE IF NOT EXISTS {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # CREATE TABLE table
        modified_sql = re.sub(
            rf'\bCREATE\s+TABLE\s+{table}\b',
            f'CREATE TABLE {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # REFERENCES table(...)
        modified_sql = re.sub(
            rf'\bREFERENCES\s+{table}\s*\(',
            f'REFERENCES {prefixed_table}(',
            modified_sql,
            flags=re.IGNORECASE
        )
        # REFERENCES table)
        modified_sql = re.sub(
            rf'\bREFERENCES\s+{table}\s*\)',
            f'REFERENCES {prefixed_table})',
            modified_sql,
            flags=re.IGNORECASE
        )
        # ON table(...) - для индексов
        modified_sql = re.sub(
            rf'\bON\s+{table}\s*\(',
            f'ON {prefixed_table}(',
            modified_sql,
            flags=re.IGNORECASE
        )
        # table_name = 'table' - для проверок в information_schema
        modified_sql = re.sub(
            rf"table_name\s*=\s*'{table}'",
            f"table_name = '{prefixed_table}'",
            modified_sql,
            flags=re.IGNORECASE
        )
        # ALTER TABLE table - для ALTER TABLE команд
        modified_sql = re.sub(
            rf'\bALTER\s+TABLE\s+{table}\b',
            f'ALTER TABLE {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # TRUNCATE TABLE table
        modified_sql = re.sub(
            rf'\bTRUNCATE\s+TABLE\s+{table}\b',
            f'TRUNCATE TABLE {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
    
    return modified_sql


def main():
    if len(sys.argv) < 2:
        print("Использование: python create_prefixed_schema.py <prefix>")
        print("Пример: python create_prefixed_schema.py student4")
        sys.exit(1)
    
    prefix = sys.argv[1].strip()
    if not prefix:
        print("✗ Префикс не может быть пустым!")
        sys.exit(1)
    
    print(f"Создание структуры БД с префиксом: {prefix}")
    print("=" * 60)
    
    # Читаем оригинальный SQL
    print("Чтение init_db.sql...")
    original_sql = read_init_sql()
    
    # Модифицируем SQL для префикса
    print(f"Добавление префикса '{prefix}_' к именам таблиц...")
    prefixed_sql = add_prefix_to_sql(original_sql, prefix)
    
    # Подключаемся к удаленной БД
    print("\nПодключение к удаленной БД...")
    print("Используйте переменные окружения для параметров подключения:")
    print("  DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT")
    
    try:
        # Используем переменные окружения для подключения к удаленной БД
        db = Database()
        print(f"✓ Подключено к БД: {db.db_params['dbname']} на {db.db_params['host']}")
    except Exception as e:
        print(f"✗ Ошибка подключения к БД: {e}")
        print("\nСоздайте файл .env или установите переменные окружения:")
        print("  DB_NAME=имя_базы")
        print("  DB_USER=пользователь")
        print("  DB_PASSWORD=пароль")
        print("  DB_HOST=хост")
        print("  DB_PORT=порт")
        sys.exit(1)
    
    # Выполняем модифицированный SQL
    print(f"\nСоздание таблиц с префиксом '{prefix}_'...")
    try:
        # Правильно разбиваем SQL на команды, учитывая блоки DO $$ ... END $$
        commands = []
        current_command = ""
        in_do_block = False
        do_block_delimiter = None
        
        for line in prefixed_sql.split('\n'):
            line_stripped = line.strip()
            
            # Пропускаем комментарии
            if line_stripped.startswith('--'):
                continue
            
            # Проверяем начало блока DO $$
            if re.search(r'\bDO\s+\$\$', line_stripped, re.IGNORECASE):
                in_do_block = True
                do_block_delimiter = '$$'
                current_command = line + '\n'
                continue
            
            # Если мы в блоке DO $$
            if in_do_block:
                current_command += line + '\n'
                # Проверяем конец блока END $$
                if re.search(r'\bEND\s+\$\$', line_stripped, re.IGNORECASE):
                    if line_stripped.endswith(';'):
                        commands.append(current_command.strip())
                        current_command = ""
                        in_do_block = False
                continue
            
            # Обычная команда
            current_command += line + '\n'
            
            # Если строка заканчивается на ; и мы не в блоке
            if line_stripped.endswith(';'):
                cmd = current_command.strip()
                if cmd and not cmd.startswith('--'):
                    commands.append(cmd)
                current_command = ""
        
        # Добавляем последнюю команду, если она есть
        if current_command.strip() and not current_command.strip().startswith('--'):
            commands.append(current_command.strip())
        
        # Выполняем команды
        executed = 0
        for i, cmd in enumerate(commands, 1):
            cmd = cmd.strip()
            if not cmd:
                continue
            
            try:
                db.execute(cmd, fetch=False)
                executed += 1
            except Exception as e:
                error_str = str(e).lower()
                # Игнорируем некоторые ошибки
                if any(ignore in error_str for ignore in [
                    "already exists", "duplicate", "does not exist"
                ]):
                    # Это нормально для IF NOT EXISTS
                    pass
                else:
                    print(f"  Предупреждение при выполнении команды {i}: {e}")
        
        print(f"  Выполнено команд: {executed}/{len(commands)}")
        
        print(f"✓ Структура БД с префиксом '{prefix}_' успешно создана!")
        
        # Проверяем созданные таблицы
        try:
            tables = db.execute(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = 'public' AND table_name LIKE '{prefix}_%' "
                f"ORDER BY table_name"
            )
            if tables and len(tables) > 0:
                print(f"\nСозданные таблицы ({len(tables)}):")
                for table_row in tables:
                    if table_row and len(table_row) > 0:
                        print(f"  - {table_row[0]}")
            else:
                print(f"\n  Предупреждение: таблицы с префиксом '{prefix}_' не найдены")
        except Exception as e:
            print(f"  Не удалось получить список таблиц: {e}")
            print(f"  Но структура должна быть создана. Проверьте вручную через SQL клиент.")
        
    except Exception as e:
        print(f"✗ Ошибка при создании структуры: {e}")
        db.close()
        sys.exit(1)
    
    db.close()
    print("\n" + "=" * 60)
    print("✓ Готово! Теперь можно импортировать данные с помощью import_to_prefixed_db.py")


if __name__ == "__main__":
    main()
