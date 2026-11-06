"""Upload an existing local data/links.csv file to your private Vercel Blob store.

Run after setting BLOB_READ_WRITE_TOKEN in your local terminal.
This uploads to the same pathname used by the deployed application.
"""
import os
from pathlib import Path
from vercel.blob import sync as blob

source = Path("data/links.csv")
if not source.exists():
    raise SystemExit("No data/links.csv found. Nothing to migrate.")

if not os.environ.get("BLOB_READ_WRITE_TOKEN"):
    raise SystemExit("Set BLOB_READ_WRITE_TOKEN before running this script.")

result = blob.put_blob(
    os.environ.get("BLOB_CSV_PATH", "url-shortener/links.csv"),
    source.read_bytes(),
    access="private",
    content_type="text/csv; charset=utf-8",
    allow_overwrite=True,
)
print(f"Uploaded {source} to private Vercel Blob: {result.pathname}")
