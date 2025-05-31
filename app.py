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

# --- Dateiprüfung ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# --- Login/Logout ---
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

# --- Startseite ---
@app.route("/")
@login_required
def index():
    return render_template("index.html")

# --- Seitenansicht ---
@app.route("/view/<path:page>")
@login_required
def view_page(page):
    filepath = os.path.join(PAGES_DIR, page + ".md")
    if not os.path.isfile(filepath):
        return render_template("wiki.html", page=page, content="**Seite nicht gefunden**")
    text = open(filepath, encoding="utf-8").read()
    html = markdown.markdown(text, extensions=['fenced_code'])
    return render_template("wiki.html", page=page, content=html)

# --- Suche ---
@app.route("/search", methods=["GET","POST"])
@login_required
def search():
    query = request.form.get("q","").lower()
    results = []
    for root, _, files in os.walk(PAGES_DIR):
        for f in files:
            if f.endswith(".md"):
                content = open(os.path.join(root, f), encoding="utf-8").read().lower()
                if query in content:
                    rel = os.path.relpath(root, PAGES_DIR).replace("\\", "/")
                    name = f[:-3]
                    results.append((f"{rel}/{name}", name))
    return render_template("search.html", query=query, results=results)

# --- Seiten bearbeiten ---
@app.route("/edit/<path:page>", methods=["GET", "POST"])
@login_required
def edit_page(page):
    path = os.path.join(PAGES_DIR, page + ".md")
    if request.method == "POST":
        data = request.form["content"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return redirect(url_for("view_page", page=page))
    content = ""
    if os.path.isfile(path):
        content = open(path, encoding="utf-8").read()
    return render_template("edit.html", page=page, content=content)

# --- Neue Seite anlegen ---
@app.route("/new", methods=["GET","POST"])
@login_required
def new_page():
    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        if not name:
            error = "Seitenname darf nicht leer sein"
        else:
            safe = secure_filename(name)
            target = os.path.join(PAGES_DIR, safe + ".md")
            if os.path.exists(target):
                error = "Seite existiert bereits"
            else:
                with open(target, "w", encoding="utf-8") as f:
                    f.write(f"# {name}\n\n")
                return redirect(url_for("edit_page", page=safe))
    return render_template("newpage.html", error=error)

# --- Datei-Upload ---
@app.route("/upload", methods=["GET","POST"])
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
    return render_template("upload.html", msg=msg)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# --- Sidebar-Build mit sortierten Ordnern 01-12, ohne forum/shop/start ---
def build_sidebar():
    """
    Erstellt einen rekursiv verschachtelten Baum aller Unterverzeichnisse und Dateien unter pages/,
    sortiert alphabetisch. Überspringt dabei Seiten bzw. Ordner mit den Namen 'forum', 'shop' und 'start'.
    """
    def traverse(dir_path, parent_level):
        """
        Rekursive Helfer-Funktion: Gibt eine Liste von Diktaten zurück, die die Baumstruktur für
        das aktuelle Verzeichnis (dir_path) beschreiben.
        """
        entries = []
        # Liste aller Unterordner und Dateien alphabetisch sortieren
        items = sorted(os.listdir(dir_path))
        for item in items:
            full_path = os.path.join(dir_path, item)
            # Berechne 'rel_path' relativ zu PAGES_DIR
            rel_path = os.path.relpath(full_path, PAGES_DIR).replace("\\", "/")
            # Springe Ordner oder Dateien mit dem Namen start, shop, forum über
            base_name = os.path.splitext(item)[0]  # ohne .md
            if base_name.lower() in ("start", "shop", "forum"):
                continue

            if os.path.isdir(full_path):
                # Ordner eintragen
                entries.append({
                    "type": "folder",
                    "name": item,
                    "path": rel_path,
                    "level": parent_level
                })
                # Untereinträge (children) hinzufügen
                child_entries = traverse(full_path, parent_level + 1)
                entries.extend(child_entries)
            else:
                # Nur .md-Dateien eintragen, keine anderen Dateitypen
                if item.endswith(".md"):
                    entries.append({
                        "type": "file",
                        "name": base_name,
                        "path": rel_path[:-3],  # entferne ".md"
                        "level": parent_level
                    })
        return entries

    # Starte bei pages/ auf Level 0
    return traverse(PAGES_DIR, 0)

@app.context_processor
def inject_sidebar():
    return {"sidebar": build_sidebar()}

# --- App starten ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
