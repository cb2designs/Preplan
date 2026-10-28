# Preplan

A local first development build of the emergency pre-plan graphics application.

## Run

```sh
python3 server.py
```

Open http://127.0.0.1:8765. Create an account; the first account becomes the platform administrator. Subsequent accounts are ordinary members. Use a password of at least 10 characters. No default credentials are shipped.

## Working features

- Accounts with PBKDF2-SHA256 password hashes (600,000 iterations), opaque HttpOnly/SameSite sessions, and backend suspension checks.
- SQLite projects and private PNG/JPEG files. Every project and asset lookup checks the signed-in owner. Platform admins manage account status but cannot read others' plans.
- Example plan, image upload, FDC/FACP and a compact original abbreviation-based symbol library; placement, dragging, relabeling, deletion, text labels, undo/redo, zoom, and pan.
- Two-point scale calibration; distance and polygon area tools; feet and meters. Double-click to finish a polygon. Measurements derive from source-image coordinates. Replacing a base clears calibration and annotations.
- Explicit database save/reopen and PNG/PDF downloads with title and used-symbol legend.

## Architecture and persistence

`server.py` serves the browser application and JSON API. `static/app.js` owns the editable canvas state and export renderer. `data/preplan.db` stores users, departments, sessions, projects, and asset ownership. Binary images live in `data/assets/`, accessible only through authenticated owner-scoped endpoints. Back up the entire data directory together while the server is stopped. Set `PREPLAN_DATA` to relocate it. Browser storage is not used for persistence.

Editable project state contains source image dimensions, private asset identifier, scale (units per source pixel), units, and symbols/text/measurement geometry. Exports are derived artifacts. Department IDs and subscription status are separate from user role/status; development subscriptions have no paid entitlement enforcement. Each registration currently creates its own department. Department invitations and shared plans are not implemented.

## Development boundaries

This build binds to loopback and is not deployed. Before internet exposure: select production hosting/storage/authentication, enforce HTTPS with Secure cookies, add login throttling and recovery/email verification, invitations, migrations, operational backups, observability, and deeper request/schema validation. Initial local bootstrap admin policy is for development only. No email sending or billing is implemented.

Satellite imagery remains required for the completed product; provider pricing, attribution and export rights need selection. PDF base import is not supported. Custom symbols make no standards-compliance claim. Annual 2/4/6-seat subscriptions are planned; seat enforcement and payment processing are not active. Uploaded images must have uniform scale; distorted scans cannot be corrected by two-point calibration. No autosave yet; use Save project.

## Validation

Run `python3 -m unittest discover -s tests -v`. Tests cover authentication, ownership, saved-state integrity, private assets, administrator boundaries, suspension, and cross-origin rejection. Measurement math should match controlled source coordinates within 0.01 unit before display rounding; symbol placement and PDF download were checked in the local browser. Run `node tests/measurements.cjs` for controlled geometry and unit-conversion checks. Visual inspection of downloaded exports and testing with real property drawings remain necessary. Test real exports in Emergency Networking before operational use. Its accepted formats and limits have not been verified.


## NFPA 170 — 2024 SVG library

The library contains all 17 symbols from the user's screenshots of Table 5.2, pages 170-15 through 170-17. `static/symbols/` contains standalone SVG assets, `catalog.json` with application descriptions and characteristics, and a review sheet. The SVGs use traced vector paths, not embedded bitmap images. Colors follow the Characteristics column rather than the monochrome screenshot rendering. Digital colors are approximations and are not certified safety-color specifications.

`python scripts/build_symbols.py --source-dir /path/to/screenshots` regenerates the SVGs and the inline catalog in `static/app.js` using Pillow and the original screenshots in the directory provided with `--source-dir`. Source screenshots are not copied into public assets. Inspect generated files before distributing the app. The build script must run with the bundled Python runtime (system Python may lack Pillow).

The same SVG data powers library thumbnails, canvas markers, inspector previews, on-screen legends, PNG exports, and PDF exports. Both export actions await successful SVG decoding. Export legends grow to fit the number of used symbols. The two arrow symbols support red, blue, or green backgrounds to match an accompanying sign; their selected backgrounds persist in project items. Arrows retain the orientations shown in the supplied table. SCBA preserves a rectangular field; the prohibition symbol has a circular field.

Existing stable symbol codes retain their positions, labels, and project compatibility. HYD, GAS, ELEC and the four specific FDC codes now render the supplied pictograms. Generic FDC, FACP, riser, tank, key box, and entrance remain supplemental abbreviation markers because they were not supplied as rows in these screenshots. There is no certification or endorsement claim.

Review: http://127.0.0.1:8765/symbols/review.html

Validation: `node tests/symbols.cjs` verifies the 17 assets, inline/file parity, vector-only SVG content, source pages, characteristics and legacy-code availability. `node tests/measurements.cjs` checks existing geometry calculations. Browser review checks symbol appearance and editor loading.
