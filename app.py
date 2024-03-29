from flask import Flask, render_template, redirect, request, session, url_for
import mysql.connector as mysql
import calendar
from datetime import datetime
from passlib.hash import sha256_crypt
from config import secret_key, db

app = Flask(__name__)

app.secret_key = secret_key
calendar.setfirstweekday(calendar.SUNDAY)


def connection():
    return mysql.connect(host=db['host'], user=db['user'], passwd=db['password'], database=db['database'])


def close(conn):
    conn.commit()
    conn.close()


def get_teamname(c, teamid):
    c.execute("SELECT teamname FROM teams WHERE teamid=%s", (teamid,))
    return c.fetchone()[0]


def get_username(c, userid):
    c.execute("SELECT username FROM users WHERE userid=%s", (userid,))
    return c.fetchone()[0]


@app.route('/')
def home():
    if session.get('logged_in'):
        userdata = []
        # Open connection to the database
        conn = connection()
        c = conn.cursor()

        # Load user data
        c.execute("SELECT * FROM user_team WHERE userid=%s", (session.get('userid'),))
        userteams = c.fetchall()
        if not userteams:
            noteam = "true"
        else:
            for eachteam in userteams:
                teamname = get_teamname(c, eachteam[1])
                userdata.append([teamname, eachteam[2], eachteam[1], eachteam[4]])
            noteam = "false"

        # Close database connection
        close(conn)
        return render_template('index.html', userdata=userdata, noteam=noteam)
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
            conn = connection()
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=%s", (request.form.get('username'),))
            existing_user = c.fetchall()
            c.execute("SELECT * FROM users WHERE email=%s", (request.form.get('email'),))
            existing_email = c.fetchall()
            if len(existing_user) != 0:
                close(conn)
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
                close(conn)
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
            conn = connection()
            c = conn.cursor()

            # Check for existing users
            c.execute("SELECT * FROM users WHERE username=%s", (request.form.get('username'),))
            existing_user = c.fetchall()

            # Close database connection
            close(conn)

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
                message = "Please enter a team name."
                return render_template('timed_redirect.html', message=message, team_id="false")
            else:
                # Open connection to the database
                conn = connection()
                c = conn.cursor()

                # Check for an existing team with that name
                new_team = request.form.get('teamname')
                c.execute("SELECT * FROM teams WHERE teamname=%s", (new_team,))
                existing_team = c.fetchall()

                if len(existing_team) == 0:
                    c.execute("INSERT INTO teams (teamname) VALUES (%s)", (new_team,))
                    c.execute("SELECT teamid FROM teams WHERE teamname=%s", (new_team,))
                    new_teamid = c.fetchone()
                    c.execute("INSERT INTO user_team (userid, teamid, role, isadmin, accept) VALUES (%s, %s, %s, %s, %s)",
                              (session.get('userid'), new_teamid[0], "Leader", True, True))

                    # Close database connection
                    close(conn)
                    return redirect('/')

                else:
                    close(conn)
                    message = "Sorry, " + new_team + " is already in use."
                    return render_template('timed_redirect.html', message=message, team_id="false")


