from flask import Flask, render_template, request,session,redirect,url_for,flash
import pickle,os,sqlite3,re
from key import secret_key,salt,salt2
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from cmail import sendmail
os.chdir(os.path.abspath(os.path.dirname(__file__)))

app = Flask(__name__)
app.secret_key = b'filesystem'
app.config['SESSION_TYPE']='filesystem'


# Load the pickled model
with open('Water_Quality.pkl', 'rb') as f:
    model = pickle.load(f)


# Define the location of your SQLite database file
DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This makes column access by name possible
    return conn

def init_db():
    db = get_db_connection()
    with db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                email TEXT UNIQUE
            )'''
        )

database_path = os.path.join(app.root_path, 'database.db')
if not os.path.exists(database_path):
    init_db()


@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('username'):
        return redirect(url_for('home'))
    if request.method=='POST':
        name=request.form['name']
        password=request.form['password']
        mydb = None
        try:
            mydb=get_db_connection()
            cursor=mydb.cursor()
            cursor.execute('SELECT count(*) from users where username=? and password=?',[name,password])
            count=cursor.fetchone()[0]
            cursor.close()
            if count==1:
                session['username']=name
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password')
                return render_template('login.html')
        except Exception as e:
            print(e)
        finally:
            if mydb:
                mydb.close()
    return render_template('login.html')

@app.route('/registration',methods=['GET','POST'])
def registration():
    if session.get('username'):
        return redirect(url_for('home'))
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        mydb = None
        try:
            mydb=get_db_connection()
            cursor=mydb.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', [username])
            count=cursor.fetchone()[0]
            cursor.execute('select count(*) from users where email=?',[email])
            count1=cursor.fetchone()[0]
            cursor.close()
            if count==1:
                flash('username already in use')
                return render_template('registration.html')
            elif count1==1:
                flash('Email already in use')
                return render_template('registration.html')
            data={'username':username,'password':password,'email':email}
            subject='Email Confirmation'
            body=f"Thanks for signing up\n\nfollow this link for further steps-{url_for('confirm',token=token(data,salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('Confirmation link sent to mail')
            return redirect(url_for('login'))
        except Exception as e:
            print(e)
        finally:
            if mydb:
                mydb.close()
    return render_template('registration.html')

@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=180)
    except Exception as e:
        #print(e)
        return 'Link Expired register again'
    else:
        mydb = None
        try:
            mydb=get_db_connection()
            cursor=mydb.cursor()
            username=data['username']
            cursor.execute('select count(*) from users where username=?',[username])
            count=cursor.fetchone()[0]
            if count==1:
                cursor.close()
                flash('You are already registerterd!')
                return redirect(url_for('login'))
            else:
                cursor.execute('insert into users(username,password,email) values(?,?,?)',(data['username'], data['password'], data['email']))
                mydb.commit()
                cursor.close()
                flash('Details registered!')
                return redirect(url_for('login'))
        except Exception as e:
            print(e)
        finally:
            if mydb:
                mydb.close()


@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        mydb = None
        try:
            mydb=get_db_connection()
            cursor=mydb.cursor()
            cursor.execute('select count(*) from users where email=?',[email])
            count=cursor.fetchone()[0]
            if count==1:
                cursor.execute('SELECT email from users where email=?',[email])
                status=cursor.fetchone()[0]
                cursor.close()
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
            else:
                flash('Invalid email id')
                return render_template('forgot.html')
        except Exception as e:
            print(e)
        finally:
            if mydb:
                mydb.close()
    return render_template('forgot.html')


@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                mydb = None
                try:
                    mydb=get_db_connection()
                    cursor=mydb.cursor()
                    cursor.execute('update users set password=? where email=?',[newpassword,email])
                    mydb.commit()
                    flash('Reset Successful')
                    return redirect(url_for('login'))
                except Exception as e:
                    print(e)
                finally:
                    if mydb:
                        mydb.close()
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('username'):
        session.pop('username')
        flash('Successfully logged out')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))




# Define the route for the home page
@app.route('/')
def home():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('index.html')

# Define the route for the prediction result
@app.route('/predict', methods=['GET','POST'])
def predict():
    if not session.get('username'):
        return redirect(url_for('login'))
    # Get the user input values from the HTML form
    ph = float(request.form['ph'])
    hardness = float(request.form['hardness'])
    solids = float(request.form['solids'])
    chloramines = float(request.form['chloramines'])
    sulfate = float(request.form['sulfate'])
    conductivity = float(request.form['conductivity'])
    organic_carbon = float(request.form['organic_carbon'])
    trihalomethanes = float(request.form['trihalomethanes'])
    turbidity = float(request.form['turbidity'])

    # Create a list of the input values
    input_values = [[ph, hardness, solids, chloramines, sulfate, conductivity, organic_carbon, trihalomethanes, turbidity]]

    # Make a prediction using the model
    prediction = model.predict(input_values)

    # Convert the prediction to a string and return it
    if prediction == 0:
        result = "Healthy"
    else:
        result = "Unhealthy"

    return render_template('index.html', prediction="{}".format(result))

if __name__ == '__main__':
    app.run()
