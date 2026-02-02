# -*- coding: utf-8 -*-
from datetime import datetime


from flask import Blueprint, request, jsonify
from auth_util import current_user, get_db
from config import SHIFT_DURATION_HOURS, SHIFT_DURATION_SECONDS, LOW_STOCK_THRESHOLD, MONEY_DECIMALS, PERCENT_DECIMALS

def _shift_duration_seconds():
    return SHIFT_DURATION_SECONDS if SHIFT_DURATION_SECONDS is not None else SHIFT_DURATION_HOURS * 3600

bp = Blueprint("api_routes", __name__)


def _round_money(v):
    return round(float(v), MONEY_DECIMALS)


def _round_percent(v):
    return round(float(v), PERCENT_DECIMALS)


def _require_admin():
    u = current_user()
    if not u or u["role"] != "admin":
        return None
    return u


def _require_seller():
    u = current_user()
    if not u or u["role"] != "seller":
        return None
    return u


def _validate_phone(phone_str):
    s = (phone_str or "").strip()
    if not s:
        return None
    digits = "".join(c for c in s if c.isdigit())
    if digits.startswith("8") or digits.startswith("7"):
        digits = digits[1:]
    if len(digits) < 10:
        return "Введите корректный номер телефона (не менее 10 цифр)"
    return None


@bp.route("/stores", methods=["GET"])
def list_stores():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    rows = db.execute(
        "SELECT id_store, name, address, phone FROM stores WHERE is_active = TRUE ORDER BY name"
    ) or []
    return jsonify([{"id": r[0], "name": r[1], "address": r[2] or "", "phone": r[3] or ""} for r in rows])


