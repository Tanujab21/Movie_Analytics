"""Promote a registered user to admin. Run: python make_admin.py"""
import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), "movie_portal.db")
if not os.path.exists(db_path):
    print("Database not found. Run app.py once, then register a user, and stop the server.")
    raise SystemExit(1)

email = input("Enter the registered email to make admin: ").strip().lower()
db = sqlite3.connect(db_path)
cur = db.execute("UPDATE users SET role='admin' WHERE lower(email)=?", (email,))
db.commit()
if cur.rowcount:
    print("Success! This account is now an admin. Log out and log in again.")
else:
    print("No user found with that email. Register that account first.")
db.close()
