"""Service modules (use-case orchestration): auth.py (authorization),
organizations.py, users.py, licenses.py, dashboard.py, activation.py,
devices.py, issuance.py, signing_keys.py. No seats.py, no renewal.py --
an organization license entitles every active member directly (no seat
limit or seat-assignment step) and is a lifetime grant issued once at
activation (no renewal flow). See README.md's Phase D notes and
docs/threat-model.md.
"""
