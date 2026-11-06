import csv
import hashlib
from html import escape
import io
import json
import logging
import os
import re
import secrets
import threading
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse, urlsplit
from zoneinfo import ZoneInfo

import qrcode
from flask import Flask, abort, redirect, render_template_string, request, Response, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import pyotp
except ImportError:
    pyotp = None

IST = ZoneInfo("Asia/Kolkata")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.environ.get("ADMIN_PASSWORD") or "local-development-change-this-secret"
app.permanent_session_lifetime = timedelta(minutes=int(os.environ.get("SESSION_TIMEOUT_MINUTES", "30")))
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")))
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("url-shortener")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
CSV_DIR = Path(os.environ.get("CSV_DIR", "data"))
LINKS_BLOB_PATH = os.environ.get("BLOB_CSV_PATH", "url-shortener/links.csv")
BLOB_DIR = LINKS_BLOB_PATH.rsplit("/", 1)[0] if "/" in LINKS_BLOB_PATH else "url-shortener"
LOCK = threading.RLock()
LOGIN_ATTEMPTS = {}
LINK_FIELDS = [
    "code", "url", "mode", "category", "tags", "expires_at", "password_hash",
    "archived", "created_at", "notes", "favorite", "starts_at", "mobile_url",
    "desktop_url", "country_rules", "ab_urls", "fallback_url"
]
CLICK_FIELDS = [
    "code", "clicked_at", "visitor_key", "country", "region", "city",
    "device", "browser", "os", "referrer", "referrer_host"
]
RESERVED = {"admin", "login", "logout", "health", "favicon.ico", "robots.txt"}

def now():
    return datetime.now(IST)

def now_iso():
    return now().isoformat(timespec="seconds")

def parse_ist(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=IST)
        return dt.astimezone(IST)
    except (ValueError, TypeError):
        return None

def blob_enabled():
    return bool(os.environ.get("BLOB_READ_WRITE_TOKEN")) or bool(os.environ.get("BLOB_STORE_ID") and os.environ.get("VERCEL_OIDC_TOKEN"))

def ensure_storage():
    if os.environ.get("VERCEL") and not blob_enabled():
        raise RuntimeError("Private Vercel Blob is not connected.")

def read_object(path, fields):
    ensure_storage()
    if blob_enabled():
        from vercel.blob import sync as blob
        try:
            obj = blob.get_blob(path, access="private")
            raw = obj.body.decode("utf-8-sig")
        except Exception as exc:
            if exc.__class__.__name__ in {"BlobNotFoundError", "NotFoundError"} or "not found" in str(exc).lower():
                return []
            raise
    else:
        p = CSV_DIR / Path(path).name
        if not p.exists():
            return []
        raw = p.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return []
    return [{k: (r.get(k) or "") for k in fields} for r in csv.DictReader(io.StringIO(raw))]

def write_object(path, fields, rows):
    ensure_storage()
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fields})
    data = out.getvalue().encode("utf-8")
    if blob_enabled():
        from vercel.blob import sync as blob
        blob.put_blob(path, data, access="private", content_type="text/csv; charset=utf-8", allow_overwrite=True)
    else:
        p = CSV_DIR / Path(path).name
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)

def load_links():
    result = {}
    for row in read_object(LINKS_BLOB_PATH, LINK_FIELDS):
        code, target = row.get("code", ""), row.get("url", "")
        if not code or not target:
            continue
        row["mode"] = row.get("mode") if row.get("mode") in {"redirect", "embed"} else "embed"
        row["archived"] = "1" if row.get("archived", "").lower() in {"1", "true", "yes"} else "0"
        row["favorite"] = "1" if row.get("favorite", "").lower() in {"1", "true", "yes"} else "0"
        row["created_at"] = row.get("created_at") or now_iso()
        result[code] = row
    return result

def save_links(links):
    write_object(LINKS_BLOB_PATH, LINK_FIELDS, list(links.values()))

def clicks_path():
    return f"{BLOB_DIR}/clicks.csv"

def load_clicks():
    return read_object(clicks_path(), CLICK_FIELDS)

def save_clicks(rows):
    write_object(clicks_path(), CLICK_FIELDS, rows[-25000:])

def short_url(code):
    return request.url_root.rstrip("/") + "/" + code

