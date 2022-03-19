import os
from flask import Flask, render_template, request, url_for, redirect, flash, g, session
from flask import Flask, jsonify
from flask.helpers import send_file
from io import BytesIO
import psycopg2
import heapq
import tensorflow as tf
from dotenv import load_dotenv
import requests, json
from geopy.geocoders import Nominatim
import geocoder
import time
from pprint import pprint
import PIL.Image as Image
from transformers import DistilBertTokenizerFast
from transformers import TFDistilBertForSequenceClassification

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY")

app_root = app.root_path 
database = 'postgres://gjscfkpgyogvvp:76996cc99db43b0479e8c5ecf0181da2d41561c9f50efbd6622d97ace7259df8@ec2-3-216-221-31.compute-1.amazonaws.com:5432/df095rdjmq8tsv'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/old_ui/')
def index_old():
    return render_template('index_old.html')

# ------------- REGISTRATION
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        profile = request.files['profile']
        role = request.form['role']

        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT email FROM users")
        rs = c.fetchall()
        for rs in rs:
            if email in rs:
                flash("Email already associated with an account", 'validemail')
                break
        else:
            c.execute("""
            INSERT INTO users (name, email, password, role, profile) VALUES (%s, %s, %s, %s, %s)""", (name, email, password, role, profile.read()))
            conn.commit()
            flash(
                "Registration successfull ! You can now log in to your account ", 'register')
        conn.close

        return redirect(url_for('index'))

    return redirect(url_for('index'))


# ------------- OWNER LOGIN & LOGOUT
@app.route('/owner_login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        session.pop('owner', None)

        email = request.form['email']
        password = request.form['password']

        conn = psycopg2.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE role = 'owner' AND email = '" +
                  email+"' AND password = '"+password+"'")
        r = c.fetchall()

        for i in r:
            if (email == i[2] and password == i[3]):
                session['owner'] = i[0]
                return redirect(url_for('home'))
        else:
            flash("Invalid Email or Password", 'invalidOwner')

        conn.close()
    return redirect(url_for('index'))

@app.route('/owner_logout')
def owner_logout():
    session.pop('owner', None)
    return redirect(url_for('index'))


# ------------- USER LOGIN & LOGOUT
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        session.pop('user', None)
        session.pop('owner', None)

        email = request.form['email']
        password = request.form['password']

        conn = psycopg2.connect(database)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE role = 'user' AND email = '" +
                  email+"' AND password = '"+password+"'")
        r = c.fetchall()
        user_login = 0
        for i in r:
            if (email == i[2] and password == i[3]):
                session['user'] = i[0]
                user_login = 1
                conn.close()
                return redirect(url_for('home'))
            else:
                user_login = 0
        if user_login == 0:
            c.execute("SELECT * FROM users WHERE role = 'owner' AND email = '" +email+"' AND password = '"+password+"'")
            r = c.fetchall()
            for i in r:
                if (email == i[2] and password == i[3]):
                    session['owner'] = i[0]
                    return redirect(url_for('home'))    
                else:
                    flash("Invalid Email or Password", 'invalidUser')
            conn.close()
    return redirect(url_for('index'))

