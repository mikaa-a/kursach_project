#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для импорта данных из экспортированного SQL файла в удаленную БД с префиксом.
Использование: python import_to_prefixed_db.py <prefix> <export_file.sql>
Пример: python import_to_prefixed_db.py student4 export_20240101_120000.sql
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

# Список таблиц
TABLES = [
    'categories', 'stores', 'warehouses', 'products', 'employees',
    'shifts', 'operations', 'operation_items', 'store_product_stock',
    'warehouse_product_stock', 'notifications'
]


def replace_table_names_in_sql(sql_content, prefix):
    """Заменяет имена таблиц в SQL на версии с префиксом."""
    modified_sql = sql_content
    
    for table in TABLES:
        prefixed_table = f"{prefix}_{table}"
        # Заменяем имена таблиц в различных контекстах
        # TRUNCATE TABLE
        modified_sql = re.sub(
            rf'\bTRUNCATE\s+TABLE\s+{table}\b',
            f'TRUNCATE TABLE {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # INSERT INTO
        modified_sql = re.sub(
            rf'\bINSERT\s+INTO\s+{table}\b',
            f'INSERT INTO {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # FROM table
        modified_sql = re.sub(
            rf'\bFROM\s+{table}\b',
            f'FROM {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
        # JOIN table
        modified_sql = re.sub(
            rf'\bJOIN\s+{table}\b',
            f'JOIN {prefixed_table}',
            modified_sql,
            flags=re.IGNORECASE
        )
    
    return modified_sql


def main():
    if len(sys.argv) < 3:
        print("Использование: python import_to_prefixed_db.py <prefix> <export_file.sql>")
        print("Пример: python import_to_prefixed_db.py student4 export_20240101_120000.sql")
        sys.exit(1)
    
    prefix = sys.argv[1].strip()
    export_file = sys.argv[2].strip()
    
    if not prefix:
        print("✗ Префикс не может быть пустым!")
        sys.exit(1)
    
    if not os.path.exists(export_file):
        print(f"✗ Файл {export_file} не найден!")
        sys.exit(1)
    
    print(f"Импорт данных в БД с префиксом: {prefix}")
    print(f"Файл: {export_file}")
    print("=" * 60)
    
    # Читаем экспортированный SQL
    print("Чтение файла экспорта...")
    try:
        with open(export_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        print("✓ Файл прочитан")
    except Exception as e:
        print(f"✗ Ошибка при чтении файла: {e}")
        sys.exit(1)
    
    # Заменяем имена таблиц на версии с префиксом
    print(f"Добавление префикса '{prefix}_' к именам таблиц...")
    prefixed_sql = replace_table_names_in_sql(sql_content, prefix)
    
    # Подключаемся к удаленной БД
    print("\nПодключение к БД...")
    print("ВАЖНО: Скрипт подключается к БД, указанной в .env файле или переменных окружения!")
    print("       Текущие параметры подключения:")
    try:
        db = Database()
        dbname = db.db_params.get('dbname', 'не указано')
        host = db.db_params.get('host', 'не указано')
        port = db.db_params.get('port', 'не указано')
        print(f"  БД: {dbname}")
        print(f"  Хост: {host}")
        print(f"  Порт: {port}")
        print(f"\n✓ Подключено к БД: {dbname} на {host}:{port}")
        
        # Предупреждение, если подключается к localhost
        if host in ['localhost', '127.0.0.1', 'db']:
            print("\n⚠ ВНИМАНИЕ: Подключение к локальной БД!")
            print("   Для подключения к удаленной БД создайте файл .env с параметрами удаленной БД:")
            print("   DB_NAME=имя_удаленной_базы")
            print("   DB_USER=пользователь_удаленной_бд")
            print("   DB_PASSWORD=пароль_удаленной_бд")
            print("   DB_HOST=хост_удаленной_бд")
            print("   DB_PORT=порт_удаленной_бд")
            print("   Продолжаем с локальной БД...")
    except Exception as e:
        print(f"✗ Ошибка подключения к БД: {e}")
        print("\nСоздайте файл .env или установите переменные окружения:")
        print("  DB_NAME=имя_базы")
        print("  DB_USER=пользователь")
        print("  DB_PASSWORD=пароль")
        print("  DB_HOST=хост")
        print("  DB_PORT=порт")
        sys.exit(1)
    
    # Проверяем существование таблиц с префиксом
    print(f"\nПроверка существования таблиц с префиксом '{prefix}_'...")
    try:
        # Используем параметризованный запрос для безопасности
        like_pattern = f"{prefix}_%"
        result = db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name LIKE %s "
            "ORDER BY table_name",
            (like_pattern,)
        )
        
        # db.execute может вернуть None или список
        if result is None:
            tables = []
        elif isinstance(result, list):
            tables = result
        else:
            tables = []
        
        # Проверяем, что результат не пустой и содержит данные
        if not tables or len(tables) == 0:
            print(f"✗ Таблицы с префиксом '{prefix}_' не найдены!")
            print(f"  Сначала выполните: python create_prefixed_schema.py {prefix}")
            db.close()
            sys.exit(1)
        
        # Проверяем структуру результата
        if len(tables) > 0 and len(tables[0]) > 0:
            print(f"✓ Найдено {len(tables)} таблиц с префиксом")
        else:
            print(f"✗ Таблицы с префиксом '{prefix}_' не найдены!")
            print(f"  Сначала выполните: python create_prefixed_schema.py {prefix}")
            db.close()
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Ошибка при проверке таблиц: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n  Убедитесь, что структура создана: python create_prefixed_schema.py {prefix}")
        db.close()
        sys.exit(1)
    
    # Выполняем SQL команды
    print("\nИмпорт данных...")
    try:
        # Разбиваем на команды (разделитель - точка с запятой)
        # Убираем комментарии и пустые строки
        commands = []
        for cmd in prefixed_sql.split(';'):
            cmd = cmd.strip()
            # Пропускаем комментарии и пустые команды
            if cmd and not cmd.startswith('--') and not cmd.startswith('SET'):
                # Убираем однострочные комментарии
                lines = []
                for line in cmd.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('--'):
                        # Убираем комментарии в конце строки
                        if '--' in line:
                            line = line[:line.index('--')].strip()
                        if line:
                            lines.append(line)
                if lines:
                    commands.append('\n'.join(lines))
        
        executed = 0
        for i, cmd in enumerate(commands, 1):
            if cmd.strip():
                try:
                    db.execute(cmd, fetch=False)
                    executed += 1
                    if i % 10 == 0:
                        print(f"  Обработано команд: {i}/{len(commands)}")
                except Exception as e:
                    # Некоторые ошибки можно игнорировать
                    error_str = str(e).lower()
                    if "already exists" not in error_str and "duplicate" not in error_str:
                        print(f"  Предупреждение при выполнении команды {i}: {e}")
        
        print(f"✓ Импортировано {executed} команд")
        
        # Проверяем количество записей в таблицах
        print("\nПроверка импортированных данных:")
        for table in TABLES:
            prefixed_table = f"{prefix}_{table}"
            try:
                count_result = db.execute_one(f"SELECT COUNT(*) FROM {prefixed_table}")
                if count_result and len(count_result) > 0:
                    count = count_result[0] if count_result[0] is not None else 0
                    print(f"  {prefixed_table}: {count} записей")
                else:
                    print(f"  {prefixed_table}: не удалось получить количество")
            except Exception as e:
                print(f"  {prefixed_table}: ошибка - {e}")
        
    except Exception as e:
        print(f"✗ Ошибка при импорте: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        sys.exit(1)
    
    db.close()
    print("\n" + "=" * 60)
    print("✓ Импорт завершен успешно!")


if __name__ == "__main__":
    main()
