import sqlalchemy.pool as pool
import pymysql

def get_conn():
    conn = pymysql.connect( host="host",
                            user="user",
                            password="password",
                            database="database",
                            cursorclass=pymysql.cursors.DictCursor )
    return conn

conn_pool = pool.QueuePool(get_conn, max_overflow=10, pool_size=5)

