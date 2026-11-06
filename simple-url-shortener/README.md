# Simple URL Shortener

Standalone Flask URL shortener for Vercel. It retains private Vercel Blob storage, CSV persistence, per-link redirect and embedded modes, and the navy blue Link Manager design. No database is used.

## Included features

1. Edit an existing link's destination, mode, category, tags, expiration, and password. The short code itself remains fixed.
2. One-click copy of each short URL.
3. Search by code, destination, category, or tags. Filter by mode, category, and active or archived status.
4. Generate and download a PNG QR code for each short URL.
5. Store one category and comma-separated tags per link.
6. Track total clicks per link, all-time clicks, and recent event details including UTC timestamp, referrer, and browser user agent.
7. Import and export link records as CSV.
8. Set an optional expiration date and time. The dashboard explicitly labels this field UTC.
9. Protect an individual short link with a password. Passwords are stored as Werkzeug password hashes, never plaintext.
10. Archive and restore links. Archived and expired links return 404 to visitors.

Normal Redirect uses HTTP 302. Embedded Mode displays the destination in a full-viewport iframe, keeping the short URL in the address bar. Some destination websites block iframe embedding.

## Storage and compatibility

The app stores two private CSV objects in the existing Vercel Blob store:

- Existing link file: `url-shortener/links.csv` (the exact legacy path used by the earlier app, unless overridden by `BLOB_CSV_PATH`).
- Click log: `url-shortener/clicks.csv`, alongside the link file.

`BLOB_CSV_PATH` continues to identify the complete links CSV object path, not a directory. Its default is `url-shortener/links.csv`. If you previously set this variable to a custom path, keep that same value. The click log is written beside that file.

The app reads legacy rows with only `code,url` or `code,url,mode`. Missing modes default to `embed`, preserving the behaviour of existing links. Additional columns are added when the link file is next written. No migration or new Blob store is required.

## Deploy over your existing Vercel project

1. Back up your existing repository and, preferably, export your current links from the old dashboard before replacing files.
2. Replace the project files with the contents of this ZIP.
3. Keep the same GitHub repository, Vercel project, Blob connection, environment variables, and custom domain.
4. Ensure these existing Vercel environment variables remain configured:
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD`
   - `BLOB_READ_WRITE_TOKEN` (provided by the connected private Blob store when read/write token injection is enabled)
5. Push the changes to GitHub. Vercel should automatically redeploy.

No changes to DNS, domain settings, Blob store connection, or credentials are required.

## Local development on macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ADMIN_USERNAME=yourusername
export ADMIN_PASSWORD='use-a-long-unique-password'
python3 app.py
```

Local CSV files are written under `data/`. Open `http://localhost:5000/admin`.

## CSV import columns

Required columns: `code,url`.

Optional columns: `mode,category,tags,expires_at,password,archived`.

- `mode`: `redirect` or `embed`.
- `tags`: comma-separated text.
- `expires_at`: ISO datetime, preferably UTC, such as `2026-12-31T23:59`.
- `password`: optional plaintext input to import; the app hashes it before storage.
- `archived`: `1` or `0`.

CSV export contains the stored password hash column, not the original password. Treat exports as sensitive because they contain destinations and password hashes.

## Important operational limitations

- CSV overwrite operations are not transactional across separate Vercel Function instances. The in-process lock only coordinates requests within one instance. This remains suitable for personal, low-concurrency use, but avoid simultaneous edits/imports from multiple sessions.
- Each successful visit writes one click event. The click CSV retains the latest 25,000 events. This adds Blob operations and can increase storage usage.
- Embedded Mode depends on the destination allowing iframe embedding through its security policy. Use Normal Redirect for sites that block iframes.
- Password protection gates access to the short link; it does not make the destination website itself private after access is granted.
- Admin routes use HTTP Basic Authentication. Use a strong unique password and retain HTTPS.
