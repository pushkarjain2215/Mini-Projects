from zoneinfo import ZoneInfo
import csv, io, os, re, threading
from datetime import datetime, timezone
from functools import wraps
from secrets import compare_digest
from urllib.parse import urlparse

import qrcode
from flask import Flask, abort, redirect, render_template_string, request, Response, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

IST = ZoneInfo("Asia/Kolkata")

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
CSV_DIR = os.environ.get('CSV_DIR', 'data')
# Keep the exact legacy links.csv object path so existing deployed links remain available.
LINKS_BLOB_PATH = os.environ.get('BLOB_CSV_PATH', 'url-shortener/links.csv')
BLOB_DIR = LINKS_BLOB_PATH.rsplit('/', 1)[0] if '/' in LINKS_BLOB_PATH else 'url-shortener'
LOCK = threading.RLock()
LINK_FIELDS = ['code','url','mode','category','tags','expires_at','password_hash','archived','created_at']
CLICK_FIELDS = ['code','clicked_at','user_agent','referrer']


def now_iso(): return datetime.now(IST).isoformat(timespec='seconds')
def blob_enabled(): return bool(os.environ.get('BLOB_READ_WRITE_TOKEN')) or bool(os.environ.get('BLOB_STORE_ID') and os.environ.get('VERCEL_OIDC_TOKEN'))
def ensure_storage():
    if os.environ.get('VERCEL') and not blob_enabled(): raise RuntimeError('Private Vercel Blob is not connected.')


def read_object(path, fields):
    ensure_storage()
    if blob_enabled():
        from vercel.blob import sync as blob
        try:
            obj=blob.get_blob(path, access='private'); raw=obj.body.decode('utf-8-sig')
        except Exception as exc:
            if exc.__class__.__name__ in {'BlobNotFoundError','NotFoundError'} or 'not found' in str(exc).lower(): return []
            raise
    else:
        from pathlib import Path
        p=Path(CSV_DIR)/Path(path).name
        if not p.exists(): return []
        raw=p.read_text(encoding='utf-8-sig')
    if not raw.strip(): return []
    return [{k:(r.get(k) or '') for k in fields} for r in csv.DictReader(io.StringIO(raw))]


def write_object(path, fields, rows):
    ensure_storage(); out=io.StringIO(newline=''); w=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore'); w.writeheader()
    for row in rows: w.writerow({k:row.get(k,'') for k in fields})
    data=out.getvalue().encode('utf-8')
    if blob_enabled():
        from vercel.blob import sync as blob
        blob.put_blob(path,data,access='private',content_type='text/csv; charset=utf-8',allow_overwrite=True)
    else:
        from pathlib import Path
        p=Path(CSV_DIR)/Path(path).name; p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_bytes(data); tmp.replace(p)


def load_links():
    links={}
    for r in read_object(LINKS_BLOB_PATH, LINK_FIELDS):
        if not r['code'] or not r['url']: continue
        r['mode']=r['mode'] if r['mode'] in ('redirect','embed') else 'embed'
        r['category']=r.get('category',''); r['tags']=r.get('tags','')
        r['archived']='1' if r.get('archived','').lower() in ('1','true','yes') else '0'
        r['created_at']=r.get('created_at') or now_iso(); links[r['code']]=r
    return links


def save_links(links): write_object(LINKS_BLOB_PATH, LINK_FIELDS, list(links.values()))
def clicks_path(): return f'{BLOB_DIR}/clicks.csv'
def load_clicks(): return read_object(clicks_path(), CLICK_FIELDS)
def save_clicks(rows): write_object(clicks_path(), CLICK_FIELDS, rows[-25000:])
def short_url(code): return request.url_root.rstrip('/')+'/'+code


