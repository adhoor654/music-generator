from db_connection import conn_pool
from argon2 import PasswordHasher

def authenticate_user(username, password, debug=False):
    if(debug): print(username, password)

    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()

    # Look for password_hash in db
    cursor.execute("""
            SELECT password_hash 
            FROM  User 
            WHERE username = %(username)s
            """, {
                'username' : username
            } )
    result = cursor.fetchone()
    if(debug): print("hash in db:", result)

    # Check if submitted username exists
    if result is None:
        if(debug): print("User does not exist")
        conn.close()
        return False
    
    # Verify password_hash from db against submitted password
    hasher = PasswordHasher()
    try:
        hasher.verify(result['password_hash'], password)
    except Exception as e: 
        # Password is incorrect (or something else went wrong)
        if(debug): print("Exception:", e)
        conn.close()
        return False

    # Submitted username and password is correct
    if(debug): print("User and password are correct")
    conn.close()
    return True
#end authenticate_user()

def add_user(username, email, password, debug=False):
    if(debug): print(username, email, password)
#end add_user()