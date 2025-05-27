
from flask import Flask, render_template, request, redirect, url_for, session
import os
import markdown
from functools import wraps

app = Flask(__name__)
app.secret_key = 'geheim'

PAGES_DIR = 'pages'

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@login_required
def index():
    pages = os.listdir(PAGES_DIR)
    return render_template('index.html', pages=pages)

@app.route('/view/<page>')
@login_required
def view(page):
    filepath = os.path.join(PAGES_DIR, page)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        html = markdown.markdown(content)
        return render_template('layout.html', content=html, title=page)
    return "Seite nicht gefunden", 404

@app.route('/edit/<page>', methods=['GET', 'POST'])
@login_required
def edit(page):
    filepath = os.path.join(PAGES_DIR, page)
    if request.method == 'POST':
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(request.form['content'])
        return redirect(url_for('view', page=page))
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ''
    return render_template('edit.html', page=page, content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    os.makedirs(PAGES_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