@app.route('/user_logout')
def user_logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# ------------- HOME PAGE
@app.route('/home', methods=['GET', 'POST'])
def home():
    if g.user:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE id = '"+str(session['user'])+"'")
        rs = c.fetchone()

        c.execute("SELECT COUNT(review) FROM reviews WHERE userid= '"+str(session['user'])+"'")
        reviewno = c.fetchone()

        c.execute("SELECT r.review, r.place, r.sentiment, p.propertyname FROM reviews r, places p WHERE r.place = p.id AND r.userid = '"+str(session['user'])+"'")
        reviews = c.fetchall()

        if rs[6] is not None:
            c.execute("SELECT * FROM places WHERE venue = '"+rs[6]+"' ORDER BY RANDOM() LIMIT 3")
            hotvenues = c.fetchall()
            venueType = rs[6]
        else:
            c.execute("SELECT * FROM places ORDER BY RANDOM() LIMIT 3")
            hotvenues = c.fetchall()
            venueType = 'Select Venue'

        if request.method == 'POST':
            profilepic = request.files['profilepic']
            c.execute("UPDATE users SET profile = (%s) WHERE id = (%s)", (profilepic.read(), session['user']))

            conn.commit()
            conn.close()

            flash("Profile Picture Updated successfully ! ", 'profileupdate')
            return redirect(url_for('home'))

        conn.close()
        print(hotvenues)
        app_nom = Nominatim(user_agent="tutorial")
        my_location= geocoder.ip('me')
        latitude= my_location.geojson['features'][0]['properties']['lat']
        longitude = my_location.geojson['features'][0]['properties']['lng']
        print(latitude,longitude)
        #get the location
        
        context = {
            'rs': rs,
            'hotvenues': hotvenues,
            'venueType': venueType,
            'reviewno': reviewno,
            'reviews': reviews,
            'latitude': latitude,
            'longitude':longitude
        }
        print(hotvenues)
        return render_template('user/user_home.html', **context)
    elif g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE id = '"+str(session['owner'])+"'")
        rs = c.fetchone()

        c.execute("SELECT COUNT(propertyname) FROM places WHERE owner= '"+str(session['owner'])+"'")
        placeno = c.fetchone()

        if request.method == 'POST':
            profilepic = request.files['profilepic']
            c.execute("UPDATE users SET profile = (%s) WHERE id = (%s)", (profilepic.read(), session['owner']))

            conn.commit()
            conn.close()

            flash("Profile Picture Updated successfully ! ", 'profileupdate')
            return redirect(url_for('home'))

        c.execute("SELECT * FROM places WHERE owner = '"+str(session['owner'])+"'")
        place = c.fetchall()
        conn.close()
        print(place)
        context = {
            'rs': rs,
            'placeno': placeno
        }
        return render_template('owner/owner_home.html', **context)
    return redirect(url_for('index'))


# ------------- HOT VENUE PREFERENCE
@app.route('/preference<int:id>', methods=['GET', 'POST'])
def preference(id):
    if request.method == 'POST':
        conn = psycopg2.connect(database)
        c = conn.cursor()

        preference = request.form['venue']
        c.execute("UPDATE users SET preference = (%s) WHERE id = (%s)", (preference, id))
        conn.commit()
        conn.close()

        flash("Preference Updated successfully ! ", 'preference')
        return redirect(url_for('home'))


# ------------- RECOMMENDATION
@app.route('/recommendation', methods=['GET', 'POST'])
def recommendation():
    if g.user:
        if request.method == 'POST':
            conn = psycopg2.connect(database)
            c = conn.cursor()

            facilities = ''
            city = request.form['city']
            state = request.form['state']
            place = request.form['place']
            value = request.form.getlist('check')

            c.execute("""SELECT * FROM places WHERE venue = %s AND state = %s AND city = %s""", (place, state, city))
            placesss = c.fetchall()
            scores = list()
            for rs in placesss:
                text = rs[9]
                li = list(text.split(" "))
                res = len(set(value) & set(li)) / float(len(set(value) | set(li))) * 100
                scores.append(res)
            
            recom = heapq.nlargest(3, range(len(scores)), key=scores.__getitem__)
            percent = heapq.nlargest(3, scores)

            recomend = list()
            for i in recom:
                recomend.append(placesss[i][0])
            
            c.execute("SELECT * FROM places WHERE id = '"+str(recomend[0])+"'")
            place1 = c.fetchone()
            c.execute("SELECT * FROM places WHERE id = '"+str(recomend[1])+"'")
            place2 = c.fetchone()
            c.execute("SELECT * FROM places WHERE id = '"+str(recomend[2])+"'")
            place3 = c.fetchone()

            c.execute("SELECT * FROM reviews WHERE place = '"+str(recomend[0])+"'")
            review1 = c.fetchall()
            c.execute("SELECT * FROM reviews WHERE place = '"+str(recomend[1])+"'")
            review2 = c.fetchall()
            c.execute("SELECT * FROM reviews WHERE place = '"+str(recomend[2])+"'")
            review3 = c.fetchall()
        
            context = {
                'percent': percent,
                'place1': place1,
                'review1': review1,
                'place2': place2,
                'review2': review2,
                'place3': place3,
                'review3': review3,
            }
            return render_template('user/user_recommendation.html', **context)
    return redirect(url_for('index'))


