import sqlite3

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
# 工地資料
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS sites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT '啟用'
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
    site_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(tool_id) REFERENCES tools(id),
    FOREIGN KEY(site_id) REFERENCES sites(id)
)
""")

# 如果舊資料表沒有 site_id，就補上
try:
    cursor.execute("ALTER TABLE borrow_records ADD COLUMN site_id INTEGER")
except sqlite3.OperationalError:
    pass

# ===========================
# 管理員
# role:
# super = 總管理員
# site  = 工地主任
# ===========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT DEFAULT 'super',
    site_id INTEGER,
    FOREIGN KEY(site_id) REFERENCES sites(id)
)
""")

# 如果舊 admins 沒有 role / site_id，就補上
try:
    cursor.execute("ALTER TABLE admins ADD COLUMN role TEXT DEFAULT 'super'")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE admins ADD COLUMN site_id INTEGER")
except sqlite3.OperationalError:
    pass

# ===========================
# 預設工地
# ===========================
cursor.execute("INSERT OR IGNORE INTO sites(id, name, status) VALUES(1, 'A工地', '啟用')")
cursor.execute("INSERT OR IGNORE INTO sites(id, name, status) VALUES(2, 'B工地', '啟用')")
cursor.execute("INSERT OR IGNORE INTO sites(id, name, status) VALUES(3, 'C工地', '啟用')")

# ===========================
# 預設管理員
# ===========================
cursor.execute("""
INSERT OR IGNORE INTO admins(id, username, password, role, site_id)
VALUES(1, 'admin', '123456', 'super', NULL)
""")

# 若舊 admin 已存在，補成總管理員
cursor.execute("""
UPDATE admins
SET role='super', site_id=NULL
WHERE username='admin'
""")

# 預設工地主任帳號
cursor.execute("""
INSERT OR IGNORE INTO admins(username, password, role, site_id)
VALUES('siteA', '123456', 'site', 1)
""")

cursor.execute("""
INSERT OR IGNORE INTO admins(username, password, role, site_id)
VALUES('siteB', '123456', 'site', 2)
""")

cursor.execute("""
INSERT OR IGNORE INTO admins(username, password, role, site_id)
VALUES('siteC', '123456', 'site', 3)
""")

# ===========================
# 工具分類
# ===========================
cursor.execute("""
INSERT OR IGNORE INTO categories(id,name)
VALUES
(1,'電動工具'),
(2,'手工具'),
(3,'測量工具'),
(4,'安全用品'),
(5,'其他')
""")

# ===========================
# 測試工具：只有 tools 空的時候才建立
# ===========================
cursor.execute("SELECT COUNT(*) FROM tools")
tool_count = cursor.fetchone()[0]

if tool_count == 0:
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
print("工地借物管理系統 V2.1")
print("資料庫升級完成！")
print("總管理員：admin / 86251390")
print("M05工地主任：itc-m05 / m054270")
print("M21工地主任：itc-m21 / m214270")
print("N01工地主任：itc-n01 / n014270")
print("N02工地主任：itc-n02 / n024270")
print("="*40)