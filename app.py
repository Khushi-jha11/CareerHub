"""
CareerHub - an AI-assisted job application tracker.

Run locally:
    pip install -r requirements.txt
    flask --app app run --debug
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from extensions import db, login_manager
from matcher import match_resume_to_job
from models import STAGES, Application, ResumeVersion, User

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'careerhub.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # -- auth --------------------------------------------------------------

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("All fields are required.", "error")
                return render_template("signup.html")

            if len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
                return render_template("signup.html")

            if User.query.filter_by(username=username).first():
                flash("That username is already taken.", "error")
                return render_template("signup.html")

            if User.query.filter_by(email=email).first():
                flash("An account with that email already exists.", "error")
                return render_template("signup.html")

            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Welcome to CareerHub! Your account is ready.", "success")
            return redirect(url_for("dashboard"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            identifier = request.form.get("identifier", "").strip().lower()
            password = request.form.get("password", "")

            user = User.query.filter(
                (db.func.lower(User.username) == identifier) | (User.email == identifier)
            ).first()

            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))

            flash("Incorrect username/email or password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You've been logged out.", "info")
        return redirect(url_for("login"))

    # -- dashboard -----------------------------------------------------------

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        apps = Application.query.filter_by(user_id=current_user.id).all()

        status_counts = Counter(a.status for a in apps)
        status_data = {stage: status_counts.get(stage, 0) for stage in STAGES}

        total = len(apps)
        interviewing_or_better = sum(
            1 for a in apps if a.status in ("Interview", "Offer")
        )
        response_rate = round(
            (interviewing_or_better / total * 100) if total else 0, 1
        )

        avg_match = None
        scored = [a.match_score for a in apps if a.match_score is not None]
        if scored:
            avg_match = round(sum(scored) / len(scored), 1)

        recent = sorted(apps, key=lambda a: a.last_updated, reverse=True)[:5]

        return render_template(
            "dashboard.html",
            total=total,
            status_data=status_data,
            response_rate=response_rate,
            avg_match=avg_match,
            recent=recent,
            stages=STAGES,
        )

    # -- applications --------------------------------------------------------

    @app.route("/applications")
    @login_required
    def applications():
        status_filter = request.args.get("status", "all")
        query = Application.query.filter_by(user_id=current_user.id)
        if status_filter != "all":
            query = query.filter_by(status=status_filter)
        apps = query.order_by(Application.last_updated.desc()).all()
        return render_template(
            "applications.html", apps=apps, stages=STAGES, active_filter=status_filter
        )

    @app.route("/applications/new", methods=["GET", "POST"])
    @login_required
    def new_application():
        if request.method == "POST":
            company = request.form.get("company", "").strip()
            role = request.form.get("role", "").strip()
            job_description = request.form.get("job_description", "").strip()
            job_url = request.form.get("job_url", "").strip()
            applied_date_str = request.form.get("applied_date", "")

            if not company or not role:
                flash("Company and role are required.", "error")
                return render_template("add_application.html", stages=STAGES)

            try:
                applied_date = (
                    datetime.strptime(applied_date_str, "%Y-%m-%d").date()
                    if applied_date_str
                    else date.today()
                )
            except ValueError:
                applied_date = date.today()

            app_obj = Application(
                user_id=current_user.id,
                company=company,
                role=role,
                job_description=job_description,
                job_url=job_url,
                applied_date=applied_date,
                status="Applied",
            )

            # Auto-score against the user's most recent saved resume, if any
            latest_resume = (
                ResumeVersion.query.filter_by(user_id=current_user.id)
                .order_by(ResumeVersion.created_at.desc())
                .first()
            )
            if latest_resume and job_description:
                result = match_resume_to_job(latest_resume.content, job_description)
                app_obj.match_score = result.score
                app_obj.matched_skills = ", ".join(result.matched_skills)
                app_obj.missing_skills = ", ".join(result.missing_skills)

            db.session.add(app_obj)
            db.session.commit()
            flash(f"Added application to {company}.", "success")
            return redirect(url_for("applications"))

        return render_template("add_application.html", stages=STAGES)

    @app.route("/applications/<int:app_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_application(app_id: int):
        app_obj = Application.query.filter_by(
            id=app_id, user_id=current_user.id
        ).first_or_404()

        if request.method == "POST":
            app_obj.company = request.form.get("company", app_obj.company).strip()
            app_obj.role = request.form.get("role", app_obj.role).strip()
            app_obj.status = request.form.get("status", app_obj.status)
            app_obj.job_url = request.form.get("job_url", app_obj.job_url).strip()
            app_obj.notes = request.form.get("notes", app_obj.notes).strip()
            app_obj.job_description = request.form.get(
                "job_description", app_obj.job_description
            ).strip()
            db.session.commit()
            flash("Application updated.", "success")
            return redirect(url_for("applications"))

        return render_template("edit_application.html", app=app_obj, stages=STAGES)

    @app.route("/applications/<int:app_id>/delete", methods=["POST"])
    @login_required
    def delete_application(app_id: int):
        app_obj = Application.query.filter_by(
            id=app_id, user_id=current_user.id
        ).first_or_404()
        db.session.delete(app_obj)
        db.session.commit()
        flash("Application deleted.", "info")
        return redirect(url_for("applications"))

    # -- resume analyzer ------------------------------------------------------

    @app.route("/analyzer", methods=["GET", "POST"])
    @login_required
    def analyzer():
        result = None
        resume_text = ""
        job_description = ""

        if request.method == "POST":
            resume_text = request.form.get("resume_text", "").strip()
            job_description = request.form.get("job_description", "").strip()
            save_resume = request.form.get("save_resume") == "on"

            if not resume_text or not job_description:
                flash("Paste both your resume text and the job description.", "error")
            else:
                result = match_resume_to_job(resume_text, job_description)
                if save_resume:
                    resume = ResumeVersion(
                        user_id=current_user.id,
                        label=f"Resume saved {datetime.utcnow():%Y-%m-%d %H:%M}",
                        content=resume_text,
                    )
                    db.session.add(resume)
                    db.session.commit()
                    flash("Resume saved for future auto-matching.", "success")

        saved_resumes = (
            ResumeVersion.query.filter_by(user_id=current_user.id)
            .order_by(ResumeVersion.created_at.desc())
            .all()
        )

        return render_template(
            "analyzer.html",
            result=result,
            resume_text=resume_text,
            job_description=job_description,
            saved_resumes=saved_resumes,
        )


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
