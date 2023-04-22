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

    return render_template("sign_in.html", output = result)

@app.route('/sign_up/')
def sign_up():
    return render_template("sign_up.html")

# Run the app
if __name__ == '__main__':
    app.run(debug = True)