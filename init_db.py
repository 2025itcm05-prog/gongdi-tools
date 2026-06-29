import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT '啟用'
)
""")

sites = [
    (1, "M05工地", "啟用"),
    (2, "M21工地", "啟用"),
    (3, "N01工地", "啟用"),
    (4, "N02工地", "啟用")
]

for site in sites:
    cursor.execute("""
        INSERT OR IGNORE INTO sites(id, name, status)
        VALUES(?, ?, ?)
    """, site)

cursor.execute("""
UPDATE sites SET name='M05工地', status='啟用' WHERE id=1
""")
cursor.execute("""
UPDATE sites SET name='M21工地', status='啟用' WHERE id=2
""")
cursor.execute("""
UPDATE sites SET name='N01工地', status='啟用' WHERE id=3
""")
cursor.execute("""
UPDATE sites SET name='N02工地', status='啟用' WHERE id=4
""")

conn.commit()
conn.close()

print("工地資料建立完成")