Abdul Basit - BSCS23023

# StudySync Assignment 4

Repository name required by the assignment:

```text
PDC-Sp24-BSCS23023-Basit
```

Every response returns the required header:

```text
X-Student-ID: BSCS23023
```

## Chosen Part 3 Fix

This implementation fixes the synchronization problem with optimistic locking.
Every document has a `version`. Clients must send the version they read in the
`If-Match` header when editing. If another user already updated the document, the
server rejects the stale write with `409 Conflict` instead of silently overwriting
someone else's work.

## Run the API

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Useful endpoints:

```text
POST /reset
GET /documents/shared-notes
PUT /naive/documents/shared-notes
PUT /documents/shared-notes
```

Example protected update:

```bash
curl -X PUT http://127.0.0.1:8000/documents/shared-notes \
  -H "Content-Type: application/json" \
  -H "If-Match: 1" \
  -d "{\"content\":\"Updated notes\"}"
```

## Run the Tests

```bash
pytest -q
```

The tests demonstrate:

- the custom `X-Student-ID` middleware header is present;
- the naive endpoint loses one user's update;
- the fixed endpoint allows one concurrent update and rejects the stale update.
