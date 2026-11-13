#!/usr/bin/env python3
"""Versioned TennisMyLife CSV snapshots. Original bytes preserved; no model operations."""
import csv
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = "https://stats.tennismylife.org/data/"
FILES = ("2025.csv", "2026.csv", "ongoing_tourneys.csv")
MAX_BYTES = 5_000_000

def fetch(name):
    url = ROOT + name
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TennisPredictionEngine-ResearchArchive/1.0",
                "Accept": "text/csv",
            })
            with urllib.request.urlopen(req, timeout=35) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                data = response.read(MAX_BYTES + 1)
            if status != 200:
                raise RuntimeError("HTTP %s" % status)
            if len(data) > MAX_BYTES:
                raise RuntimeError("CSV exceeds 5MB cap")
            if not data:
                raise RuntimeError("empty CSV")
            parsed = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
            if len(parsed) < 2 or len(parsed[0]) != 50:
                raise RuntimeError("schema mismatch, expected 50 columns")
            if any(len(row) != 50 for row in parsed):
                raise RuntimeError("inconsistent CSV columns")
            if len(set(map(tuple, parsed[1:]))) != len(parsed) - 1:
                raise RuntimeError("duplicate data rows")
            return data, {
                "url": url, "http_status": status, "content_type": content_type,
                "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                "columns": len(parsed[0]), "rows": len(parsed) - 1,
                "duplicate_rows": 0, "schema_valid": True,
            }
        except Exception as exc:
            last_error = "%s: %s" % (type(exc).__name__, str(exc)[:350])
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(last_error)

def artifact_exists(name, sha):
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        return False  # Local execution is an independent, new snapshot.
    artifact_name = "tml-%s-%s" % (name.removesuffix(".csv"), sha)
    url = "https://api.github.com/repos/%s/actions/artifacts?%s" % (
        repository, urllib.parse.urlencode({"name": artifact_name, "per_page": 100}))
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=25) as resp:
        listing = json.load(resp)
    return any(
        x.get("name") == artifact_name and not x.get("expired", False)
        for x in listing.get("artifacts", [])
    )

def main():
    observed = datetime.now(timezone.utc).isoformat()
    Path("run_manifest").mkdir(exist_ok=True)
    manifest = {"observed_at_utc": observed, "source": ROOT, "files": {}}
    failure = False
    outputs = []
    for name in FILES:
        stem = name.removesuffix(".csv")
        key = stem.replace("-", "_")
        try:
            payload, detail = fetch(name)
            exists = artifact_exists(name, detail["sha256"])
            detail["status"] = "NO_CHANGE" if exists else "CHANGED"
            if not exists:
                output_folder = Path("snapshots") / stem
                output_folder.mkdir(parents=True, exist_ok=True)
                filename = "%s_%s_%s.csv" % (
                    stem, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                    detail["sha256"][:16])
                (output_folder / filename).write_bytes(payload)
                detail["snapshot_file"] = str(output_folder / filename)
            outputs.append("upload_%s=%s" % (key, str(not exists).lower()))
            outputs.append("hash_%s=%s" % (key, detail["sha256"]))
            manifest["files"][name] = detail
            print("%s: %s rows=%d bytes=%d sha256=%s" % (
                name, detail["status"], detail["rows"], detail["bytes"],
                detail["sha256"]), flush=True)
        except Exception as exc:
            failure = True
            manifest["files"][name] = {"status": "FAILED_FETCH_OR_VERIFY", "error": str(exc)}
            outputs.append("upload_%s=false" % key)
            print("::error::%s failed: %s" % (name, exc), flush=True)
    content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    Path("run_manifest/manifest.json").write_text(content, encoding="utf-8")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a", encoding="utf-8") as f:
        f.write("### TennisMyLife raw CSV snapshot\n\n")
        for name, info in manifest["files"].items():
            f.write("- %s: %s | SHA: %s | rows: %s\n" % (
                name, info["status"], info.get("sha256", "unknown"), info.get("rows", "unknown")))
        f.write("\nNo model changes; only verified raw source snapshots.\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write("\n".join(outputs) + "\n")
    if failure:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
