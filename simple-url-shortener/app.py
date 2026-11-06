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
  <title>Link Manager</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy-950:#07111E; --navy-900:#0A192F; --navy-800:#112240; --navy-700:#1D3557;
      --navy-600:#254B7C; --navy-500:#3B609B; --navy-100:#E6EEF8; --navy-50:#F0F5FA;
      --accent-blue:#1E40AF; --bg-main:#F8FAFC; --bg-card:#FFFFFF; --text-main:#0F172A;
      --text-muted:#475569; --text-light:#64748B; --border-color:#E2E8F0; --border-hover:#1E40AF;
      --shadow-sm:0 1px 3px rgba(10,25,47,.04); --shadow-md:0 4px 12px -2px rgba(10,25,47,.08);
      --shadow-lg:0 12px 28px -4px rgba(10,25,47,.12); --radius-sm:8px; --radius-md:12px;
      --radius-lg:16px; --transition:all .25s cubic-bezier(.16,1,.3,1);
    }
    * { box-sizing:border-box; }
    body {
      margin:0; font-family:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
      background-color:var(--bg-main);
      background-image:url("data:image/svg+xml,%3Csvg width='24' height='24' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='12' cy='12' r='1.5' fill='%230F172A' fill-opacity='0.16'/%3E%3C/svg%3E");
      color:var(--text-main); min-height:100vh; -webkit-font-smoothing:antialiased;
    }
    .header { background:var(--navy-900); color:#fff; padding:1.1rem 2rem; border-bottom:1px solid rgba(255,255,255,.08); }
    .header-container { max-width:1240px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.75rem; }
    .brand { display:flex; align-items:center; gap:.75rem; color:#fff; }
    .brand-icon { width:40px; height:40px; border-radius:var(--radius-sm); background:linear-gradient(135deg,#1E40AF 0%,#0A192F 100%); border:1px solid rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; }
    .brand-icon svg { width:22px; height:22px; }
    .brand-title { font-size:1.25rem; font-weight:700; letter-spacing:-.02em; }
    .header-desc { color:#94A3B8; font-size:.85rem; font-weight:500; }
    .container { max-width:1100px; margin:0 auto; padding:2.25rem 1.25rem 4rem; }
    .intro { margin-bottom:1.5rem; }
    .eyebrow { color:var(--navy-600); font-size:.72rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
    h1 { margin:.35rem 0 .4rem; font-size:clamp(1.65rem,3vw,2.15rem); letter-spacing:-.04em; }
    .subtitle { margin:0; color:var(--text-muted); font-size:.95rem; }
    .card { background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-lg); box-shadow:var(--shadow-md); padding:1.5rem; margin-bottom:1.5rem; }
    .card h2 { margin:0 0 1.15rem; font-size:1.05rem; letter-spacing:-.02em; }
    .form-grid { display:grid; grid-template-columns:1fr 1.6fr 1fr auto; gap:.85rem; align-items:end; }
    .field { display:flex; flex-direction:column; gap:.45rem; min-width:0; }
    label { font-size:.8rem; font-weight:700; color:var(--navy-800); }
    input,select { width:100%; min-width:0; min-height:43px; padding:.65rem .8rem; border:1px solid var(--border-color); border-radius:var(--radius-sm); background:#fff; color:var(--text-main); font:inherit; font-size:.86rem; outline:none; transition:var(--transition); }
    input:focus,select:focus { border-color:var(--accent-blue); box-shadow:0 0 0 3px rgba(30,64,175,.1); }
    button { font-family:inherit; font-weight:700; border-radius:var(--radius-sm); padding:.7rem 1.15rem; cursor:pointer; border:1px solid var(--navy-900); background:var(--navy-900); color:#fff; display:inline-flex; align-items:center; justify-content:center; gap:.5rem; font-size:.875rem; transition:var(--transition); white-space:nowrap; }
    button:hover:not(:disabled) { background:var(--accent-blue); border-color:var(--accent-blue); }
    .message { padding:.8rem 1rem; margin-bottom:1rem; border:1px solid #BFDBFE; border-radius:var(--radius-sm); background:#EFF6FF; color:var(--navy-800); font-size:.86rem; }
    .section-heading { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:1rem; }
    .section-heading h2 { margin:0; font-size:1.05rem; }
    .count { color:var(--text-light); font-size:.8rem; font-weight:700; background:var(--navy-50); border:1px solid var(--navy-100); border-radius:20px; padding:.25rem .65rem; }
    .table-wrap { overflow-x:auto; }
    table { width:100%; border-collapse:collapse; min-width:680px; }
    th { padding:.75rem .8rem; background:var(--navy-50); color:var(--navy-800); text-align:left; font-size:.72rem; text-transform:uppercase; letter-spacing:.06em; }
    th:first-child { border-radius:7px 0 0 7px; } th:last-child { border-radius:0 7px 7px 0; }
    td { padding:.9rem .8rem; border-bottom:1px solid var(--border-color); color:var(--text-muted); font-size:.83rem; vertical-align:middle; overflow-wrap:anywhere; }
    tr:last-child td { border-bottom:0; }
    .short-link { color:var(--accent-blue); font-weight:700; text-decoration:none; } .short-link:hover { text-decoration:underline; }
    .mode { display:inline-flex; padding:.25rem .55rem; border-radius:20px; background:var(--navy-50); color:var(--navy-700); font-size:.72rem; font-weight:700; }
    .delete-form { margin:0; } .delete-btn { padding:.42rem .7rem; background:#fff; color:#991B1B; border:1px solid #FECACA; font-size:.78rem; }
    .delete-btn:hover:not(:disabled) { background:#FEF2F2; border-color:#EF4444; color:#991B1B; }
    .empty { padding:2.5rem 1rem; text-align:center; color:var(--text-light); font-size:.9rem; }
    .footer { text-align:center; color:var(--text-light); font-size:.75rem; padding-top:.5rem; }
    @media(max-width:900px) { .form-grid { grid-template-columns:1fr 1fr; } }
    @media(max-width:600px) { .header { padding:1rem 1.1rem; } .header-desc { width:100%; padding-left:3.25rem; } .container { padding:1.5rem .9rem 3rem; } .card { padding:1.1rem; } .form-grid { grid-template-columns:1fr; } .form-grid button { width:100%; } }
  </style>
</head>
<body>
  <header class="header"><div class="header-container">
    <div class="brand">
      <div class="brand-icon"><svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.72-1.71"/></svg></div>
      <span class="brand-title">Link Manager</span>
    </div>
    <div class="header-desc">Personal URL shortener</div>
  </div></header>
  <main class="container">
    <section class="intro"><div class="eyebrow">Workspace</div><h1>Manage your short links</h1><p class="subtitle">Create custom links, choose how they open, and manage your destinations.</p></section>
    {% if message %}<div class="message">{{ message }}</div>{% endif %}
    <section class="card">
      <h2>Create a short link</h2>
      <form method="post" action="/admin/add"><div class="form-grid">
        <div class="field"><label for="code">Custom code</label><input id="code" name="code" placeholder="e.g. github" required pattern="[A-Za-z0-9_-]+" title="Use letters, numbers, hyphens, or underscores"></div>
        <div class="field"><label for="url">Destination URL</label><input id="url" name="url" type="url" placeholder="https://example.com" required></div>
        <div class="field"><label for="mode">Link behaviour</label><select id="mode" name="mode"><option value="redirect">Normal redirect</option><option value="embed">Embedded mode</option></select></div>
        <button type="submit">Create link</button>
      </div></form>
    </section>
    <section class="card">
      <div class="section-heading"><h2>Your links</h2><span class="count">{{ links|length }} total</span></div>
      {% if links %}<div class="table-wrap"><table>
        <thead><tr><th>Short link</th><th>Destination</th><th>Mode</th><th>Action</th></tr></thead>
        <tbody>{% for code, item in links %}<tr>
          <td><a class="short-link" href="{{ request.host_url }}{{ code }}" target="_blank" rel="noopener">{{ request.host_url }}{{ code }}</a></td>
          <td>{{ item.url }}</td><td><span class="mode">{{ "Embedded" if item.mode == "embed" else "Redirect" }}</span></td>
          <td><form class="delete-form" method="post" action="/admin/delete/{{ code }}" onsubmit="return confirm('Delete this short link?')"><button class="delete-btn" type="submit">Delete</button></form></td>
        </tr>{% endfor %}</tbody>
      </table></div>{% else %}<div class="empty">No short links yet. Create your first one above.</div>{% endif %}
    </section>
    <div class="footer">Private link management · Public short links</div>
  </main>
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
    links = {}
    for row in reader:
        code, url = row.get("code"), row.get("url")
        if code and url:
            mode = row.get("mode") or "embed"
            if mode not in ("redirect", "embed"):
                mode = "embed"
            links[code] = {"url": url, "mode": mode}
    return links


def write_links(links):
    ensure_storage_is_configured()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["code", "url", "mode"])
    writer.writeheader()
    for code, item in sorted(links.items()):
        writer.writerow({"code": code, "url": item["url"], "mode": item.get("mode", "embed")})
    csv_bytes = output.getvalue().encode("utf-8")

    if blob_storage_enabled():
        from vercel.blob import sync as blob
        blob.put_blob(BLOB_PATH, csv_bytes, access="private",
                      content_type="text/csv; charset=utf-8", allow_overwrite=True)
        return

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
    mode = request.form.get("mode", "redirect").strip()
    if mode not in ("redirect", "embed"):
        abort(400, "Invalid link mode.")

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
        links[code] = {"url": url, "mode": mode}
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
  <title>{{ code }}</title>
  <style>
    html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
    iframe { display: block; width: 100%; height: 100%; border: 0; }
  </style>
</head>
<body>
  <iframe src="{{ destination }}" title="Destination website"
          referrerpolicy="no-referrer-when-downgrade"
          allow="fullscreen; autoplay; clipboard-read; clipboard-write"></iframe>
</body>
</html>
"""


@app.get("/<code>")
def follow_link(code):
    links = read_links()
    item = links.get(code)
    if not item:
        abort(404)
    destination = item["url"]
    if item.get("mode", "embed") == "redirect":
        return redirect(destination, code=302)
    return render_template_string(EMBED_PAGE, code=code, destination=destination)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
