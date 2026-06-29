from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


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

    conn.close()

    return render_template("borrow.html", user=user, tools=tools)


@app.route("/borrow_submit", methods=["POST"])
def borrow_submit():
    user_id = request.form["user_id"]

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
                    INSERT INTO borrow_records(user_id, tool_id, quantity)
                    VALUES(?, ?, ?)
                """, (user_id, tool_id, qty))

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
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            borrow_records.id,
            users.name AS user_name,
            users.phone,
            tools.name AS tool_name,
            borrow_records.quantity,
            borrow_records.borrow_time,
            borrow_records.return_time,
            borrow_records.status
        FROM borrow_records
        JOIN users ON borrow_records.user_id = users.id
        JOIN tools ON borrow_records.tool_id = tools.id
        ORDER BY borrow_records.borrow_time DESC
    """)

    records = cursor.fetchall()
    conn.close()

    return render_template("history.html", records=records)


@app.route("/return_tool/<int:record_id>")
def return_tool(record_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tool_id, quantity, status
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
            return redirect("/admin")

        return "帳號或密碼錯誤<br><a href='/admin_login'>重新登入</a>"

    return render_template("admin_login.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/admin_tools")
def admin_tools():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM tools
        ORDER BY name
    """)

    tools = cursor.fetchall()
    conn.close()

    return render_template("admin_tools.html", tools=tools)


@app.route("/add_tool", methods=["POST"])
def add_tool():
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
    total_quantity = int(request.form["total_quantity"])
    available_quantity = int(request.form["available_quantity"])
    location = request.form["location"]
    status = request.form["status"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tools
        SET total_quantity=?,
            available_quantity=?,
            location=?,
            status=?
        WHERE id=?
    """, (
        total_quantity,
        available_quantity,
        location,
        status,
        tool_id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin_tools")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)