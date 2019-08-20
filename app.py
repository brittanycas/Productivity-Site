from flask import Flask, render_template, request
import sqlite3
from passlib.hash import sha256_crypt

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')
    elif request.method == "POST":
        # Check for data in registration form
        if not request.form.get('name') or \
                not request.form.get('username') or \
                not request.form.get('email') or \
                not request.form.get('password') or \
                not request.form.get('confirm'):
            return "please fully fill out registration"
        else:
            # Open connection to the database
            conn = sqlite3.connect('userdata.db')
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=?", (request.form.get('username'),))
            existing_user = c.fetchall()
            c.execute("SELECT * FROM users WHERE email=?", (request.form.get('email'),))
            existing_email = c.fetchall()
            if len(existing_user) != 0:
                return "username is already in use"
            if len(existing_email) != 0:
                return "email is already associated with an account"
            else:
                hashed_pass = sha256_crypt.hash(request.form.get('password'))
                # Add user to database
                c.execute("""INSERT INTO users (username, name, email, hashedpassword)
                            VALUES (?, ?, ?, ?)""", (request.form.get('username'), request.form.get('name'),
                                                     request.form.get('email'), hashed_pass,))
                # Close database connection
                conn.commit()
                conn.close()

                return 'success'


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == "POST":
        # Check for data in login form
        if not request.form.get('username') or not request.form.get('password'):
            return "Please enter username and password to login"
        else:
            # Open connection to the database
            conn = sqlite3.connect('userdata.db')
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=?", (request.form.get('username'),))
            existing_user = c.fetchall()

            # Close database connection
            conn.commit()
            conn.close()

            # Check for valid username
            if len(existing_user) == 0:
                return "Invalid user name"
            else:
                # Check for valid password
                if sha256_crypt.verify(request.form.get('password'), existing_user[0][4]):
                    return render_template('/')
                else:
                    return "Invalid login credentials"


if __name__ == '__main__':
    app.run()
