import sqlite3

# 建立資料庫
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ===========================
# 借用人資料
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===========================
# 工具分類
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
""")

# ===========================
# 工具資料
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS tools(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER,
    total_quantity INTEGER NOT NULL DEFAULT 0,
    available_quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    image TEXT,
    status TEXT DEFAULT '正常',
    FOREIGN KEY(category_id) REFERENCES categories(id)
)
""")

# ===========================
# 借用紀錄
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS borrow_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tool_id INTEGER,
    quantity INTEGER NOT NULL,
    borrow_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    return_time TIMESTAMP,
    status TEXT DEFAULT '借出',
    remark TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(tool_id) REFERENCES tools(id)
)
""")

# ===========================
# 管理員
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# 建立預設管理員
cursor.execute("""
INSERT OR IGNORE INTO admins(username,password)
VALUES('admin','123456')
""")

# 建立工具分類
cursor.execute("""
INSERT OR IGNORE INTO categories(id,name)
VALUES
(1,'電動工具'),
(2,'手工具'),
(3,'測量工具'),
(4,'安全用品'),
(5,'其他')
""")

# 建立測試工具
tools = [
("電鑽",1,20,20,"A倉"),
("打石機",1,5,5,"A倉"),
("砂輪機",1,10,10,"A倉"),
("延長線",5,30,30,"B倉"),
("安全帽",4,100,100,"安全倉"),
("反光背心",4,80,80,"安全倉"),
("水平儀",3,15,15,"工具櫃"),
("捲尺",3,40,40,"工具櫃"),
("鐵鎚",2,25,25,"工具櫃"),
("活動板手",2,30,30,"工具櫃")
]

for tool in tools:
    cursor.execute("""
    INSERT INTO tools(
        name,
        category_id,
        total_quantity,
        available_quantity,
        location
    )
    VALUES(?,?,?,?,?)
    """, tool)

conn.commit()
conn.close()

print("="*40)
print("工地借物管理系統 V2")
print("資料庫建立完成！")
print("預設管理員：admin")
print("預設密碼：123456")
print("="*40)