from flask import Flask, redirect, url_for, g, session, request, jsonify, render_template
from flask_oauthlib.client import OAuth, OAuthException
from flask_wtf import FlaskForm
from flask_table import Table, Col
from wtforms import SubmitField
from logging import Logger
import uuid
import os
import requests
import sys
import pypyodbc



app = Flask(__name__)
app.config["SECRET_KEY"] = 'secretkey'
oauth = OAuth(app)
SQL = pypyodbc.connect('Driver={ODBC Driver 17 for SQL Server};Server=;Database=;uid=;pwd=')





# Azure Login  Details:
tenant_name = ''
microsoft = oauth.remote_app(
	'microsoft',
	consumer_key='',
	consumer_secret='',
	request_token_params={'scope': 'offline_access User.Read'},
	base_url='https://graph.microsoft.com/v1.0/',
	request_token_url=None,
	access_token_method='POST',
	access_token_url=str.format('https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token', tenant=tenant_name),
	authorize_url=str.format('https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize', tenant=tenant_name)
)



# Index Page with Login Button
@app.route('/')
def home():
    return render_template("home.html")

#Login
@app.route('/login', methods = ['POST', 'GET'])
def login():
	if 'microsoft_token' in session:
		return redirect(url_for('me'))
	# Generate the guid to only accept initiated logins
	guid = uuid.uuid4()
	session['state'] = guid
	return microsoft.authorize(callback=url_for('authorized', _external=True), state=guid)

# User Logout will Redirect to Homepage.
@app.route('/logout', methods = ['POST', 'GET'])
def logout():
	session.pop('microsoft_token', None)
	session.pop('state', None)
	return redirect(url_for('home'))


@app.route('/login/authorized')
def authorized():
	response = microsoft.authorized_response()
	if response is None:
		return "Access Denied: Reason=%s\nError=%s" % (
			response.get('error'),
			request.get('error_description')
		)
	# Check response for state
	print("Response: " + str(response))
	if str(session['state']) != str(request.args['state']):
		raise Exception('State has been messed with, end authentication')
	# Okay to store this in a local variable, encrypt if it's going to client
	# machine or database. Treat as a password.
	session['microsoft_token'] = (response['access_token'], '')
	return redirect(url_for('me'))


'''
class Results(Table):
	vcenter = Col('vCenter')
'''

class loginForm(FlaskForm):
      submit = SubmitField("Delete")


'''
If User has a Session Token: LoggedIn page will display 
For the user.
'''
@app.route('/loggedin', methods = ['POST', 'GET'])
def me():
	form = loginForm()
	displayName = microsoft.get('me?$select=displayName')
	Email = microsoft.get('me?$select=mail')
	userName = displayName.data['displayName'] 
	userEmail = Email.data['mail']

	'''
	Using the users email Address to split from '@'
	Assigning the first Element of users email to login_id
	'''
	userid = userEmail.split("@")
	#login_id = userid[0]

	conn = get_db()
	query = ''
	conn.execute(query)
	vcentercategories = conn.fetchall()


	if request.method == "POST":
		print("Testing post") 

	return render_template('loggedin.html', userName=str(userName), vcentercategories=vcentercategories, form=form)

	
#Getting Session Token
@microsoft.tokengetter
def get_microsoft_oauth_token():
	return session.get('microsoft_token')

'''
Database Connection  & Tear Down when Not inuse
'''
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = SQL.cursor()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

'''
Error Handler for Error 404 and 500
'''
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", title = '404'), 404

@app.errorhandler(500)
def errorhandler(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
