from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
from werkzeug.utils import secure_filename
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # change this for production

# ---------------- MySQL Configuration ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'agAARYA@3075'
app.config['MYSQL_DB'] = 'college_lostfound'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mysql = MySQL(app)

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            flash('Email already registered!', 'danger')
        else:
            cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)',
                           (name, email, password))
            mysql.connection.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cursor.fetchone()

        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect email or password!', 'danger')

    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        category = request.form.get('category', '')

        if search:
            query += " AND (title LIKE %s OR description LIKE %s OR location LIKE %s)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]

        if category and category != "All":
            query += " AND category = %s"
            params.append(category)

    query += " ORDER BY date_reported DESC"
    cursor.execute(query, tuple(params))
    items = cursor.fetchall()

    return render_template('dashboard.html', items=items, name=session['name'])


@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        location = request.form['location']
        file = request.files['image']

        image_path = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            # Store only relative path for easier access in HTML
            image_path = f"uploads/{filename}"

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'INSERT INTO items (title, description, category, date_reported, location, image_path, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (title, description, category, date.today(), location, image_path, session['id'])
        )
        mysql.connection.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_item.html')


@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if item belongs to current user
    cursor.execute("SELECT * FROM items WHERE id = %s AND user_id = %s", (item_id, session['id']))
    item = cursor.fetchone()

    if item:
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        mysql.connection.commit()

        # Optionally, delete the image file
        if item['image_path']:
            image_full_path = os.path.join('static', item['image_path'])
            try:
                os.remove(image_full_path)
            except FileNotFoundError:
                pass

        flash('Item deleted successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        return "You are not authorized to delete this item.", 403


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('name', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
