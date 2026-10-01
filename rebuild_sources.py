"""Reacquire the attributed original shapes named by the public catalog."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
MODELS = RAW / "models"


def download(url: str) -> bytes:
    error = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Eris-source-rebuild/1"})
            with urllib.request.urlopen(req, timeout=45) as response:
                if response.status != 200:
                    raise IOError(f"HTTP {response.status}")
                return response.read()
        except OSError as exc:
            error = exc
            time.sleep(min(2 ** attempt, 12))
    raise IOError(f"Could not download {url}") from error


def main() -> None:
    catalog = json.loads((ROOT / "SOURCE_CATALOG_PUBLIC.json").read_text(encoding="utf-8"))
    if len(catalog) != 294:
        raise ValueError("Expected 294 catalog entries")
    MODELS.mkdir(parents=True, exist_ok=True)
    for index, record in enumerate(catalog, 1):
        path = RAW / record["file"]
        if not path.exists():
            path.write_bytes(download(record["shape_url"]))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record["sha256"]:
            raise ValueError(f"Hash mismatch for {record['shape_url']}")
        if index % 25 == 0:
            print(f"verified {index}/{len(catalog)}", flush=True)
    (RAW / "SOURCE_CATALOG.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print("Source corpus verified")


if __name__ == "__main__":
    main()
