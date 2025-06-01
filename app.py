from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os
import markdown
from werkzeug.utils import secure_filename

app = Flask(__name__)
PAGES_DIR = 'pages'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}


# --- Dateityp-Prüfung für Uploads ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# --- Wurzel-URL: leitet auf /view/start weiter ---
@app.route("/")
def index():
    return redirect(url_for("view_page", page="start"))


# --- Seitenansicht (Wiki, Shop, Forum) öffentlich ---
@app.route("/view/<path:page>")
def view_page(page):
    filepath = os.path.join(PAGES_DIR, page + ".md")

    # Nur bei "shop" und "forum" keine Sidebar anzeigen:
    show_sidebar = not (page.lower() in ("shop", "forum"))

    if not os.path.isfile(filepath):
        return render_template(
            "wiki.html",
            page=page,
            content="**Seite nicht gefunden**",
            show_sidebar=show_sidebar
        )

    text = open(filepath, encoding="utf-8").read()
    html = markdown.markdown(text, extensions=['fenced_code'])
    return render_template(
        "wiki.html",
        page=page,
        content=html,
        show_sidebar=show_sidebar
    )


# --- Suche über alle Markdown-Dateien öffentlich ---
@app.route("/search", methods=["GET", "POST"])
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
    # Suche zeigt immer die Sidebar
    return render_template("search.html", query=query, results=results, show_sidebar=True)


# --- Datei-Upload (Markdown, Bilder etc.) öffentlich ---
@app.route("/upload", methods=["GET", "POST"])
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
    # Upload-Seite zeigt keine Sidebar
    return render_template("upload.html", msg=msg, show_sidebar=False)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# --- API: Liste aller Seiten öffentlich ---
@app.route("/api/pages", methods=["GET"])
def api_pages():
    """
    Liefert alle Wiki-Pfade (ohne .md) als JSON:
    { "pages": ["01.Welt_und_Geografie/Weltbeschreibung_Tremborum", ...] }
    """
    pages_list = []
    for root, _, files in os.walk(PAGES_DIR):
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(root, PAGES_DIR).replace("\\", "/")
                name = f[:-3]
                if rel == ".":
                    pages_list.append(name)
                else:
                    pages_list.append(f"{rel}/{name}")
    return jsonify({"pages": pages_list})


# --- API: Einzelne Seite (Markdown-Inhalt) öffentlich ---
@app.route("/api/page/<path:page>", methods=["GET"])
def api_page(page):
    """
    Liefert den reinen Markdown-Text von pages/<page>.md:
    { "page": "<page>", "content": "<roher Markdown>" }
    """
    filepath = os.path.join(PAGES_DIR, page + ".md")
    if not os.path.isfile(filepath):
        return jsonify({"error": "Seite nicht gefunden", "page": page}), 404

    content = open(filepath, encoding="utf-8").read()
    return jsonify({"page": page, "content": content})


# --- Sidebar-Baumstruktur erstellen (rekursiv) ---
def build_sidebar():
    """
    Erzeugt einen verschachtelten Baum aller Ordner und Markdown-Dateien unter pages/,
    sortiert alphabetisch. Überspringt 'start', 'shop' und 'forum'.
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

            # Überspringe 'start', 'shop', 'forum' in der Sidebar
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
    # Die Sidebar-Daten stehen allen Templates zur Verfügung
    return {"sidebar": build_sidebar()}


# --- App starten ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