def require_admin(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        a=request.authorization
        if not ADMIN_PASSWORD or not a or not compare_digest(a.username or '',ADMIN_USERNAME) or not compare_digest(a.password or '',ADMIN_PASSWORD):
            return Response('Authentication required',401,{'WWW-Authenticate':'Basic realm="URL shortener admin"'})
        return fn(*args,**kwargs)
    return wrapped


def valid_url(value):
    p=urlparse(value or ''); return p.scheme in ('http','https') and bool(p.netloc)
def expired(item):
    val=item.get('expires_at','')
    if not val: return False
    try:
        d=datetime.fromisoformat(val.replace('Z','+00:00'))
        if d.tzinfo is None: d=d.astimezone()
        return d <= datetime.now(d.tzinfo).astimezone(timezone.utc)
    except ValueError: return False

STYLE = r'''
:root{--navy-950:#07111E;--navy-900:#0A192F;--navy-800:#112240;--navy-700:#1D3557;--navy-600:#254B7C;--navy-100:#E6EEF8;--navy-50:#F0F5FA;--accent:#1E40AF;--bg:#F8FAFC;--text:#0F172A;--muted:#475569;--light:#64748B;--border:#E2E8F0}
*{box-sizing:border-box}body{margin:0;font-family:'Plus Jakarta Sans',system-ui,sans-serif;background-color:var(--bg);background-image:radial-gradient(#cbd5e1 1px,transparent 1px);background-size:24px 24px;color:var(--text);min-height:100vh}.header{background:var(--navy-900);color:white;padding:18px 28px}.head{max-width:1240px;margin:auto;display:flex;align-items:center;justify-content:space-between;gap:12px}.brand{display:flex;align-items:center;gap:12px;font-weight:800;font-size:20px}.logo{width:40px;height:40px;border-radius:9px;background:linear-gradient(135deg,#1e40af,#0a192f);border:1px solid #52647c;display:grid;place-items:center}.muted-head{color:#94a3b8;font-size:13px}.wrap{max-width:1180px;margin:34px auto;padding:0 20px 50px}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:800;color:var(--navy-600);text-transform:uppercase}h1{font-size:30px;letter-spacing:-1px;margin:6px 0}.sub{color:var(--muted);margin:0 0 22px;font-size:14px}.card{background:white;border:1px solid var(--border);border-radius:14px;box-shadow:0 4px 14px #0a192f0d;padding:22px;margin:0 0 20px}.card h2{font-size:16px;margin:0 0 16px}.grid{display:grid;grid-template-columns:1fr 1.5fr 1fr 1fr;gap:12px;align-items:end}.field{display:flex;flex-direction:column;gap:6px;min-width:0}label{font-size:12px;font-weight:700;color:var(--navy-800)}input,select{width:100%;min-height:42px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;font:inherit;font-size:13px;background:white;color:var(--text)}input:focus,select:focus{outline:0;border-color:var(--accent);box-shadow:0 0 0 3px #1e40af18}button,.btn{border:1px solid var(--navy-900);background:var(--navy-900);color:white;padding:10px 14px;border-radius:8px;font:700 12px inherit;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap}button:hover,.btn:hover{background:var(--accent)}.btn-light{background:white;color:var(--navy-800);border-color:var(--border)}.btn-light:hover{background:var(--navy-50);color:var(--navy-900)}.btn-danger{background:white;color:#991b1b;border-color:#fecaca}.msg{padding:12px 14px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;color:var(--navy-800);font-size:13px;margin-bottom:16px}.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin-bottom:16px}.toolbar .field{flex:1;min-width:150px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.stat{background:white;border:1px solid var(--border);border-radius:12px;padding:16px}.stat b{display:block;font-size:25px;color:var(--navy-900)}.stat span{font-size:11px;color:var(--light);font-weight:700}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:900px}th{text-align:left;background:var(--navy-50);color:var(--navy-800);font-size:10px;letter-spacing:.7px;text-transform:uppercase;padding:12px}td{border-bottom:1px solid var(--border);padding:12px;font-size:12px;color:var(--muted);vertical-align:middle}.short{font-weight:800;color:var(--accent);text-decoration:none}.pill{display:inline-block;padding:4px 8px;border-radius:20px;background:var(--navy-50);color:var(--navy-700);font-size:10px;font-weight:800}.actions{display:flex;gap:5px;flex-wrap:wrap}.actions button,.actions .btn{padding:6px 8px;font-size:10px}.empty{text-align:center;color:var(--light);padding:35px}.small{font-size:11px;color:var(--light)}.inline{display:inline}.footer{text-align:center;color:var(--light);font-size:11px;padding:12px}@media(max-width:950px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.header{padding:14px}.wrap{padding:0 12px 30px;margin:22px auto}.card{padding:15px}.grid{grid-template-columns:1fr}.head{align-items:flex-start;flex-direction:column}}
'''

DASH = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Link Manager</title><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"><style>'''+STYLE+'''</style></head><body><header class="header"><div class="head"><div class="brand"><div class="logo">↗</div>Link Manager</div><div class="muted-head">Personal URL shortener</div></div></header><main class="wrap"><div class="eyebrow">Workspace</div><h1>Manage your short links</h1><p class="sub">Create, organise, protect and analyse your personal short links.</p>{% if message %}<div class="msg">{{ message }}</div>{% endif %}
<div class="stats"><div class="stat"><b>{{ stats.total }}</b><span>TOTAL LINKS</span></div><div class="stat"><b>{{ stats.active }}</b><span>ACTIVE LINKS</span></div><div class="stat"><b>{{ stats.archived }}</b><span>ARCHIVED</span></div><div class="stat"><b>{{ stats.clicks }}</b><span>ALL TIME CLICKS</span></div></div>
<section class="card"><h2>{{ 'Edit short link' if editing else 'Create a short link' }}</h2><form method="post" action="{{ '/admin/edit/'+editing.code if editing else '/admin/add' }}"><div class="grid"><div class="field"><label>Custom code</label><input name="code" required pattern="[A-Za-z0-9_-]{1,64}" value="{{ editing.code if editing else '' }}" {{ 'readonly' if editing else '' }} placeholder="e.g. github"></div><div class="field"><label>Destination URL</label><input name="url" type="url" required value="{{ editing.url if editing else '' }}" placeholder="https://example.com"></div><div class="field"><label>Link behaviour</label><select name="mode"><option value="redirect" {{ 'selected' if editing and editing.mode=='redirect' else '' }}>Normal redirect</option><option value="embed" {{ 'selected' if editing and editing.mode=='embed' else '' }}>Embedded mode</option></select></div><div class="field"><label>Category</label><input name="category" value="{{ editing.category if editing else '' }}" placeholder="Work, Personal"></div><div class="field"><label>Tags (comma separated)</label><input name="tags" value="{{ editing.tags if editing else '' }}" placeholder="portfolio, docs"></div><div class="field"><label>Expires at (UTC, optional)</label><input name="expires_at" type="datetime-local" value="{{ editing.expires_at if editing else '' }}"></div><div class="field"><label>Link password (optional)</label><input name="password" type="password" placeholder="Leave blank to keep current"></div><button type="submit">{{ 'Save changes' if editing else 'Create link' }}</button></div><p class="small">Leave password blank when editing to keep the current password. Short codes cannot be changed.</p></form></section>
<section class="card"><h2>Find and manage links</h2><form method="get" action="/admin" class="toolbar"><div class="field"><label>Search</label><input name="q" value="{{ q }}" placeholder="Code, URL, category or tag"></div><div class="field"><label>Mode</label><select name="mode"><option value="">All modes</option><option value="redirect" {{ 'selected' if mode=='redirect' else '' }}>Redirect</option><option value="embed" {{ 'selected' if mode=='embed' else '' }}>Embedded</option></select></div><div class="field"><label>Category</label><select name="category"><option value="">All categories</option>{% for c in categories %}<option value="{{ c }}" {{ 'selected' if category==c else '' }}>{{ c }}</option>{% endfor %}</select></div><div class="field"><label>Status</label><select name="status"><option value="active" {{ 'selected' if status=='active' else '' }}>Active</option><option value="archived" {{ 'selected' if status=='archived' else '' }}>Archived</option><option value="all" {{ 'selected' if status=='all' else '' }}>All</option></select></div><button>Filter</button><a class="btn btn-light" href="/admin">Reset</a></form><div class="actions" style="margin-bottom:14px"><a class="btn btn-light" href="/admin/export">Export CSV</a><a class="btn btn-light" href="/admin/import">Import CSV</a><a class="btn btn-light" href="/admin/analytics">Click analytics</a></div>
{% if links %}<div class="table-wrap"><table><thead><tr><th>Short link</th><th>Destination</th><th>Mode</th><th>Category / tags</th><th>Clicks</th><th>Expiry</th><th>Actions</th></tr></thead><tbody>{% for code,item in links %}<tr><td><a class="short" href="{{ short_url(code) }}" target="_blank">/{{ code }}</a><div class="small">{{ 'Archived' if item.archived=='1' else 'Active' }}</div></td><td>{{ item.url }}</td><td><span class="pill">{{ 'Embedded' if item.mode=='embed' else 'Redirect' }}</span>{% if item.password_hash %} <span class="pill">Password</span>{% endif %}</td><td>{{ item.category or '—' }}<div class="small">{{ item.tags }}</div></td><td>{{ counts.get(code,0) }}</td><td>{{ item.expires_at or 'Never' }}</td><td><div class="actions"><button type="button" class="copy" data-url="{{ short_url(code) }}">Copy</button><a class="btn btn-light" href="/admin/qr/{{ code }}">QR</a><a class="btn btn-light" href="/admin/analytics/{{ code }}">Stats</a><a class="btn btn-light" href="/admin/edit/{{ code }}">Edit</a><form class="inline" method="post" action="/admin/archive/{{ code }}"><button class="btn btn-light">{{ 'Restore' if item.archived=='1' else 'Archive' }}</button></form><form class="inline" method="post" action="/admin/delete/{{ code }}" onsubmit="return confirm('Permanently delete this link?')"><button class="btn btn-danger">Delete</button></form></div></td></tr>{% endfor %}</tbody></table></div>{% else %}<div class="empty">No links match these filters.</div>{% endif %}</section><div class="footer">Private link management · Public short links · CSV backed storage</div></main><script>document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{try{await navigator.clipboard.writeText(b.dataset.url);b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1300)}catch(e){prompt('Copy link',b.dataset.url)}})</script></body></html>'''

EMBED='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ code }}</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden}iframe{width:100%;height:100%;border:0;display:block}</style></head><body><iframe src="{{ destination }}" title="Destination website" allow="fullscreen; autoplay"></iframe></body></html>'''
PASS='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Protected link</title><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet"><style>'''+STYLE+'''</style></head><body><main class="wrap" style="max-width:460px;margin:12vh auto"><section class="card"><h1>Protected link</h1><p class="sub">Enter the password to continue.</p>{% if error %}<div class="msg">{{ error }}</div>{% endif %}<form method="post"><div class="field"><label>Password</label><input type="password" name="password" required autofocus></div><p><button>Continue</button></p></form></section></main></body></html>'''

