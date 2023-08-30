import sqlalchemy.pool as pool
import pymysql

def get_conn():
    conn = pymysql.connect( host="localhost",
                            user="root",
                            password="Tltsdtrqqxkirv",
                            database="music-generator",
                            cursorclass=pymysql.cursors.DictCursor )
    return conn

conn_pool = pool.QueuePool(get_conn, max_overflow=10, pool_size=5)

