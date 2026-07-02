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
    return current_admin()


@app.after_request
def add_mobile_style_and_credit(response):
    content_type = response.headers.get("Content-Type", "")

    if "text/html" not in content_type:
        return response

    html = response.get_data(as_text=True)

    mobile_style = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style id="mobile-v24-style">
body{
    font-family: Arial, "微軟正黑體";
    font-size: 34px;
    margin: 25px;
    padding-bottom: 60px;
}

h1{
    font-size: 56px;
}

h2{
    font-size: 46px;
}

h3{
    font-size: 40px;
}

p, a, label{
    font-size: 34px;
}

button{
    font-size: 34px;
    padding: 16px 34px;
    margin: 10px;
    min-height: 75px;
}

input, select{
    font-size: 34px;
    padding: 12px;
    min-height: 60px;
    max-width: 95%;
}

table{
    width: 100%;
    font-size: 30px;
    border-collapse: collapse;
}

th, td{
    padding: 14px;
}

.creator-514{
    position: fixed;
    right: 12px;
    bottom: 8px;
    font-size: 18px;
    color: #888;
    background: rgba(255,255,255,0.8);
    padding: 4px 8px;
    z-index: 9999;
}
</style>
"""

    if "mobile-v24-style" not in html and "</head>" in html:
        html = html.replace("</head>", mobile_style + "\n</head>")

    if "creator-514" not in html and "</body>" in html:
        html = html.replace("</body>", '<div class="creator-514">製作人：514</div>\n</body>')

    response.set_data(html)
    return response




@app.route("/")
def index():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM sites
        WHERE status='啟用'
        ORDER BY name
    """)

    sites = cursor.fetchall()
    conn.close()

    return render_template("index.html", sites=sites)


@app.route("/site")
def select_site():
    site_id = request.args.get("site_id")

    if not site_id:
        return redirect("/")

    session["site_id"] = int(site_id)

    return redirect("/search")


@app.route("/search")
def search_page():
    if "site_id" not in session:
        return redirect("/")

    return render_template("search.html")


@app.route("/search_user", methods=["POST"])
def search_user():
    phone = request.form["phone"]

    if "site_id" not in session:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE phone=?", (phone,))
    user = cursor.fetchone()

    conn.close()

    return render_template(
        "user_result.html",
        user=user,
        phone=phone,
        site_id=session["site_id"]
    )


@app.route("/add_user", methods=["POST"])
def add_user():
    name = request.form["name"]
    phone = request.form["phone"]

    if "site_id" not in session:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users(name, phone) VALUES(?, ?)",
        (name, phone)
    )

    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return redirect(f"/borrow/{user_id}")