def valid_url(value):
    try:
        parsed = urlsplit((value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not any(c.isspace() for c in value)
    except Exception:
        return False

def link_state(item):
    if item.get("archived") == "1":
        return "Archived"
    start = parse_ist(item.get("starts_at"))
    expiry = parse_ist(item.get("expires_at"))
    if start and now() < start:
        return "Scheduled"
    if expiry and now() >= expiry:
        return "Expired"
    return "Active"

def get_client_ip():
    # Do not trust arbitrary forwarded headers on non-Vercel deployments.
    if os.environ.get("VERCEL"):
        return request.headers.get("x-forwarded-for", request.remote_addr or "").split(",")[0].strip()
    return request.remote_addr or ""

def visitor_key():
    ip = get_client_ip()
    day = now().strftime("%Y-%m-%d")
    secret = os.environ.get("ANALYTICS_HASH_SECRET") or app.secret_key
    return hashlib.sha256(f"{secret}|{day}|{ip}".encode()).hexdigest()[:24] if ip else ""

def parse_agent(ua):
    low = ua.lower()
    device = "Mobile" if any(x in low for x in ("mobile", "android", "iphone")) else ("Tablet" if "ipad" in low or "tablet" in low else "Desktop")
    browser = "Edge" if "edg/" in low else ("Firefox" if "firefox/" in low else ("Chrome" if "chrome/" in low else ("Safari" if "safari/" in low else "Other")))
    os_name = "iOS" if "iphone" in low or "ipad" in low else ("Android" if "android" in low else ("Windows" if "windows" in low else ("macOS" if "mac os" in low or "macintosh" in low else ("Linux" if "linux" in low else "Other"))))
    return device, browser, os_name

def record_click(code):
    ua = request.user_agent.string[:300]
    device, browser, os_name = parse_agent(ua)
    ref = (request.referrer or "")[:500]
    try:
        host = urlsplit(ref).netloc[:180]
    except Exception:
        host = ""
    event = {
        "code": code, "clicked_at": now_iso(), "visitor_key": visitor_key(),
        "country": request.headers.get("x-vercel-ip-country", "")[:8],
        "region": request.headers.get("x-vercel-ip-country-region", "")[:80],
        "city": request.headers.get("x-vercel-ip-city", "")[:100],
        "device": device, "browser": browser, "os": os_name,
        "referrer": ref, "referrer_host": host
    }
    with LOCK:
        events = load_clicks()
        events.append(event)
        save_clicks(events)

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("login", next=request.path))
        session.permanent = True
        return fn(*args, **kwargs)
    return wrapped

def login_limited(ip):
    now_ts = datetime.now().timestamp()
    attempts = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now_ts - t < 900]
    LOGIN_ATTEMPTS[ip] = attempts
    return len(attempts) >= 8

def log_login_failure(ip):
    LOGIN_ATTEMPTS.setdefault(ip, []).append(datetime.now().timestamp())

def totp_required():
    return bool(os.environ.get("ADMIN_TOTP_SECRET"))

def valid_totp(code):
    secret = os.environ.get("ADMIN_TOTP_SECRET", "").replace(" ", "")
    if not secret:
        return True
    if not pyotp:
        return False
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:
        return False

LOGIN_PAGE = r"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Admin login</title><style>body{font-family:system-ui;background:#f8fafc;display:grid;place-items:center;min-height:100vh;margin:0;color:#0f172a}.box{background:white;padding:30px;border:1px solid #e2e8f0;border-radius:16px;width:min(380px,calc(100% - 40px));box-shadow:0 8px 30px #0a192f12}h1{font-size:23px;margin:0 0 8px}.muted{color:#64748b;font-size:13px;margin-bottom:20px}label{display:block;font-size:12px;font-weight:700;margin:12px 0 6px}input{width:100%;box-sizing:border-box;padding:12px;border:1px solid #cbd5e1;border-radius:8px}button{margin-top:18px;width:100%;padding:12px;background:#0a192f;color:white;border:0;border-radius:8px;font-weight:700}.error{color:#991b1b;background:#fef2f2;padding:10px;border-radius:7px;font-size:13px}</style></head><body><form class="box" method="post"><h1>Link Manager</h1><div class="muted">Sign in to manage your links.</div>{% if error %}<div class="error">{{ error }}</div>{% endif %}<label>Username</label><input name="username" autocomplete="username" required><label>Password</label><input name="password" type="password" autocomplete="current-password" required>{% if totp %}<label>Authenticator code</label><input name="totp" inputmode="numeric" pattern="[0-9]{6}" autocomplete="one-time-code" required>{% endif %}<button>Sign in</button></form></body></html>"""

