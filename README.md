# CareerHub

An AI-assisted job application tracker. Track every application through
its pipeline (Applied → Screening → Interview → Offer/Rejected), and
score how well your resume matches a job description before you apply.

## Features

- **Authentication** — signup/login with hashed passwords (Flask-Login)
- **Application tracker** — add, edit, delete, and filter applications by stage
- **Dashboard** — total applications, response rate, average resume match, and a pipeline view of how many applications sit at each stage
- **Resume ↔ job matcher** — paste a resume and job description to get a match score, matched skills, and missing skills, using a curated skills vocabulary (no external API keys needed)
- **Auto-matching** — save a resume once, and every new application you log is automatically scored against it if you include a job description

## Tech stack

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** SQLite (zero setup — a `careerhub.db` file is created automatically)
- **Frontend:** Server-rendered Jinja2 templates, hand-written CSS (no framework)
- **Tests:** pytest

## Getting started

```bash
git clone https://github.com/yourusername/careerhub.git
cd careerhub
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt

flask --app app run --debug
```

Then open **http://127.0.0.1:5000** in your browser, sign up, and start tracking.

### Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask session signing key — set a real random value in production |
| `DATABASE_URL` | `sqlite:///careerhub.db` | SQLAlchemy database URI — point this at Postgres/MySQL in production |

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Project structure

```
careerhub/
├── app.py                  # Flask app factory + all routes
├── models.py                # User, Application, ResumeVersion (SQLAlchemy)
├── extensions.py             # db / login_manager instances
├── matcher.py                # resume <-> job description matching logic
├── templates/                # Jinja2 templates
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── applications.html
│   ├── add_application.html
│   ├── edit_application.html
│   └── analyzer.html
├── static/css/style.css      # design system (see below)
├── tests/test_app.py          # pytest suite
├── requirements.txt
├── .gitignore
└── LICENSE
```

## How the resume matcher works

`matcher.py` compares the resume text and job description against a
curated vocabulary of ~60 common technical/professional skills (Python,
React, Docker, Agile, communication, etc.), plus a smaller secondary
signal from generic keyword overlap. It returns:

- an overall **match score** (0–100%)
- the list of **matched skills** found in both texts
- the list of **missing skills** — present in the job description but not the resume

This is intentionally dependency-free (no external ML API or model
weights), which keeps the project deployable anywhere with zero API
keys — but the design leaves room to swap in a real embeddings-based
model (e.g. sentence-transformers, or an LLM call) later without
touching any other part of the app; `matcher.py` is the single place
that would need to change.

## Deploying

This is a standard Flask + SQLAlchemy app, so it deploys cleanly to
Render, Railway, Fly.io, or a small VPS. For production:

1. Set `SECRET_KEY` to a real random value
2. Point `DATABASE_URL` at Postgres (SQLite is fine for demos, but doesn't handle concurrent writes well)
3. Run with a production WSGI server, e.g. `gunicorn app:app`

## License

MIT — see [LICENSE](LICENSE).
