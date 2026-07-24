"""
Database models for CareerHub.
"""

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

STAGES = ["Applied", "Screening", "Interview", "Offer", "Rejected"]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship(
        "Application", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    resumes = db.relationship(
        "ResumeVersion", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    job_description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="Applied")
    job_url = db.Column(db.String(300), default="")
    notes = db.Column(db.Text, default="")

    match_score = db.Column(db.Float, nullable=True)
    matched_skills = db.Column(db.Text, default="")
    missing_skills = db.Column(db.Text, default="")

    applied_date = db.Column(db.Date, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def status_index(self) -> int:
        try:
            return STAGES.index(self.status)
        except ValueError:
            return 0


class ResumeVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    label = db.Column(db.String(120), default="My resume")
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
