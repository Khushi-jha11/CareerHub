import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SECRET_KEY"] = "test-secret"

    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False

    yield application

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, username="jane", email="jane@example.com", password="secret123"):
    return client.post(
        "/signup",
        data={"username": username, "email": email, "password": password},
        follow_redirects=True,
    )


def test_signup_creates_user_and_redirects_to_dashboard(client):
    response = signup(client)
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_duplicate_username_rejected(client):
    signup(client)
    client.get("/logout")
    response = signup(client, email="other@example.com")
    assert b"already taken" in response.data


def test_login_with_wrong_password_fails(client):
    signup(client)
    client.get("/logout")
    response = client.post(
        "/login",
        data={"identifier": "jane", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert b"Incorrect username" in response.data


def test_add_application_requires_login(client):
    response = client.get("/applications/new", follow_redirects=True)
    assert b"Please log in" in response.data


def test_add_and_view_application(client):
    signup(client)
    response = client.post(
        "/applications/new",
        data={
            "company": "Acme Corp",
            "role": "Backend Engineer",
            "job_description": "Looking for Python, Flask, and SQL experience.",
            "job_url": "",
            "applied_date": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Acme Corp" in response.data


def test_dashboard_shows_pipeline_stages(client):
    signup(client)
    response = client.get("/dashboard")
    assert b"Applied" in response.data
    assert b"Interview" in response.data


def test_resume_matcher_scores_overlap(client):
    signup(client)
    response = client.post(
        "/analyzer",
        data={
            "resume_text": "Experienced with Python, Flask, SQL, and Docker.",
            "job_description": "We need someone skilled in Python and SQL.",
        },
        follow_redirects=True,
    )
    assert b"match score" in response.data
    assert b"python" in response.data.lower()
