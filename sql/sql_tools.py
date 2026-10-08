import pymysql

class SQLTools:
    def __init__(self):
        self.config = dict(
            host="127.0.0.1",
            port=3306,
            user="root",
            password="std20050526@",
            db="agent",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    def sql_add(self, username,password):
        conn = pymysql.connect(**self.config)
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users_data (username, password) VALUES (%s, %s)",
                            (username, password))
        except Exception as e:
                print(e)
        finally:
            conn.close()

