from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import markdown
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'geheim'
PAGES_DIR = 'pages'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}


# --- Authentifizierung ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# --- Dateityp‐Prüfung für den Upload ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# --- Login / Logout ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (request.form["username"], request.form["password"]) == ("admin", "admin"):
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Falscher Benutzername oder Passwort"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- Wurzel‐URL: leitet direkt auf /view/start weiter ---
@app.route("/")
@login_required
def index():
    return redirect(url_for("view_page", page="start"))


# --- Seitenansicht (Wiki, Shop, Forum) ---
@app.route("/view/<path:page>")
@login_required
def view_page(page):
    filepath = os.path.join(PAGES_DIR, page + ".md")

    # Nur bei "shop" und "forum" keine Sidebar anzeigen:
    show_sidebar = not (page.lower() in ("shop", "forum"))

    if not os.path.isfile(filepath):
        # Seite nicht gefunden – trotzdem Sidebar‐Flag beibehalten
        return render_template("wiki.html",
                               page=page,
                               content="**Seite nicht gefunden**",
                               show_sidebar=show_sidebar)

    text = open(filepath, encoding="utf-8").read()
    html = markdown.markdown(text, extensions=['fenced_code'])
    return render_template("wiki.html",
                           page=page,
                           content=html,
                           show_sidebar=show_sidebar)


# --- Suche über alle Markdown‐Dateien ---
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    query = request.form.get("q", "").lower()
    results = []
    for root, _, files in os.walk(PAGES_DIR):
        for f in files:
            if f.endswith(".md"):
                content = open(os.path.join(root, f), encoding="utf-8").read().lower()
                if query in content:
                    rel = os.path.relpath(root, PAGES_DIR).replace("\\", "/")
                    name = f[:-3]
                    results.append((f"{rel}/{name}", name))
    # Suche soll immer Sidebar anzeigen:
    return render_template("search.html", query=query, results=results, show_sidebar=True)


# --- Datei‐Upload (Markdown, Bilder etc.) ---
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    msg = None
    if request.method == "POST":
        file = request.files.get("file")
        if file and allowed_file(file.filename):
            fname = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(os.path.join(UPLOAD_FOLDER, fname))
            msg = "Upload erfolgreich"
        else:
            msg = "Ungültige Datei"
    # Upload‐Formular zeigt keine Sidebar (separat von Wiki‐Inhalten)
    return render_template("upload.html", msg=msg, show_sidebar=False)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# --- Sidebar‐Baumstruktur erstellen (rekursiv) ---
def build_sidebar():
    """
    Erzeugt einen verschachtelten Baum aller Ordner und Markdown-Dateien unter pages/,
    sortiert alphabetisch. Überspringt dabei 'start', 'shop' und 'forum' komplett.
    """
    def traverse(directory, level=0):
        nodes = []
        try:
            items = sorted(os.listdir(directory))
        except FileNotFoundError:
            return nodes

        for item in items:
            full_path = os.path.join(directory, item)
            base_name, ext = os.path.splitext(item)

            # Keine Links/Ordner für 'start', 'shop' oder 'forum' in der Sidebar
            if base_name.lower() in ("start", "shop", "forum"):
                continue

            if os.path.isdir(full_path):
                node = {
                    "type": "folder",
                    "name": item,
                    "path": os.path.relpath(full_path, PAGES_DIR).replace("\\", "/"),
                    "level": level,
                    "children": traverse(full_path, level + 1)
                }
                nodes.append(node)

            elif ext.lower() == ".md":
                node = {
                    "type": "file",
                    "name": base_name,
                    "path": os.path.join(
                        os.path.relpath(directory, PAGES_DIR).replace("\\", "/"),
                        base_name
                    ).lstrip("/"),
                    "level": level
                }
                nodes.append(node)

        return nodes

    return traverse(PAGES_DIR, 0)


@app.context_processor
def inject_sidebar():
    # Die Sidebar‐Daten stehen allen Templates zur Verfügung – ob sie tatsächlich gerendert
    # werden, entscheidet das Template über show_sidebar.
    return {"sidebar": build_sidebar()}


# --- App starten ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
