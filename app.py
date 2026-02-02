# -*- coding: utf-8 -*-
import os
import sys

if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, session, redirect, url_for, request, g
from werkzeug.security import check_password_hash, generate_password_hash

from config import SECRET_KEY
from auth_util import get_db, current_user

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


@app.teardown_appcontext
def close_db(e):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_admin_user():
    db = get_db()
    row = db.execute_one("SELECT id_employee FROM employees WHERE login = %s", ("admin",))
    if row:
        return
    pw_hash = generate_password_hash("admin123", method="pbkdf2:sha256")
    db.execute(
        """INSERT INTO employees (login, password_hash, full_name, role, is_active)
           VALUES (%s, %s, %s, %s, TRUE)""",
        ("admin", pw_hash, "Администратор системы (директор)", "admin"),
        fetch=False,
    )


@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user["role"] == "admin":
        return redirect(url_for("admin_routes.admin_main"))
    return redirect(url_for("seller_routes.seller_main"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user():
            return redirect(url_for("index"))
        return __render_login_page()
    login_name = (request.form.get("login") or "").strip()
    password = request.form.get("password") or ""
    if not login_name or not password:
        return __render_login_page(error="Введите логин и пароль")
    db = get_db()
    row = db.execute_one(
        """SELECT id_employee, password_hash, role, store_id FROM employees
           WHERE login = %s AND is_active = TRUE""",
        (login_name,),
    )
    if not row or not check_password_hash(row[1], password):
        return __render_login_page(error="Неверный логин или пароль")
    user_id, _ph, role, store_id = row
    session.clear()
    session["user_id"] = user_id
    session["role"] = role
    session["store_id"] = store_id
    session.permanent = True
    if role == "admin":
        return redirect(url_for("admin_routes.admin_main"))
    db = get_db()
    existing = db.execute_one(
        "SELECT id_shift FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL",
        (user_id, store_id),
    )
    if not existing:
        db.execute(
            "INSERT INTO shifts (employee_id, store_id, shift_start, status) VALUES (%s, %s, CURRENT_TIMESTAMP, 'open')",
            (user_id, store_id),
            fetch=False,
        )
    return redirect(url_for("seller_routes.seller_main"))


def __render_login_page(error=None):
    from flask import render_template

    return render_template("login.html", error=error)


@app.route("/start")
def start():
    session.clear()
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    role = session.get("role")
    store_id = session.get("store_id")
    session.clear()
    if role == "seller" and user_id and store_id:
        db = get_db()
        row = db.execute_one(
            "SELECT id_shift FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL ORDER BY shift_start DESC LIMIT 1",
            (user_id, store_id),
        )
        if row:
            db.execute(
                "UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s",
                (row[0],),
                fetch=False,
            )
            return redirect(url_for("seller_routes.shift_report", shift_id=row[0]))
    return redirect(url_for("login"))


@app.route("/api/check-db")
def check_db():
    from flask import jsonify
    try:
        db = get_db()
        dbname = db.db_params.get("dbname", "?")
        host = db.db_params.get("host", "?")
        row = db.execute_one(
            "SELECT id_employee, is_active FROM employees WHERE login = %s",
            ("admin",),
        )
        if row:
            return jsonify({
                "ok": True,
                "database": dbname,
                "host": host,
                "admin_exists": True,
                "admin_active": bool(row[1]),
                "message": "Подключение к БД успешно. Пользователь admin есть в таблице employees.",
            })
        return jsonify({
            "ok": True,
            "database": dbname,
            "host": host,
            "admin_exists": False,
            "message": "Подключение к БД успешно, но пользователя admin нет в таблице employees.",
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "message": "Ошибка подключения к БД. Проверьте параметры в .env (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).",
        }), 500


@app.route("/api/fix-admin-password")
def fix_admin_password():
    from flask import jsonify
    try:
        db = get_db()
        pw_hash = generate_password_hash("admin123", method="pbkdf2:sha256")
        db.execute(
            "UPDATE employees SET password_hash = %s WHERE login = 'admin'",
            (pw_hash,),
            fetch=False,
        )
        return jsonify({
            "ok": True,
            "message": "Пароль admin обновлён. Войдите: логин admin, пароль admin123.",
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


from routes import admin_routes, seller_routes, api_routes

app.register_blueprint(admin_routes.bp, url_prefix="/admin")
app.register_blueprint(seller_routes.bp, url_prefix="/seller")
app.register_blueprint(api_routes.bp, url_prefix="/api")


@app.before_request
def ensure_admin_user():
    if request.endpoint and request.endpoint != "static":
        try:
            init_admin_user()
        except Exception:
            pass


if __name__ == "__main__":
    import webbrowser
    import threading
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:5000/start")
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