# ------------- PLACES - VIEW, ADD, DELETE, UPDATE, ANALYSIS
@app.route('/owner_place')
def owner_place():
    if g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT * FROM places WHERE owner = '"+str(session['owner'])+"'")
        place = c.fetchall()

        context = {
            'place': place
        }
        return render_template('owner/owner_place.html', **context)
    return redirect(url_for('index'))

@app.route('/owner_new_place', methods=['GET', 'POST'])
def owner_new_place():
    if g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE id = '"+str(session['owner'])+"'")
        rs = c.fetchone()

        context = {
            'rs': rs,
        }

        if request.method == 'POST':

            facilities = ''

            propertyname = request.form['propertyname']
            propertypic = request.files['propertypic']
            shop = request.form['shop']
            city = request.form['city']
            state = request.form['state']
            pincode = request.form['pincode']
            telephone = request.form['telephone']
            venue = request.form['place']
            owner = session['owner']

            value = request.form.getlist('check')
            for values in value:
                facilities += values + " "

            c.execute("""
            INSERT into places (propertyname, propertypic, shop, city, state, pincode, telephone, venue, facilities, owner) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (propertyname, propertypic.read(), shop, city, state, pincode, telephone, venue, facilities, owner))

            conn.commit()
            conn.close()

            flash("New Place added successfully ! ", 'newplace')
            return redirect(url_for('owner_place'))
        return render_template('owner/owner_new_place.html', **context)
    return redirect(url_for('index'))

@app.route('/owner_delete_place<int:id>')
def owner_delete_place(id):
    if g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("DELETE FROM places WHERE id = '"+str(id)+"'")
        conn.commit()
        conn.close()
        flash("Place data deleted ! ", 'delete')
        return redirect(url_for('owner_place'))
    return redirect(url_for('index'))

@app.route('/owner_update_place<int:id>', methods=['POST', 'GET'])
def owner_update_place(id):
    if g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE id = '"+str(session['owner'])+"'")
        rs = c.fetchone()

        c.execute("SELECT * FROM places WHERE id = '"+str(id)+"'")
        place = c.fetchone()

        context = {
            'rs': rs,
            'place': place
        }

        if request.method == 'POST':

                facilities = ''

                propertyname = request.form['propertyname']
                propertypic = request.files['propertypic']
                shop = request.form['shop']
                city = request.form['city']
                state = request.form['state']
                pincode = request.form['pincode']
                telephone = request.form['telephone']
                venue = request.form['place']
                owner = session['owner']

                value = request.form.getlist('check')
                for values in value:
                    facilities += values + ", "

                c.execute("""
                UPDATE places SET (propertyname, propertypic, shop, city, state, pincode, telephone, venue, facilities, owner) = (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) WHERE id = %s
                """, (propertyname, propertypic.read(), shop, city, state, pincode, telephone, venue, facilities, owner, id))

                conn.commit()
                conn.close()

                flash("Place data updated added successfully ! ", 'updateplace')
                return redirect(url_for('owner_place'))

        return render_template('owner/owner_update_place.html', **context)
    return redirect(url_for('index'))

@app.route('/owner_review_place<int:id>')
def owner_review_place(id):
    if g.owner:
        conn = psycopg2.connect(database)
        c = conn.cursor()

        c.execute("SELECT propertyname FROM places WHERE id = '"+str(id)+"'")
        name = c.fetchone()

        c.execute("SELECT * FROM reviews WHERE place = '"+str(id)+"'")
        reviews = c.fetchall()

        c.execute("SELECT COUNT(sentiment) FROM reviews WHERE sentiment = 'Positive' AND place = '"+str(id)+"'")
        positive = c.fetchone()

        c.execute("SELECT COUNT(sentiment) FROM reviews WHERE sentiment = 'Negative' AND place = '"+str(id)+"'")
        negative = c.fetchone()
        
        context = {
            'name': name,
            'reviews': reviews,
            'positive': positive,
            'negative': negative
        }

        return render_template('owner/owner_review_place.html', **context)


# ------------- PROFILE PICTURES AND NAME
@app.route('/profile<int:id>')
def profile(id):
    conn = psycopg2.connect(database)
    c = conn.cursor()

    c.execute("SELECT profile FROM users WHERE id = '"+str(id)+"'")
    rs = c.fetchone()
    print(rs)
    picture = rs[0]
    conn.close()
    if len(BytesIO(picture).getvalue()) != 0:            
        return send_file(BytesIO(picture), attachment_filename='flask.png', as_attachment=False)
    else:
        img_path = app_root+"/static/assets/images/user.png"
        print(img_path)
        with open(img_path, "rb") as image:
            f = image.read()
            img_bytes = bytearray(f)
        return send_file(BytesIO(img_bytes), attachment_filename='flask.png', as_attachment=False)

@app.route('/place_profile<int:id>')
def place_profile(id):
    conn = psycopg2.connect(database)
    c = conn.cursor()

    c.execute("SELECT * FROM places WHERE id = '"+str(id)+"'")
    rs = c.fetchone()
    picture = rs[2]

    return send_file(BytesIO(picture), attachment_filename='flask.png', as_attachment=False)

@app.route('/place_name<int:id>')
def place_name(id):
    conn = psycopg2.connect(database)
    c = conn.cursor()

    c.execute("SELECT * FROM places WHERE id = '"+str(id)+"'")
    rs = c.fetchone()
    placename = rs[1]

    return placename

# ------------- REVIEW
def review_model(review):
    loaded_model = TFDistilBertForSequenceClassification.from_pretrained("./model")
    tokenizer = DistilBertTokenizerFast.from_pretrained('distilbert-base-uncased')

    predict_input = tokenizer.encode(review,truncation=True,padding=True,return_tensors="tf")

    tf_output = loaded_model.predict(predict_input)[0]
    tf_prediction = tf.nn.softmax(tf_output, axis=1)
    
    labels = ['Negative','Positive']
    label = tf.argmax(tf_prediction, axis=1)
    label = label.numpy()
    return(labels[label[0]])

@app.route('/review<int:id>', methods=['POST', 'GET'])
def review(id):
    if request.method == 'POST':
        conn = psycopg2.connect(database)
        c = conn.cursor()

        review = request.form['review']
        place = id
        sentiment = review_model(review)

        if g.user:
            c.execute("SELECT name FROM users WHERE id = '"+str(session['user'])+"'")
            name = c.fetchone()
            userid = session['user']
        elif g.owner:
            c.execute("SELECT name FROM users WHERE id = '"+str(session['owner'])+"'")
            name = c.fetchone()
            userid = session['owner']
        else:
            return redirect(url_for(index))

        c.execute("INSERT INTO reviews (name, review, place, sentiment, userid) VALUES (%s, %s, %s, %s, %s)", (name[0], review, place, sentiment, userid))
        conn.commit()
        return redirect(url_for('home'))


@app.before_request
def before_request():
    g.user = None
    g.owner = None
    if 'user' in session:
        g.user = session['user']
    if 'owner' in session:
        g.owner = session['owner']

if __name__ == "__main__":
    app.run(debug=True, host='192.168.0.103')