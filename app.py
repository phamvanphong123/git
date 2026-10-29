# he thong dang ky su kien cong ty xyz
import os
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-doi-khi-trien-khai")
app.config["DATABASE"] = os.environ.get("DATABASE", os.path.join(app.root_path, "xyz_events.db"))
app.teardown_appcontext(db.close_db)

ROLE_HOME = {"Employee": "employee_home", "Organizer": "organizer_home", "Admin": "admin_home"}
ROLE_LABEL = {"Employee": "Nhân viên", "Organizer": "Người tổ chức", "Admin": "Quản trị viên"}

S_OPEN, S_FULL, S_CLOSED, S_ENDED, S_CANCELLED = (
    "dang mo",
    "full",
    "da dong",
    "da ket thuc",
    "da huy",
)
"dang mo dang ky het cho thu hoi su kien!" 
STATUSES = [S_OPEN, S_FULL, S_CLOSED, S_ENDED, S_CANCELLED]
STATUS_CSS = {S_OPEN: "open", S_FULL: "full", S_CLOSED: "closed", S_ENDED: "ended", S_CANCELLED: "cancelled"}

# bao mat co ban va nguoi dung hien dai
@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db.query_one(
            "SELECT u.*, d.name AS dept FROM users u JOIN departments d ON d.id = u.department_id "
            "WHERE u.id = ?", (uid,))
        if g.user is None or not g.user["is_active"]:   # tài khoản bị khóa/xóa khi đang đăng nhập
            session.clear()
            g.user = None
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["ROLE_LABEL"] = ROLE_LABEL


@app.template_filter("vn_time")
def vn_time(value):
    return datetime.strptime(value, db.FMT).strftime("%d/%m/%Y %H:%M")


def role_required(*roles):
#kiem tra quyen xem duoc o hay bi duoi
    def deco(view):
        @wraps(view)
        def wrapper(*a, **kw):
            if g.user is None:
                return redirect(url_for("login"))
            if g.user["role"] not in roles:
                abort(403)
            return view(*a, **kw)
        return wrapper
    return deco

#US01: dang nhap
@app.route("/")
def index():
    if g.user:
        return redirect(url_for(ROLE_HOME[g.user["role"]]))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for(ROLE_HOME[g.user["role"]]))
    error, email = None, ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            error = "vui long nhap lai email va mat khau."
        else:
            user = db.query_one("SELECT * FROM users WHERE email = ?", (email,))
            if user is None or not check_password_hash(user["password_hash"], password):
                error = "thong tin dang nhap khong chinh xac"            # AC2
            elif not user["is_active"]:
                error = "tai khoan bi khoa. vui long lien he adin."
            else:
                session.clear()
                session["uid"] = user["id"]
                return redirect(url_for(ROLE_HOME[user["role"]]))        # AC3
    return render_template("login.html", error=error, email=email)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# giao dien theo role
@app.route("/organizer")
@role_required("Organizer")
def organizer_home():
    return render_template("role_home.html", title="giao die nguoi to chuc", items=[
        "tao, chinh sua su kien (US6)",
        "quanly nguoi tham gia va diem danh(US7)",
        "dardboard thong ke(US8)"])


@app.route("/admin")
@role_required("Admin")
def admin_home():
    return render_template("role_home.html", title="giao dien quan tri he thong", items=[
        "quan ly phong ban , tai khoan, mo tai khoan",
        "quan ly su kien",
        "dardboard thong ke (US8)"])

# xem danh sach tim kiem loc su kien
def event_status(ev, now):
    if ev["status"] == "Cancelled":
        return S_CANCELLED
    if datetime.strptime(ev["start_time"], db.FMT) <= now:
        return S_ENDED
    if ev["registered"] >= ev["max_participants"]:
        return S_FULL
    if datetime.strptime(ev["registration_deadline"], db.FMT) < now:
        return S_CLOSED
    return S_OPEN


def parse_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d") if text else None
    except ValueError:
        return False


@app.route("/employee")
@role_required("Employee")
def employee_home():
    q = request.args.get("q", "").strip()[:100]
    date_from, date_to = request.args.get("from", ""), request.args.get("to", "")
    dept = request.args.get("dept", "")
    status = request.args.get("status", "")
    errors = []

    sql = ("SELECT e.*, d.name AS dept, "
           "(SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id "
           " AND r.status IN ('Registered','Confirmed','Attended')) AS registered "
           "FROM events e JOIN departments d ON d.id = e.department_id WHERE 1 = 1")
    args = []
    if q:
        like = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND e.name LIKE ? ESCAPE '\\'"
        args.append(f"%{like}%")
    d_from, d_to = parse_date(date_from), parse_date(date_to)
    if d_from is False or d_to is False:
        errors.append("Ngày lọc không hợp lệ.")
    elif d_from and d_to and d_from > d_to:
        errors.append("ngay bat dau loc phai truoc hoac bang ngay do .")
    else:
        if d_from:
            sql += " AND e.start_time >= ?"
            args.append(d_from.strftime("%Y-%m-%d 00:00"))
        if d_to:
            sql += " AND e.start_time <= ?"
            args.append(d_to.strftime("%Y-%m-%d 23:59"))
    if dept.isdigit():
        sql += " AND e.department_id = ?"
        args.append(int(dept))
    sql += " ORDER BY e.start_time"

    now = datetime.now()
    events = []
    for row in db.query(sql, args):
        ev = dict(row)
        ev["state"] = event_status(ev, now)
        if status in STATUSES and ev["state"] != status:
            continue
        ev["css"] = STATUS_CSS[ev["state"]]
        events.append(ev)

    filtering = bool(q or date_from or date_to or dept or status)
    return render_template(
        "events.html", events=events, errors=errors, filtering=filtering,
        departments=db.query("SELECT id, name FROM departments ORDER BY id"),
        statuses=STATUSES, f={"q": q, "from": date_from, "to": date_to, "dept": dept, "status": status})


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def http_error(err):
    msg = {400: "yeu cau khong hop le vui long tai lai trang",
           403: "ban khong co quen truy cap chuc nang nay.",
           404: "khong tim thay trang ban yeu cau ."}[err.code]
    return render_template("error.html", code=err.code, message=msg), err.code


db.ensure_db(app.config["DATABASE"])

if __name__ == "__main__":
    app.run(debug=True)
