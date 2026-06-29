from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "gongdi-tools-secret-key"


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def current_admin():
    if "admin_id" not in session:
        return None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admins WHERE id=?", (session["admin_id"],))
    admin = cursor.fetchone()

    conn.close()
    return admin


def require_admin():
    admin = current_admin()
    if not admin:
        return None
    return admin


@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, total_quantity, available_quantity, location, status
        FROM tools
        ORDER BY name
    """)

    tools = cursor.fetchall()
    conn.close()

    return render_template("index.html", tools=tools)


@app.route("/search_user", methods=["POST"])
def search_user():
    phone = request.form["phone"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE phone=?", (phone,))
    user = cursor.fetchone()

    conn.close()

    return render_template("user_result.html", user=user, phone=phone)


@app.route("/add_user", methods=["POST"])
def add_user():
    name = request.form["name"]
    phone = request.form["phone"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users(name, phone) VALUES(?, ?)",
        (name, phone)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/borrow/<int:user_id>")
def borrow_page(user_id):
    admin = current_admin()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM tools
        WHERE available_quantity > 0
        AND status='正常'
        ORDER BY name
    """)
    tools = cursor.fetchall()

    if admin and admin["role"] == "site":
        cursor.execute("SELECT * FROM sites WHERE id=?", (admin["site_id"],))
        sites = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM sites WHERE status='啟用' ORDER BY name")
        sites = cursor.fetchall()

    conn.close()

    return render_template("borrow.html", user=user, tools=tools, sites=sites, admin=admin)


@app.route("/borrow_submit", methods=["POST"])
def borrow_submit():
    user_id = request.form["user_id"]
    site_id = request.form["site_id"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, available_quantity FROM tools")
    tools = cursor.fetchall()

    for tool in tools:
        tool_id = tool["id"]
        available_quantity = tool["available_quantity"]

        qty = request.form.get(f"qty_{tool_id}")

        if qty and int(qty) > 0:
            qty = int(qty)

            if qty <= available_quantity:
                cursor.execute("""
                    INSERT INTO borrow_records(user_id, tool_id, quantity, site_id)
                    VALUES(?, ?, ?, ?)
                """, (user_id, tool_id, qty, site_id))

                cursor.execute("""
                    UPDATE tools
                    SET available_quantity = available_quantity - ?
                    WHERE id=?
                """, (qty, tool_id))

    conn.commit()
    conn.close()

    return redirect("/history")


@app.route("/history")
def history():
    admin = current_admin()

    conn = get_db()
    cursor = conn.cursor()

    if admin and admin["role"] == "site":
        cursor.execute("""
            SELECT
                borrow_records.id,
                users.name AS user_name,
                users.phone,
                tools.name AS tool_name,
                sites.name AS site_name,
                borrow_records.quantity,
                borrow_records.borrow_time,
                borrow_records.return_time,
                borrow_records.status
            FROM borrow_records
            JOIN users ON borrow_records.user_id = users.id
            JOIN tools ON borrow_records.tool_id = tools.id
            LEFT JOIN sites ON borrow_records.site_id = sites.id
            WHERE borrow_records.site_id=?
            ORDER BY borrow_records.borrow_time DESC
        """, (admin["site_id"],))
    else:
        cursor.execute("""
            SELECT
                borrow_records.id,
                users.name AS user_name,
                users.phone,
                tools.name AS tool_name,
                sites.name AS site_name,
                borrow_records.quantity,
                borrow_records.borrow_time,
                borrow_records.return_time,
                borrow_records.status
            FROM borrow_records
            JOIN users ON borrow_records.user_id = users.id
            JOIN tools ON borrow_records.tool_id = tools.id
            LEFT JOIN sites ON borrow_records.site_id = sites.id
            ORDER BY borrow_records.borrow_time DESC
        """)

    records = cursor.fetchall()
    conn.close()

    return render_template("history.html", records=records, admin=admin)


@app.route("/return_tool/<int:record_id>")
def return_tool(record_id):
    admin = current_admin()

    conn = get_db()
    cursor = conn.cursor()

    if admin and admin["role"] == "site":
        cursor.execute("""
            SELECT tool_id, quantity, status, site_id
            FROM borrow_records
            WHERE id=? AND site_id=?
        """, (record_id, admin["site_id"]))
    else:
        cursor.execute("""
            SELECT tool_id, quantity, status, site_id
            FROM borrow_records
            WHERE id=?
        """, (record_id,))

    record = cursor.fetchone()

    if record and record["status"] == "借出":
        cursor.execute("""
            UPDATE borrow_records
            SET status='已歸還',
                return_time=CURRENT_TIMESTAMP
            WHERE id=?
        """, (record_id,))

        cursor.execute("""
            UPDATE tools
            SET available_quantity = available_quantity + ?
            WHERE id=?
        """, (record["quantity"], record["tool_id"]))

        conn.commit()

    conn.close()

    return redirect("/history")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (username, password)
        )

        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session["admin_role"] = admin["role"]
            session["admin_site_id"] = admin["site_id"]
            return redirect("/admin")

        return "帳號或密碼錯誤<br><a href=' '>重新登入</a >"

    return render_template("admin_login.html")