@app.get('/')
def home(): return 'Personal URL shortener is running.'

@app.get('/admin')
@require_admin
def admin():
    data=load_links(); events=load_clicks(); counts={}
    for e in events: counts[e['code']]=counts.get(e['code'],0)+1
    q=request.args.get('q','').lower().strip(); mode=request.args.get('mode',''); category=request.args.get('category',''); status=request.args.get('status','active')
    cats=sorted({x['category'] for x in data.values() if x['category']}); shown=[]
    for code,item in data.items():
        if status=='active' and item['archived']=='1': continue
        if status=='archived' and item['archived']!='1': continue
        if mode and item['mode']!=mode: continue
        if category and item['category']!=category: continue
        if q and q not in ' '.join([code,item['url'],item['category'],item['tags']]).lower(): continue
        shown.append((code,item))
    shown.sort(key=lambda x:x[0].lower())
    stats={'total':len(data),'active':sum(x['archived']!='1' and not expired(x) for x in data.values()),'archived':sum(x['archived']=='1' for x in data.values()),'clicks':len(events)}
    return render_template_string(DASH,links=shown,stats=stats,counts=counts,q=q,mode=mode,category=category,status=status,categories=cats,message=request.args.get('message',''),editing=None,short_url=short_url)

@app.post('/admin/add')
@require_admin
def add_link():
    code=request.form.get('code','').strip(); dest=request.form.get('url','').strip(); mode=request.form.get('mode','redirect'); expiry=request.form.get('expires_at','').strip(); pwd=request.form.get('password','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',code) or code.lower() in {'admin','favicon.ico','robots.txt'}: abort(400,'Invalid or reserved short code.')
    if not valid_url(dest) or mode not in ('redirect','embed'): abort(400,'Invalid destination or mode.')
    if expiry:
        try: datetime.fromisoformat(expiry)
        except ValueError: abort(400,'Invalid expiry date.')
    with LOCK:
        links=load_links()
        if code in links: return redirect('/admin?message=Short+code+already+exists.')
        links[code]={'code':code,'url':dest,'mode':mode,'category':request.form.get('category','').strip()[:80],'tags':request.form.get('tags','').strip()[:300],'expires_at':expiry,'password_hash':generate_password_hash(pwd) if pwd else '','archived':'0','created_at':now_iso()}; save_links(links)
    return redirect('/admin?message=Link+created.')

