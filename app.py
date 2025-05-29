from flask import Flask, render_template, request, redirect, url_for, session
import os
import markdown
from functools import wraps

app = Flask(__name__)
app.secret_key = 'geheim'
PAGES_DIR = 'pages'

# --- Login-System ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Falscher Benutzername oder Passwort"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Startseite ---
@app.route("/")
@login_required
def index():
    return redirect(url_for("view_page", page="start"))

# --- Seitenansicht ---
@app.route("/view/<path:page>")
@login_required
def view_page(page):
    filepath = os.path.join(PAGES_DIR, page + ".md")
    if not os.path.isfile(filepath):
        return render_template("wiki.html", page=page, content="(Seite nicht gefunden.)")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
        content = markdown.markdown(text)
    return render_template("wiki.html", page=page, content=content)

# --- Seiten bearbeiten ---
@app.route("/edit/<path:page>", methods=["GET", "POST"])
@login_required
def edit_page(page):
    filepath = os.path.join(PAGES_DIR, page + ".md")
    if request.method == "POST":
        content = request.form.get("content", "")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return redirect(url_for("view_page", page=page))

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = ""
    return render_template("edit.html", page=page, content=content)

# --- Sidebar Struktur anzeigen ---
@app.route("/wiki")
@login_required
def wiki():
    entries = []
    for root, dirs, files in os.walk(PAGES_DIR):
        level = root.replace(PAGES_DIR, '').count(os.sep)
        folder = os.path.basename(root)
        relpath = os.path.relpath(root, PAGES_DIR)
        if relpath == "." or folder == "pages":
            continue
        entries.append((relpath.replace("\\", "/"), folder, level, True))
        for f in sorted(files):
            if f.endswith(".md"):
                name = f[:-3]
                entries.append((os.path.join(relpath, name).replace("\\", "/"), name, level + 1, False))
    return render_template("index.html", entries=entries)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)