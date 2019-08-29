from flask import Flask, render_template, redirect, request, session, url_for
import mysql.connector as mysql
import calendar
from datetime import datetime
from passlib.hash import sha256_crypt
from config import secret_key, db

app = Flask(__name__)

app.secret_key = secret_key
calendar.setfirstweekday(calendar.SUNDAY)


@app.route('/')
def home():
    if session.get('logged_in'):
        userdata = []
        # Open connection to the database
        conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
        c = conn.cursor()

        # Load user data
        c.execute("SELECT * FROM user_team WHERE userid=%s", (session.get('userid'),))
        userteams = c.fetchall()
        for team in userteams:
            c.execute("SELECT teamname FROM teams WHERE teamid=%s", (team[1],))
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
        return render_template('register.html', success="false", fail="false")
    elif request.method == "POST":
        # Check for data in registration form
        if not request.form.get('name') or \
                not request.form.get('username') or \
                not request.form.get('email') or \
                not request.form.get('password') or \
                not request.form.get('confirm'):
            message = "Please fully fill out registration form."
            return render_template('register.html', message=message, success="false", fail="true")
        else:
            # Open connection to the database
            conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=%s", (request.form.get('username'),))
            existing_user = c.fetchall()
            c.execute("SELECT * FROM users WHERE email=%s", (request.form.get('email'),))
            existing_email = c.fetchall()
            if len(existing_user) != 0:
                conn.commit()
                conn.close()
                message = "Sorry, that username is already in use."
                return render_template('register.html', message=message, success="false", fail="true")
            if len(existing_email) != 0:
                conn.commit()
                conn.close()
                message = "That email is already associated with an account. " \
                          "If you have already registered please use the above link to login."
                return render_template('register.html', message=message, success="false", fail="true")
            else:
                hashed_pass = sha256_crypt.hash(request.form.get('password'))
                # Add user to database
                c.execute("""INSERT INTO users (username, name, email, hash)
                            VALUES (%s, %s, %s, %s)""", (request.form.get('username'), request.form.get('name'),
                                                         request.form.get('email'), hashed_pass,))
                # Close database connection
                conn.commit()
                conn.close()

                return render_template('register.html', success="true", fail="false")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html', fail="false")
    elif request.method == "POST":
        # Check for data in login form
        if not request.form.get('username') or not request.form.get('password'):
            message = "Please enter username and password to login"
            return render_template('login.html', fail="true", message=message)
        else:
            # Open connection to the database
            conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=%s", (request.form.get('username'),))
            existing_user = c.fetchall()

            # Close database connection
            conn.commit()
            conn.close()

            # Check for valid username
            if len(existing_user) == 0:
                message = "Invalid user name"
                return render_template('login.html', fail="true", message=message)
            else:
                # Check for valid password
                if sha256_crypt.verify(request.form.get('password'), existing_user[0][4]):
                    session['username'] = request.form.get('username')
                    session['logged_in'] = True
                    session['userid'] = existing_user[0][0]
                    return redirect('/')
                else:
                    message = "Invalid login credentials"
                    return render_template('login.html', fail="true", message=message)


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
                conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
                c = conn.cursor()

                # Check for existing users
                c.execute("SELECT * FROM teams WHERE teamname=%s", (new_team,))
                existing_team = c.fetchall()

                if len(existing_team) == 0:
                    c.execute("INSERT INTO teams (teamname) VALUES (%s)", (new_team,))
                    c.execute("SELECT teamid FROM teams WHERE teamname=%s", (new_team,))
                    new_teamid = c.fetchone()
                    c.execute("INSERT INTO user_team (userid, teamid) VALUES (%s, %s)",
                              (session.get('userid'), new_teamid[0],))

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
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        else:
            # Open connection to the database
            conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
            c = conn.cursor()

            # Load team name
            c.execute("SELECT teamname FROM teams WHERE teamid=%s", (team_id,))
            teamname = c.fetchone()[0]
            teamdata.append(teamname)
            teamdata.append(request.form.get('team_id'))

            # Load team members
            memberslist = []
            c.execute("SELECT * FROM user_team WHERE teamid=%s", (team_id,))
            members = c.fetchall()
            for member in members:
                c.execute("SELECT username FROM users WHERE userid=%s", (member[0],))
                membername = c.fetchone()[0]
                memberslist.append([membername, member[2]])

            # Load team events
            events = []
            c.execute("SELECT * FROM events WHERE teamid=%s", (team_id,))
            allevents = c.fetchall()
            for oneevent in allevents:
                c.execute("SELECT username FROM users WHERE userid=%s", (oneevent[2],))
                usersname = c.fetchone()[0]
                date = oneevent[5]
                time = (datetime.min + (oneevent[6])).time()
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
            formatcal = "<div id=" + thismonthid + ">" + currentmonthcal + "</div>" + \
                        "<div id=" + nextmonthid + ">" + nextmonthcal + "</div>"
            active_months = [[today.month, today.year], [next_month, next_year]]
            return render_template('team.html', team=teamdata, members=memberslist, events=events, calendar=formatcal,
                                   act=active_months)
    else:
        return redirect('/')


