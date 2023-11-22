from flask import Flask, request, render_template, redirect, session
from flask_session import Session
import registration
from model.baseline_generation import generate
from midi_synthesizer import synthesize
from processing import postprocess
from db_connection import conn_pool
import datetime
import boto3

# Declare Flask app
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Bind '/' to main()
@app.route('/', methods=['GET', 'POST'])
def main():
    # Define default values of the form
    default_form = {
        'test' : 'debug box',
        'genre' : 'classical',
        'tempo' : 2,
        'length' : 1,
        'piano' : 'piano',
        'guitar' : 'guitar',
        'drums' : 'drums',
        'violin' : 'violin',
        'flute' : 'flute',
        'saxophone' : 'saxophone',
        'dynamics' : 2
    }
    # Handle form submission (2 cases)
    if request.method == "POST":
        # START 'GENERATE MUSIC' CASE
        if request.form["action"] == "Generate":
            # Print form data for debug purposes
            form = request.form
            print("FORM DATA")
            print(form)
            print("END OF FORM DATA", flush=True)

            # Generate & edit song
            filepath = generate()
            print("FILEPATH:", filepath)
            postprocess(filepath, request.form) # Alters instruments, tempo, dynamic
            synthesize(filepath) # Creates WAV from MIDI

            # Update page
            return render_template("home.html", output=filepath, params=request.form)
        # END 'GENERATE MUSIC' CASE
        # START 'BOOKMARK SONG' CASE
        elif request.form["action"] == "Bookmark": 
            # Get connection, make cursor
            conn = conn_pool.connect()
            cursor = conn.cursor()

            # Set up arguments for upload
            username=session["username"]
            timestamp = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            song_name = request.form["song_name"]
            if(song_name==""):
                song_name = timestamp
            print("Adding bookmark for", username, "created at", timestamp, "named", song_name)

            # Upload bookmark to s3
            uploaded_filename = username + "_" + song_name
            s3 = boto3.resource('s3',
                aws_access_key_id='AKIA6IAKFM3XLCMLYVPQ',
                aws_secret_access_key='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') 
            bucket = s3.Bucket('cmpe295-riffmuse-generated-music')
            
            bucket.upload_file('static/test_output.mid', uploaded_filename+'.mid')
            midi_link = 'https://cmpe295-riffmuse-generated-music.s3.us-west-1.amazonaws.com/'+uploaded_filename+'.mid'
            
            bucket.upload_file('static/test_output.wav', uploaded_filename+'.wav')
            wav_link  = 'https://cmpe295-riffmuse-generated-music.s3.us-west-1.amazonaws.com/'+uploaded_filename+'.wav'

            # Set up other arguments
            map = { '1':'slow', '2':'medium', '3':'fast'}
            tempo = map[ request.form["tempo"] ]

            map = { '1':'short', '2':'medium', '3':'long'}
            length = map[ request.form["length"] ]

            map = { '1':'soft', '2':'medium', '3':'loud'}
            dynamics = map[ request.form["dynamics"] ]

            instruments = ""
            if 'piano' in request.form:
                instruments += "piano "
            if 'guitar' in request.form:
                instruments += "guitar "
            if 'drums' in request.form:
                instruments += "drums "
            if 'violin' in request.form:
                instruments += "violin "
            if 'flute' in request.form:
                instruments += "flute "
            if 'saxophone' in request.form:
                instruments += "saxophone "
            
            # Insert new bookmark entry in database
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

            # Redirect page
            return redirect('/bookmarks/')
        # END 'BOOKMARK SONG' CASE
    # Render default page
    return render_template("home.html", output = "", params=default_form)

@app.route('/faq/')
def faq():
    return render_template("faq.html")

@app.route('/sign_in/', methods=['GET', 'POST'])
def sign_in():
    # Handle user's sign in request
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")

        # If details are correct, redirect to homepage
        if registration.authenticate_user(username, password, debug=True):
            result = "Sign in successful"
            session["logged_in"] = True
            session["username"] = username
            return redirect("/") 
        # If details are wrong, display error message
        else:
            result = "Sign in failed"

    # Default page has no result message
    else:
        result = ""
    return render_template("sign_in.html", output = result)

@app.route('/sign_up/', methods=['GET', 'POST'])
def sign_up():
    # Handle user's sign up request
    if request.method == "POST":
        username   = request.form.get("username").lower()
        email      = request.form.get("email")
        password   = request.form.get("password")
        password2  = request.form.get("confirm password")

        # Validate/Sanitize user input
        form_is_ok = registration.check_params(username, email, password, password2)
        print(form_is_ok)

        # If all input is valid, try registering the user
        if form_is_ok[0]:
            # If registration works, redirect to homepage
            if registration.add_user(username, email, password, debug=True):
                result = "Thanks for signing up!"
                session["logged_in"] = True
                session["username"] = username
                return redirect("/")
            # If there was some problem with registration, display error message
            else:
                result = "Sorry, something went wrong."
        # If some input is invalid, display corresponding error message
        else:
            result = "Sign up failed:\n" + form_is_ok[1]
    
    # Default page has no result message
    else:
        result = ""
    return render_template("sign_up.html", output = result)

@app.route('/sign_out/')
def sign_out():
    # Reset session variables
    session["logged_in"] = False
    session["username"] = None
    # Redirect to homepage
    return redirect("/")

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

    # Determine how long ago each bookmark was created
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

    # Render page with bookmark data
    return render_template("bookmarks.html", input = bookmarkData) 

@app.route('/bookmarks/delete=<time_created>', methods=['GET', 'POST'])
def delete_bookmark(time_created):
    print("Deleting bookmark created at", time_created)
    # Get connection, make cursor
    conn = conn_pool.connect()
    cursor = conn.cursor()

    # Run query to delete bookmark
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

    # Return user to bookmarks page
    return redirect('/bookmarks/')

# Run the app
if __name__ == '__main__':
    app.run(debug = True)