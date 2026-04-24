import sqlite3
import os

db_path = r'c:\Users\Admin\Desktop\SFRAS\database.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, roll_number, course, role FROM student")
    rows = cursor.fetchall()
    print("ID | Name | Roll | Course | Role")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
    conn.close()
