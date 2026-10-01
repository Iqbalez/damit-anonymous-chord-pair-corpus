"""Build frozen private raw records from attributed DAMIT shape downloads.

The creator stores a random secret outside the public source release. Keeping it
private prevents the public generator from reconstructing evaluation labels.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import secrets
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PRIVATE = ROOT / ".private"
Y_GRID = np.linspace(-1.55, 1.55, 125)
STATIONS = np.linspace(-.95, .95, 9)


def frozen_secret() -> bytes:
    PRIVATE.mkdir(exist_ok=True)
    path = PRIVATE / "generation_secret.hex"
    if not path.exists():
        path.write_text(secrets.token_hex(32) + "\n", encoding="ascii")
    value = bytes.fromhex(path.read_text(encoding="ascii").strip())
    if len(value) != 32:
        raise ValueError("Creator-private secret must be 32 bytes")
    return value


def derive(secret: bytes, purpose: str, number: int) -> bytes:
    return hmac.new(secret, f"{purpose}:{number}".encode("ascii"), hashlib.sha256).digest()


def load_vertices(path: Path, expected_count: int) -> np.ndarray:
    with path.open(encoding="ascii") as f:
        header = f.readline().split()
        if len(header) != 2 or int(header[0]) != expected_count:
            raise ValueError(f"Shape header mismatch: {path}")
        vertices = np.array([list(map(float, f.readline().split())) for _ in range(expected_count)])
    if vertices.shape != (expected_count, 3) or not np.isfinite(vertices).all():
        raise ValueError(f"Invalid vertices: {path}")
    vertices -= vertices.mean(axis=0)
    radius = math.sqrt(float(np.mean(np.sum(vertices * vertices, axis=1))))
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError(f"Degenerate vertices: {path}")
    return np.round(vertices / radius, 6)


def chord_profile(vertices: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    points = (vertices @ rotation.T)[:, :2]
    polygon = points[ConvexHull(points).vertices]
    following = np.roll(polygon, -1, axis=0)
    lo = np.minimum(polygon[:, 1], following[:, 1])
    hi = np.maximum(polygon[:, 1], following[:, 1])
    den = following[:, 1] - polygon[:, 1]
    y = Y_GRID[:, None]
    crossing = (lo[None, :] <= y) & (y < hi[None, :]) & (np.abs(den)[None, :] > 1e-12)
    safe_den = np.where(np.abs(den) > 1e-12, den, 1.0)
    x = polygon[None, :, 0] + (y - polygon[None, :, 1]) * (
        following[None, :, 0] - polygon[None, :, 0]
    ) / safe_den[None, :]
    xmax = np.max(np.where(crossing, x, -np.inf), axis=1)
    xmin = np.min(np.where(crossing, x, np.inf), axis=1)
    valid = np.sum(crossing, axis=1) >= 2
    return np.where(valid, np.where(valid, xmax, 0.0) - np.where(valid, xmin, 0.0), 0.0)


def observe(vertices: np.ndarray, rng: np.random.Generator) -> list[list[float]]:
    events = []
    for _ in range(2):
        rotation = Rotation.random(random_state=rng).as_matrix()
        profile = chord_profile(vertices, rotation)
        center_error = rng.uniform(-.14, .14)
        widths = np.interp(STATIONS + center_error, Y_GRID, profile)
        widths = np.maximum(0, widths + rng.normal(0, .025, len(widths)))
        events.append([round(float(x), 6) for x in widths])
    return events


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def main() -> None:
    secret = frozen_secret()
    catalog = json.loads((RAW / "SOURCE_CATALOG.json").read_text(encoding="utf-8"))
    if len(catalog) != 294:
        raise ValueError(f"Expected 294 source models; got {len(catalog)}")
    numbers = [r["asteroid_number"] for r in catalog]
    if len(set(numbers)) != len(numbers) or numbers != sorted(numbers):
        raise ValueError("Source asteroids must be unique and sorted")
    models, cases = [], []
    for receipt in catalog:
        number = receipt["asteroid_number"]
        path = RAW / receipt["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
            raise ValueError(f"Source SHA mismatch for {number}")
        vertices = load_vertices(path, receipt["vertices"])
        model_id = "m_" + derive(secret, "model-id", number).hex()[:18]
        case_id = "occ_" + derive(secret, "case-id", number).hex()[:18]
        nonce = derive(secret, "case-nonce", number).hex()
        rng = np.random.default_rng(int.from_bytes(derive(secret, "observation", number)[:8], "big"))
        events = observe(vertices, rng)
        models.append({"source_number": number, "source_model_id": receipt["model_id"],
                       "model_id": model_id, "vertices": vertices.tolist(),
                       "source_url": receipt["shape_url"],
                       "reference_urls": receipt["reference_urls"],
                       "source_sha256": receipt["sha256"],
                       "development_source": receipt["development_source"]})
        cases.append({"source_number": number, "case_id": case_id,
                      "nonce": nonce, "event_1_widths": events[0],
                      "event_2_widths": events[1]})
    if len({m["model_id"] for m in models}) != 294 or len({c["case_id"] for c in cases}) != 294:
        raise ValueError("Public identifier collision")
    write_jsonl(RAW / "models.jsonl", models)
    write_jsonl(RAW / "cases.jsonl", cases)
    (RAW / "DATA_LICENSE.txt").write_text(
        "DAMIT source shape models: Creative Commons Attribution 4.0 International (CC BY 4.0), "
        "except where otherwise stated by the source. Original model authors are cited for every "
        "selected record in models.jsonl. Source: https://damit.cuni.cz/projects/damit/ . "
        "Database paper: Durech et al. (2010), DAMIT: a database of asteroid models, "
        "https://doi.org/10.1051/0004-6361/200912693 .\n"
        "Original generated occultation observations and dataset documentation: CC BY 4.0. "
        "The observations are simulated, not historical field measurements.\n"
        "Generator source code: MIT license in the public source release.\n",
        encoding="utf-8",
    )
    print(f"generated {len(models)} models and {len(cases)} independent cases")


if __name__ == "__main__":
    main()
