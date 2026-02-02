# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, request
from auth_util import current_user, require_seller, get_db

bp = Blueprint("seller_routes", __name__, template_folder="../templates")


def _seller_nav(active=None):
    items = [
        ("seller_routes.seller_main", "Главная страница"),
        ("seller_routes.sales", "Продажи"),
    ]
    return [{"url": url_for(name), "label": label, "active": name == active} for name, label in items]


@bp.route("/")
@require_seller
def seller_main():
    db = get_db()
    user = current_user()
    existing = db.execute_one(
        "SELECT id_shift FROM shifts WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL",
        (user["id"], user["store_id"]),
    )
    if not existing:
        db.execute(
            "INSERT INTO shifts (employee_id, store_id, shift_start, status) VALUES (%s, %s, CURRENT_TIMESTAMP, 'open')",
            (user["id"], user["store_id"]),
            fetch=False,
        )
    from datetime import timezone
    from config import SHIFT_DURATION_HOURS, SHIFT_DURATION_SECONDS
    _duration_sec = (SHIFT_DURATION_SECONDS if SHIFT_DURATION_SECONDS is not None else SHIFT_DURATION_HOURS * 3600)
    shift = db.execute_one(
        """SELECT id_shift, shift_start,
           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - shift_start))::BIGINT AS elapsed_sec
           FROM shifts
           WHERE employee_id = %s AND store_id = %s AND shift_end IS NULL
           ORDER BY shift_start DESC LIMIT 1""",
        (user["id"], user["store_id"]),
    )
    shift_info = None
    if shift:
        id_shift, shift_start, elapsed_sec = shift[0], shift[1], (shift[2] or 0)
        if elapsed_sec >= _duration_sec:
            db.execute("UPDATE shifts SET shift_end = CURRENT_TIMESTAMP, status = 'closed' WHERE id_shift = %s", (id_shift,), fetch=False)
            return redirect(url_for("seller_routes.shift_report", shift_id=id_shift))
        opened = shift_start
        if opened.tzinfo is None:
            opened_utc = opened.replace(tzinfo=timezone.utc)
        else:
            opened_utc = opened.astimezone(timezone.utc)
        hours = int(elapsed_sec // 3600)
        opened_iso = opened_utc.isoformat() if shift_start else ""
        shift_info = {
            "id": id_shift,
            "opened_at": shift_start,
            "opened_iso": opened_iso,
            "work_hours": hours,
        }
    return render_template("seller/main.html", user=user, nav_items=_seller_nav("seller_routes.seller_main"), brand_url=url_for("seller_routes.seller_main"), shift_info=shift_info)


@bp.route("/sales")
@require_seller
def sales():
    user = current_user()
    return render_template("seller/sales.html", user=user, nav_items=_seller_nav("seller_routes.sales"), brand_url=url_for("seller_routes.seller_main"))


@bp.route("/shift-report")
def shift_report():
    shift_id = request.args.get("shift_id", type=int)
    if not shift_id:
        return redirect(url_for("login"))
    return render_template("seller/shift_report.html", shift_id=shift_id, brand_url=url_for("login"))
