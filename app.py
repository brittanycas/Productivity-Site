from flask import Flask, render_template, redirect, request, session, escape
import sqlite3
import calendar
from datetime import datetime
from passlib.hash import sha256_crypt
from config import secret_key

app = Flask(__name__)

app.secret_key = secret_key
calendar.setfirstweekday(calendar.SUNDAY)

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
        return render_template('landing.html')


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
                conn.commit()
                conn.close()
                return "username is already in use"
            if len(existing_email) != 0:
                conn.commit()
                conn.close()
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
                    conn.commit()
                    conn.close()
                    return "Team name is already in use"


@app.route('/team', methods=["GET", "POST"])
def team():
    if request.method == "POST":
        teamdata = []
        # Open connection to the database
        conn = sqlite3.connect('userdata.db')
        c = conn.cursor()

        # Load team name
        c.execute("SELECT teamname FROM teams WHERE teamid=?", (request.form.get('team_id'),))
        teamname = c.fetchone()[0]
        teamdata.append(teamname)
        teamdata.append(request.form.get('team_id'))

        # Load team members
        memberslist = []
        c.execute("SELECT * FROM user_team WHERE teamid=?", (request.form.get('team_id'),))
        members = c.fetchall()
        for member in members:
            c.execute("SELECT username FROM users WHERE userid=?", (member[0],))
            membername = c.fetchone()[0]
            memberslist.append([membername, member[2]])

        # Load team events
        events = []
        c.execute("SELECT * FROM events WHERE teamid=?", (request.form.get('team_id'),))
        allevents = c.fetchall()
        for oneevent in allevents:
            c.execute("SELECT username FROM users WHERE userid=?", (oneevent[2],))
            usersname = c.fetchone()[0]
            date = datetime.strptime(oneevent[5], "%Y-%m-%d")
            time = datetime.strptime(oneevent[6], "%H:%M")
            eventtime = date.strftime("%a %b %d %Y") + " at " + time.strftime("%I:%M %p")
            events.append([oneevent[3], oneevent[4], eventtime, usersname])
        # Close database connection
        conn.commit()
        conn.close()

        # Render calendar for next two months
        today = datetime.today()
        newcal = calendar.HTMLCalendar(firstweekday=6)
        if today.month == 12:
            next_month = 1
            next_year = today.year + 1
        else:
            next_month = today.month + 1
            next_year = today.year
        currentmonthcal = newcal.formatmonth(today.year, today.month, withyear=True)
        nextmonthcal = newcal.formatmonth(next_year, next_month, withyear=True)
        thismonthid = str(today.month) + "-" + str(today.year)
        nextmonthid = str(next_month) + "-" + str(next_year)
        formatcal = "<div id="+ thismonthid + ">" + currentmonthcal +"</div>" + \
                    "<div id="+ nextmonthid + ">" + nextmonthcal + "</div>"
        active_months = [[today.month, today.year], [next_month, next_year]]
        return render_template('team.html', team=teamdata, members=memberslist, events=events, calendar=formatcal, act=active_months)
    else:
        return render_template('index.html')

@app.route('/addmember', methods=["GET", "POST"])
def addmember():
    if request.method == "POST":
        if not request.form.get('team') or not request.form.get('newmember'):
            return redirect('/')
        else:
            # Open database connection
            conn = sqlite3.connect('userdata.db')
            c = conn.cursor()

            # Find user id for new member
            c.execute("SELECT userid FROM users WHERE username=?", (request.form.get('newmember'),))
            memberid = c.fetchone()

            # Check that the submitted username was valid
            if not memberid:
                conn.commit()
                conn.close()
                return "User does not exist"
            else:
                #Add user to team
                teamdata = request.form.get('team')
                teamid = teamdata.replace("'", "").strip('[]').split(',')
                c.execute("INSERT INTO user_team (userid, teamid) VALUES (?,?)", (memberid[0], teamid[1]))
                conn.commit()
                conn.close()
                return "User has been added"


    else:
        return redirect('/')


@app.route('/leave', methods=["GET", "POST"])
def leave():
    if request.method == "POST":
        conn = sqlite3.connect('userdata.db')
        c = conn.cursor()

        # Remove user from team
        c.execute("DELETE FROM user_team WHERE userid=? AND teamid=?", (session.get('userid'), (request.form.get('team_id')),))

        # Close database connection
        conn.commit()
        conn.close()
        return redirect('/')
    else:
        return redirect('/')


@app.route('/newevent', methods=["GET", "POST"])
def newevent():
    if request.method == "POST":
        return render_template("newevent.html", team=request.form.get('team'))
    else:
        return redirect('/')


@app.route('/addevent', methods=["GET", "POST"])
def addevent():
    if request.method == "POST":
        # Check for user input
        if not request.form.get('title') or \
                not request.form.get('date') or \
                not request.form.get('time'):
            return "please fully fill out event form"
        else:
            # Add event to the database
            conn = sqlite3.connect('userdata.db')
            c = conn.cursor()

            c.execute("INSERT INTO events (teamid, userid, title, details, date, time, addedon) VALUES (?, ?, ?, ?, ?, ?, ?)",(
                        request.form.get('team'), session.get('userid'),
                        request.form.get('title'), request.form.get('details'),
                        request.form.get('date'), request.form.get('time'),
                        datetime.now(),))

            # Close database connection
            conn.commit()
            conn.close()
            return redirect('/')
    else:
        return redirect('/')


if __name__ == '__main__':
    app.run()
