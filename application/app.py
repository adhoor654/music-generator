from flask import Flask, request, render_template, redirect, session
from flask_session import Session
import pandas as pd
import joblib
import registration

PKL_FILEPATH = "ML integration/clf.pkl"

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
        
        # Unpickle classifier
        clf = joblib.load(PKL_FILEPATH)
        
        # Get values through input bars
        height = request.form.get("height")
        weight = request.form.get("weight")
        
        # Put inputs to dataframe
        X = pd.DataFrame([[height, weight]], columns = ["Height", "Weight"])
        
        # Get prediction
        prediction = clf.predict(X)[0]
        
    else:
        prediction = ""
        
    return render_template("home.html", output = prediction)

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
    return render_template("bookmarks.html")

# Run the app
if __name__ == '__main__':
    app.run(debug = True)