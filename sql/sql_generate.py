import pymysql

conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="std20050526@",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
)

cur = conn.cursor()

cur.execute("CREATE DATABASE IF NOT EXISTS agent DEFAULT CHARSET utf8mb4")
print("建表成功")

cur.execute("USE agent")

cur.execute("""
    CREATE TABLE IF NOT EXISTS users_data (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        username    VARCHAR(50)  NOT NULL UNIQUE,
        password    VARCHAR(100) NOT NULL,
        create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("表创建成功")

cur.close()
conn.close()

