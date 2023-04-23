from db_connection import conn_pool
from argon2 import PasswordHasher
import re

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

def check_params(username, email, password, password2):    
    # Check if username is valid
    if username_is_valid(username) == False:
        return [False, "Username is invalid"]
    
    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()
    
    # Check if this username already exists in db
    cursor.execute("""
            SELECT * 
            FROM  User 
            WHERE username = %(username)s
            """, {
                'username' : username
            } )
    result = cursor.fetchone()
    if result is not None:
        conn.close()
        return [False, "There is already an account with this username"]

    # Check if email is valid
    if email_is_valid(email) == False:
        return [False, "Email is invalid"]

    # Check if this email already exists in db
    cursor.execute("""
            SELECT * 
            FROM  User 
            WHERE email = %(email)s
            """, {
                'email' : email
            } )
    result = cursor.fetchone()
    if result is not None:
        conn.close()
        return [False, "There is already an account with this email"]
    
    conn.close()

    # Check if password is valid
    if password_is_valid(password) == False:
        return [False, "Password is invalid"]
    
    # Check if these password fields match
    if (password != password2):
        return [False, "Passwords do not match"]
    
    return [True, "No problems with registration parameters"]
#end check_params()

def username_is_valid(username):
    if (len(username) < 6 or len(username) > 25):
        return False #username is too short or too long
    if re.search("[^a-z0-9_-]", username) is not None:
        return False #username contains invalid characters
    return True
#end username_is_valid()

def email_is_valid(email):
    if (len(email) > 256):
        return False #email is too long
    if re.search(".*@[^@.]*\.[^@.]+", email) is None:
        return False #email is not in the format (something)@(something).(something)
    return True
#end email_is_valid()

def password_is_valid(password):
    if (len(password) < 8 or len(password) > 20):
        return False #password is too short or too long
    if re.search("[A-Z]", password) is None:
        return False #password is missing an uppercase letter
    if re.search("[a-z]", password) is None:
        return False #password is missing a lowercase letter
    if re.search("[0-9]", password) is None:
        return False #password is missing a number
    return True
#end password_is_valid() 

def add_user(username, email, password, debug=False):
    if(debug): print(username, email, password)
    
    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()

    # Generate hash for submitted password
    hasher = PasswordHasher()
    try:
        password_hash = hasher.hash(password)
    except Exception as e:
        # Error in generating the hash
        if(debug): print("Exception:", e)
        conn.close()
        return False
    
    # Store username, email, and password_hash in db
    try:
        if(debug): print("""
                INSERT INTO User (username, email, password_hash)
                VALUES (%(username)s, %(email)s, %(password_hash)s)
                """, {
                    'username' : username,
                    'email' : email,
                    'password_hash' : password_hash
                } )
        cursor.execute("""
                INSERT INTO User (username, email, password_hash)
                VALUES (%(username)s, %(email)s, %(password_hash)s)
                """, {
                    'username' : username,
                    'email' : email,
                    'password_hash' : password_hash
                } )
        conn.commit()
    except Exception as e:
        # Failed in adding new user to db
        if(debug): print("Exception:", e)
        conn.close()
        return False

    if(debug): print("Register successful")
    conn.close()
    return True
#end add_user()