@app.route("/borrow/<int:user_id>")
def borrow_page(user_id):
    admin = current_admin()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if admin and admin["role"] == "site":
        selected_site_id = admin["site_id"]
        cursor.execute("SELECT * FROM sites WHERE id=?", (selected_site_id,))
        sites = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT *
            FROM sites
            WHERE status='啟用'
            ORDER BY name
        """)
        sites = cursor.fetchall()

        selected_site_id = session.get("site_id")

        if selected_site_id is None and sites:
            selected_site_id = sites[0]["id"]
            session["site_id"] = selected_site_id

    if selected_site_id:
        cursor.execute("""
            SELECT
                tools.id,
                tools.name,
                tools.location,
                tools.status,
                site_tools.total_quantity,
                site_tools.available_quantity
            FROM site_tools
            JOIN tools ON site_tools.tool_id = tools.id
            WHERE site_tools.site_id=?
            AND site_tools.available_quantity > 0
            AND tools.status='正常'
            ORDER BY tools.name
        """, (selected_site_id,))
        tools = cursor.fetchall()
    else:
        tools = []

    conn.close()

    return render_template(
        "borrow.html",
        user=user,
        tools=tools,
        sites=sites,
        admin=admin,
        selected_site_id=selected_site_id
    )


@app.route("/borrow_submit", methods=["POST"])
def borrow_submit():
    user_id = request.form["user_id"]
    site_id = int(request.form["site_id"])

    admin = current_admin()

    if admin and admin["role"] == "site":
        site_id = admin["site_id"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tool_id, available_quantity
        FROM site_tools
        WHERE site_id=?
    """, (site_id,))

    site_tools = cursor.fetchall()

    for item in site_tools:
        tool_id = item["tool_id"]
        available_quantity = item["available_quantity"]

        qty = request.form.get(f"qty_{tool_id}")

        if qty and int(qty) > 0:
            qty = int(qty)

            if qty <= available_quantity:
                cursor.execute("""
                    INSERT INTO borrow_records(
                        user_id,
                        tool_id,
                        quantity,
                        site_id
                    )
                    VALUES(?, ?, ?, ?)
                """, (user_id, tool_id, qty, site_id))

                cursor.execute("""
                    UPDATE site_tools
                    SET available_quantity = available_quantity - ?
                    WHERE site_id=? AND tool_id=?
                """, (qty, site_id, tool_id))

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
                borrow_records.status,
                return_users.name AS return_user_name
            FROM borrow_records
            JOIN users ON borrow_records.user_id = users.id
            JOIN tools ON borrow_records.tool_id = tools.id
            LEFT JOIN sites ON borrow_records.site_id = sites.id
            LEFT JOIN return_users ON borrow_records.return_user_id = return_users.id
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
                borrow_records.status,
                return_users.name AS return_user_name
            FROM borrow_records
            JOIN users ON borrow_records.user_id = users.id
            JOIN tools ON borrow_records.tool_id = tools.id
            LEFT JOIN sites ON borrow_records.site_id = sites.id
            LEFT JOIN return_users ON borrow_records.return_user_id = return_users.id
            ORDER BY borrow_records.borrow_time DESC
        """)

    records = cursor.fetchall()
    conn.close()

    return render_template("history.html", records=records, admin=admin)


@app.route("/return_tool/<int:record_id>", methods=["POST"])
def return_tool(record_id):
    admin = current_admin()
    return_code = request.form.get("return_code", "").strip()

    if not return_code:
        return "請輸入歸還碼。<br><a href='/history'>返回借用紀錄</a>"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM return_users
        WHERE return_code=? AND status='啟用'
    """, (return_code,))

    return_user = cursor.fetchone()

    if not return_user:
        conn.close()
        return "歸還碼錯誤或已停用。<br><a href='/history'>返回借用紀錄</a>"

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
                return_time=CURRENT_TIMESTAMP,
                return_user_id=?
            WHERE id=?
        """, (return_user["id"], record_id))

        cursor.execute("""
            UPDATE site_tools
            SET available_quantity = available_quantity + ?
            WHERE site_id=? AND tool_id=?
        """, (
            record["quantity"],
            record["site_id"],
            record["tool_id"]
        ))

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

        return "帳號或密碼錯誤<br><a href='/admin_login'>重新登入</a>"

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

    if admin["role"] == "site":
        cursor.execute("""
            SELECT
                site_tools.id AS site_tool_id,
                sites.name AS site_name,
                tools.id AS tool_id,
                tools.name,
                tools.location,
                tools.status,
                site_tools.total_quantity,
                site_tools.available_quantity
            FROM site_tools
            JOIN tools ON tools.id = site_tools.tool_id
            JOIN sites ON sites.id = site_tools.site_id
            WHERE site_tools.site_id=?
            ORDER BY tools.name
        """, (admin["site_id"],))
    else:
        cursor.execute("""
            SELECT
                site_tools.id AS site_tool_id,
                sites.name AS site_name,
                tools.id AS tool_id,
                tools.name,
                tools.location,
                tools.status,
                site_tools.total_quantity,
                site_tools.available_quantity
            FROM site_tools
            JOIN tools ON tools.id = site_tools.tool_id
            JOIN sites ON sites.id = site_tools.site_id
            ORDER BY tools.name, sites.name
        """)

    tools = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_tools.html",
        tools=tools,
        admin=admin,
        site_mode=(admin["role"] == "site")
    )


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
            category_id,
            total_quantity,
            available_quantity,
            location,
            status
        )
        VALUES(?, 5, ?, ?, ?, '正常')
    """, (name, total_quantity, total_quantity, location))

    tool_id = cursor.lastrowid

    if admin["role"] == "site":
        cursor.execute("""
            INSERT INTO site_tools(
                site_id,
                tool_id,
                total_quantity,
                available_quantity
            )
            VALUES(?, ?, ?, ?)
        """, (
            admin["site_id"],
            tool_id,
            total_quantity,
            total_quantity
        ))
    else:
        cursor.execute("SELECT id FROM sites WHERE status='啟用'")
        sites = cursor.fetchall()

        for site in sites:
            cursor.execute("""
                INSERT INTO site_tools(
                    site_id,
                    tool_id,
                    total_quantity,
                    available_quantity
                )
                VALUES(?, ?, ?, ?)
            """, (
                site["id"],
                tool_id,
                total_quantity,
                total_quantity
            ))

    conn.commit()
    conn.close()

    return redirect("/admin_tools")


