# Personal URL Shortener

A standalone Flask URL shortener for Vercel. This version retains the existing private Vercel Blob storage path and CSV based persistence. The admin interface uses the navy and white Link Manager design.

## Features

### Security and reliability
1. Admin login uses a signed session with a configurable inactivity timeout.
2. Optional authenticator based two factor authentication using TOTP.
3. Login attempt throttling, with a limit of eight failed attempts per IP in a rolling fifteen minute window per running function instance.
4. Password protected short links store password hashes.
5. Private CSV backup download containing both links and click history.
6. Health check at `/health`.
7. CSV imports validate URLs and short codes, enforce a 2 MB upload limit, and write through a temporary local file when running locally.
8. Error logging is sent to the Vercel function logs.

### Analytics
1. Total clicks and daily unique visitor estimates.
2. Seven day click trend.
3. Device, browser, operating system, country, and referrer host breakdowns.
4. Per link click history with IST timestamps.
5. Visitor identifiers are daily salted hashes. Raw visitor IP addresses are not stored.
6. Country, region, and city values use Vercel request headers when available. City and region are stored in the event schema for future reporting.

### Link management and routing
1. Create, edit, archive, restore, clone, and bulk manage links.
2. Search by code, URL, category, tags, and notes.
3. Custom QR code downloads.
4. Categories, tags, private notes, and favourites.
5. CSV import and export.
6. Optional password protection.
7. Scheduled activation and expiration dates interpreted in India Standard Time.
8. Normal HTTP 302 redirect or full viewport embedded mode.
9. Device based destination routing for mobile and desktop visitors.
10. Country based routing using a JSON map of two letter country codes to destination URLs.
11. A/B destinations, one per line, assigned consistently using a daily visitor hash.

## Existing data compatibility

The application continues to use the existing links object:
`url-shortener/links.csv`

The click log is stored beside it:
`url-shortener/clicks.csv`

`BLOB_CSV_PATH` continues to identify the complete links CSV object path. Keep its current value if you previously configured a custom path. Existing rows with only `code,url` or `code,url,mode` remain readable. Missing legacy modes default to embedded mode to preserve existing behaviour. New links default to normal redirect mode.

The new CSV columns are appended when links are next saved. No new Blob store or DNS change is required.

## Vercel environment variables

Keep the existing variables:
* `ADMIN_USERNAME`
* `ADMIN_PASSWORD`
* `BLOB_READ_WRITE_TOKEN`
* `BLOB_CSV_PATH`, only if you previously set a custom path

Recommended additions:
* `FLASK_SECRET_KEY`: a long random secret used to sign admin sessions. Set this to a stable value in Vercel.
* `ANALYTICS_HASH_SECRET`: a separate long random secret used to derive daily visitor identifiers.
* `SESSION_TIMEOUT_MINUTES`: inactivity timeout in minutes. Defaults to 30.
* `ADMIN_TOTP_SECRET`: optional Base32 TOTP secret from an authenticator application. When configured, a six digit authenticator code is required at login.

If `ADMIN_TOTP_SECRET` is configured, `pyotp` is installed by requirements. Generate and retain the TOTP secret securely. Losing it can lock you out until the environment variable is changed.

Do not change or disconnect the existing private Blob store.

## Deploy on the existing Vercel project

1. Download and extract this ZIP.
2. Back up the GitHub repository and download a data backup from `/admin/backup` before replacing the application.
3. Replace the repository files with the extracted project files.
4. Add the recommended environment variables in Vercel Project Settings, Environment Variables. Keep the existing Blob token and admin credentials.
5. Commit and push to the same GitHub repository.
6. Wait for the Vercel deployment to complete, then open `/login` on your custom domain.

No DNS or domain changes are required.

## Local development on macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ADMIN_USERNAME=yourusername
export ADMIN_PASSWORD='use-a-long-unique-password'
export FLASK_SECRET_KEY='use-a-long-random-secret'
python3 app.py
```

Open `http://localhost:5000/login`. Local CSV files are stored in `data/`.

## CSV format

Required columns: `code,url`.

Optional columns include:
`mode,category,tags,expires_at,starts_at,password,password_hash,archived,favorite,created_at,notes,mobile_url,desktop_url,country_rules,ab_urls,fallback_url`.

The `expires_at` and `starts_at` values accept ISO date and time values. Naive values are interpreted as IST. Prefer values in `YYYY-MM-DDTHH:MM` format when entering them through the dashboard.

CSV exports include password hashes, not plaintext passwords. Treat exports and backups as sensitive.

## Important limitations

* Vercel serverless functions are ephemeral. Login rate limiting is in memory and therefore applies per running function instance, not globally across all instances. For stronger distributed rate limiting, use a shared rate limit store.
* CSV writes are not transactional across separate Vercel function instances. The in process lock coordinates requests only within one instance. This remains intended for personal, low concurrency use. For higher concurrency, migrate link and event records to a database.
* Click history retains the latest 25,000 events. Each click appends to the CSV and rewrites the click object, which can become expensive as traffic grows.
* Unique visitors are estimates based on a daily salted hash of the request IP. They are not cross day identities and can be affected by shared networks, proxies, and changing IP addresses.
* Country analytics depend on Vercel geo headers. Region and city fields may remain blank when the hosting platform does not provide those headers.
* A/B allocation is stable for a visitor on a given day, not a permanent cross day assignment.
* Country rules and device destinations apply to redirect and embedded links. A/B routing takes precedence over device routing, and country routing takes precedence over A/B routing.
* The fallback URL field is retained in the CSV schema for compatibility and future use. It does not currently perform active destination health checks or automatic failover.
* Embedded mode requires the destination website to permit iframe embedding. Some sites block it through CSP or X-Frame-Options.
* Password protection gates access to the short link. It does not make the destination website private after access is granted.
* Admin sessions require a stable `FLASK_SECRET_KEY` across deployments and function instances. Set it in Vercel before production use.