@app.route('/team', methods=["GET", "POST"])
def team():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        else:
            # Open connection to the database
            conn = connection()
            c = conn.cursor()

            # Load team name
            teamname = get_teamname(c, team_id)
            teamdata = [teamname, team_id]

            # Check if user is admin
            c.execute("SELECT isadmin FROM user_team WHERE teamid=%s AND userid=%s", (team_id, session.get('userid')))
            isadmin = c.fetchone()[0]

            # Load team members
            memberslist = []
            c.execute("SELECT * FROM user_team WHERE teamid=%s AND accept=%s", (team_id, True),)
            members = c.fetchall()
            for member in members:
                membername = get_username(c, member[0])
                memberslist.append([membername, member[2]])

            # Load team events
            events = []
            c.execute("SELECT * FROM events WHERE teamid=%s", (team_id,))
            allevents = c.fetchall()
            for oneevent in allevents:
                usersname = get_username(c, oneevent[2])
                date = oneevent[5]
                time = (datetime.min + (oneevent[6])).time()
                eventtime = date.strftime("%a %b %d %Y") + " at " + time.strftime("%I:%M %p")
                events.append([oneevent[3], oneevent[4], eventtime, usersname])


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

            # Gather messages
            messages = []
            c.execute("SELECT userid, subject, message, sent FROM messages WHERE teamid=%s ORDER BY sent DESC", (team_id,))
            allmessage = c.fetchall()[:5]
            for eachmessage in allmessage:
                user_sent = get_username(c, eachmessage[0])
                sent = eachmessage[3].strftime("%I:%M %p") + " on " + eachmessage[3].strftime("%m/%d/%y")
                mes_text = eachmessage[2] if len(eachmessage[2]) < 100 else eachmessage[2][:100] + '...'
                messages.append([user_sent, eachmessage[1], mes_text, sent])

            # Close database connection
            close(conn)

            return render_template('team.html', team=teamdata, members=memberslist, events=events, calendar=formatcal,
                                   act=active_months, messages=messages, isadmin=isadmin)
    else:
        return redirect('/')


@app.route('/addmember', methods=["GET", "POST"])
def addmember():
    if request.method == "POST":
        if not request.form.get('team') or not request.form.get('newmember'):
            return redirect('/')
        else:
            # Open database connection
            conn = connection()
            c = conn.cursor()

            # Find user id for new member
            c.execute("SELECT userid FROM users WHERE username=%s", (request.form.get('newmember'),))
            memberid = c.fetchone()

            # Load team information
            teamdata = request.form.get('team')
            teamid = teamdata.replace("'", "").strip('[]').split(',')

            # Check that the submitted username was valid
            if not memberid:
                close(conn)
                message = request.form.get('newmember') + " is not a valid username"
                return render_template('timed_redirect.html', message=message, team_id=teamid[1])
            else:
                # Check if user is already a member of the team
                c.execute("SELECT * FROM user_team WHERE userid=%s AND teamid=%s", (memberid[0], teamid[1]))
                inteam = c.fetchone()
                if not inteam:
                    # Add user to team
                    c.execute("INSERT INTO user_team (userid, teamid, accept) VALUES (%s,%s,%s)", (memberid[0], teamid[1], False))
                    close(conn)
                    message = request.form.get('newmember') + " has been sent an invite to the team."
                    return render_template('timed_redirect.html', message=message, team_id=teamid[1])
                else:
                    close(conn)
                    message = request.form.get('newmember') + " is already a member of the team."
                    return render_template('timed_redirect.html', message=message, team_id=teamid[1])
    else:
        return redirect('/')


@app.route('/messageboard', methods=["GET", "POST"])
def messageboard():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        else:
            # Open connection to the database
            conn = connection()
            c = conn.cursor()

            # Load team name
            teamname = get_teamname(c, team_id)
            teamdata = [teamname, team_id]

            # Gather messages
            messages = []
            c.execute("SELECT userid, subject, message, sent FROM messages WHERE teamid=%s ORDER BY sent DESC", (team_id,))
            allmessage = c.fetchall()
            for eachmessage in allmessage:
                user_sent = get_username(c, eachmessage[0])
                sent = eachmessage[3].strftime("%I:%M %p") + " on " + eachmessage[3].strftime("%m/%d/%y")
                messages.append([user_sent, eachmessage[1], eachmessage[2], sent])

            # Close database connection
            close(conn)

            return render_template('messageboard.html', team=teamdata, messages=messages)
    else:
        return redirect('/')


@app.route('/join', methods=["GET", "POST"])
def join():
    if request.method == "POST":
        conn = connection()
        c = conn.cursor()

        # Remove user from team
        c.execute("UPDATE user_team SET accept = true WHERE userid=%s AND teamid=%s",
                  (session.get('userid'), (request.form.get('team_id')),))

        # Close database connection
        close(conn)
        return redirect('/')

    else:
        redirect('/')