@app.get('/admin/edit/<code>')
@require_admin
def edit_link(code):
    links=load_links(); item=links.get(code)
    if not item: abort(404)
    events=load_clicks(); counts={}
    for e in events: counts[e['code']]=counts.get(e['code'],0)+1
    stats={'total':len(links),'active':sum(x['archived']!='1' and not expired(x) for x in links.values()),'archived':sum(x['archived']=='1' for x in links.values()),'clicks':len(events)}
    return render_template_string(DASH,links=sorted(links.items()),stats=stats,counts=counts,q='',mode='',category='',status='all',categories=sorted({x['category'] for x in links.values() if x['category']}),message='',editing=item,short_url=short_url)

@app.post('/admin/edit/<code>')
@require_admin
def save_edit(code):
    with LOCK:
        links=load_links(); item=links.get(code)
        if not item: abort(404)
        dest=request.form.get('url','').strip(); mode=request.form.get('mode','redirect'); expiry=request.form.get('expires_at','').strip()
        if not valid_url(dest) or mode not in ('redirect','embed'): abort(400,'Invalid destination or mode.')
        if expiry:
            try: datetime.fromisoformat(expiry)
            except ValueError: abort(400,'Invalid expiry date.')
        item.update(url=dest,mode=mode,category=request.form.get('category','').strip()[:80],tags=request.form.get('tags','').strip()[:300],expires_at=expiry)
        pwd=request.form.get('password','')
        if pwd: item['password_hash']=generate_password_hash(pwd)
        save_links(links)
    return redirect('/admin?message=Changes+saved.')

