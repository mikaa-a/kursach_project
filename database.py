# -*- coding: utf-8 -*-
import os
import sys
import psycopg2
from contextlib import contextmanager


class Database:
    def __init__(self, dbname: str = "kursach1",
                 user: str = "postgres",
                 password: str = "1234",
                 host: str = "localhost",
                 port: str = "5432"):
        if sys.platform == "win32":
            os.environ["PYTHONUTF8"] = "1"

        dbname = os.environ.get("DB_NAME", dbname)
        user = os.environ.get("DB_USER", user)
        password = os.environ.get("DB_PASSWORD", password)
        host = os.environ.get("DB_HOST", host)
        port = os.environ.get("DB_PORT", port)

        self.db_params = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'client_encoding': 'UTF8'
        }

        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.db_params)
            self.connection.autocommit = False
        except Exception as e:
            raise RuntimeError(f"Ошибка подключения к БД: {e}") from e

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_cursor(self):
        try:
            if self.connection is None or self.connection.closed:
                self.connect()
            return self.connection.cursor()
        except Exception:
            self.connect()
            return self.connection.cursor()

    @contextmanager
    def cursor(self):
        cur = self.get_cursor()
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()

    def execute(self, query: str, params=None, fetch=True):
        with self.cursor() as cur:
            cur.execute(query, params or ())
            if fetch and cur.description:
                return cur.fetchall()
            return None

    def execute_one(self, query: str, params=None):
        with self.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone() if cur.description else None