@app.route("/admin_logout")
def admin_logout():
    session.clear()
    return redirect("/")


@app.route("/admin")
def admin():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    conn = get_db()
    cursor = conn.cursor()

    if admin["role"] == "site":
        cursor.execute("SELECT * FROM sites WHERE id=?", (admin["site_id"],))
        site = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM borrow_records
            WHERE site_id=? AND status='借出'
        """, (admin["site_id"],))
        borrowed_count = cursor.fetchone()["count"]

        conn.close()

        return render_template(
            "admin.html",
            admin=admin,
            site=site,
            borrowed_count=borrowed_count
        )

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM borrow_records
        WHERE status='借出'
    """)
    borrowed_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM sites WHERE status='啟用'")
    site_count = cursor.fetchone()["count"]

    conn.close()

    return render_template(
        "admin.html",
        admin=admin,
        site=None,
        borrowed_count=borrowed_count,
        site_count=site_count
    )


@app.route("/admin_tools")
def admin_tools():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM tools
        ORDER BY name
    """)

    tools = cursor.fetchall()
    conn.close()

    return render_template("admin_tools.html", tools=tools, admin=admin)


@app.route("/add_tool", methods=["POST"])
def add_tool():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    name = request.form["name"]
    total_quantity = int(request.form["total_quantity"])
    location = request.form["location"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tools(
            name,
            total_quantity,
            available_quantity,
            location,
            status
        )
        VALUES(?, ?, ?, ?, '正常')
    """, (name, total_quantity, total_quantity, location))

    conn.commit()
    conn.close()

    return redirect("/admin_tools")


@app.route("/update_tool/<int:tool_id>", methods=["POST"])
def update_tool(tool_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    name = request.form["name"]
    total_quantity = int(request.form["total_quantity"])
    available_quantity = int(request.form["available_quantity"])
    location = request.form["location"]
    status = request.form["status"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tools
        SET name=?,
            total_quantity=?,
            available_quantity=?,
            location=?,
            status=?
        WHERE id=?
    """, (
        name,
        total_quantity,
        available_quantity,
        location,
        status,
        tool_id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin_tools")


@app.route("/delete_tool/<int:tool_id>")
def delete_tool(tool_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM borrow_records
        WHERE tool_id=? AND status='借出'
    """, (tool_id,))

    borrowed_count = cursor.fetchone()[0]

    if borrowed_count > 0:
        conn.close()
        return "這個工具目前有人借用中，不能刪除。<br><a href='/admin_tools'>返回工具管理</a >"

    cursor.execute("DELETE FROM tools WHERE id=?", (tool_id,))

    conn.commit()
    conn.close()

    return redirect("/admin_tools")


@app.route("/admin_sites")
def admin_sites():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限管理工地。<br><a href='/admin'>返回後台</a >"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sites ORDER BY name")
    sites = cursor.fetchall()

    conn.close()

    return render_template("admin_sites.html", sites=sites, admin=admin)


@app.route("/add_site", methods=["POST"])
def add_site():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限新增工地。<br><a href='/admin'>返回後台</a >"

    name = request.form["name"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO sites(name, status) VALUES(?, '啟用')",
        (name,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin_sites")


@app.route("/update_site/<int:site_id>", methods=["POST"])
def update_site(site_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限修改工地。<br><a href='/admin'>返回後台</a >"

    name = request.form["name"]
    status = request.form["status"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sites
        SET name=?, status=?
        WHERE id=?
    """, (name, status, site_id))

    conn.commit()
    conn.close()

    return redirect("/admin_sites")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)