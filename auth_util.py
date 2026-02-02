# -*- coding: utf-8 -*-
from functools import wraps
from flask import g, session, redirect, url_for
from database import Database


def get_db():
    if "db" not in g:
        g.db = Database()
    return g.db


def current_user():
    if not session.get("user_id"):
        return None
    db = get_db()
    row = db.execute_one(
        """SELECT e.id_employee, e.login, e.full_name, e.role, e.store_id, s.name AS store_name
           FROM employees e
           LEFT JOIN stores s ON s.id_store = e.store_id
           WHERE e.id_employee = %s AND e.is_active = TRUE""",
        (session["user_id"],),
    )
    if not row:
        return None
    return {
        "id": row[0],
        "login": row[1],
        "full_name": row[2],
        "role": row[3],
        "store_id": row[4],
        "store_name": row[5],
    }


def require_admin(f):
    @wraps(f)
    def inner(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if user["role"] != "admin":
            return redirect(url_for("seller_routes.seller_main"))
        return f(*args, **kwargs)

    return inner


def require_seller(f):
    @wraps(f)
    def inner(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("login"))
        if user["role"] != "seller":
            return redirect(url_for("admin_routes.admin_main"))
        return f(*args, **kwargs)

    return inner
