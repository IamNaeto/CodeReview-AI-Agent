# Scenario 1: Security - SQL Injection & Input Validation
# Expected: Critical SQL Injection finding from Security agent

import sqlite3

def get_user_by_username(username):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    # VULNERABILITY: Direct string concatenation into SQL
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user[2] == password:  # plaintext comparison
        return True
    return False

