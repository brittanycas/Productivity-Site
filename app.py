from flask import Flask, render_template, redirect, request, session, escape
import sqlite3
from passlib.hash import sha256_crypt
from config import secret_key

app = Flask(__name__)

app.secret_key = secret_key


@app.route('/')
def home():
    if session.get('logged_in'):
        userdata = []
        # Open connection to the database
        conn = sqlite3.connect('userdata.db')
        c = conn.cursor()

        # Load user data
        c.execute("SELECT * FROM user_team WHERE userid=?", (session.get('userid'),))
        userteams = c.fetchall()
        for team in userteams:
            c.execute("SELECT teamname FROM teams WHERE teamid=?", (team[1],))
            teamname = c.fetchone()
            userdata.append([teamname[0], team[2], team[1]])

        # Close database connection
        conn.commit()
        conn.close()
        return render_template('index.html', userdata=userdata)
    else:
        return render_template('login.html')


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
                c.execute("""INSERT INTO users (username, name, email, hash)
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
                    session['username'] = request.form.get('username')
                    session['logged_in'] = True
                    session['userid'] = existing_user[0][0]
                    return redirect('/')
                else:
                    return "Invalid login credentials"


@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect('/')


@app.route('/newteam', methods=["GET", "POST"])
def createteam():
    if not session.get('logged_in'):
        return redirect('/')
    else:
        if request.method == "GET":
            return render_template('newteam.html')
        elif request.method == "POST":
            # Check for data in login form
            if not request.form.get('teamname'):
                return "Please enter a team name"
            else:
                # Open connection to the database
                new_team = request.form.get('teamname')
                conn = sqlite3.connect('userdata.db')
                c = conn.cursor()

                # Check for existing users
                c.execute("SELECT * FROM teams WHERE teamname=?", (new_team,))
                existing_team = c.fetchall()

                if len(existing_team) == 0:
                    c.execute("INSERT INTO teams (teamname) VALUES (?)", (new_team,))
                    c.execute("SELECT teamid FROM teams WHERE teamname=?", (new_team,))
                    new_teamid = c.fetchone()
                    c.execute("INSERT INTO user_team (userid, teamid) VALUES (?, ?)",(session.get('userid'), new_teamid[0],))

                    # Close database connection
                    conn.commit()
                    conn.close()
                    return redirect('/')

                else:
                    return "Team name is already in use"


@app.route('/team', methods=["GET", "POST"])
def team():
    if request.method == "POST":
        # Open connection to the database
        conn = sqlite3.connect('userdata.db')
        c = conn.cursor()

        # Load team name
        c.execute("SELECT teamname FROM teams WHERE teamid=?", (request.form.get('team_id'),))
        teamname = c.fetchone()[0]

        # Load team members
        memberslist = []
        c.execute("SELECT * FROM user_team WHERE teamid=?", (request.form.get('team_id'),))
        members = c.fetchall()
        for member in members:
            c.execute("SELECT username FROM users WHERE userid=?", (member[0],))
            membername = c.fetchone()[0]
            memberslist.append([membername, member[2]])

        # Close database connection
        conn.commit()
        conn.close()
        return render_template('team.html', team=teamname, members=memberslist)
    else:
        return render_template('index.html')


if __name__ == '__main__':
    app.run()
