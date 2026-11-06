# Simple URL Shortener: Vercel + Private Blob + CSV

This is the Vercel-ready version of the Flask URL shortener.

- Flask handles the dashboard and public redirects.
- A **private Vercel Blob store** stores `url-shortener/links.csv`.
- The CSV contains only `code` and `url`.
- The admin dashboard uses HTTP Basic Authentication.
- Local development uses `data/links.csv` unless Blob credentials are configured.

## 1. Create a private Vercel Blob store

1. Create a Vercel project by importing this repository.
2. In the Vercel project, open **Storage**.
3. Choose **Create Storage**, then **Blob**.
4. Select **Private** access. Do not choose Public.
5. Create the store.
6. Connect the store to this Vercel project for Production and Preview. Also select Development if you want to use Blob locally.
7. Vercel will provide the Blob environment variables. When connected to the project, the Python SDK can use Vercel OIDC credentials automatically. A `BLOB_READ_WRITE_TOKEN` is also supported.

Private storage matters: the CSV must not be accessible through a public Blob URL. Short links expose only their destination through your Flask redirect route.

## 2. Configure project environment variables

In Vercel, open **Project Settings → Environment Variables** and add:

- `ADMIN_USERNAME`: your chosen admin username
- `ADMIN_PASSWORD`: a long, unique password

The Blob connection supplies its own credentials. Do not paste credentials into source code or commit them to GitHub.

Optional:
- `BLOB_CSV_PATH`: defaults to `url-shortener/links.csv`

## 3. Deploy

Vercel detects the Flask app from the root `app.py` file.

1. Push this project to GitHub.
2. Import the repository at https://vercel.com/new.
3. Deploy. No custom build command is required.
4. Open `/admin` on the deployed domain and enter your admin credentials.

For Vercel's current Flask deployment instructions, see:
https://vercel.com/kb/guide/ship-a-flask-app-on-vercel

## 4. Local development on macOS

The app still works locally with a CSV file, so you do not need a Blob token just to test the interface:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ADMIN_USERNAME=pushkar
export ADMIN_PASSWORD='use-a-long-unique-password'

python3 app.py
```

Open http://localhost:5000/admin.

The local CSV is stored at `data/links.csv`. It is ignored by Git.

If you want local development to use the private Blob store instead, connect the project with the Vercel CLI and pull the development environment variables:

```bash
npm install -g vercel
vercel login
vercel link
vercel env pull .env.local
```

Then load `.env.local` into your shell before running `python3 app.py`, or export the required Blob credentials in your terminal. Never commit `.env.local`.

## 5. Migrate existing local links

If you created links in your old local `data/links.csv`, upload them before relying on the deployed app.

1. Obtain a Blob read-write token from your Vercel Blob store settings.
2. In your local terminal, activate the virtual environment and set:

```bash
export BLOB_READ_WRITE_TOKEN='paste-your-token-here'
```

3. Run:

```bash
python3 migrate_csv_to_blob.py
```

The script uploads `data/links.csv` to the private Blob path used by the app. Do not share the token or commit it to GitHub.

## 6. Connect your custom domain

In Vercel, open **Project → Settings → Domains**, add your domain or subdomain, and follow the exact DNS records Vercel displays. After DNS verification, Vercel provisions HTTPS.

A subdomain such as `go.example.com` is a good choice if your main domain hosts another website.

## Important limitations

This is designed for personal, low-volume use and infrequent link edits. Vercel Functions are stateless and can run on multiple instances. The process-local lock prevents overlapping writes only within one instance. Two simultaneous admin writes on separate instances could overwrite one another because a single CSV file does not provide database-style transactions or distributed locking.

For your personal use, avoid editing links simultaneously from multiple browser sessions. Keep periodic backups of the CSV. Public visitors can follow links, but cannot read the private CSV directly.


## Embedded mode

Every short link renders its destination inside an iframe. The browser address bar remains on the short URL, for example `https://go.example.com/github`.

Some destination websites deliberately block iframe embedding using `X-Frame-Options` or Content-Security-Policy `frame-ancestors`. Those sites cannot be embedded by this app; the page provides an "Open destination in a new tab" fallback. Embedded pages may also have limitations with authentication, cookies, payments, and browser permissions. This mode does not proxy or copy the destination website.


The embedded page fills the viewport without an application toolbar or banner.