@app.route("/update_site_tool/<int:site_tool_id>", methods=["POST"])
def update_site_tool(site_tool_id):
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
        SELECT site_tools.site_id, site_tools.tool_id
        FROM site_tools
        WHERE site_tools.id=?
    """, (site_tool_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return redirect("/admin_tools")

    if admin["role"] == "site" and row["site_id"] != admin["site_id"]:
        conn.close()
        return "你沒有權限修改這個工地的工具。<br><a href='/admin_tools'>返回工具管理</a>"

    cursor.execute("""
        UPDATE tools
        SET name=?, location=?, status=?
        WHERE id=?
    """, (
        name,
        location,
        status,
        row["tool_id"]
    ))

    cursor.execute("""
        UPDATE site_tools
        SET total_quantity=?,
            available_quantity=?
        WHERE id=?
    """, (
        total_quantity,
        available_quantity,
        site_tool_id
    ))

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
            location=?,
            status=?
        WHERE id=?
    """, (
        name,
        location,
        status,
        tool_id
    ))

    if admin["role"] == "site":
        cursor.execute("""
            UPDATE site_tools
            SET total_quantity=?,
                available_quantity=?
            WHERE site_id=? AND tool_id=?
        """, (
            total_quantity,
            available_quantity,
            admin["site_id"],
            tool_id
        ))
    else:
        cursor.execute("""
            UPDATE site_tools
            SET total_quantity=?,
                available_quantity=?
            WHERE tool_id=?
        """, (
            total_quantity,
            available_quantity,
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

    if admin["role"] == "site":
        cursor.execute("""
            SELECT COUNT(*)
            FROM borrow_records
            WHERE tool_id=? AND site_id=? AND status='借出'
        """, (tool_id, admin["site_id"]))
    else:
        cursor.execute("""
            SELECT COUNT(*)
            FROM borrow_records
            WHERE tool_id=? AND status='借出'
        """, (tool_id,))

    borrowed_count = cursor.fetchone()[0]

    if borrowed_count > 0:
        conn.close()
        return "這個工具目前有人借用中，不能刪除。<br><a href='/admin_tools'>返回工具管理</a>"

    if admin["role"] == "site":
        cursor.execute("""
            DELETE FROM site_tools
            WHERE site_id=? AND tool_id=?
        """, (admin["site_id"], tool_id))
    else:
        cursor.execute("DELETE FROM site_tools WHERE tool_id=?", (tool_id,))
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
        return "你沒有權限管理工地。<br><a href='/admin'>返回後台</a>"

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
        return "你沒有權限新增工地。<br><a href='/admin'>返回後台</a>"

    name = request.form["name"]
    admin_username = request.form.get("admin_username", "").strip()
    admin_password = request.form.get("admin_password", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO sites(name, status) VALUES(?, '啟用')",
        (name,)
    )

    site_id = cursor.lastrowid

    cursor.execute("SELECT id FROM tools")
    tools = cursor.fetchall()

    for tool in tools:
        cursor.execute("""
            INSERT OR IGNORE INTO site_tools(
                site_id,
                tool_id,
                total_quantity,
                available_quantity
            )
            VALUES(?, ?, 0, 0)
        """, (site_id, tool["id"]))

    if admin_username and admin_password:
        cursor.execute("""
            INSERT INTO admins(
                username,
                password,
                role,
                site_id
            )
            VALUES(?, ?, 'site', ?)
        """, (
            admin_username,
            admin_password,
            site_id
        ))

    conn.commit()
    conn.close()

    return redirect("/admin_sites")


@app.route("/update_site/<int:site_id>", methods=["POST"])
def update_site(site_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限修改工地。<br><a href='/admin'>返回後台</a>"

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


@app.route("/admin_return_users")
def admin_return_users():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限管理歸還人員。<br><a href='/admin'>返回後台</a>"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM return_users
        ORDER BY name
    """)

    return_users = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_return_users.html",
        return_users=return_users,
        admin=admin
    )


@app.route("/add_return_user", methods=["POST"])
def add_return_user():
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限新增歸還人員。<br><a href='/admin'>返回後台</a>"

    name = request.form["name"].strip()
    return_code = request.form["return_code"].strip()

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO return_users(
                name,
                return_code,
                status
            )
            VALUES(?, ?, '啟用')
        """, (name, return_code))

        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "歸還碼已被使用，請換一組。<br><a href='/admin_return_users'>返回歸還人員管理</a>"

    conn.close()

    return redirect("/admin_return_users")


@app.route("/update_return_user/<int:return_user_id>", methods=["POST"])
def update_return_user(return_user_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限修改歸還人員。<br><a href='/admin'>返回後台</a>"

    name = request.form["name"].strip()
    return_code = request.form["return_code"].strip()
    status = request.form["status"]

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE return_users
            SET name=?,
                return_code=?,
                status=?
            WHERE id=?
        """, (
            name,
            return_code,
            status,
            return_user_id
        ))

        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "歸還碼已被使用，請換一組。<br><a href='/admin_return_users'>返回歸還人員管理</a>"

    conn.close()

    return redirect("/admin_return_users")


@app.route("/delete_return_user/<int:return_user_id>")
def delete_return_user(return_user_id):
    admin = require_admin()
    if not admin:
        return redirect("/admin_login")

    if admin["role"] != "super":
        return "你沒有權限刪除歸還人員。<br><a href='/admin'>返回後台</a>"

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM return_users
        WHERE id=?
    """, (return_user_id,))

    conn.commit()
    conn.close()

    return redirect("/admin_return_users")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
