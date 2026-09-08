# Job Marketplace API

A backend service for a small job marketplace — employers post jobs,
candidates apply to them. Built with FastAPI, kept intentionally small.

## Why it's built this way

The brief was pretty open about tech choices, so I went with Python and
FastAPI because it gets validation, error handling, and interactive docs
almost for free, which meant I could spend my time on the actual design
(the data model, the business rules, the API shape) instead of on
plumbing.

Storage is just two Python dictionaries in memory. That was a deliberate
call, not a shortcut I ran out of time to fix — the brief says in-memory
storage is fine, and keeping it simple here meant every layer above it
(the endpoint logic, the validation, the error handling) still looks
exactly like it would on top of a real database. If this needed to go
further, the only file that would change is the "storage" section near
the top of `app.py` — everything else already treats it as a black box.

## Getting it running

```bash
pip install -r requirements.txt
uvicorn app:app
```

Windows users: if `pip`/`uvicorn` on your machine don't point at the
Python you expect (this tripped me up too, if you've got more than one
Python install floating around — MSYS2, WSL, the Windows Store version,
etc.), use `py -m pip install -r requirements.txt` and `py -m uvicorn
app:app` instead. The `py` launcher is more reliable about finding your
actual Windows Python.

Once it's running, open **http://127.0.0.1:8000/docs**. That's not a
frontend I built — it's FastAPI generating an interactive page directly
from the code, and it's a normal, legitimate way to exercise a backend
API without writing a client for it. Expand an endpoint, hit "Try it
out," fill in the fields, hit "Execute." You're sending a real request
to your own running server and seeing the real response.

A good order to try things in:

1. `POST /jobs` — create a job, copy the `id` it gives you back.
2. `GET /jobs/{job_id}` — confirm it's there.
3. `GET /jobs` — see it in the full list; try `?status=OPEN` to filter.
4. `POST /jobs/{job_id}/applications` — apply to it with a name and email.
5. `GET /jobs/{job_id}/applications` — see the application show up.
6. `POST /jobs/{job_id}/close` — close the job.
7. Try step 4 again on that same job. You should get `409 Conflict` this
   time — that's the "closed jobs stop accepting applications" rule
   actually being enforced, not just described in a comment somewhere.

## Running the tests
 
```bash
pytest
```
 
(Windows: `py -m pytest`, for the same reason as above.)
 
A successful run looks like this:
 
```
============================= test session starts ==============================
collected 16 items
 
test_app.py ................                                          [100%]
 
============================== 16 passed in 0.31s ===============================
```
 
Each dot is one passing test. If something fails, a dot turns into an
`F` and pytest prints exactly which assertion failed and why — the line
starting with `FAILED test_app.py::...` tells you which test broke.
 
`test_app.py` covers every endpoint's happy path plus the error cases —
missing job (`404`), closed job rejecting an application (`409`), bad
input (`422`) — and `conftest.py` resets the in-memory storage before
each test so they don't interfere with each other.

## What's in `app.py`

One file, organized in the order a request actually moves through it:

- **Data models** — what a request body has to look like, and what a
  response looks like. I split each resource into a `...Create` version
  (only what a client is allowed to send) and a full version (adds the
  fields the server generates — `id`, `status`, timestamps). That split
  is what stops a client from, say, setting their own job status to
  `OPEN` on creation — the field simply isn't in the model they're
  allowed to send.
- **Storage** — the two dictionaries mentioned above.
- **Job endpoints** — create, get one, list (with a status filter),
  close.
- **Application endpoints** — submit, list for a given job.

Everything's kept in one file on purpose — for a project this size, I'd
rather it read start to finish than be split across folders you have to
jump between. 

## A few decisions worth explaining

**Closing a job is idempotent.** Closing an already-closed job just
returns it as-is (`200`), rather than erroring. If a client's intent is
"make sure this job is closed," retrying that call shouldn't punish them
for it.

**IDs are UUIDs, not auto-incrementing numbers.** Mostly future-proofing
— it means nothing ever needs a shared counter to hand out the next id,
which starts to matter the moment there's a real database or more than
one server involved.

**Validation happens before your code even runs.** `candidate_email` is
typed as an actual email field, not just a string — send something that
isn't a valid email and FastAPI rejects it with a `422` automatically,
which is one less thing to check by hand inside the function.

## If this were going to production

A few things I'd tackle first, roughly in order of how soon they'd
matter: a real database behind the storage layer, authentication (so
only the employer who posted a job can close it), pagination on the list
endpoints, and stopping the same email from applying to the same job
twice.