@bp.route("/stores/<int:store_id>", methods=["GET"])
def get_store(store_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    row = db.execute_one("SELECT id_store, name, address, phone FROM stores WHERE id_store = %s AND is_active = TRUE", (store_id,))
    if not row:
        return jsonify({"error": "Магазин не найден"}), 404
    return jsonify({"id": row[0], "name": row[1], "address": row[2] or "", "phone": row[3] or ""})


@bp.route("/stores", methods=["POST"])
def create_store():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    err = _validate_phone(data.get("phone"))
    if err:
        return jsonify({"error": err}), 400
    db = get_db()
    db.execute(
        "INSERT INTO stores (name, address, phone, is_active) VALUES (%s, %s, %s, TRUE)",
        (name, (data.get("address") or "").strip(), (data.get("phone") or "").strip()),
        fetch=False,
    )
    row = db.execute_one("SELECT id_store FROM stores ORDER BY id_store DESC LIMIT 1")
    return jsonify({"id": row[0], "name": name})


@bp.route("/stores/<int:store_id>", methods=["PUT"])
def update_store(store_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    err = _validate_phone(data.get("phone"))
    if err:
        return jsonify({"error": err}), 400
    db = get_db()
    db.execute(
        "UPDATE stores SET name = %s, address = %s, phone = %s WHERE id_store = %s",
        (name, (data.get("address") or "").strip(), (data.get("phone") or "").strip(), store_id),
        fetch=False,
    )
    return jsonify({"ok": True})


@bp.route("/stores/<int:store_id>", methods=["DELETE"])
def delete_store(store_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    db.execute("UPDATE stores SET is_active = FALSE WHERE id_store = %s", (store_id,), fetch=False)
    return jsonify({"ok": True})


@bp.route("/stores/<int:store_id>/stock", methods=["GET"])
def get_store_stock(store_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    rows = db.execute(
        """SELECT p.id_product, p.name, sps.quantity FROM store_product_stock sps
           JOIN products p ON p.id_product = sps.product_id WHERE sps.store_id = %s ORDER BY p.name""",
        (store_id,),
    ) or []
    return jsonify([{"product_id": r[0], "product_name": r[1], "quantity": r[2]} for r in rows])


@bp.route("/warehouses", methods=["GET"])
def list_warehouses():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    rows = db.execute(
        "SELECT id_warehouse, name, address, phone, area FROM warehouses WHERE is_active = TRUE ORDER BY name"
    ) or []
    return jsonify([{"id": r[0], "name": r[1], "address": r[2] or "", "phone": r[3] or "", "area": float(r[4] or 0)} for r in rows])


@bp.route("/warehouses/<int:wh_id>", methods=["GET"])
def get_warehouse(wh_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    row = db.execute_one("SELECT id_warehouse, name, address, phone, area FROM warehouses WHERE id_warehouse = %s AND is_active = TRUE", (wh_id,))
    if not row:
        return jsonify({"error": "Склад не найден"}), 404
    return jsonify({"id": row[0], "name": row[1], "address": row[2] or "", "phone": row[3] or "", "area": float(row[4] or 0)})


@bp.route("/warehouses", methods=["POST"])
def create_warehouse():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    err = _validate_phone(data.get("phone"))
    if err:
        return jsonify({"error": err}), 400
    db = get_db()
    db.execute(
        "INSERT INTO warehouses (name, address, phone, area, is_active) VALUES (%s, %s, %s, %s, TRUE)",
        (name, (data.get("address") or "").strip(), (data.get("phone") or "").strip(), float(data.get("area") or 0)),
        fetch=False,
    )
    row = db.execute_one("SELECT id_warehouse FROM warehouses ORDER BY id_warehouse DESC LIMIT 1")
    return jsonify({"id": row[0], "name": name})


@bp.route("/warehouses/<int:wh_id>", methods=["PUT"])
def update_warehouse(wh_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    err = _validate_phone(data.get("phone"))
    if err:
        return jsonify({"error": err}), 400
    db = get_db()
    db.execute(
        "UPDATE warehouses SET name = %s, address = %s, phone = %s, area = %s WHERE id_warehouse = %s",
        (name, (data.get("address") or "").strip(), (data.get("phone") or "").strip(), float(data.get("area") or 0), wh_id),
        fetch=False,
    )
    return jsonify({"ok": True})


@bp.route("/warehouses/<int:wh_id>", methods=["DELETE"])
def delete_warehouse(wh_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    db.execute("UPDATE warehouses SET is_active = FALSE WHERE id_warehouse = %s", (wh_id,), fetch=False)
    return jsonify({"ok": True})


@bp.route("/warehouses/<int:wh_id>/stock", methods=["GET"])
def get_warehouse_stock(wh_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    rows = db.execute(
        """SELECT p.id_product, p.name, wps.quantity FROM warehouse_product_stock wps
           JOIN products p ON p.id_product = wps.product_id WHERE wps.warehouse_id = %s ORDER BY p.name""",
        (wh_id,),
    ) or []
    return jsonify([{"product_id": r[0], "product_name": r[1], "quantity": r[2]} for r in rows])


@bp.route("/products", methods=["GET"])
def list_products():
    u = current_user()
    if not u:
        return jsonify({"error": "Авторизуйтесь"}), 403
    db = get_db()
    try:
        rows = db.execute(
            """SELECT p.id_product, p.name, p.unit, p.purchase_price, p.retail_price, p.min_stock_level
               FROM products p WHERE p.is_active = TRUE ORDER BY p.name"""
        ) or []
    except Exception:
        rows = db.execute(
            "SELECT id_product, name, unit, purchase_price, retail_price, 5 FROM products WHERE is_active = TRUE ORDER BY name"
        ) or []
    return jsonify([
        {"id": r[0], "name": r[1], "unit": r[2], "purchase_price": _round_money(r[3]), "retail_price": _round_money(r[4]), "min_stock": r[5]}
        for r in rows
    ])


@bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    row = db.execute_one(
        "SELECT id_product, name, unit, purchase_price, retail_price, min_stock_level, category_id FROM products WHERE id_product = %s AND is_active = TRUE",
        (product_id,),
    )
    if not row:
        return jsonify({"error": "Товар не найден"}), 404
    return jsonify({
        "id": row[0], "name": row[1], "unit": row[2],
        "purchase_price": _round_money(row[3]), "retail_price": _round_money(row[4]),
        "min_stock": row[5], "category_id": row[6],
    })


@bp.route("/products", methods=["POST"])
def create_product():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    db = get_db()
    art = (data.get("article") or "").strip() or ("ART-%s" % datetime.now().strftime("%Y%m%d%H%M"))
    db.execute(
        """INSERT INTO products (article, name, category_id, unit, purchase_price, retail_price, min_stock_level, is_active)
           VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)""",
        (art, name, data.get("category_id") or None, data.get("unit") or "шт",
         float(data.get("purchase_price") or 0), float(data.get("retail_price") or 0), int(data.get("min_stock") or 5)),
        fetch=False,
    )
    row = db.execute_one("SELECT id_product FROM products ORDER BY id_product DESC LIMIT 1")
    return jsonify({"id": row[0], "name": name})


@bp.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    db = get_db()
    db.execute(
        """UPDATE products SET name = %s, category_id = %s, unit = %s, purchase_price = %s, retail_price = %s, min_stock_level = %s WHERE id_product = %s""",
        (name, data.get("category_id") or None, data.get("unit") or "шт",
         float(data.get("purchase_price") or 0), float(data.get("retail_price") or 0), int(data.get("min_stock") or 5), product_id),
        fetch=False,
    )
    return jsonify({"ok": True})


@bp.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    db.execute("UPDATE products SET is_active = FALSE WHERE id_product = %s", (product_id,), fetch=False)
    return jsonify({"ok": True})


@bp.route("/categories", methods=["GET"])
def list_categories():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    try:
        rows = db.execute("SELECT id, name FROM categories ORDER BY name") or []
        return jsonify([{"id": r[0], "name": r[1]} for r in rows])
    except Exception:
        try:
            rows = db.execute("SELECT id_category, name FROM categories ORDER BY name") or []
            return jsonify([{"id": r[0], "name": r[1]} for r in rows])
        except Exception:
            return jsonify([])


@bp.route("/categories", methods=["POST"])
def create_category():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите название"}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO categories (name) VALUES (%s)", (name,), fetch=False)
    except Exception:
        db.execute("INSERT INTO categories (name) VALUES (%s)", (name,), fetch=False)
    row = db.execute_one("SELECT id FROM categories ORDER BY id DESC LIMIT 1")
    if not row:
        row = db.execute_one("SELECT id_category FROM categories ORDER BY id_category DESC LIMIT 1")
    return jsonify({"id": row[0], "name": name})


@bp.route("/employees", methods=["GET"])
def list_employees():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    rows = db.execute(
        """SELECT e.id_employee, e.login, e.full_name, e.role, e.store_id, s.name AS store_name, e.is_active
           FROM employees e LEFT JOIN stores s ON s.id_store = e.store_id
           WHERE e.role IN ('admin', 'seller') ORDER BY e.role, e.full_name"""
    ) or []
    return jsonify([
        {"id": r[0], "login": r[1], "full_name": r[2], "role": r[3], "store_id": r[4], "store_name": r[5] or "", "active": r[6]}
        for r in rows
    ])


@bp.route("/employees/<int:emp_id>", methods=["GET"])
def get_employee(emp_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    row = db.execute_one(
        "SELECT id_employee, login, full_name, role, store_id, is_active FROM employees WHERE id_employee = %s",
        (emp_id,),
    )
    if not row:
        return jsonify({"error": "Сотрудник не найден"}), 404
    return jsonify({"id": row[0], "login": row[1], "full_name": row[2], "role": row[3], "store_id": row[4], "active": row[5]})


@bp.route("/employees", methods=["POST"])
def create_employee():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    login = (data.get("login") or "").strip()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    if not login or not password or not full_name:
        return jsonify({"error": "Укажите логин, пароль и ФИО"}), 400
    from werkzeug.security import generate_password_hash
    db = get_db()
    existing = db.execute_one("SELECT id_employee FROM employees WHERE login = %s", (login,))
    if existing:
        return jsonify({"error": "Логин уже занят"}), 400
    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
    db.execute(
        "INSERT INTO employees (login, password_hash, full_name, role, store_id, is_active) VALUES (%s, %s, %s, %s, %s, TRUE)",
        (login, pw_hash, full_name, data.get("role") or "seller", data.get("store_id") or None),
        fetch=False,
    )
    row = db.execute_one("SELECT id_employee FROM employees ORDER BY id_employee DESC LIMIT 1")
    return jsonify({"id": row[0], "login": login})


@bp.route("/employees/<int:emp_id>", methods=["PUT"])
def update_employee(emp_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    full_name = (data.get("full_name") or "").strip()
    if not full_name:
        return jsonify({"error": "Укажите ФИО"}), 400
    db = get_db()
    db.execute(
        "UPDATE employees SET full_name = %s, role = %s, store_id = %s, is_active = %s WHERE id_employee = %s",
        (full_name, data.get("role") or "seller", data.get("store_id") or None, bool(data.get("active", True)), emp_id),
        fetch=False,
    )
    return jsonify({"ok": True})


@bp.route("/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    db.execute("UPDATE employees SET is_active = FALSE WHERE id_employee = %s", (emp_id,), fetch=False)
    return jsonify({"ok": True})


@bp.route("/shifts/current", methods=["GET"])
def current_shift():
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    db = get_db()
    row = db.execute_one(
        """SELECT id_shift, shift_start,
           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - shift_start))::BIGINT AS elapsed_sec
           FROM shifts
           WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL
           ORDER BY shift_start DESC LIMIT 1""",
        (u["id"], u["store_id"]),
    )
    if not row:
        return jsonify({"shift": None})
    id_shift, shift_start, elapsed_sec = row[0], row[1], (row[2] or 0)
    limit_sec = _shift_duration_seconds()
    if elapsed_sec >= limit_sec:
        db.execute(
            "UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s",
            (id_shift,),
            fetch=False,
        )
        return jsonify({"shift": None, "closed": True, "shift_id": id_shift})
    hours = int(elapsed_sec // 3600)
    minutes = int((elapsed_sec % 3600) // 60)
    return jsonify({
        "shift": {"id": id_shift, "opened_at": row[1].isoformat(), "work_hours": hours, "work_minutes": minutes},
    })


@bp.route("/shifts/open", methods=["POST"])
def open_shift():
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    db = get_db()
    existing = db.execute_one(
        "SELECT id_shift FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL",
        (u["id"], u["store_id"]),
    )
    if existing:
        return jsonify({"shift_id": existing[0], "already_open": True})
    db.execute(
        "INSERT INTO shifts (employee_id, store_id, shift_start, status) VALUES (%s, %s, CURRENT_TIMESTAMP, 'open')",
        (u["id"], u["store_id"]),
        fetch=False,
    )
    row = db.execute_one("SELECT id_shift FROM shifts ORDER BY id_shift DESC LIMIT 1")
    return jsonify({"shift_id": row[0]})


@bp.route("/shifts/<int:shift_id>/close", methods=["POST"])
def close_shift(shift_id):
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    db = get_db()
    row = db.execute_one("SELECT employee_id, store_id FROM shifts WHERE id_shift = %s AND shift_end IS NULL", (shift_id,))
    if not row or row[0] != u["id"] or row[1] != u["store_id"]:
        return jsonify({"error": "Смена не найдена или уже закрыта"}), 400
    db.execute(
        "UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s",
        (shift_id,),
        fetch=False,
    )
    return jsonify({"ok": True})


@bp.route("/shifts/<int:shift_id>/report", methods=["GET"])
def shift_report_api(shift_id):
    db = get_db()
    shift_row = db.execute_one(
        """SELECT s.id_shift, s.shift_start, s.shift_end, s.employee_id, s.store_id,
                  e.full_name, st.name AS store_name
           FROM shifts s
           JOIN employees e ON e.id_employee = s.employee_id
           LEFT JOIN stores st ON st.id_store = s.store_id
           WHERE s.id_shift = %s""",
        (shift_id,),
    )
    if not shift_row:
        return jsonify({"error": "Смена не найдена"}), 404
    sid, start_ts, end_ts, emp_id, store_id, seller_name, store_name = shift_row
    start_str = start_ts.strftime("%H:%M") if start_ts else ""
    end_str = end_ts.strftime("%H:%M") if end_ts else ""
    date_str = start_ts.strftime("%d.%m.%Y") if start_ts else ""
    sales_rows = db.execute(
        """SELECT id_operation, created_at, total_revenue, total_cost, total_profit, operation_type, original_operation_id
           FROM operations
           WHERE shift_id = %s AND (operation_type = 'sale' OR operation_type = 'return')
           ORDER BY created_at""",
        (shift_id,),
    ) or []
    totals_sale = db.execute_one(
        """SELECT COALESCE(SUM(total_revenue), 0), COALESCE(SUM(total_cost), 0), COALESCE(SUM(total_profit), 0)
           FROM operations WHERE shift_id = %s AND operation_type = 'sale'""",
        (shift_id,),
    )
    totals_ret = db.execute_one(
        """SELECT COALESCE(SUM(total_revenue), 0), COALESCE(SUM(total_cost), 0), COALESCE(SUM(total_profit), 0)
           FROM operations WHERE shift_id = %s AND operation_type = 'return'""",
        (shift_id,),
    )
    rev_s = (totals_sale[0] or 0) if totals_sale else 0
    cost_s = (totals_sale[1] or 0) if totals_sale else 0
    profit_s = (totals_sale[2] or 0) if totals_sale else 0
    rev_r = (totals_ret[0] or 0) if totals_ret else 0
    cost_r = (totals_ret[1] or 0) if totals_ret else 0
    profit_r = (totals_ret[2] or 0) if totals_ret else 0
    rev = rev_s - rev_r
    cost = cost_s - cost_r
    profit = profit_s - profit_r
    return jsonify({
        "shift_id": sid,
        "seller_name": seller_name or "",
        "store_name": store_name or "",
        "date": date_str,
        "shift_start": start_str,
        "shift_end": end_str,
        "total_revenue": _round_money(rev),
        "total_cost": _round_money(cost),
        "total_profit": _round_money(profit),
        "sales": [
            {"id": r[0], "created_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
             "total_revenue": _round_money(r[2]), "total_cost": _round_money(r[3]), "total_profit": _round_money(r[4]),
             "operation_type": r[5] if len(r) > 5 else "sale", "original_operation_id": r[6] if len(r) > 6 else None}
            for r in sales_rows
        ],
    })


@bp.route("/sales", methods=["POST"])
def create_sale():
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    data = request.get_json() or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "Добавьте товары в чек"}), 400
    db = get_db()
    shift_row = db.execute_one(
        """SELECT id_shift,
           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - shift_start))::BIGINT AS elapsed_sec
           FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL ORDER BY shift_start DESC LIMIT 1""",
        (u["id"], u["store_id"]),
    )
    if not shift_row:
        return jsonify({"error": "Сначала откройте смену"}), 400
    shift_id, elapsed_sec = shift_row[0], (shift_row[1] or 0)
    if elapsed_sec >= _shift_duration_seconds():
        db.execute("UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s", (shift_id,), fetch=False)
        return jsonify({"error": "Смена закрыта по истечении заданного времени. Откройте новую смену."}), 400
    store_id = u["store_id"]
    total_revenue = total_cost = total_profit = 0
    line_items = []
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("quantity") or 0)
        if not pid or qty <= 0:
            continue
        prod = db.execute_one(
            "SELECT retail_price, purchase_price FROM products WHERE id_product = %s",
            (pid,),
        )
        if not prod:
            continue
        price, cost_unit = float(prod[0]), float(prod[1])
        revenue = price * qty
        cost = cost_unit * qty
        profit = revenue - cost
        total_revenue += revenue
        total_cost += cost
        total_profit += profit
        line_items.append({"product_id": pid, "quantity": qty, "price": price, "cost": cost_unit, "revenue": revenue, "profit": profit})
    if not line_items:
        return jsonify({"error": "Добавьте товары в чек"}), 400
    for it in line_items:
        row = db.execute_one(
            "SELECT quantity FROM store_product_stock WHERE store_id = %s AND product_id = %s",
            (store_id, it["product_id"]),
        )
        avail = (row[0] or 0) if row else 0
        if avail < it["quantity"]:
            return jsonify({"error": "Недостаточно товара на точке (остаток %s)" % avail}), 400
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO operations (operation_type, shift_id, employee_id, store_id, operation_date, total_revenue, total_cost, total_profit, created_at)
               VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id_operation""",
            ("sale", shift_id, u["id"], store_id, _round_money(total_revenue), _round_money(total_cost), _round_money(total_profit)),
        )
        check_id = cur.fetchone()[0]
        for it in line_items:
            cur.execute(
                """INSERT INTO operation_items (operation_id, product_id, quantity, unit_price, purchase_price, total_price, cost, profit)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (check_id, it["product_id"], it["quantity"], it["price"], it["cost"], it["revenue"], it["cost"], it["profit"]),
            )
            cur.execute(
                "UPDATE store_product_stock SET quantity = quantity - %s, update_date = CURRENT_TIMESTAMP WHERE store_id = %s AND product_id = %s",
                (it["quantity"], store_id, it["product_id"]),
            )
        for it in line_items:
            cur.execute(
                "SELECT quantity FROM store_product_stock WHERE store_id = %s AND product_id = %s",
                (store_id, it["product_id"]),
            )
            r = cur.fetchone()
            q = (r[0] or 0) if r else 0
            if q < LOW_STOCK_THRESHOLD:
                cur.execute(
                    "INSERT INTO notifications (product_id, store_id, warehouse_id, current_quantity, threshold, status, created_at) VALUES (%s, %s, NULL, %s, %s, 'unread', CURRENT_TIMESTAMP)",
                    (it["product_id"], store_id, q, LOW_STOCK_THRESHOLD),
                )
    return jsonify({"ok": True, "check_id": check_id, "total": _round_money(total_revenue)})


@bp.route("/sales/by-store-date", methods=["GET"])
def sales_by_store_date():
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    date_str = request.args.get("date") or ""
    if not date_str:
        return jsonify([])
    db = get_db()
    rows = db.execute(
        """WITH sale_products AS (
             SELECT o.id_operation, oi.product_id, oi.quantity AS sold
             FROM operations o
             JOIN operation_items oi ON oi.operation_id = o.id_operation
             WHERE o.store_id = %s AND o.operation_type = 'sale' AND (o.created_at::date) = %s
           ),
           returned_by_sale_product AS (
             SELECT r.original_operation_id AS id_operation, oi.product_id, SUM(oi.quantity) AS returned
             FROM operations r
             JOIN operation_items oi ON oi.operation_id = r.id_operation
             WHERE r.operation_type = 'return' AND r.original_operation_id IS NOT NULL
             GROUP BY r.original_operation_id, oi.product_id
           ),
           not_fully_returned AS (
             SELECT DISTINCT s.id_operation
             FROM sale_products s
             LEFT JOIN returned_by_sale_product r ON r.id_operation = s.id_operation AND r.product_id = s.product_id
             WHERE s.sold > COALESCE(r.returned, 0)
           )
           SELECT o.id_operation, o.created_at, o.total_revenue
           FROM operations o
           WHERE o.store_id = %s AND o.operation_type = 'sale' AND (o.created_at::date) = %s
             AND o.id_operation IN (SELECT id_operation FROM not_fully_returned)
           ORDER BY o.created_at""",
        (u["store_id"], date_str, u["store_id"], date_str),
    ) or []
    return jsonify([
        {"id": r[0], "created_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]), "total_revenue": _round_money(r[2])}
        for r in rows
    ])


@bp.route("/operations/<int:op_id>/items", methods=["GET"])
def operation_items(op_id):
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    db = get_db()
    op = db.execute_one(
        "SELECT id_operation, store_id, operation_type FROM operations WHERE id_operation = %s",
        (op_id,),
    )
    if not op or op[1] != u["store_id"] or op[2] != "sale":
        return jsonify({"error": "Продажа не найдена или доступ запрещён"}), 404
    rows = db.execute(
        """SELECT oi.product_id, p.name, oi.quantity, oi.unit_price, oi.total_price
           FROM operation_items oi
           JOIN products p ON p.id_product = oi.product_id
           WHERE oi.operation_id = %s ORDER BY oi.product_id""",
        (op_id,),
    ) or []
    returned = {}
    for r in db.execute(
        """SELECT oi.product_id, SUM(oi.quantity)
           FROM operations o
           JOIN operation_items oi ON oi.operation_id = o.id_operation
           WHERE o.operation_type = 'return' AND o.original_operation_id = %s
           GROUP BY oi.product_id""",
        (op_id,),
    ) or []:
        returned[r[0]] = r[1]
    out = []
    for r in rows:
        pid, name, sold, uprice, tprice = r[0], r[1], r[2], r[3], r[4]
        already = returned.get(pid, 0)
        remaining = max(0, sold - already)
        out.append({
            "product_id": pid, "product_name": name,
            "quantity": sold, "already_returned": already, "remaining": remaining,
            "unit_price": _round_money(uprice), "total_price": _round_money(tprice),
        })
    return jsonify(out)


@bp.route("/returns", methods=["POST"])
def create_return():
    u = _require_seller()
    if not u:
        return jsonify({"error": "Доступ только для продавца"}), 403
    data = request.get_json() or {}
    original_id = data.get("original_operation_id")
    items = data.get("items") or []
    if not original_id or not items:
        return jsonify({"error": "Укажите продажу и товары для возврата"}), 400
    db = get_db()
    sale_row = db.execute_one(
        "SELECT id_operation, store_id, operation_type FROM operations WHERE id_operation = %s",
        (original_id,),
    )
    if not sale_row or sale_row[1] != u["store_id"] or sale_row[2] != "sale":
        return jsonify({"error": "Продажа не найдена или доступ запрещён"}), 400
    sold = {}
    for row in db.execute(
        "SELECT product_id, quantity FROM operation_items WHERE operation_id = %s",
        (original_id,),
    ) or []:
        sold[row[0]] = row[1]
    returned = {}
    for row in db.execute(
        """SELECT oi.product_id, SUM(oi.quantity)
           FROM operations o JOIN operation_items oi ON oi.operation_id = o.id_operation
           WHERE o.operation_type = 'return' AND o.original_operation_id = %s
           GROUP BY oi.product_id""",
        (original_id,),
    ) or []:
        returned[row[0]] = row[1]
    return_items = []
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("quantity") or 0)
        if not pid or qty <= 0:
            continue
        sold_qty = sold.get(pid, 0)
        already = returned.get(pid, 0)
        remaining = max(0, sold_qty - already)
        if pid not in sold or qty > remaining:
            return jsonify({"error": "Количество возврата по товару не может превышать оставшееся к возврату (продано минус уже возвращено)"}), 400
        return_items.append({"product_id": pid, "quantity": qty})
    if not return_items:
        return jsonify({"error": "Добавьте товары для возврата"}), 400
    shift_row = db.execute_one(
        """SELECT id_shift,
           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - shift_start))::BIGINT AS elapsed_sec
           FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL ORDER BY shift_start DESC LIMIT 1""",
        (u["id"], u["store_id"]),
    )
    if not shift_row:
        return jsonify({"error": "Сначала откройте смену"}), 400
    shift_id, elapsed_sec = shift_row[0], (shift_row[1] or 0)
    if elapsed_sec >= _shift_duration_seconds():
        db.execute("UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s", (shift_id,), fetch=False)
        return jsonify({"error": "Смена закрыта по времени. Откройте новую смену."}), 400
    store_id = u["store_id"]
    total_revenue = total_cost = total_profit = 0
    line_items = []
    for it in return_items:
        pid, qty = it["product_id"], it["quantity"]
        prod = db.execute_one(
            "SELECT retail_price, purchase_price FROM products WHERE id_product = %s",
            (pid,),
        )
        if not prod:
            continue
        price, cost_unit = float(prod[0]), float(prod[1])
        revenue = price * qty
        cost = cost_unit * qty
        profit = revenue - cost
        total_revenue += revenue
        total_cost += cost
        total_profit += profit
        line_items.append({"product_id": pid, "quantity": qty, "price": price, "cost": cost_unit, "revenue": revenue, "profit": profit})
    if not line_items:
        return jsonify({"error": "Добавьте товары для возврата"}), 400
    try:
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO operations (operation_type, shift_id, employee_id, store_id, operation_date, total_revenue, total_cost, total_profit, created_at, original_operation_id)
                   VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, CURRENT_TIMESTAMP, %s) RETURNING id_operation""",
                ("return", shift_id, u["id"], store_id, _round_money(total_revenue), _round_money(total_cost), _round_money(total_profit), original_id),
            )
            return_id = cur.fetchone()[0]
            for it in line_items:
                cur.execute(
                    """INSERT INTO operation_items (operation_id, product_id, quantity, unit_price, purchase_price, total_price, cost, profit)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (return_id, it["product_id"], it["quantity"], it["price"], it["cost"], it["revenue"], it["cost"], it["profit"]),
                )
                cur.execute(
                    """INSERT INTO store_product_stock (store_id, product_id, quantity, update_date) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                       ON CONFLICT (store_id, product_id) DO UPDATE SET quantity = store_product_stock.quantity + EXCLUDED.quantity, update_date = CURRENT_TIMESTAMP""",
                    (store_id, it["product_id"], it["quantity"]),
                )
    except Exception as e:
        err = str(e)
        if "original_operation_id" in err and ("column" in err.lower() or "does not exist" in err.lower()):
            return jsonify({"error": "В базе нет колонки для возвратов. Выполните скрипт init_db.sql заново (блок с original_operation_id)."}), 500
        return jsonify({"error": "Ошибка при сохранении возврата: " + err}), 500
    return jsonify({"ok": True, "return_id": return_id, "total": _round_money(total_revenue)})


@bp.route("/receipt", methods=["POST"])
def create_receipt():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    store_id = data.get("store_id")
    warehouse_id = data.get("warehouse_id")
    product_id = data.get("product_id")
    quantity = int(data.get("quantity") or 0)
    if (store_id is None and warehouse_id is None) or not product_id or quantity <= 0:
        return jsonify({"error": "Укажите точку, товар и количество"}), 400
    db = get_db()
    if store_id:
        cur = db.get_cursor()
        try:
            cur.execute(
                "INSERT INTO store_product_stock (store_id, product_id, quantity, update_date) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (store_id, product_id) DO UPDATE SET quantity = store_product_stock.quantity + EXCLUDED.quantity, update_date = CURRENT_TIMESTAMP",
                (store_id, product_id, quantity),
            )
            db.connection.commit()
        except Exception as e:
            db.connection.rollback()
            return jsonify({"error": str(e)}), 400
        finally:
            cur.close()
    else:
        cur = db.get_cursor()
        try:
            cur.execute(
                "INSERT INTO warehouse_product_stock (warehouse_id, product_id, quantity, update_date) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (warehouse_id, product_id) DO UPDATE SET quantity = warehouse_product_stock.quantity + EXCLUDED.quantity, update_date = CURRENT_TIMESTAMP",
                (warehouse_id, product_id, quantity),
            )
            db.connection.commit()
        except Exception as e:
            db.connection.rollback()
            return jsonify({"error": str(e)}), 400
        finally:
            cur.close()
    return jsonify({"ok": True})


@bp.route("/distribution", methods=["POST"])
def create_distribution():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    data = request.get_json() or {}
    from_wh = data.get("from_warehouse_id")
    to_store = data.get("to_store_id")
    to_wh = data.get("to_warehouse_id")
    product_id = data.get("product_id")
    quantity = int(data.get("quantity") or 0)
    if not from_wh or not product_id or quantity <= 0:
        return jsonify({"error": "Укажите склад-источник, товар и количество"}), 400
    if (to_store is None or to_store == "") and (to_wh is None or to_wh == ""):
        return jsonify({"error": "Укажите пункт назначения (магазин или склад)"}), 400
    db = get_db()
    row = db.execute_one(
        "SELECT quantity FROM warehouse_product_stock WHERE warehouse_id = %s AND product_id = %s",
        (from_wh, product_id),
    )
    avail = (row[0] or 0) if row else 0
    if avail < quantity:
        return jsonify({"error": "Недостаточно товара на складе"}), 400
    with db.cursor() as cur:
        cur.execute("UPDATE warehouse_product_stock SET quantity = quantity - %s, update_date = CURRENT_TIMESTAMP WHERE warehouse_id = %s AND product_id = %s", (quantity, from_wh, product_id))
        if to_store:
            cur.execute(
                "INSERT INTO store_product_stock (store_id, product_id, quantity, update_date) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (store_id, product_id) DO UPDATE SET quantity = store_product_stock.quantity + EXCLUDED.quantity, update_date = CURRENT_TIMESTAMP",
                (to_store, product_id, quantity),
            )
        else:
            cur.execute(
                "INSERT INTO warehouse_product_stock (warehouse_id, product_id, quantity, update_date) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (warehouse_id, product_id) DO UPDATE SET quantity = warehouse_product_stock.quantity + EXCLUDED.quantity, update_date = CURRENT_TIMESTAMP",
                (to_wh, product_id, quantity),
            )
    return jsonify({"ok": True})


@bp.route("/reports/sales", methods=["GET"])
def report_sales():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    date_from = request.args.get("date_from") or ""
    date_to = request.args.get("date_to") or ""
    q = """SELECT o.id_operation, o.created_at, s.name AS store_name, e.full_name AS seller_name,
                  o.total_revenue, o.total_cost, o.total_profit, o.operation_type, o.original_operation_id
           FROM operations o
           JOIN stores s ON s.id_store = o.store_id
           JOIN employees e ON e.id_employee = o.employee_id
           WHERE (o.operation_type = 'sale' OR o.operation_type = 'return')
           AND 1=1"""
    params = []
    if date_from:
        q += " AND o.created_at::date >= %s"
        params.append(date_from)
    if date_to:
        q += " AND o.created_at::date <= %s"
        params.append(date_to)
    q += " ORDER BY o.created_at DESC"
    rows = db.execute(q, tuple(params)) if params else db.execute(q) or []
    return jsonify([
        {"id": r[0], "created_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
         "store_name": r[2], "seller_name": r[3],
         "total_revenue": _round_money(r[4]), "total_cost": _round_money(r[5]), "total_profit": _round_money(r[6]),
         "operation_type": r[7] or "sale", "original_operation_id": r[8]}
        for r in rows
    ])


@bp.route("/reports/summary", methods=["GET"])
def report_summary():
    if not _require_admin():
        return jsonify({"error": "Доступ запрещён"}), 403
    db = get_db()
    date_from = request.args.get("date_from") or ""
    date_to = request.args.get("date_to") or ""
    base = " AND o.created_at::date >= %s" if date_from else ""
    base += " AND o.created_at::date <= %s" if date_to else ""
    params = ([date_from] if date_from else []) + ([date_to] if date_to else [])
    q_sale = """SELECT COALESCE(SUM(o.total_revenue), 0), COALESCE(SUM(o.total_cost), 0), COALESCE(SUM(o.total_profit), 0)
                FROM operations o WHERE o.operation_type = 'sale' AND 1=1""" + base
    q_ret = """SELECT COALESCE(SUM(o.total_revenue), 0), COALESCE(SUM(o.total_cost), 0), COALESCE(SUM(o.total_profit), 0)
               FROM operations o WHERE o.operation_type = 'return' AND 1=1""" + base
    row_sale = db.execute_one(q_sale, tuple(params)) if params else db.execute_one(q_sale)
    row_ret = db.execute_one(q_ret, tuple(params)) if params else db.execute_one(q_ret)
    rev_sale = (row_sale[0] or 0) if row_sale else 0
    cost_sale = (row_sale[1] or 0) if row_sale else 0
    profit_sale = (row_sale[2] or 0) if row_sale else 0
    rev_ret = (row_ret[0] or 0) if row_ret else 0
    cost_ret = (row_ret[1] or 0) if row_ret else 0
    profit_ret = (row_ret[2] or 0) if row_ret else 0
    rev = rev_sale - rev_ret
    cost = cost_sale - cost_ret
    profit = profit_sale - profit_ret
    margin = _round_percent((profit / rev * 100) if rev else 0)
    return jsonify({
        "total_revenue": _round_money(rev),
        "total_cost": _round_money(cost),
        "total_profit": _round_money(profit),
        "margin_percent": margin,
        "total_revenue_sales": _round_money(rev_sale),
        "total_revenue_returns": _round_money(rev_ret),
    })
