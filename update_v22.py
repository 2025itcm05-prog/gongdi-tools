import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# 建立各工地工具庫存表
cursor.execute("""
CREATE TABLE IF NOT EXISTS site_tools(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    tool_id INTEGER NOT NULL,
    total_quantity INTEGER NOT NULL DEFAULT 0,
    available_quantity INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(site_id) REFERENCES sites(id),
    FOREIGN KEY(tool_id) REFERENCES tools(id),
    UNIQUE(site_id, tool_id)
)
""")

# 取得所有工地
cursor.execute("SELECT id FROM sites WHERE status='啟用'")
sites = cursor.fetchall()

# 取得所有工具
cursor.execute("""
SELECT id, total_quantity, available_quantity
FROM tools
""")
tools = cursor.fetchall()

# 把目前 tools 的數量複製到每個工地
for site in sites:
    site_id = site[0]

    for tool in tools:
        tool_id = tool[0]
        total_quantity = tool[1]
        available_quantity = tool[2]

        cursor.execute("""
            INSERT OR IGNORE INTO site_tools(
                site_id,
                tool_id,
                total_quantity,
                available_quantity
            )
            VALUES(?, ?, ?, ?)
        """, (
            site_id,
            tool_id,
            total_quantity,
            available_quantity
        ))

conn.commit()
conn.close()

print("=" * 40)
print("V2.2 升級完成")
print("已建立 site_tools 工地工具庫存表")
print("已把現有工具複製到每個工地")
print("=" * 40)