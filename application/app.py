from flask import Flask, request, render_template, redirect, session
from flask_session import Session
import pandas as pd
import joblib
import registration
from model.baseline_generation import generate
from midi_synthesizer import synthesize
from db_connection import conn_pool
import datetime
import boto3

# Declare a Flask app
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Bind '/' to main()
@app.route('/', methods=['GET', 'POST'])
def main():
    
    # If a form is submitted
    if request.method == "POST":
        if request.form["action"] == "Generate":        
            # Get values through input bars
            genre = request.form.get("genre")
            tempo = request.form["tempo"]
            length = request.form.get("length")
            instruments = request.form.getlist("instruments")
            dynamics = request.form.get("dynamics")

            # Put inputs to dataframe
            params = pd.DataFrame([[genre, tempo, length, instruments, dynamics]], columns = ["Genre", "Tempo", "Length", "Instruments", "Dynamics"])
            print(params)
            
            #Generate & synthesize song
            filepath = generate()
            print(filepath)

            synthesize(filepath)

            #rename and pack files for potential upload?

            #make Generation settings textfile

            music = filepath
            return render_template("home.html", output = music)
        elif request.form["action"] == "Bookmark": 
            # Get connection, make cursor
            conn = conn_pool.connect()
            cursor = conn.cursor()

            #Set up arguments for upload
            username=session["username"]
            timestamp = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            print("Adding bookmark created at", timestamp)

            song_name = request.form["song_name"]
            if(song_name==""):
                song_name = timestamp
            print("THIS BOOKMARK IS NAMED", song_name)

            #Upload bookmark to s3
            uploaded_filename = username + "_" + song_name
            s3 = boto3.resource('s3',
                aws_access_key_id='AWS_ACCESS_KEY',
                aws_secret_access_key='SECRET_ACCESS_KEY')
            bucket = s3.Bucket('cmpe295-riffmuse-generated-music')
            
            bucket.upload_file('static/test_output.mid', uploaded_filename+'.mid')
            midi_link = 'https://cmpe295-riffmuse-generated-music.s3.us-west-1.amazonaws.com/'+uploaded_filename+'.mid'
            
            bucket.upload_file('static/test_output.wav', uploaded_filename+'.wav')
            wav_link  = 'https://cmpe295-riffmuse-generated-music.s3.us-west-1.amazonaws.com/'+uploaded_filename+'.wav'

            #Set up other arguments
            match request.form["tempo"]:
                case "1":
                    tempo = "slow"
                case "2":
                    tempo = "medium"
                case "3":
                    tempo = "fast"

            match request.form["length"]:
                case "1":
                    length = "short"
                case "2":
                    length = "medium"
                case "3":
                    length = "long"

            match request.form["dynamics"]:
                case "1":
                    dynamics = "soft"
                case "2":
                    dynamics = "medium"
                case "3":
                    dynamics = "loud"

            comma = ", "
            instruments = comma.join(request.form.getlist("instruments"))

            #Insert new bookmark entry in database
            cursor.execute("""
                    INSERT INTO Bookmarks VALUES (%(username)s, %(song_name)s, %(time_created)s, %(genre)s, %(tempo)s, %(length)s, %(instruments)s, %(dynamics)s, %(midi_link)s, %(wav_link)s)""",
                    {
                        'username' : username,
                        'song_name' : song_name,
                        'time_created' : timestamp,
                        'genre' : request.form.get("genre"),
                        'tempo' : tempo,
                        'length' : length,
                        'instruments' : instruments,
                        'dynamics' : dynamics,
                        'midi_link' : midi_link,
                        'wav_link' : wav_link
                    } )
            conn.commit()
            conn.close()

            return redirect('/bookmarks/')
    return render_template("home.html", output = "")

@app.route('/faq/')
def faq():
    return render_template("faq.html")

@app.route('/sign_in/', methods=['GET', 'POST'])
def sign_in():
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        
        if registration.authenticate_user(username, password, debug=True):
            result = "Sign in successful"
            session["logged_in"] = True
            session["username"] = username
            return redirect("/") #redirect to home page
        else:
            result = "Sign in failed"

    else:
        result = ""

    return render_template("sign_in.html", output = result)

@app.route('/sign_up/', methods=['GET', 'POST'])
def sign_up():
    if request.method == "POST":
        username   = request.form.get("username").lower()
        email      = request.form.get("email")
        password   = request.form.get("password")
        password2  = request.form.get("confirm password")

        form_is_ok = registration.check_params(username, email, password, password2)
        print(form_is_ok)
        if form_is_ok[0]:
            if registration.add_user(username, email, password, debug=True):
                result = "Thanks for signing up!"
                session["logged_in"] = True
                session["username"] = username
                return redirect("/") #redirect to home page
            else:
                result = "Sorry, something went wrong."
        else:
            result = "Sign up failed:\n" + form_is_ok[1]
    else:
        result = ""

    return render_template("sign_up.html", output = result)

@app.route('/sign_out/')
def sign_out():
    session["logged_in"] = False
    session["username"] = None
    return render_template("sign_out.html")

@app.route('/bookmarks/')
def bookmarks():
    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()

    # Grab all bookmark data for user
    username = session["username"]
    cursor.execute("""
            SELECT * 
            FROM  Bookmarks 
            WHERE username = %(username)s
            """, {
                'username' : username
            } )
    bookmarkData = cursor.fetchall()

    for row in bookmarkData:
        delta = (datetime.datetime.today() - row['time_created']).total_seconds()
        if (delta < 60): #Less than a minute
            timeDiff = "Less than 1 minute ago"
        elif (delta < 3600): #Less than an hour
            delta = str(int(delta / 60)) #Convert to minutes
            timeDiff = delta + " minute(s) ago"
        elif (delta < 86400): #Less than an day
            delta = str(int(delta / 3600)) #Convert to hours
            timeDiff = delta + " hour(s) ago"
        elif (delta < 2592000): #Less than a month
            delta = str(int(delta / 86400)) #Convert to days
            timeDiff = delta + " day(s) ago"
        else:
            timeDiff="More than one month ago"
        row['username'] = timeDiff
    print(bookmarkData)
    conn.close()
    return render_template("bookmarks.html", input = bookmarkData) 

@app.route('/bookmarks/delete=<time_created>', methods=['GET', 'POST'])
def delete_bookmark(time_created):
    print("Deleting bookmark created at", time_created)
    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()

    username=session["username"]
    cursor.execute("""
            DELETE FROM Bookmarks 
            WHERE username = %(username)s
                AND time_created = %(time_created)s
            """, {
                'username' : username,
                'time_created' : time_created 
            } )
    conn.commit()
    conn.close()
    return redirect('/bookmarks/')

@app.route('/bookmarks/new', methods=['GET', 'POST'])
def add_bookmark():
    print("Adding bookmark created at", datetime.datetime.today())
    # Get connection, make cursor
    # conn = conn_pool.connect()
    # cursor = conn.cursor()

    # username=session["username"]
    # cursor.execute("""
    #         DELETE FROM Bookmarks 
    #         WHERE username = %(username)s
    #             AND time_created = %(time_created)s
    #         """, {
    #             'username' : username,
    #             'time_created' : time_created 
    #         } )
    # conn.commit()
    # conn.close()
    return redirect('/bookmarks/')

# Run the app
if __name__ == '__main__':
    app.run(debug = True)