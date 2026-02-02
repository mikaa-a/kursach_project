# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, request, g, make_response
from auth_util import current_user, require_admin, get_db

bp = Blueprint("admin_routes", __name__, template_folder="../templates")


def _admin_nav(active=None):
    items = [
        ("admin_routes.admin_main", "Главная страница"),
        ("admin_routes.stores", "Магазины"),
        ("admin_routes.warehouses", "Склады"),
        ("admin_routes.distribution", "Распределение"),
        ("admin_routes.products", "Товары"),
        ("admin_routes.employees", "Сотрудники"),
        ("admin_routes.sales", "Продажи"),
        ("admin_routes.reports", "Отчеты"),
    ]
    return [{"url": url_for(name), "label": label, "active": name == active} for name, label in items]


@bp.route("/")
@require_admin
def admin_main():
    db = get_db()
    user = current_user()
    notifications = db.execute(
        """SELECT p.name AS product_name, p.id_product AS product_id,
                  s.name AS location_name, sps.quantity, sps.store_id, NULL::int AS warehouse_id
           FROM store_product_stock sps
           JOIN products p ON p.id_product = sps.product_id
           JOIN stores s ON s.id_store = sps.store_id
           WHERE sps.quantity < p.min_stock_level AND sps.quantity >= 0
           UNION ALL
           SELECT p.name, p.id_product, w.name, wps.quantity, NULL::int, wps.warehouse_id
           FROM warehouse_product_stock wps
           JOIN products p ON p.id_product = wps.product_id
           JOIN warehouses w ON w.id_warehouse = wps.warehouse_id
           WHERE wps.quantity < p.min_stock_level AND wps.quantity >= 0
           ORDER BY quantity ASC"""
    ) or []
    return render_template(
        "admin/main.html",
        user=user,
        nav_items=_admin_nav("admin_routes.admin_main"),
        brand_url=url_for("admin_routes.admin_main"),
        notifications=[{"product_name": n[0], "product_id": n[1], "location_name": n[2], "quantity": n[3], "store_id": n[4], "warehouse_id": n[5]} for n in notifications],
    )


@bp.route("/stores")
@require_admin
def stores():
    db = get_db()
    user = current_user()
    rows = db.execute(
        """SELECT s.id_store, s.name, s.address, s.phone
           FROM stores s WHERE s.is_active = TRUE ORDER BY s.name"""
    ) or []
    stores_list = [{"id": r[0], "name": r[1], "address": r[2] or "", "phone": r[3] or ""} for r in rows]
    resp = make_response(render_template("admin/stores.html", user=user, nav_items=_admin_nav("admin_routes.stores"), brand_url=url_for("admin_routes.admin_main"), stores_list=stores_list))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@bp.route("/warehouses")
@require_admin
def warehouses():
    db = get_db()
    user = current_user()
    rows = db.execute(
        """SELECT w.id_warehouse, w.name, w.address, w.phone, w.area
           FROM warehouses w WHERE w.is_active = TRUE ORDER BY w.name"""
    ) or []
    warehouses_list = [{"id": r[0], "name": r[1], "address": r[2] or "", "phone": r[3] or "", "area": float(r[4] or 0)} for r in rows]
    resp = make_response(render_template("admin/warehouses.html", user=user, nav_items=_admin_nav("admin_routes.warehouses"), brand_url=url_for("admin_routes.admin_main"), warehouses_list=warehouses_list))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return resp


@bp.route("/distribution")
@require_admin
def distribution():
    user = current_user()
    return render_template("admin/distribution.html", user=user, nav_items=_admin_nav("admin_routes.distribution"), brand_url=url_for("admin_routes.admin_main"))


@bp.route("/products")
@require_admin
def products():
    db = get_db()
    user = current_user()
    rows = None
    for join_cond in ["c.id = p.category_id", "c.id_category = p.category_id"]:
        try:
            rows = db.execute(
                """SELECT p.id_product, p.name, c.name AS category_name, p.unit,
                          p.purchase_price, p.retail_price, p.min_stock_level
                   FROM products p
                   LEFT JOIN categories c ON """ + join_cond + """
                   WHERE p.is_active = TRUE
                   ORDER BY p.name"""
            ) or []
            break
        except Exception:
            continue
    if rows is None:
        rows = db.execute(
            """SELECT p.id_product, p.name, p.unit,
                      p.purchase_price, p.retail_price, p.min_stock_level
               FROM products p
               WHERE p.is_active = TRUE
               ORDER BY p.name"""
        ) or []
        products_list = [
            {"id": r[0], "name": r[1], "category": "", "unit": r[2], "purchase_price": float(r[3]), "retail_price": float(r[4]), "min_stock": r[5]}
            for r in rows
        ]
    else:
        products_list = [
            {"id": r[0], "name": r[1], "category": r[2] or "", "unit": r[3], "purchase_price": float(r[4]), "retail_price": float(r[5]), "min_stock": r[6]}
            for r in rows
        ]
    return render_template("admin/products.html", user=user, nav_items=_admin_nav("admin_routes.products"), brand_url=url_for("admin_routes.admin_main"), products_list=products_list)


@bp.route("/employees")
@require_admin
def employees():
    db = get_db()
    user = current_user()
    rows = db.execute(
        """SELECT e.id_employee, e.login, e.full_name, e.role, e.store_id, s.name AS store_name, e.is_active
           FROM employees e
           LEFT JOIN stores s ON s.id_store = e.store_id
           WHERE e.role IN ('admin', 'seller')
           ORDER BY e.role, e.full_name"""
    ) or []
    employees_list = [
        {"id": r[0], "login": r[1], "full_name": r[2], "role": r[3], "store_id": r[4], "store_name": r[5] or "", "active": r[6]}
        for r in rows
    ]
    return render_template("admin/employees.html", user=user, nav_items=_admin_nav("admin_routes.employees"), brand_url=url_for("admin_routes.admin_main"), employees_list=employees_list)


@bp.route("/sales")
@require_admin
def sales():
    user = current_user()
    return render_template("admin/sales.html", user=user, nav_items=_admin_nav("admin_routes.sales"), brand_url=url_for("admin_routes.admin_main"))


@bp.route("/reports")
@require_admin
def reports():
    user = current_user()
    return render_template("admin/reports.html", user=user, nav_items=_admin_nav("admin_routes.reports"), brand_url=url_for("admin_routes.admin_main"))
