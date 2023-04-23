from flask import Flask, request, render_template
import pandas as pd
import joblib
import login_register

PKL_FILEPATH = "ML integration/clf.pkl"

# Declare a Flask app
app = Flask(__name__)

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
        username = request.form.get("username")
        password = request.form.get("password")
        
        if login_register.authenticate_user(username, password, debug=True):
            result = "Sign in successful"
        else:
            result = "Sign in failed"

    else:
        result = ""

    return render_template("sign_in.html", output = result)

@app.route('/sign_up/', methods=['GET', 'POST'])
def sign_up():
    if request.method == "POST":
        username   = request.form.get("username")
        email      = request.form.get("email")
        password   = request.form.get("password")
        password2 = request.form.get("confirm password")

        form_is_ok = login_register.check_registration_params(username, email, password, password2)
        print(form_is_ok)
        if form_is_ok[0]:
            if login_register.add_user(username, email, password, debug=True):
                result = "Thanks for signing up!"
            else:
                result = "Sorry, something went wrong."
        else:
            result = "Sign up failed:\n" + form_is_ok[1]
    else:
        result = ""

    return render_template("sign_up.html", output = result)

# Run the app
if __name__ == '__main__':
    app.run(debug = True)