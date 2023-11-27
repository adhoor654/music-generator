import sqlalchemy.pool as pool
import pymysql

def get_conn():

    conn = pymysql.connect( host="project.cjq9ha2mxapc.us-east-1.rds.amazonaws.com",
                            user="admin",
                            password="admin295",
                            database="project",
                            cursorclass=pymysql.cursors.DictCursor )
    return conn

conn_pool = pool.QueuePool(get_conn, max_overflow=10, pool_size=5)


                            
# conn = pymysql.connect( host="host.docker.internal",
#                           user="root",
#                            password="Tltsdtrqqxkirv",
#                            database="music-generator",
#                            cursorclass=pymysql.cursors.DictCursor ) 