PASS = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Protected link</title><style>body{font-family:system-ui;background:#f8fafc;display:grid;place-items:center;min-height:100vh}.box{background:white;padding:28px;border:1px solid #e2e8f0;border-radius:14px;width:min(360px,90%)}input,button{box-sizing:border-box;width:100%;padding:12px;margin-top:10px;border-radius:8px;border:1px solid #cbd5e1}button{background:#0a192f;color:white}.err{color:#b91c1c}</style></head><body><form class="box" method="post"><h2>Protected link</h2><p>Enter the password to continue.</p>{% if error %}<p class="err">{{ error }}</p>{% endif %}<input type="password" name="password" required autofocus><button>Continue</button></form></body></html>"""

EMBED = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ code }}</title><style>html,body,iframe{margin:0;width:100%;height:100%;border:0;overflow:hidden}iframe{position:fixed;inset:0}</style></head><body><iframe src="{{ destination }}" referrerpolicy="no-referrer-when-downgrade" allow="fullscreen"></iframe></body></html>"""

STYLE = r"""
:root{--navy:#0A192F;--blue:#1E40AF;--bg:#F8FAFC;--text:#0F172A;--muted:#475569;--line:#E2E8F0}
*{box-sizing:border-box}body{margin:0;font-family:'Plus Jakarta Sans',system-ui,sans-serif;background-color:var(--bg);background-image:radial-gradient(#cbd5e1 1px,transparent 1px);background-size:24px 24px;color:var(--text);min-height:100vh}.header{background:var(--navy);color:white;padding:17px 24px}.head{max-width:1280px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:12px}.brand{font-weight:800;font-size:20px}.muted-head{color:#cbd5e1;font-size:12px}.wrap{max-width:1280px;margin:30px auto;padding:0 20px 50px}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:800;color:#254b7c;text-transform:uppercase}h1{font-size:28px;margin:6px 0}.sub{color:var(--muted);font-size:13px;margin:0 0 20px}.card,.stat{background:white;border:1px solid var(--line);border-radius:13px;box-shadow:0 4px 14px #0a192f0d}.card{padding:20px;margin-bottom:18px}.card h2{font-size:16px;margin:0 0 14px}.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:11px;margin:18px 0}.stat{padding:14px}.stat b{display:block;font-size:24px;color:var(--navy)}.stat span{font-size:10px;color:#64748b;font-weight:800}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px;align-items:end}.field{display:flex;flex-direction:column;gap:6px;min-width:0}label{font-size:11px;font-weight:800;color:#112240}input,select,textarea{width:100%;min-height:40px;padding:9px 11px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:12px;background:white;color:var(--text)}button,.btn{border:1px solid var(--navy);background:var(--navy);color:white;padding:9px 12px;border-radius:8px;font:700 11px system-ui;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:5px;white-space:nowrap}.btn-light{background:white;color:var(--navy);border-color:var(--line)}.btn-danger{background:white;color:#991b1b;border-color:#fecaca}.msg{padding:11px 13px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;color:#112240;font-size:12px;margin:12px 0}.toolbar{display:flex;gap:9px;flex-wrap:wrap;align-items:end;margin-bottom:13px}.toolbar .field{flex:1;min-width:130px}.actions{display:flex;gap:5px;flex-wrap:wrap}.actions button,.actions .btn{padding:6px 8px;font-size:10px}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:1000px}th{text-align:left;background:#f0f5fa;color:#112240;font-size:10px;padding:11px;text-transform:uppercase}td{border-bottom:1px solid var(--line);padding:10px;font-size:11px;color:#475569;vertical-align:middle}.short{font-weight:800;color:var(--blue);text-decoration:none}.pill{display:inline-block;padding:4px 7px;border-radius:20px;background:#f0f5fa;color:#1d3557;font-size:9px;font-weight:800}.small{font-size:10px;color:#64748b}.inline{display:inline}.chart{height:220px;width:100%}.chart svg{width:100%;height:100%}.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}.error{color:#991b1b}.footer{text-align:center;color:#64748b;font-size:10px;padding:10px}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{grid-template-columns:repeat(3,1fr)}}@media(max-width:600px){.wrap{padding:0 12px 30px;margin:20px auto}.grid,.split{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.header{padding:14px}}
"""

DASH = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Link Manager</title><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>"""+STYLE+r"""</style></head><body><header class="header"><div class="head"><div class="brand">↗ Link Manager</div><div class="muted-head">Personal URL shortener · IST</div><div class="actions"><a class="btn btn-light" href="/admin/analytics">Analytics</a><a class="btn btn-light" href="/admin/backup">Backup</a><a class="btn btn-light" href="/admin/logout">Logout</a></div></div></header><main class="wrap"><div class="eyebrow">Workspace</div><h1>Manage your short links</h1><p class="sub">Create, organise, protect and analyse your personal short links.</p>{% if message %}<div class="msg">{{ message }}</div>{% endif %}
<div class="stats"><div class="stat"><b>{{ stats.total }}</b><span>TOTAL LINKS</span></div><div class="stat"><b>{{ stats.active }}</b><span>ACTIVE</span></div><div class="stat"><b>{{ stats.scheduled }}</b><span>SCHEDULED</span></div><div class="stat"><b>{{ stats.archived }}</b><span>ARCHIVED</span></div><div class="stat"><b>{{ stats.clicks }}</b><span>RECORDED CLICKS</span></div></div>
<section class="card"><h2>{{ 'Edit short link' if editing else 'Create a short link' }}</h2><form method="post" action="{{ '/admin/edit/'+editing.code if editing else '/admin/add' }}"><div class="grid">
<div class="field"><label>Custom code</label><input name="code" required pattern="[A-Za-z0-9_-]{1,64}" value="{{ editing.code if editing else '' }}" {{ 'readonly' if editing else '' }} placeholder="github"></div>
<div class="field"><label>Destination URL</label><input name="url" type="url" required value="{{ editing.url if editing else '' }}" placeholder="https://example.com"></div>
<div class="field"><label>Behaviour</label><select name="mode"><option value="redirect" {{ 'selected' if editing and editing.mode=='redirect' else '' }}>Normal redirect</option><option value="embed" {{ 'selected' if editing and editing.mode=='embed' else '' }}>Embedded mode</option></select></div>
<div class="field"><label>Category</label><input name="category" value="{{ editing.category if editing else '' }}" placeholder="Work, Personal"></div>
<div class="field"><label>Tags</label><input name="tags" value="{{ editing.tags if editing else '' }}" placeholder="portfolio, docs"></div>
<div class="field"><label>Starts at (IST)</label><input name="starts_at" type="datetime-local" value="{{ editing.starts_at if editing else '' }}"></div>
<div class="field"><label>Expires at (IST)</label><input name="expires_at" type="datetime-local" value="{{ editing.expires_at if editing else '' }}"></div>
<div class="field"><label>Link password</label><input name="password" type="password" placeholder="Blank keeps existing"></div>
<div class="field"><label>Mobile destination (optional)</label><input name="mobile_url" type="url" value="{{ editing.mobile_url if editing else '' }}" placeholder="https://m.example.com"></div>
<div class="field"><label>Desktop destination (optional)</label><input name="desktop_url" type="url" value="{{ editing.desktop_url if editing else '' }}" placeholder="https://www.example.com"></div>
<div class="field"><label>Fallback URL (optional)</label><input name="fallback_url" type="url" value="{{ editing.fallback_url if editing else '' }}" placeholder="https://backup.example.com"></div>
<div class="field"><label>A/B destinations (one URL per line)</label><textarea name="ab_urls" rows="2" placeholder="Optional, takes precedence over device routing">{{ editing.ab_urls if editing else '' }}</textarea></div>
<div class="field"><label>Country rules (JSON)</label><textarea name="country_rules" rows="2" placeholder='{"IN":"https://example.in"}'>{{ editing.country_rules if editing else '' }}</textarea></div>
<div class="field"><label>Private notes</label><input name="notes" value="{{ editing.notes if editing else '' }}" placeholder="Internal note"></div>
<div class="field"><label>Favourite</label><select name="favorite"><option value="0">No</option><option value="1" {{ 'selected' if editing and editing.favorite=='1' else '' }}>Yes</option></select></div>
<button type="submit">{{ 'Save changes' if editing else 'Create link' }}</button></div><p class="small">A/B destinations are assigned by a stable visitor hash. Country routing uses Vercel geo headers. Scheduled links activate at the selected IST time.</p></form></section>
<section class="card"><h2>Find and manage links</h2><form method="get" class="toolbar"><div class="field"><label>Search</label><input name="q" value="{{ q }}" placeholder="Code, URL, category, tags or notes"></div><div class="field"><label>Mode</label><select name="mode"><option value="">All</option><option value="redirect" {{ 'selected' if mode=='redirect' else '' }}>Redirect</option><option value="embed" {{ 'selected' if mode=='embed' else '' }}>Embedded</option></select></div><div class="field"><label>Status</label><select name="status"><option value="active" {{ 'selected' if status=='active' else '' }}>Active</option><option value="archived" {{ 'selected' if status=='archived' else '' }}>Archived</option><option value="all" {{ 'selected' if status=='all' else '' }}>All</option></select></div><button>Filter</button><a class="btn btn-light" href="/admin">Reset</a></form><div class="actions" style="margin-bottom:13px"><a class="btn btn-light" href="/admin/export">Export CSV</a><a class="btn btn-light" href="/admin/import">Import CSV</a><a class="btn btn-light" href="/admin/analytics">Analytics</a><a class="btn btn-light" href="/admin/backup">Download backup</a></div>
<form method="post" action="/admin/bulk" id="bulk"><div class="toolbar"><select name="action"><option value="archive">Archive selected</option><option value="restore">Restore selected</option><option value="favorite">Favourite selected</option><option value="unfavorite">Unfavourite selected</option><option value="delete">Delete selected</option></select><button class="btn-light" type="submit" onclick="return confirm('Apply this action to selected links?')">Apply bulk action</button></div>
{% if links %}<div class="table-wrap"><table><thead><tr><th><input type="checkbox" onclick="document.querySelectorAll('.pick').forEach(x=>x.checked=this.checked)"></th><th>Short link</th><th>Destination</th><th>Mode / status</th><th>Clicks</th><th>Actions</th></tr></thead><tbody>{% for code,item in links %}<tr><td><input class="pick" type="checkbox" name="codes" value="{{ code }}"></td><td><a class="short" href="{{ short_url(code) }}" target="_blank">/{{ code }}</a><div class="small">{{ item.category }} · {{ item.tags }}</div></td><td>{{ item.url[:90] }}{% if item.favorite=='1' %} ★{% endif %}</td><td><span class="pill">{{ item.mode }}</span> <span class="pill">{{ states[code] }}</span>{% if item.password_hash %}<span class="pill">Protected</span>{% endif %}</td><td>{{ counts.get(code,0) }}</td><td><div class="actions"><button type="button" class="copy" data-url="{{ short_url(code) }}">Copy</button><a class="btn btn-light" href="/admin/qr/{{ code }}">QR</a><a class="btn btn-light" href="/admin/analytics/{{ code }}">Stats</a><a class="btn btn-light" href="/admin/clone/{{ code }}">Clone</a><a class="btn btn-light" href="/admin/edit/{{ code }}">Edit</a><form class="inline" method="post" action="/admin/archive/{{ code }}"><button class="btn-light">{{ 'Restore' if item.archived=='1' else 'Archive' }}</button></form></div></td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="small">No links match these filters.</p>{% endif %}</form></section><div class="footer">All application dates and times are interpreted in India Standard Time.</div></main><script>document.querySelectorAll('.copy').forEach(b=>b.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(b.dataset.url);b.textContent='Copied'}catch(e){prompt('Copy short URL',b.dataset.url)}}));</script></body></html>"""

def dashboard_context(links, events, **kwargs):
    counts = Counter(e["code"] for e in events)
    states = {c: link_state(item) for c, item in links.items()}
    stats = {
        "total": len(links),
        "active": sum(s == "Active" for s in states.values()),
        "scheduled": sum(s == "Scheduled" for s in states.values()),
        "archived": sum(s == "Archived" for s in states.values()),
        "clicks": len(events)
    }
    return dict(stats=stats, counts=counts, states=states, short_url=short_url, **kwargs)

@app.get("/")
def home():
    return "Personal URL shortener is running."

@app.get("/health")
def health():
    return {"status": "ok", "timezone": "Asia/Kolkata", "storage": "blob" if blob_enabled() else "local"}

@app.route("/login", methods=["GET", "POST"])
def login():
    ip = get_client_ip()
    if login_limited(ip):
        return render_template_string(LOGIN_PAGE, error="Too many attempts. Try again in 15 minutes.", totp=totp_required()), 429
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        totp = request.form.get("totp", "")
        valid = bool(ADMIN_PASSWORD) and secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD) and valid_totp(totp)
        if valid:
            session.clear()
            session["admin_authenticated"] = True
            session.permanent = True
            LOGIN_ATTEMPTS.pop(ip, None)
            next_path = request.args.get("next", "")
            return redirect(next_path if next_path.startswith("/") and not next_path.startswith("//") else "/admin")
        log_login_failure(ip)
        error = "Invalid credentials or authenticator code."
    return render_template_string(LOGIN_PAGE, error=error, totp=totp_required())

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.get("/admin")
@admin_required
def admin():
    links = load_links()
    events = load_clicks()
    q = request.args.get("q", "").lower().strip()
    mode = request.args.get("mode", "")
    status = request.args.get("status", "active")
    shown = []
    for code, item in links.items():
        state = link_state(item)
        if status == "active" and item["archived"] == "1":
            continue
        if status == "archived" and item["archived"] != "1":
            continue
        if mode and item["mode"] != mode:
            continue
        haystack = " ".join([code, item["url"], item.get("category", ""), item.get("tags", ""), item.get("notes", "")]).lower()
        if q and q not in haystack:
            continue
        shown.append((code, item))
    shown.sort(key=lambda x: (x[1].get("favorite") != "1", x[0].lower()))
    context = dashboard_context(links, events, links=shown, q=q, mode=mode, status=status, message=request.args.get("message", ""), editing=None)
    return render_template_string(DASH, **context)

def form_item(code, old=None):
    old = old or {}
    dest = request.form.get("url", "").strip()
    mode = request.form.get("mode", "redirect")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", code) or code.lower() in RESERVED:
        abort(400, "Invalid or reserved short code.")
    if not valid_url(dest) or mode not in {"redirect", "embed"}:
        abort(400, "Invalid destination URL or mode.")
    values = {}
    for field, limit in [("category", 80), ("tags", 300), ("notes", 500)]:
        values[field] = request.form.get(field, "").strip()[:limit]
    for field in ["mobile_url", "desktop_url", "fallback_url"]:
        value = request.form.get(field, "").strip()
        if value and not valid_url(value):
            abort(400, f"Invalid {field.replace('_', ' ')}.")
        values[field] = value
    for field in ["starts_at", "expires_at"]:
        value = request.form.get(field, "").strip()
        if value and not parse_ist(value):
            abort(400, f"Invalid {field.replace('_', ' ')}.")
        values[field] = value
    country_rules = request.form.get("country_rules", "").strip()
    if country_rules:
        try:
            parsed = json.loads(country_rules)
            if not isinstance(parsed, dict) or any(not re.fullmatch(r"[A-Z]{2}", str(k)) or not valid_url(v) for k, v in parsed.items()):
                raise ValueError()
        except Exception:
            abort(400, "Country rules must be a JSON object mapping two letter country codes to valid URLs.")
    ab_urls = request.form.get("ab_urls", "").strip()
    ab_list = [x.strip() for x in ab_urls.splitlines() if x.strip()]
    if len(ab_list) > 10 or any(not valid_url(x) for x in ab_list):
        abort(400, "A/B testing accepts up to 10 valid URLs, one per line.")
    password = request.form.get("password", "")
    return {
        "code": code, "url": dest, "mode": mode, **values,
        "country_rules": country_rules, "ab_urls": "\n".join(ab_list),
        "favorite": "1" if request.form.get("favorite") == "1" else "0",
        "password_hash": generate_password_hash(password) if password else old.get("password_hash", ""),
        "archived": old.get("archived", "0"), "created_at": old.get("created_at") or now_iso()
    }

@app.post("/admin/add")
@admin_required
def add_link():
    code = request.form.get("code", "").strip()
    with LOCK:
        links = load_links()
        if code in links:
            return redirect("/admin?message=Short+code+already+exists.")
        links[code] = form_item(code)
        save_links(links)
    return redirect("/admin?message=Link+created.")

@app.get("/admin/edit/<code>")
@admin_required
def edit_link(code):
    links = load_links()
    item = links.get(code)
    if not item:
        abort(404)
    context = dashboard_context(links, load_clicks(), links=sorted(links.items()), q="", mode="", status="all", message="", editing=item)
    return render_template_string(DASH, **context)

@app.post("/admin/edit/<code>")
@admin_required
def save_edit(code):
    with LOCK:
        links = load_links()
        if code not in links:
            abort(404)
        links[code] = form_item(code, links[code])
        save_links(links)
    return redirect("/admin?message=Changes+saved.")

@app.post("/admin/archive/<code>")
@admin_required
def archive_link(code):
    with LOCK:
        links = load_links()
        if code not in links:
            abort(404)
        links[code]["archived"] = "0" if links[code]["archived"] == "1" else "1"
        save_links(links)
    return redirect("/admin?message=Link+status+updated.")

@app.post("/admin/bulk")
@admin_required
def bulk_action():
    action = request.form.get("action", "")
    codes = request.form.getlist("codes")
    if len(codes) > 500:
        abort(400, "Select no more than 500 links at a time.")
    with LOCK:
        links = load_links()
        for code in codes:
            if code not in links:
                continue
            if action == "archive":
                links[code]["archived"] = "1"
            elif action == "restore":
                links[code]["archived"] = "0"
            elif action == "favorite":
                links[code]["favorite"] = "1"
            elif action == "unfavorite":
                links[code]["favorite"] = "0"
            elif action == "delete":
                links.pop(code, None)
            else:
                abort(400, "Unknown bulk action.")
        save_links(links)
    return redirect("/admin?message=Bulk+action+completed.")

@app.get("/admin/clone/<code>")
@admin_required
def clone_link(code):
    links = load_links()
    source = links.get(code)
    if not source:
        abort(404)
    new_code = f"{code}-copy"
    suffix = 2
    while new_code in links:
        new_code = f"{code}-copy{suffix}"
        suffix += 1
    clone = dict(source)
    clone.update(code=new_code, created_at=now_iso(), archived="0", favorite="0", password_hash="")
    links[new_code] = clone
    save_links(links)
    return redirect("/admin/edit/" + new_code)

@app.get("/admin/export")
@admin_required
def export_csv():
    rows = read_object(LINKS_BLOB_PATH, LINK_FIELDS)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=LINK_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=short-links-export.csv"})

@app.route("/admin/import", methods=["GET", "POST"])
@admin_required
def import_csv():
    if request.method == "GET":
        return render_template_string("""<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>"""+STYLE+"""</style></head><body><main class="wrap"><section class="card"><h1>Import CSV</h1><p class="sub">Required columns: code,url. Optional columns follow the current export format.</p><form method="post" enctype="multipart/form-data"><input type="file" name="file" accept=".csv,text/csv" required><p><button>Import links</button> <a class="btn btn-light" href="/admin">Back</a></p></form></section></main></body></html>""")
    upload = request.files.get("file")
    if not upload:
        abort(400, "Choose a CSV file.")
    try:
        raw = upload.stream.read(2_000_001)
        if len(raw) > 2_000_000:
            abort(413, "CSV file is larger than 2 MB.")
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    except UnicodeDecodeError:
        abort(400, "CSV must be UTF-8 encoded.")
    with LOCK:
        links = load_links()
        count = 0
        for row in rows:
            code = (row.get("code") or "").strip()
            dest = (row.get("url") or "").strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", code) or code.lower() in RESERVED or not valid_url(dest):
                continue
            previous = links.get(code, {})
            item = {k: row.get(k, previous.get(k, "")) for k in LINK_FIELDS}
            item.update(code=code, url=dest, created_at=previous.get("created_at") or now_iso())
            item["mode"] = item["mode"] if item["mode"] in {"redirect", "embed"} else "redirect"
            if row.get("password"):
                item["password_hash"] = generate_password_hash(row["password"])
            item["archived"] = "1" if str(item.get("archived", "0")).lower() in {"1", "true", "yes"} else "0"
            links[code] = item
            count += 1
        save_links(links)
    return redirect(f"/admin?message=Imported+or+updated+{count}+links.")

@app.get("/admin/backup")
@admin_required
def backup():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for path, fields, name in [(LINKS_BLOB_PATH, LINK_FIELDS, "links.csv"), (clicks_path(), CLICK_FIELDS, "clicks.csv")]:
            out = io.StringIO(newline="")
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(read_object(path, fields))
            z.writestr(name, out.getvalue())
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name=f"url-shortener-backup-{now().strftime('%Y%m%d-%H%M')}-IST.zip")

def analytics_payload():
    events = load_clicks()
    links = load_links()
    counts = Counter(e["code"] for e in events)
    today = now().date()
    daily = Counter()
    for event in events:
        dt = parse_ist(event.get("clicked_at"))
        if dt:
            daily[dt.strftime("%Y-%m-%d")] += 1
    last7 = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]
    unique = len({(e.get("clicked_at", "")[:10], e.get("visitor_key", "")) for e in events if e.get("visitor_key")})
    return events, links, counts, daily, last7, unique

