# DAMIT Anonymous Chord Pair Corpus

This repository documents and generates a benchmark for associating two simulated stellar-occultation chord profiles with one of eight anonymous asteroid shape models. The shapes are real published models from DAMIT. The chord profiles are **simulated** from those models; they are not historical occultation measurements.

`SOURCE_CATALOG_PUBLIC.json` lists all 294 selected source models, their direct DAMIT shape URLs, SHA-256 hashes, model-specific publication references and whether they were used during development. There are 119 development identities and 175 later acquired identities. The development identities are assigned only to training in the frozen benchmark. Every source model has a cited original publication. No personal data is present.

The official DAMIT site states that its content is [CC BY 4.0 except where otherwise stated](https://damit.cuni.cz/projects/damit/pages/about_damit), and asks users to cite each original model publication, the [DAMIT database paper](https://doi.org/10.1051/0004-6361/200912693), and DAMIT itself. The catalog provides model-specific reference links. This derived corpus and its documentation are CC BY 4.0; the original generator code in this repository is MIT. See `LICENSE_DATA.md` and `LICENSE_CODE.txt`.

The source provenance is reproducible: `python rebuild_sources.py` fetches the 294 files from DAMIT and verifies every SHA-256 digest. `generate_raw.py` generates case observations from those source files. It creates a random 32-byte creator secret in `.private/generation_secret.hex`; keep that file private. Reusing a retained secret reproduces the same raw records. Publishing that secret or the raw case file would expose challenge answers. The platform raw upload is frozen separately and is not published here.

The generation steps normalize each source vertex set to zero centroid and unit root-mean-square radius; randomly rotate it independently for two events; project its convex hull; measure widths at nine parallel station offsets; add a small hidden center shift and Gaussian timing-width noise; and clip negative reported widths to zero. The participant sees the two width arrays and eight candidate model IDs. The target is the candidate model that generated both events. This is an intentionally simplified simulator of chord geometry, not a model of orbital ephemerides, stellar diffraction, observer weather or detector cadence.

For research context, published occultation fitting typically starts with the asteroid identity and uses chords to [scale or distinguish known shape/spin models](https://arxiv.org/abs/1104.4227). Here the identity and both orientations are latent, and the required output is the correct model among unrelated source asteroids. The final benchmark consists of 194 training asteroids and 100 identity-disjoint evaluation asteroids.

## Files

- `SOURCE_CATALOG_PUBLIC.json`: the 294 original-model receipts and reference links; no case IDs, observations, generation secret or target slots.
- `rebuild_sources.py`: source downloader and hash verifier.
- `generate_raw.py`: observation and identifier generator adapted to run from this repository root; requires a creator-private secret for the frozen benchmark.
- `LICENSE_DATA.md`: source attribution and derived-data license.
- `LICENSE_CODE.txt`: MIT code license.

No frozen evaluation observations, labels, answers or private seed are included in this public repository.