@app.route('/leave', methods=["GET", "POST"])
def leave():
    if request.method == "POST":
        conn = connection()
        c = conn.cursor()

        # Remove user from team
        c.execute("DELETE FROM user_team WHERE userid=%s AND teamid=%s",
                  (session.get('userid'), (request.form.get('team_id')),))

        # Close database connection
        close(conn)
        return redirect('/')
    else:
        return redirect('/')


@app.route('/newevent', methods=["GET", "POST"])
def newevent():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        return render_template("newevent.html", team=team_id)
    else:
        return redirect('/')


@app.route('/addevent', methods=["GET", "POST"])
def addevent():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        # Check for user input
        if not request.form.get('title') or \
                not request.form.get('date') or \
                not request.form.get('time'):
            message = "Please fully completed event form"
            return render_template('timed_redirect.html', message=message, team_id=team_id)
        else:
            # Add event to the database
            conn = connection()
            c = conn.cursor()
            data = (
                team_id, str(session.get('userid')),
                request.form.get('title'), request.form.get('details'),
                request.form.get('date'), request.form.get('time')
            )
            c.execute(
                "INSERT INTO events (teamid, userid, title, details, `date`, `time`) VALUES (%s, %s, %s, %s, %s, %s)",
                data)

            # Clear out old events from the database
            today = datetime.today()
            if today.month == 1:
                last_month = 12
                last_year = today.year - 1
            else:
                last_month = today.month - 1
                last_year = today.year
            old_date_start = str(last_year) + "-" + str(last_month) + "-01"
            old_date_end = str(last_year) + "-" + str(last_month) + "-31"
            c.execute("DELETE FROM events WHERE date between %s AND %s", (old_date_start, old_date_end,))

            # Close database connection
            close(conn)

            return redirect(url_for('team', team_id_form=team_id), code=307)
    else:
        return redirect('/')


@app.route('/mail', methods=["GET", "POST"])
def sendmail():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')
        # Get all team accepted team members emails
        conn = connection()
        c = conn.cursor()
        c.execute("SELECT userid FROM user_team WHERE teamid=%s", (team_id,))
        members = c.fetchall()
        emails = []
        for member in members:
            c.execute("SELECT email FROM users WHERE userid=%s", (member))
            email = c.fetchone()[0]
            emails.append(email)

        # Get input from form
        data = (team_id, session.get('userid'), request.form.get('subject'), request.form.get('body'))

        # Send message
        c.execute("INSERT INTO messages (teamid, userid, subject, message) VALUES (%s, %s, %s, %s)", data)
        close(conn)

        return redirect(url_for('team', team_id_form=team_id), code=307)

    else:
        redirect('/')


@app.route('/inbox', methods=["GET", "POST"])
def inbox():
    if session.get('logged_in'):
        messages = []
        conn = connection()
        c = conn.cursor()
        c.execute("SELECT teamid FROM user_team WHERE userid=%s", (session.get('userid'),))
        teams = c.fetchall()[0]
        for team in teams:
            teamname = get_teamname(c, team)
            c.execute("SELECT * FROM messages WHERE teamid=%s ORDER BY sent DESC", (team,))
            allmessage = c.fetchall()
            for eachmessage in allmessage:
                user_sent = get_username(c, eachmessage[1])
                sent = eachmessage[5].strftime("%I:%M %p") + " on " + eachmessage[5].strftime("%m/%d/%y")
                mes_text = eachmessage[4] if len(eachmessage[4]) < 100 else eachmessage[4][:100] + '...'
                messages.append([teamname, user_sent, eachmessage[3], mes_text, sent, eachmessage[0]])
        close(conn)
        return render_template('/inbox.html', messages=messages)
    else:
        return redirect('/')