@app.get("/admin/analytics")
@admin_required
def analytics():
    events, links, counts, daily, days, unique = analytics_payload()
    device = Counter(e.get("device", "Unknown") for e in events)
    browser = Counter(e.get("browser", "Unknown") for e in events)
    country = Counter(e.get("country", "Unknown") or "Unknown" for e in events)
    refs = Counter(e.get("referrer_host", "Direct") or "Direct" for e in events)
    maxv = max([daily[d] for d in days] + [1])
    bars = "".join(f'<div style="flex:1;display:flex;flex-direction:column;justify-content:end;align-items:center;gap:6px"><div title="{daily[d]} clicks" style="width:65%;height:{max(3, daily[d]/maxv*150)}px;background:#1e40af;border-radius:5px 5px 0 0"></div><small>{d[5:]}</small></div>' for d in days)
    top = sorted(links, key=lambda c: counts[c], reverse=True)[:10]
    top_rows = "".join(f'<tr><td>/{escape(c)}</td><td>{escape(links[c]["url"][:100])}</td><td>{counts[c]}</td></tr>' for c in top)
    def rows(counter):
        return "".join(f"<tr><td>{escape(str(k))}</td><td>{v}</td></tr>" for k, v in counter.most_common(10))
    html = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>"""+STYLE+"""</style></head><body><header class="header"><div class="head"><div class="brand">Link Manager · Analytics</div><div class="actions"><a class="btn btn-light" href="/admin">Dashboard</a><a class="btn btn-light" href="/admin/backup">Backup</a></div></div></header><main class="wrap"><h1>Analytics overview</h1><p class="sub">Latest 25,000 click events. Visitor identifiers are daily salted hashes, not stored IP addresses.</p><div class="stats"><div class="stat"><b>{{ total }}</b><span>RECORDED CLICKS</span></div><div class="stat"><b>{{ unique }}</b><span>DAILY UNIQUE VISITORS</span></div><div class="stat"><b>{{ links }}</b><span>LINKS</span></div><div class="stat"><b>{{ today }}</b><span>CLICKS TODAY</span></div></div><section class="card"><h2>Clicks over the last 7 days</h2><div style="height:190px;display:flex;align-items:end;gap:10px">{{ bars|safe }}</div></section><div class="split"><section class="card"><h2>Devices</h2><table><tbody>{{ device|safe }}</tbody></table></section><section class="card"><h2>Browsers</h2><table><tbody>{{ browser|safe }}</tbody></table></section><section class="card"><h2>Countries</h2><table><tbody>{{ country|safe }}</tbody></table></section><section class="card"><h2>Referrers</h2><table><tbody>{{ refs|safe }}</tbody></table></section></div><section class="card"><h2>Top links</h2><div class="table-wrap"><table><thead><tr><th>Short code</th><th>Destination</th><th>Clicks</th></tr></thead><tbody>{{ top_rows|safe }}</tbody></table></div></section></main></body></html>"""
    return render_template_string(html, total=len(events), unique=unique, links=len(links), today=daily[now().strftime("%Y-%m-%d")], bars=bars, device=rows(device), browser=rows(browser), country=rows(country), refs=rows(refs), top_rows=top_rows)

@app.get("/admin/analytics/<code>")
@admin_required
def link_analytics(code):
    links = load_links()
    if code not in links:
        abort(404)
    events = [e for e in load_clicks() if e["code"] == code]
    count = len(events)
    unique = len({(e.get("clicked_at", "")[:10], e.get("visitor_key", "")) for e in events if e.get("visitor_key")})
    recent = "".join(f"<tr><td>{escape(e['clicked_at'])}</td><td>{escape(e['country'] or 'Unknown')}</td><td>{escape(e['device'])}</td><td>{escape(e['browser'])}</td><td>{escape(e['referrer_host'] or 'Direct')}</td></tr>" for e in events[-100:][::-1])
    return render_template_string("""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>"""+STYLE+"""</style></head><body><main class="wrap"><section class="card"><h1>Analytics: /{{ code }}</h1><p class="sub">{{ count }} clicks · {{ unique }} daily unique visitors</p><div class="table-wrap"><table><thead><tr><th>Time (IST)</th><th>Country</th><th>Device</th><th>Browser</th><th>Referrer</th></tr></thead><tbody>{{ recent|safe }}</tbody></table></div><p><a class="btn btn-light" href="/admin">Dashboard</a></p></section></main></body></html>""", code=code, count=count, unique=unique, recent=recent)

@app.get("/admin/qr/<code>")
@admin_required
def qr_code(code):
    if code not in load_links():
        abort(404)
    image = qrcode.make(short_url(code))
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", download_name=f"{code}-qr.png")

@app.route("/<code>", methods=["GET", "POST"])
def follow_link(code):
    item = load_links().get(code)
    if not item or item["archived"] == "1":
        abort(404)
    state = link_state(item)
    if state in {"Expired", "Scheduled"}:
        abort(404)
    if item.get("password_hash"):
        if request.method == "GET":
            return render_template_string(PASS, error="")
        if not check_password_hash(item["password_hash"], request.form.get("password", "")):
            return render_template_string(PASS, error="Incorrect password."), 401
    record_click(code)
    country = request.headers.get("x-vercel-ip-country", "").upper()
    target = item["url"]
    try:
        rules = json.loads(item.get("country_rules") or "{}")
        if country in rules:
            target = rules[country]
    except Exception:
        pass
    if target == item["url"] and item.get("ab_urls"):
        choices = [x for x in item["ab_urls"].splitlines() if valid_url(x)]
        if choices:
            visitor = visitor_key() or secrets.token_hex(8)
            index = int(hashlib.sha256(visitor.encode()).hexdigest(), 16) % len(choices)
            target = choices[index]
    if target == item["url"]:
        device, _, _ = parse_agent(request.user_agent.string)
        device_target = item.get("mobile_url") if device in {"Mobile", "Tablet"} else item.get("desktop_url")
        if device_target and valid_url(device_target):
            target = device_target
    if item["mode"] == "embed":
        return render_template_string(EMBED, code=code, destination=target)
    return redirect(target, code=302)

@app.errorhandler(500)
def internal_error(error):
    log.exception("Unhandled application error: %s", error)
    return "An internal error occurred. Check the Vercel function logs.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