@app.route('/addmember', methods=["GET", "POST"])
def addmember():
    if request.method == "POST":
        if not request.form.get('team') or not request.form.get('newmember'):
            return redirect('/')
        else:
            # Open database connection
            conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
            c = conn.cursor()

            # Find user id for new member
            c.execute("SELECT userid FROM users WHERE username=%s", (request.form.get('newmember'),))
            memberid = c.fetchone()

            # Load team information
            teamdata = request.form.get('team')
            teamid = teamdata.replace("'", "").strip('[]').split(',')

            # Check that the submitted username was valid
            if not memberid:
                conn.commit()
                conn.close()
                message = request.form.get('newmember') + " is not a valid username"
                return render_template('timed_redirect.html', message=message, team_id=teamid[1])
            else:
                # Check if user is already a member of the team
                c.execute("SELECT * FROM user_team WHERE userid=%s AND teamid=%s", (memberid[0], teamid[1]))
                inteam = c.fetchone()
                if not inteam:
                    # Add user to team
                    c.execute("INSERT INTO user_team (userid, teamid) VALUES (%s,%s)", (memberid[0], teamid[1]))
                    conn.commit()
                    conn.close()
                    message = request.form.get('newmember') + " has been added to the team."
                    return render_template('timed_redirect.html', message=message, team_id=teamid[1])
                else:
                    conn.commit()
                    conn.close()
                    message = request.form.get('newmember') + " is already a member of the team."
                    return render_template('timed_redirect.html', message=message, team_id=teamid[1])
    else:
        return redirect('/')


@app.route('/leave', methods=["GET", "POST"])
def leave():
    if request.method == "POST":
        conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
        c = conn.cursor()

        # Remove user from team
        c.execute("DELETE FROM user_team WHERE userid=%s AND teamid=%s",
                  (session.get('userid'), (request.form.get('team_id')),))

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
            message = "Please fully completed event form"
            return render_template('timed_redirect.html', message=message, team_id=request.form.get('team'))
        else:
            # Add event to the database
            conn = mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])
            c = conn.cursor()
            data = (
                request.form.get('team'), str(session.get('userid')),
                request.form.get('title'), request.form.get('details'),
                request.form.get('date'), request.form.get('time')
            )
            c.execute(
                "INSERT INTO events (teamid, userid, title, details, `date`, `time`) VALUES (%s, %s, %s, %s, %s, %s)",
                data)

            # Close database connection
            conn.commit()
            conn.close()

            return redirect(url_for('team', team_id_form=request.form.get('team')), code=307)
    else:
        return redirect('/')


if __name__ == '__main__':
    app.run()
