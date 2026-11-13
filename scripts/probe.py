#!/usr/bin/env python3
"""Read-only connectivity probe. Never prints or publishes source CSV content."""
import csv, hashlib, io, json, socket, ssl, urllib.error, urllib.request, urllib.parse
from datetime import datetime, timezone

BASE = "https://stats.tennismylife.org"
URLS = [
    BASE + "/api/data-files",
    BASE + "/data/2025.csv",
    BASE + "/data/2026.csv",
    BASE + "/data/ongoing_tourneys.csv",
]
def probe(url):
    result = {"url": url, "utc": datetime.now(timezone.utc).isoformat()}
    try:
        host = urllib.parse.urlparse(url).hostname
        result["dns"] = sorted({entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    except Exception as exc:
        result["dns_error"] = "%s: %s" % (type(exc).__name__, str(exc)[:240])
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "TennisPredictionEngine-Diagnostic/1.0",
            "Accept": "text/csv, application/json, */*",
        })
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as resp:
            payload = resp.read(5_000_001)
            result["http_status"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            if len(payload) > 5_000_000:
                result["error"] = "response_exceeds_5MB_limit"
                return result
            result["bytes"] = len(payload)
            result["sha256"] = hashlib.sha256(payload).hexdigest()
            if url.endswith(".csv"):
                try:
                    decoded = payload.decode("utf-8-sig")
                    rows = list(csv.reader(io.StringIO(decoded)))
                    result["header_columns"] = len(rows[0]) if rows else 0
                    result["data_rows"] = max(0, len(rows) - 1)
                    result["consistent_columns"] = bool(rows) and all(len(r) == len(rows[0]) for r in rows)
                    result["csv_valid"] = bool(rows and len(rows[0]) > 1 and result["consistent_columns"])
                except Exception as exc:
                    result["csv_parse_error"] = "%s: %s" % (type(exc).__name__, str(exc)[:240])
            else:
                try:
                    obj = json.loads(payload)
                    result["json_valid"] = True
                    result["json_kind"] = type(obj).__name__
                except (ValueError, UnicodeError):
                    result["json_valid"] = False
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["error"] = "%s: %s" % (type(exc).__name__, str(exc.reason)[:240])
    except Exception as exc:
        result["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:240])
    return result

if __name__ == "__main__":
    for u in URLS:
        print(json.dumps(probe(u), ensure_ascii=False, sort_keys=True), flush=True)