@app.post('/admin/delete/<code>')
@require_admin
def delete_link(code):
    with LOCK:
        links=load_links(); links.pop(code,None); save_links(links)
    return redirect('/admin?message=Link+deleted.')

@app.post('/admin/archive/<code>')
@require_admin
def archive_link(code):
    with LOCK:
        links=load_links()
        if code not in links: abort(404)
        links[code]['archived']='0' if links[code]['archived']=='1' else '1'; save_links(links)
    return redirect('/admin?message=Link+status+updated.')

@app.get('/admin/export')
@require_admin
def export_csv():
    rows=read_object(LINKS_BLOB_PATH,LINK_FIELDS); out=io.StringIO(newline=''); w=csv.DictWriter(out,fieldnames=LINK_FIELDS); w.writeheader(); w.writerows(rows)
    return Response('\ufeff'+out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=short-links-export.csv'})

@app.route('/admin/import',methods=['GET','POST'])
@require_admin
def import_csv():
    if request.method=='GET':
        return '''<!doctype html><html><head><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet"><style>'''+STYLE+'''</style></head><body><main class="wrap"><section class="card"><h1>Import CSV</h1><p class="sub">Required columns: code,url. Optional: mode,category,tags,expires_at,password,archived.</p><form method="post" enctype="multipart/form-data"><input type="file" name="file" accept=".csv,text/csv" required><p><button>Import links</button> <a class="btn btn-light" href="/admin">Back</a></p></form></section></main></body></html>'''
    f=request.files.get('file')
    if not f: abort(400,'Choose a CSV file.')
    try: rows=list(csv.DictReader(io.StringIO(f.stream.read().decode('utf-8-sig'))))
    except Exception: abort(400,'Could not read CSV.')
    count=0
    with LOCK:
        links=load_links()
        for row in rows:
            code=(row.get('code') or '').strip(); dest=(row.get('url') or '').strip()
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',code) or code.lower() in {'admin','favicon.ico'} or not valid_url(dest): continue
            old=links.get(code,{}); mode=row.get('mode') or 'redirect'; mode=mode if mode in ('redirect','embed') else 'redirect'; pwd=row.get('password') or ''
            links[code]={'code':code,'url':dest,'mode':mode,'category':(row.get('category') or '')[:80],'tags':(row.get('tags') or '')[:300],'expires_at':row.get('expires_at') or '','password_hash':generate_password_hash(pwd) if pwd else (row.get('password_hash') or old.get('password_hash','')),'archived':'1' if (row.get('archived') or '0').lower() in ('1','true','yes') else '0','created_at':old.get('created_at') or now_iso()}; count+=1
        save_links(links)
    return redirect(f'/admin?message=Imported+or+updated+{count}+links.')

@app.get('/admin/analytics')
@require_admin
def analytics():
    events=load_clicks(); links=load_links(); counts={}
    for e in events: counts[e['code']]=counts.get(e['code'],0)+1
    rows=''.join(f'<tr><td>/{c}</td><td>{i["url"]}</td><td>{counts.get(c,0)}</td></tr>' for c,i in sorted(links.items(),key=lambda x:counts.get(x[0],0),reverse=True))
    return render_template_string('''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet"><style>'''+STYLE+'''</style></head><body><header class="header"><div class="head"><div class="brand">Link Manager · Analytics</div><a class="btn btn-light" href="/admin">Dashboard</a></div></header><main class="wrap"><section class="card"><h1>Click analytics</h1><p class="sub">{{ total }} total click events recorded.</p><div class="table-wrap"><table><thead><tr><th>Short code</th><th>Destination</th><th>Clicks</th></tr></thead><tbody>'''+rows+'''</tbody></table></div></section></main></body></html>''',total=len(events))

@app.get('/admin/analytics/<code>')
@require_admin
def link_analytics(code):
    if code not in load_links(): abort(404)
    events=[e for e in load_clicks() if e['code']==code][-100:][::-1]
    rows=''.join(f'<tr><td>{e["clicked_at"]}</td><td>{e["referrer"]}</td><td>{e["user_agent"]}</td></tr>' for e in events)
    return render_template_string('''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>'''+STYLE+'''</style></head><body><main class="wrap"><section class="card"><h1>Analytics: /{{ code }}</h1><p class="sub">Showing latest {{ count }} events.</p><table><thead><tr><th>UTC time</th><th>Referrer</th><th>Browser</th></tr></thead><tbody>'''+rows+'''</tbody></table><p><a class="btn btn-light" href="/admin">Dashboard</a></p></section></main></body></html>''',code=code,count=len(events))

@app.get('/admin/qr/<code>')
@require_admin
def qr_code(code):
    if code not in load_links(): abort(404)
    image=qrcode.make(short_url(code)); buf=io.BytesIO(); image.save(buf,format='PNG'); buf.seek(0)
    return send_file(buf,mimetype='image/png',download_name=f'{code}-qr.png')

@app.route('/<code>',methods=['GET','POST'])
def follow_link(code):
    item=load_links().get(code)
    if not item or item['archived']=='1' or expired(item): abort(404)
    if item.get('password_hash'):
        if request.method=='GET': return render_template_string(PASS,error='')
        if not check_password_hash(item['password_hash'],request.form.get('password','')): return render_template_string(PASS,error='Incorrect password.'),401
    with LOCK:
        events=load_clicks(); events.append({'code':code,'clicked_at':now_iso(),'user_agent':request.user_agent.string[:300],'referrer':(request.referrer or '')[:500]}); save_clicks(events)
    if item['mode']=='redirect': return redirect(item['url'],code=302)
    return render_template_string(EMBED,code=code,destination=item['url'])

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT','5000')))
