import csv
import io
import os
import re
import threading
from functools import wraps
from secrets import compare_digest
from urllib.parse import urlparse

from flask import Flask, abort, redirect, render_template_string, request, Response

app = Flask(__name__)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
CSV_PATH = os.environ.get("LINKS_CSV", "data/links.csv")
BLOB_PATH = os.environ.get("BLOB_CSV_PATH", "url-shortener/links.csv")

# This lock prevents overlapping writes within one running instance.
# It is not a distributed lock across separate Vercel instances.
file_lock = threading.Lock()

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>My URL Shortener</title>
  <style>
    body { font: 16px system-ui, sans-serif; max-width: 850px; margin: 40px auto; padding: 0 18px; color: #222; }
    h1 { margin-bottom: 8px; }
    form.add { display: grid; gap: 10px; grid-template-columns: 1fr 1fr auto; margin: 24px 0; }
    input, button { font: inherit; padding: 10px; }
    button { cursor: pointer; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td { text-align: left; border-bottom: 1px solid #ddd; padding: 10px 6px; overflow-wrap: anywhere; }
    .msg { padding: 10px; background: #f2f5ff; border-radius: 6px; }
    .delete { padding: 5px 8px; }
    @media (max-width: 650px) { form.add { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>My URL Shortener</h1>
  <p>Create and manage your personal short links.</p>
  {% if message %}<p class="msg">{{ message }}</p>{% endif %}
  <form class="add" method="post" action="/admin/add">
    <input name="code" placeholder="Custom code, e.g. github" required
           pattern="[A-Za-z0-9_-]+" title="Use letters, numbers, hyphens, or underscores">
    <input name="url" type="url" placeholder="https://example.com" required>
    <button type="submit">Create link</button>
  </form>
  <h2>Your links ({{ links|length }})</h2>
  {% if links %}
  <table>
    <thead><tr><th>Short link</th><th>Destination</th><th></th></tr></thead>
    <tbody>
    {% for code, url in links %}
      <tr>
        <td><a href="{{ request.host_url }}{{ code }}" target="_blank" rel="noopener">{{ request.host_url }}{{ code }}</a></td>
        <td>{{ url }}</td>
        <td>
          <form method="post" action="/admin/delete/{{ code }}" onsubmit="return confirm('Delete this short link?')">
            <button class="delete" type="submit">Delete</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p>No links created yet.</p>
  {% endif %}
</body>
</html>
"""


def blob_storage_enabled():
    """Use Blob when its credentials exist; use local CSV for local development."""
    has_static_token = bool(os.environ.get("BLOB_READ_WRITE_TOKEN"))
    has_oidc = bool(os.environ.get("BLOB_STORE_ID") and os.environ.get("VERCEL_OIDC_TOKEN"))
    return has_static_token or has_oidc


def ensure_storage_is_configured():
    # Never silently write to Vercel's temporary filesystem in production.
    if os.environ.get("VERCEL") and not blob_storage_enabled():
        raise RuntimeError(
            "Vercel Blob is not connected. Connect a private Blob store to this project."
        )


def read_links():
    ensure_storage_is_configured()

    if blob_storage_enabled():
        from vercel.blob import sync as blob
        try:
            result = blob.get_blob(BLOB_PATH, access="private")
            content = result.body.decode("utf-8")
        except FileNotFoundError:
            return {}
        return parse_csv(content)

    # Local development fallback. This file is not used for Vercel production.
    from pathlib import Path
    local_path = Path(CSV_PATH)
    if not local_path.exists():
        return {}
    return parse_csv(local_path.read_text(encoding="utf-8"))


def parse_csv(content):
    reader = csv.DictReader(io.StringIO(content))
    return {
        row["code"]: row["url"]
        for row in reader
        if row.get("code") and row.get("url")
    }


def write_links(links):
    ensure_storage_is_configured()

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["code", "url"])
    writer.writeheader()
    for code, url in sorted(links.items()):
        writer.writerow({"code": code, "url": url})
    csv_bytes = output.getvalue().encode("utf-8")

    if blob_storage_enabled():
        from vercel.blob import sync as blob
        blob.put_blob(
            BLOB_PATH,
            csv_bytes,
            access="private",
            content_type="text/csv; charset=utf-8",
            allow_overwrite=True,
        )
        return

    # Local development fallback.
    from pathlib import Path
    local_path = Path(CSV_PATH)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = local_path.with_suffix(local_path.suffix + ".tmp")
    temp_path.write_bytes(csv_bytes)
    temp_path.replace(local_path)


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if (
            not ADMIN_PASSWORD
            or not auth
            or not compare_digest(auth.username or "", ADMIN_USERNAME)
            or not compare_digest(auth.password or "", ADMIN_PASSWORD)
        ):
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="URL shortener admin"'},
            )
        return fn(*args, **kwargs)
    return wrapper


def valid_destination(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


@app.get("/")
def home():
    return "Personal URL shortener is running."


@app.get("/admin")
@require_admin
def admin():
    links = read_links()
    message = request.args.get("message", "")
    return render_template_string(PAGE, links=sorted(links.items()), message=message)


@app.post("/admin/add")
@require_admin
def add_link():
    code = request.form.get("code", "").strip()
    url = request.form.get("url", "").strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", code):
        abort(400, "Short code must be 1 to 64 letters, numbers, hyphens, or underscores.")
    if code.lower() in {"admin", "favicon.ico"}:
        abort(400, "That short code is reserved.")
    if not valid_destination(url):
        abort(400, "Destination must be a valid http:// or https:// URL.")

    with file_lock:
        links = read_links()
        if code in links:
            return redirect("/admin?message=That+short+code+already+exists.")
        links[code] = url
        write_links(links)

    return redirect("/admin?message=Link+created.")


@app.post("/admin/delete/<code>")
@require_admin
def delete_link(code):
    with file_lock:
        links = read_links()
        if code in links:
            del links[code]
            write_links(links)
    return redirect("/admin?message=Link+deleted.")


EMBED_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ code }} | Embedded destination</title>
  <style>
    html, body { margin: 0; width: 100%; height: 100%; font-family: system-ui, sans-serif; }
    .topbar { box-sizing: border-box; height: 42px; padding: 10px 14px; background: #f4f4f5;
              color: #333; font-size: 13px; display: flex; justify-content: space-between;
              align-items: center; gap: 12px; }
    .topbar a { color: #2457c5; text-decoration: none; white-space: nowrap; }
    iframe { display: block; width: 100%; height: calc(100% - 42px); border: 0; }
  </style>
</head>
<body>
  <div class="topbar">
    <span>Destination for /{{ code }}</span>
    <a href="{{ destination }}" target="_blank" rel="noopener noreferrer">Open destination in a new tab</a>
  </div>
  <iframe src="{{ destination }}" title="Destination website"
          referrerpolicy="no-referrer-when-downgrade"
          allow="fullscreen; autoplay; clipboard-read; clipboard-write"></iframe>
</body>
</html>
"""


@app.get("/<code>")
def follow_link(code):
    links = read_links()
    destination = links.get(code)
    if not destination:
        abort(404)
    # Embedded mode keeps the short URL in the browser address bar.
    return render_template_string(EMBED_PAGE, code=code, destination=destination)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
