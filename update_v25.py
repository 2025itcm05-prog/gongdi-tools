import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS return_users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    return_code TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT '啟用'
)
""")

try:
    cursor.execute("ALTER TABLE borrow_records ADD COLUMN return_user_id INTEGER")
except sqlite3.OperationalError:
    pass

conn.commit()
conn.close()

print("V2.5 資料庫升級完成")