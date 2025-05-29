from flask import Flask, render_template, request, redirect, url_for, session
import os
import markdown
from functools import wraps

app = Flask(__name__)
app.secret_key = 'geheim'
PAGES_DIR = 'pages'

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/view/<path:page>")
@login_required
def view_page(page):
    if not page.endswith(".md"):
        page += ".md"
    filepath = os.path.join(PAGES_DIR, page)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = markdown.markdown(f.read())
        return render_template("layout.html", content=content, page=page)
    return "Seite nicht gefunden.", 404

@app.route("/edit/<path:page>", methods=["GET", "POST"])
@login_required
def edit_page(page):
    if not page.endswith(".md"):
        page += ".md"
    filepath = os.path.join(PAGES_DIR, page)
    if request.method == "POST":
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(request.form["content"])
        return redirect(url_for("view_page", page=page[:-3]))
    content = ""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    return render_template("edit.html", content=content, page=page[:-3])

@app.route("/new", methods=["POST"])
@login_required
def new_page():
    path = request.form["path"]
    full_path = os.path.join(PAGES_DIR, path)
    if not full_path.endswith(".md"):
        full_path += ".md"
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write("# Neue Seite")
    return redirect(url_for("edit_page", page=path.replace(".md", "")))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["logged_in"] = True
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    os.makedirs(PAGES_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