@app.route('/admin', methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get('team_id'):
            team_id = request.form.get('team_id')
        else:
            team_id = request.args.get('team_id_form')
        if not team_id:
            return redirect('/')

        # Confirm that user has admin privilege
        conn = connection()
        c = conn.cursor()
        c.execute("SELECT isadmin FROM user_team WHERE userid=%s AND teamid=%s",
                  (session.get('userid'), team_id,))
        isadmin = c.fetchone()[0]
        if not isadmin:
            close(conn)
            message = "Sorry, you do not have admin rights"
            return render_template('timed_redirect.html', message=message)
        elif isadmin:
            # Load admin page

            # Get team info
            teamname = get_teamname(c, team_id)
            teamdata = [teamname, team_id]

            # Load team members
            memberslist = []
            c.execute("SELECT * FROM user_team WHERE teamid=%s AND accept=%s", (team_id, True), )
            members = c.fetchall()
            for member in members:
                membername = get_username(c, member[0])
                memberslist.append([membername, member[2], member[0]])

            # Load team events
            events = []
            c.execute("SELECT * FROM events WHERE teamid=%s", (team_id,))
            allevents = c.fetchall()
            for oneevent in allevents:
                usersname = get_username(c, oneevent[2],)
                date = oneevent[5]
                time = (datetime.min + (oneevent[6])).time()
                eventtime = date.strftime("%a %b %d %Y") + " at " + time.strftime("%I:%M %p")
                events.append([oneevent[3], oneevent[4], eventtime, usersname, oneevent[0]])

            # Gather messages
            messages = []
            c.execute("SELECT * FROM messages WHERE teamid=%s", (team_id,))
            allmessage = c.fetchall()
            for eachmessage in allmessage:
                user_sent = get_username(c, eachmessage[2])
                sent = eachmessage[5].strftime("%I:%M %p") + " on " + eachmessage[5].strftime("%m/%d/%y")
                messages.append([user_sent, eachmessage[3], eachmessage[4], sent, eachmessage[0]])

            # Close database connection
            close(conn)
            return render_template('teamadmin.html', team=teamdata, members=memberslist, events=events, messages=messages)
        else:
            # Something went wrong
            close(conn)
            message = "Sorry, something went wrong"
            return render_template('timed_redirect.html', message=message)
    else:
        return redirect('/')


@app.route('/deletemessage', methods=["GET", "POST"])
def deletemess():
    if request.method == "POST":
        if not request.form.get('mess_id'):
            return redirect('/')
        else:
            conn = connection()
            c = conn.cursor()
            c.execute("DELETE FROM messages WHERE messageid=%s", (request.form.get('mess_id'),))
            close(conn)
            return redirect(url_for('admin', team_id_form=request.form.get('team_id')), code=307)
    else:
        return redirect('/')


@app.route('/deleteevent', methods=["GET", "POST"])
def deleteevent():
    if request.method == "POST":
        if not request.form.get('event_id'):
            return redirect('/')
        else:
            conn = connection()
            c = conn.cursor()
            c.execute("DELETE FROM events WHERE id=%s", (request.form.get('event_id'),))
            close(conn)
            return redirect(url_for('admin', team_id_form=request.form.get('team_id')), code=307)
    else:
        return redirect('/')


@app.route('/changerole', methods=["GET", "POST"])
def changerole():
    if request.method == "POST":
        if not request.form.get('member_id'):
            return redirect('/')
        else:
            conn = connection()
            c = conn.cursor()
            data = (request.form.get('role'), request.form.get('member_id'), request.form.get('team_id'))
            c.execute("UPDATE user_team SET role = %s WHERE userid=%s AND teamid=%s", data)
            close(conn)
            return redirect(url_for('admin', team_id_form=request.form.get('team_id')), code=307)
    else:
        return redirect('/')

@app.route('/removeuser', methods=["GET", "POST"])
def removeuser():
    if request.method == "POST":
        if not request.form.get('member_id'):
            return redirect('/')
        else:
            conn = connection()
            c = conn.cursor()
            c.execute("DELETE FROM user_team WHERE userid=%s AND teamid=%s",
                      (request.form.get('member_id'), request.form.get('team_id')))
            close(conn)
            return redirect(url_for('admin', team_id_form=request.form.get('team_id')), code=307)
    else:
        return redirect('/')


if __name__ == '__main__':
    app.run()
